import itertools
import threading
import socket
from typing import List, Tuple

# Constants
HEARTBEAT_PACKET: bytes = b'GWCCCL0001'
RESPONSE_PACKETS: List[bytes] = [
    bytes.fromhex("01 26 00 00 00 06 01 03 0B B7 00 0A"),
    bytes.fromhex("01 6E 00 00 00 06 01 03 0B ED 00 06"),
    bytes.fromhex("01 B6 00 00 00 06 01 03 0C 83 00 08"),
]

class TCPSocketServer:
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 6000,
        heartbeat_packet: bytes = HEARTBEAT_PACKET,
        response_packets: List[bytes] = RESPONSE_PACKETS
    ):
        self.host = host
        self.port = port
        self.heartbeat_packet = heartbeat_packet
        self.response_packets = response_packets
        self.response_cycle = itertools.cycle(enumerate(self.response_packets))
        self.cycle_lock = threading.Lock()

    def handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]) -> None:
        """Handles a single client's communication."""
        client_id = f"{addr[0]}:{addr[1]}"
        print(f"[+] Connected: {client_id}")
        client_socket.settimeout(120)

        try:
            # Step 1: Expect heartbeat
            data = client_socket.recv(1024)
            if data != self.heartbeat_packet:
                print(f"[!] Invalid heartbeat from {client_id}: {data}")
                return
            print(f"[✓] Valid heartbeat from {client_id}")

            # Step 2: Begin response loop
            while True:
                with self.cycle_lock:
                    index, packet = next(self.response_cycle)

                try:
                    client_socket.sendall(packet)
                    print(f"[→] Sent response #{index} to {client_id}")
                except socket.error as e:
                    print(f"[!] Send error to {client_id}: {e}")
                    break

                try:
                    response = client_socket.recv(1024)
                    if not response:
                        print(f"[-] {client_id} closed connection")
                        break
                    print(f"[←] Received from {client_id}: {response.hex().upper()}")
                except socket.timeout:
                    print(f"[!] Timeout from {client_id}")
                    break

        except (socket.timeout, socket.error, ConnectionResetError) as e:
            print(f"[!] Connection issue with {client_id}: {e}")
        finally:
            client_socket.close()
            print(f"[-] Disconnected: {client_id}")

    def start_server(self) -> None:
        """Starts the threaded TCP server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(50)
            print(f"[*] Server running on {self.host}:{self.port}")

            try:
                while True:
                    client_socket, addr = server_socket.accept()
                    print(f"[+] Incoming connection from {addr[0]}:{addr[1]}")
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    ).start()
            except KeyboardInterrupt:
                print("\n[*] Server interrupted. Shutting down...")
            except Exception as e:
                print(f"[!] Server error: {e}")
