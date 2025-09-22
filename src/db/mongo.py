from typing import Optional, Dict, Any, List, cast, Tuple
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.read_preferences import ReadPreference

from typing import List, Dict, Any
from pymongo.errors import PyMongoError
from src.logger import get_logger

from src.config import Config
from src.logger import get_logger

logger = get_logger("mongo")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None

_users: Optional[Collection] = None
_portfolios: Optional[Collection] = None
_trades: Optional[Collection] = None
_quotes: Optional[Collection] = None


def init_mongo() -> None:
    global _client, _db
    if _client is not None:
        return
    _client = MongoClient(Config.MONGODB_URL)
    _db = cast(Database, _client[Config.DATABASE_NAME])
    logger.info("Mongo connected DB=%s", Config.DATABASE_NAME)


def get_client() -> MongoClient:
    global _client
    if _client is None:
        init_mongo()
    assert _client is not None
    return _client


def get_db() -> Database:
    global _db
    if _db is None:
        init_mongo()
    assert _db is not None
    return _db


def get_users_collection() -> Collection:
    global _users
    if _users is None:
        _users = get_db()["users"]
    return _users


def get_portfolios_collection() -> Collection:
    global _portfolios
    if _portfolios is None:
        _portfolios = get_db()["portfolios"]
    return _portfolios


def get_trades_collection() -> Collection:
    global _trades
    if _trades is None:
        _trades = get_db()["trades"]
    return _trades


def get_quotes_collection() -> Collection:
    global _quotes
    if _quotes is None:
        _quotes = get_db()["quotes"]
    return _quotes


logger = get_logger("mongo")


def insert_many_quotes(docs: List[Dict[str, Any]]) -> int:
    """
    Backward-compatible helper for Module 1.
    Inserts multiple quote docs into the quotes collection.
    Returns number of docs attempted (0 if none).
    """
    if not docs:
        return 0
    col = get_quotes_collection()
    try:
        col.insert_many(docs, ordered=False)
        logger.info("Inserted %d quotes", len(docs))
        return len(docs)
    except PyMongoError as e:
        logger.error("Mongo insert_many failed: %s", str(e))
        return 0


def insert_quote(doc: Dict[str, Any]) -> None:
    """
    Backward-compatible single insert helper (not used by scheduler, but harmless).
    """
    col = get_quotes_collection()
    try:
        col.insert_one(doc)
    except PyMongoError as e:
        logger.error("Mongo insert_one failed: %s", str(e))


def _find_index_by_keys(
    col: Collection, keys: List[Tuple[str, int]]
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Returns (name, info) for an existing index with the exact key pattern, else (None, None).
    """
    target = list(keys)
    for name, info in col.index_information().items():
        if info.get("key") == target:
            return name, info
    return None, None


def ensure_indexes() -> None:
    """
    Idempotent index creation. Skips creation if an index with the same key pattern already exists,
    regardless of its name, to avoid IndexOptionsConflict.
    """
    # users: unique username
    users = get_users_collection()
    name, info = _find_index_by_keys(users, [("username", ASCENDING)])
    if info is None:
        users.create_index([("username", ASCENDING)], unique=True)
    else:
        # If an existing index on username is non-unique, warn the user to drop it manually.
        if not bool(info.get("unique", False)):
            logger.warning(
                "Found existing index on users.username that is not unique (name=%s). "
                "To enforce uniqueness, drop it in mongosh: db.users.dropIndex('%s') and rerun.",
                name,
                name,
            )

    # portfolios
    portfolios = get_portfolios_collection()
    if _find_index_by_keys(portfolios, [("user_id", ASCENDING)])[1] is None:
        # unique one-per-user
        portfolios.create_index([("user_id", ASCENDING)], unique=True)
    if _find_index_by_keys(portfolios, [("updated_at", ASCENDING)])[1] is None:
        portfolios.create_index([("updated_at", ASCENDING)])
    if (
        _find_index_by_keys(portfolios, [("user_id", ASCENDING), ("rev", ASCENDING)])[1]
        is None
    ):
        portfolios.create_index([("user_id", ASCENDING), ("rev", ASCENDING)])

    # trades
    trades = get_trades_collection()
    if (
        _find_index_by_keys(
            trades, [("user_id", ASCENDING), ("executed_at", ASCENDING)]
        )[1]
        is None
    ):
        trades.create_index([("user_id", ASCENDING), ("executed_at", ASCENDING)])
    if (
        _find_index_by_keys(
            trades,
            [("user_id", ASCENDING), ("token", ASCENDING), ("executed_at", ASCENDING)],
        )[1]
        is None
    ):
        trades.create_index(
            [("user_id", ASCENDING), ("token", ASCENDING), ("executed_at", ASCENDING)]
        )

    # quotes (Module 1)
    quotes = get_quotes_collection()
    if (
        _find_index_by_keys(quotes, [("symbol", ASCENDING), ("timestamp", ASCENDING)])[
            1
        ]
        is None
    ):
        quotes.create_index([("symbol", ASCENDING), ("timestamp", ASCENDING)])
    if (
        _find_index_by_keys(quotes, [("token", ASCENDING), ("timestamp", ASCENDING)])[1]
        is None
    ):
        quotes.create_index([("token", ASCENDING), ("timestamp", ASCENDING)])

    logger.info("Indexes ensured for users, portfolios, trades, quotes")
    # inside ensure_indexes() at the end
    try:
        from src.db.sessions import ensure_session_indexes

        ensure_session_indexes()
    except Exception as e:
        logger.warning("Failed ensuring session indexes: %s", e)


def server_supports_transactions() -> bool:
    """
    Returns True if the MongoDB server supports transactions (replica set or sharded cluster).
    """
    try:
        client = get_client()
        try:
            hello = client.admin.command("hello")  # MongoDB 4.2+
        except Exception:
            hello = client.admin.command("isMaster")  # fallback for older
        is_replica = bool(hello.get("setName")) or bool(hello.get("isreplicaset"))
        has_sessions = "logicalSessionTimeoutMinutes" in hello
        return bool(is_replica and has_sessions)
    except Exception as e:
        logger.warning("Transaction support check failed: %s", e)
        return False


TXN_RC = ReadConcern("local")
TXN_WC = WriteConcern("majority")
TXN_RP = ReadPreference.PRIMARY
