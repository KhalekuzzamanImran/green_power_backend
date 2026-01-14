import itertools
import threading
import socket
import struct
import logging
import pymongo
import sys
import os
import django
from typing import List, Tuple, Dict
from datetime import datetime, timezone
from pathlib import Path
from django.apps import apps

from config.mongodb import MongoDBClient

# Constants
HEARTBEAT_PACKET: bytes = b"GWCCCL0001"
RESPONSE_PACKETS: List[bytes] = [
    bytes.fromhex("01 26 00 00 00 06 01 03 0B B7 00 0A"),
    bytes.fromhex("01 6E 00 00 00 06 01 03 0B ED 00 06"),
    bytes.fromhex("01 B6 00 00 00 06 01 03 0C 83 00 08"),
]
RECV_BUFFER_SIZE: int = 1024
CLIENT_TIMEOUT: int = 120  # seconds

log = logging.getLogger(__name__)
if not log.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_django() -> None:
    if apps.ready:
        return

    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(base_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        django.setup()
    except Exception:
        log.exception("Failed to set up Django")
        raise


setup_django()


class TCPSocketServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 6000,
        heartbeat_packet: bytes = HEARTBEAT_PACKET,
        response_packets: List[bytes] = RESPONSE_PACKETS,
    ):
        self.host = host
        self.port = port
        self.heartbeat_packet = heartbeat_packet
        self.response_packets = response_packets
        self.response_cycle = itertools.cycle(enumerate(self.response_packets))
        self.cycle_lock = threading.Lock()
        self.mongodb = MongoDBClient.require_db()
        self.collections = {
            "solar_data": self.mongodb["solar_data"],
            "today_solar_data": self.mongodb["today_solar_data"],
            "current_month_solar_data": self.mongodb["current_month_solar_data"],
        }
        self.mongo_lock = threading.Lock()

    def _store_data(self, data: Dict[str, List[float]], client_id: str) -> None:
        """Store data with thread-safe MongoDB operations."""
        if len(data) != 3:
            return

        now = datetime.now(timezone.utc)

        document = {
            "timestamp": now,
            "client_id": client_id,
            "current": data.get("response_0", []),
            "power": data.get("response_1", []),
            "energy_consumption": data.get("response_2", []),
        }

        try:
            with self.mongo_lock:
                self.collections["solar_data"].insert_one(document)
                self.collections["today_solar_data"].insert_one(document)
                self.collections["current_month_solar_data"].insert_one(document)

            log.info(f"[+] Data stored in all MongoDB collections for {client_id} at {now}")

        except pymongo.errors.PyMongoError as e:
            log.error(f"[!] MongoDB error for {client_id}: {e}")

    def _process_response(self, index: int, hex_response: str) -> List[float]:
        """Process the hex response with validation."""
        if "0103" not in hex_response:
            return []

        try:
            _, payload = hex_response.split("0103", 1)
            payload = payload[2:]

            chunk_size = 16 if index == 2 else 8
            if len(payload) % chunk_size != 0:
                log.warning(f"[!] Invalid payload length {len(payload)}")
                return []

            chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]

            converted_values = []
            for chunk in chunks:
                try:
                    value = struct.unpack("!f" if chunk_size == 8 else "!q", bytes.fromhex(chunk))[0]
                    converted_values.append(float(value))
                except (struct.error, ValueError) as e:
                    log.warning(f"[!] Data unpacking error: {e}")

            return converted_values

        except Exception as e:
            log.warning(f"[!] Processing error: {e}")
            return []

    def handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]) -> None:
        """Handles a single client connection."""
        client_id = f"{addr[0]}:{addr[1]}"
        accumulated_data = {}

        with client_socket:
            client_socket.settimeout(CLIENT_TIMEOUT)

            try:
                while True:
                    data = client_socket.recv(RECV_BUFFER_SIZE)
                    if not data:
                        log.info(f"[-] Client disconnected: {client_id}")
                        break

                    log.debug(f"[←] Heartbeat received from {client_id}: {data}")

                    if data == self.heartbeat_packet:
                        with self.cycle_lock:
                            index, response_packet = next(self.response_cycle)

                        log.debug(f"[→] Sending response #{index} to {client_id}")
                        client_socket.sendall(response_packet)

                        try:
                            response = client_socket.recv(RECV_BUFFER_SIZE)
                            if not response:
                                log.warning(f"[-] Client {client_id} disconnected after response")
                                break

                            hex_response = response.hex().upper()
                            log.debug(f"[←] Response from {client_id}: {hex_response}")
                            values = self._process_response(index, hex_response)
                            if values:
                                accumulated_data[f"response_{index}"] = values
                                if len(accumulated_data) == 3:
                                    self._store_data(accumulated_data, client_id)
                                    accumulated_data = {}

                        except (socket.timeout, socket.error):
                            log.warning(f"[!] Timeout waiting for response from {client_id}")
                            break
                    else:
                        log.warning(f"[!] Unrecognized packet from {client_id}: {data}")

            except socket.timeout:
                log.warning(f"[!] Connection timeout with {client_id} ({CLIENT_TIMEOUT}s inactivity)")
            except (socket.error, ConnectionResetError, BrokenPipeError):
                log.error(f"[!] Connection lost with {client_id}")
            except Exception as e:
                log.exception(f"[!] Error handling {client_id}: {e}")

    def start_server(self) -> None:
        """Starts the TCP server and listens for connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(50)
            log.info(f"[*] Server listening on {self.host}:{self.port}")

            try:
                while True:
                    client_socket, addr = server_socket.accept()
                    log.info(f"[+] New connection from {addr[0]}:{addr[1]}")
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True,
                    ).start()
            except KeyboardInterrupt:
                log.info("\n[*] Server shutdown requested. Exiting gracefully...")
            except Exception as e:
                log.exception(f"[!] Server error: {e}")


def main() -> None:
    try:
        server = TCPSocketServer()
    except RuntimeError as exc:
        log.critical(str(exc))
        sys.exit(1)
    server.start_server()


if __name__ == "__main__":
    main()
