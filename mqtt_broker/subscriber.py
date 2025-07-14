import os
import sys
import json
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# ─────── Load Environment Variables ───────
load_dotenv()

# ─────── Django Setup ───────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'green_power_backend.settings')

import django
django.setup()

# ─────── Logger Setup ───────
logger = logging.getLogger('subscriber')

# Fallback for standalone script runs
if not logger.hasHandlers():
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

        logger.info(
            f"[MQTTConfig] Initialized: broker={self.broker}, port={self.port}, "
            f"keepalive={self.keepalive}, topics={self.topics}"
        )

    def _parse_topics(self, topics_str: str) -> List[str]:
        """
        Parses a JSON-formatted list of strings representing MQTT topics.
        """
        try:
            topics = json.loads(topics_str)
            if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                return topics
        except (json.JSONDecodeError, TypeError):
            logger.exception("Failed to parse MQTT_TOPICS.")

        logger.error("Invalid MQTT_TOPICS format. Must be a JSON array of strings.")
        return []

# ─────── Entry Point ───────
if __name__ == '__main__':
    config = MQTTConfig()
