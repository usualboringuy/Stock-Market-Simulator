"""
MongoDB Handler: manages connection and collections with .env loading
"""

import logging
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class MongoHandler:
    def __init__(self):
        load_dotenv()
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """Establish MongoDB connection"""
        user = os.getenv("MONGO_USERNAME")
        password = os.getenv("MONGO_PASSWORD")
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        db_name = os.getenv("DATABASE_NAME", "stock_simulator")

        if user and password:
            user_enc = quote_plus(user)
            pass_enc = quote_plus(password)
            uri = f"mongodb://{user_enc}:{pass_enc}@{host}:{port}/{db_name}?authSource=admin"
        else:
            uri = f"mongodb://{host}:{port}/"

        try:
            self.client = MongoClient(uri)
            self.db = self.client[db_name]
            self.db.command("ping")  # Test connection
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def get_collection(self, name):
        """Get MongoDB collection, raising if DB is not connected"""
        if self.db is None:
            raise RuntimeError("MongoDB not connected")
        return self.db[name]

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
