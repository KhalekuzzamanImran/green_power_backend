import os
import sys
import json
import logging
import time
import signal
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from paho.mqtt import client as mqtt_client
from queue import Queue, Full, Empty

# ─────── Load Environment Variables ───────
load_dotenv()

# ─────── Constants ───────
DEFAULT_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 60
QUEUE_TIMEOUT = 1
QUEUE_MAX_SIZE = 1000

# ─────── Django Setup ───────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'green_power_backend.settings')

import django
django.setup()

# ─────── log Setup ───────
log = logging.getLogger('subscriber')

# Fallback for standalone script runs
if not log.hasHandlers():
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s %(name)s - %(message)s'
    )

# ─────── MQTT Configuration ───────
class MQTTConfig:
    """
    Loads and stores MQTT broker configuration from environment variables.
    """

    def __init__(self):
        self.broker: str = os.getenv('MQTT_BROKER', 'localhost')
        self.port: int = int(os.getenv('MQTT_PORT', 1883))
        self.username: str = os.getenv('MQTT_USERNAME')
        self.password: str = os.getenv('MQTT_PASSWORD')
        self.keepalive: int = int(os.getenv('MQTT_KEEPALIVE', 60))
        self.topics: List[str] = self._parse_topics(os.getenv('MQTT_TOPICS', '[]'))

        # log.info(
        #     f"[MQTTConfig] Initialized: broker={self.broker}, port={self.port}, "
        #     f"keepalive={self.keepalive}, topics={self.topics}"
        # )

    def _parse_topics(self, topics_str: str) -> List[str]:
        """
        Parses a JSON-formatted list of strings representing MQTT topics.
        """
        try:
            topics = json.loads(topics_str)
            if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                return topics
        except (json.JSONDecodeError, TypeError):
            log.exception("Failed to parse MQTT_TOPICS.")

        log.error("Invalid MQTT_TOPICS format. Must be a JSON array of strings.")
        return []


# ─────── MQTT Subscriber ───────
class MQTTSubscriber:
    def __init__(self, config: MQTTConfig):
        self.config = config
        self.client = self._init_mqtt_client()
        self.connected = False
        self.should_reconnect = True
        self.reconnect_delay = DEFAULT_RECONNECT_DELAY
        self.message_queue = Queue(maxsize=QUEUE_MAX_SIZE)

    def _init_mqtt_client(self) -> mqtt_client.Client:
        client = mqtt_client.Client(
            client_id=f"mqtt-subscriber-{time.time_ns()}",
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2
        )

        if self.config.username and self.config.password:
            client.username_pw_set(self.config.username, self.config.password)

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        return client

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.connected = True
            self.reconnect_delay = DEFAULT_RECONNECT_DELAY
            log.info("Connected to MQTT broker.")

            for topic in self.config.topics:
                try:
                    client.subscribe(topic)
                    log.info(f"Subscribed to topic: {topic}")
                except Exception as e:
                    log.error(f"Failed to subscribe to topic {topic}: {e}")
        else:
            log.error(f"Failed to connect to MQTT broker (code: {reason_code})")

    def _on_disconnect(self, client, userdata, reason_code, properties=None):
        self.connected = False
        log.warning(f"Disconnected from MQTT broker (code: {reason_code})")

        if self.should_reconnect:
            self._reconnect()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            log.info(f"Received message on topic '{msg.topic}': {payload}")
            self.message_queue.put_nowait(payload)
        except json.JSONDecodeError:
            log.error(f"Invalid JSON in message from topic '{msg.topic}'")
        except Full:
            log.error("Message queue is full; dropping incoming message.")
        except Exception as e:
            log.exception(f"Unexpected error handling message: {e}")

    def _reconnect(self):
        while not self.connected and self.should_reconnect:
            log.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            try:
                self.client.reconnect()
                log.info("Reconnect successful.")
            except Exception as e:
                log.error(f"Reconnect failed: {e}")
            self.reconnect_delay = min(self.reconnect_delay * 2, MAX_RECONNECT_DELAY)

    def connect(self):
        try:
            self.client.connect_async(self.config.broker, self.config.port, self.config.keepalive)
            self.client.loop_start()
            log.info("MQTT Subscriber started.")
        except Exception as e:
            log.exception("Initial connection failed.")
            raise

    def disconnect(self):
        self.should_reconnect = False
        self.client.disconnect()
        self.client.loop_stop()
        log.info("MQTT Subscriber stopped.")


def main():
    subscriber = MQTTSubscriber(MQTTConfig())

    def shutdown_handler(signum, frame):
        log.info("Shutting down gracefully...")
        subscriber.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    subscriber.connect()   

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler(None, None)
    

# ─────── Entry Point ───────
if __name__ == '__main__':
    main()