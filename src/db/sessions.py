# src/db/sessions.py
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import secrets

from pymongo.collection import Collection
from pymongo import ASCENDING

from src.db.mongo import get_db
from src.config import Config
from src.logger import get_logger

logger = get_logger("sessions_repo")

_sessions_col: Optional[Collection] = None


def get_sessions_collection() -> Collection:
    global _sessions_col
    if _sessions_col is None:
        _sessions_col = get_db()["sessions"]
    return _sessions_col


def ensure_session_indexes() -> None:
    col = get_sessions_collection()
    # TTL index on expires_at
    existing = col.index_information()
    has_ttl = any(
        info.get("key") == [("expires_at", ASCENDING)] for info in existing.values()
    )
    if not has_ttl:
        try:
            col.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        except Exception as e:
            logger.warning(
                "Creating TTL index on sessions failed (may already exist): %s", e
            )


def create_session(user_id) -> str:
    col = get_sessions_collection()
    now = datetime.now(tz=timezone.utc)
    sid = secrets.token_urlsafe(32)
    doc = {
        "session_id": sid,
        "user_id": user_id,
        "created_at": now,
        "expires_at": now + timedelta(seconds=Config.SESSION_TTL_SECONDS),
    }
    col.insert_one(doc)
    return sid


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    col = get_sessions_collection()
    return col.find_one({"session_id": session_id})


def delete_session(session_id: str) -> None:
    col = get_sessions_collection()
    col.delete_one({"session_id": session_id})
