from __future__ import annotations

from typing import Optional

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from .config import settings
from .logger import logger

_CLIENT: Optional[MongoClient] = None

USERS = "users"
SESSIONS = "sessions"
PORTFOLIOS = "portfolios"
TRADES = "trades"


def connect_mongo() -> Database:
    global _CLIENT
    if _CLIENT is None:
        logger.info(
            f"Connecting MongoDB at {settings.mongodb_url} db={settings.database_name}"
        )
        _CLIENT = MongoClient(
            settings.mongodb_url, serverSelectionTimeoutMS=5000, tz_aware=True
        )
        _CLIENT.admin.command("ping")
    return _CLIENT[settings.database_name]


def get_db() -> Database:
    if _CLIENT is None:
        return connect_mongo()
    return _CLIENT[settings.database_name]


def ensure_indexes() -> None:
    db = get_db()
    # users
    db[USERS].create_index([("username", ASCENDING)], name="uq_username", unique=True)
    db[USERS].create_index([("created_at", DESCENDING)], name="ix_users_created_at")
    # sessions
    db[SESSIONS].create_index(
        [("session_id", ASCENDING)], name="uq_session_id", unique=True
    )
    db[SESSIONS].create_index([("user_id", ASCENDING)], name="ix_sessions_user")
    db[SESSIONS].create_index(
        [("expires_at", ASCENDING)], name="ttl_expires_at", expireAfterSeconds=0
    )
    # portfolios
    db[PORTFOLIOS].create_index(
        [("user_id", ASCENDING)], name="uq_portfolio_user", unique=True
    )
    db[PORTFOLIOS].create_index(
        [("updated_at", DESCENDING)], name="ix_portfolios_updated"
    )
    # trades
    db[TRADES].create_index(
        [("user_id", ASCENDING), ("executed_at", DESCENDING)],
        name="ix_trades_user_time",
    )
    db[TRADES].create_index(
        [("token", ASCENDING), ("executed_at", DESCENDING)], name="ix_trades_token_time"
    )
    logger.info("MongoDB indexes ensured")
