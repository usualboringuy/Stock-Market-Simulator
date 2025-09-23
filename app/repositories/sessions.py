from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from ..db import SESSIONS, get_db


def create_session(user_id, ttl_seconds: int = 3600) -> Dict[str, Any]:
    db = get_db()
    now = datetime.now(timezone.utc)
    sess_id = secrets.token_hex(32)
    csrf_token = secrets.token_urlsafe(32)
    doc = {
        "session_id": sess_id,
        "user_id": user_id,
        "csrf_token": csrf_token,
        "created_at": now,
        "expires_at": now + timedelta(seconds=ttl_seconds),
    }
    db[SESSIONS].insert_one(doc)
    return doc


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    return db[SESSIONS].find_one({"session_id": session_id})


def touch_session(session_id: str, ttl_seconds: int) -> bool:
    db = get_db()
    now = datetime.now(timezone.utc)
    res = db[SESSIONS].update_one(
        {"session_id": session_id},
        {"$set": {"expires_at": now + timedelta(seconds=ttl_seconds)}},
    )
    return res.modified_count == 1


def delete_session(session_id: str) -> int:
    db = get_db()
    res = db[SESSIONS].delete_one({"session_id": session_id})
    return res.deleted_count
