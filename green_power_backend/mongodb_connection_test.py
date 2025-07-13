import os
import sys
from pathlib import Path

# Configure Django settings
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # Add project root to sys.path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "green_power_backend.settings")

from green_power_backend.mongodb import MongoDBClient  

def main():
    db = MongoDBClient.get_db()
    if db is not None:
        print("✅ MongoDB connected.")
    else:
        print("❌ MongoDB connection failed.")


if __name__ == "__main__":
    main()
