import os
import sys
import json
import logging
import time
import signal
import threading
import django
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from paho.mqtt import client as mqtt_client
from queue import Queue, Full, Empty
from datetime import datetime, timezone
from pydantic import ValidationError
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# ─────── Load Environment Variables ───────
load_dotenv()

# ─────── Django Setup ───────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'green_power_backend.settings')

try:
    django.setup()
except Exception:
    logging.exception("Failed to set up Django")
    sys.exit(1)

from green_power_backend.mongodb import MongoDBClient
from grid.models import RTDataModel, ENYNowDataModel
from generator.models import GeneratorDataModel
from environment.models import EnvironmentDataModel

# ─────── Constants ───────
DEFAULT_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 60
QUEUE_TIMEOUT = 1
QUEUE_MAX_SIZE = 1000

TOPIC_MAPPING = {
    "MQTT_RT_DATA": (RTDataModel, "grid_rt_data"),
    "MQTT_ENY_NOW": (ENYNowDataModel, "grid_eny_now"),
}

ENV_TOPIC = "CCCL/PURBACHAL/ENV_01"
GEN_TOPIC = "CCCL/PURBACHAL/ENM_01"
GEN_COLLECTION = "generator_data"
ENV_COLLECTION = "environment_data"
REALTIME_GROUP = "realtime_updates"

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
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.mongodb = MongoDBClient().get_db()
        self.channel_layer = get_channel_layer()

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

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self.connected = False
        log.warning(f"Disconnected from MQTT broker (code: {reason_code})")

        if self.should_reconnect:
            self._reconnect()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            log.info(f"Received message on topic '{msg.topic}': {payload}")
            self.message_queue.put_nowait((msg.topic, payload))
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

    def _send_realtime_data(self, topic: str, data: Dict[str, Any]) -> None:
        try:
            async_to_sync(self.channel_layer.group_send)(
                REALTIME_GROUP,
                {
                    'type': 'send.update',
                    'data': {
                        'topic': topic,
                        'payload': data,
                    }
                }
            )
            log.info(f"Message successfully broadcast to group '{REALTIME_GROUP}' on topic '{topic}'")
        except Exception as e:
            log.error(f"WebSocket push failed: {e}")

    # ─────── Message Handling ───────
    def _handle_env_data(self, topic: str, payload: Dict[str, Any]):
        payload['timestamp'] = datetime.now(timezone.utc)
        
        try:
            validated = EnvironmentDataModel(**payload)
            self.mongodb[ENV_COLLECTION].insert_one(payload.copy())
            log.info(f"{topic} inserted into MongoDB")
            self._send_realtime_data(topic, validated.model_dump(mode="json"))  # Only pushed if insert succeeds
        except Exception as e:
            log.error(f"{topic} insert or validation failed: {e}")

    def _handle_generator_data(self, topic: str, payload: Dict[str, Any]):
        session = self.session_data.setdefault(topic, {})
        
        try:
            data_point = payload.get("data", [{}])[0]
            if not data_point:
                return

            timestamp = data_point.get("tp")
            points = {str(p["id"]): p["val"] for p in data_point.get("point", [])}
            doc = {"timestamp": timestamp, **points}

            if session.get("timestamp") == timestamp:
                session.update(doc)
                session["device_id"] = session.pop("0", None)

                data_to_insert = session.copy()

                try:
                    validated = GeneratorDataModel.from_flat_dict(data_to_insert)
                except ValidationError as ve:
                    log.error(f"Validation error for topic {topic}: {ve}")
                    session.clear()
                    return

                self.mongodb[GEN_COLLECTION].insert_one(data_to_insert)
                log.info(f"{topic} inserted into MongoDB.")
                self._send_realtime_data(topic, validated.model_dump(mode='json'))
                session.clear()
            else:
                session.update(doc)

        except Exception as e:
            log.error(f"{topic} insert or processing error: {e}")
            session.clear()


    def _handle_grid_data(self, topic: str, payload: Dict[str, Any]):
        model_class, collection = TOPIC_MAPPING[topic]
        session = self.session_data.setdefault(topic, {})
        session.update(payload)

        if payload.get('isend') == '1':
            try:
                session['device_id'] = session.pop('id')
                session['timestamp'] = datetime.now(timezone.utc)
                validated = model_class(**session)
                self.mongodb[collection].insert_one(session.copy())
                log.info(f"{topic} inserted into MongoDB.")
                self._send_realtime_data(topic, validated.model_dump(mode='json'))
            except ValidationError as ve:
                log.error(f"{topic} validation failed: {ve}")
            except Exception as e:
                log.error(f"{topic} insert failed: {e}")
            finally:
                session.clear()

    def _handle_message(self, topic: str, payload: Dict[str, Any]):
        if topic in TOPIC_MAPPING:
            self._handle_grid_data(topic, payload)
        elif topic == ENV_TOPIC:
            self._handle_env_data(topic, payload)
        elif topic == GEN_TOPIC:
            self._handle_generator_data(topic, payload)
        else:
            log.warning(f"Unhandled topic: {topic}")

    def _process_queue(self):
        while True:
            try:
                topic, payload = self.message_queue.get(timeout=QUEUE_TIMEOUT)
                self._handle_message(topic, payload)
            except Empty:
                continue
            except Exception as e:
                log.error(f"Queue processing error: {e}")


    def connect(self):
        try:
            self.client.connect_async(self.config.broker, self.config.port, self.config.keepalive)
            self.client.loop_start()
            threading.Thread(target=self._process_queue, daemon=True).start()
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