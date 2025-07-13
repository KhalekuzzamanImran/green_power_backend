from pymongo import MongoClient, errors
from django.conf import settings

class MongoDBClient:
    _client = None
    _db = None

    @classmethod
    def connect(cls):
        if cls._client and cls._db:
            return cls._db  # Already connected
        
        try:
            mongo_uri = getattr(settings, 'MONGO_DB_URI')
            db_name = getattr(settings, 'MONGO_DB_NAME')

            if not mongo_uri or not db_name:
                raise ValueError("MongoDB URI or DB name not set in settings.")

            cls._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
            cls._client.admin.command('ping')  # Test connection
            cls._db = cls._client[db_name]

            print(f"[MongoDB] Connected to database: {db_name}")
            return cls._db
        except (errors.ConnectionFailure, errors.ServerSelectionTimeoutError) as e:
            print(f"[MongoDB] Connection failed: {e}")
        except Exception as e:
            print(f"[MongoDB] Unexpected error during connection: {e}")

        cls._client = None
        cls._db = None
        return None
    
    @classmethod
    def get_db(cls):
        return cls._db or cls.connect()
    
    @classmethod
    def reconnect(cls):
        print("[MongoDB] Attempting reconnection...")
        cls._client = None
        cls._db = None
        return cls.connect()

