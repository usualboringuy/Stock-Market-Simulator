from typing import List, Dict, Any, Optional, cast
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from src.config import Config
from src.logger import get_logger

logger = get_logger("mongo")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None
_quotes: Optional[Collection] = None


def init_mongo() -> None:
    global _client, _db, _quotes
    if _client is not None:
        return
    _client = MongoClient(Config.MONGODB_URL)
    _db = cast(Database, _client[Config.DATABASE_NAME])
    _quotes = cast(Collection, _db[Config.QUOTES_COLLECTION])
    _quotes.create_index(
        [("symbol", ASCENDING), ("timestamp", ASCENDING)], background=True
    )
    _quotes.create_index(
        [("token", ASCENDING), ("timestamp", ASCENDING)], background=True
    )
    logger.info(
        "Mongo initialized with DB=%s, collection=%s",
        Config.DATABASE_NAME,
        Config.QUOTES_COLLECTION,
    )


def get_quotes_collection() -> Collection:
    global _quotes
    if _quotes is None:
        init_mongo()
    if _quotes is None:
        raise RuntimeError("Quotes collection not initialized")
    return _quotes


def insert_many_quotes(docs: List[Dict[str, Any]]) -> None:
    if not docs:
        return
    col = get_quotes_collection()
    try:
        col.insert_many(docs, ordered=False)
        logger.info("Inserted %d quotes", len(docs))
    except PyMongoError as e:
        logger.error("Mongo insert_many failed: %s", str(e))


def insert_quote(doc: Dict[str, Any]) -> None:
    col = get_quotes_collection()
    try:
        col.insert_one(doc)
    except PyMongoError as e:
        logger.error("Mongo insert_one failed: %s", str(e))
