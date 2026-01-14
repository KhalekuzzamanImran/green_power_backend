import logging
from typing import Optional

from django.conf import settings
from pymongo import MongoClient, errors, IndexModel, ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


DEFAULT_INDEXES = {
    "environment_data": [
        IndexModel([("timestamp", DESCENDING)]),
    ],
    "generator_data": [
        IndexModel([("timestamp", DESCENDING)]),
    ],
    "grid_rt_data": [
        IndexModel([("timestamp", DESCENDING)]),
    ],
    "grid_eny_now": [
        IndexModel([("timestamp", DESCENDING)]),
    ],
    "solar_data": [
        IndexModel([("timestamp", DESCENDING), ("client_id", ASCENDING)]),
    ],
    "today_solar_data": [
        IndexModel([("timestamp", DESCENDING)], expireAfterSeconds=86400),
    ],
    "current_month_solar_data": [
        IndexModel([("timestamp", DESCENDING)], expireAfterSeconds=2592000),
    ],
}


class MongoDBClient:
    _client: Optional[MongoClient] = None
    _db = None
    _indexes_ready = False

    @classmethod
    def connect(cls):
        if cls._client and cls._db:
            return cls._db  # Already connected

        try:
            mongo_uri = getattr(settings, 'MONGO_DB_URI')
            db_name = getattr(settings, 'MONGO_DB_NAME')

            if not mongo_uri or not db_name:
                raise ValueError("MongoDB URI or DB name not set in settings.")

            cls._client = MongoClient(
                mongo_uri,
                maxPoolSize=getattr(settings, "MONGO_MAX_POOL_SIZE", 50),
                minPoolSize=getattr(settings, "MONGO_MIN_POOL_SIZE", 0),
                connectTimeoutMS=getattr(settings, "MONGO_CONNECT_TIMEOUT_MS", 2000),
                socketTimeoutMS=getattr(settings, "MONGO_SOCKET_TIMEOUT_MS", 20000),
                serverSelectionTimeoutMS=getattr(settings, "MONGO_SERVER_SELECTION_TIMEOUT_MS", 3000),
                retryWrites=True,
            )
            cls._client.admin.command('ping')  # Test connection
            cls._db = cls._client[db_name]

            logger.info(f"[MongoDB] Connected to database: {db_name}")
            cls._ensure_indexes()
            return cls._db
        except (errors.ConnectionFailure, errors.ServerSelectionTimeoutError) as e:
            logger.critical(f"[MongoDB] Connection failed: {e}")
        except Exception as e:
            logger.critical(f"[MongoDB] Unexpected error during connection: {e}")

        cls._client = None
        cls._db = None
        return None
    
    @classmethod
    def get_db(cls):
        if cls._db is None:
            cls.connect()
        return cls._db

    @classmethod
    def require_db(cls):
        db = cls.get_db()
        if db is None:
            raise RuntimeError("MongoDB connection unavailable.")
        return db
    
    @classmethod
    def reconnect(cls):
        logger.info("[MongoDB] Attempting reconnection...")
        cls._client = None
        cls._db = None
        cls._indexes_ready = False
        return cls.connect()

    @classmethod
    def _ensure_indexes(cls) -> None:
        if cls._indexes_ready:
            return
        if not getattr(settings, "MONGO_CREATE_INDEXES", True):
            return
        if cls._db is None:
            return

        custom_indexes = getattr(settings, "MONGO_INDEXES", None)
        index_map = custom_indexes or DEFAULT_INDEXES

        for collection_name, indexes in index_map.items():
            try:
                cls._db[collection_name].create_indexes(indexes)
            except Exception as exc:
                logger.warning(f"[MongoDB] Index creation failed for {collection_name}: {exc}")

        cls._indexes_ready = True
