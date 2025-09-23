from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId

from ..db import USERS, get_db
from ..security import hash_password


def create_user(username: str, password: str) -> Dict[str, Any]:
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": now,
        "updated_at": now,
    }
    res = db[USERS].insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def get_by_username(username: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    return db[USERS].find_one({"username": username})


def get_by_id(user_id: ObjectId | str) -> Optional[Dict[str, Any]]:
    db = get_db()
    oid = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
    return db[USERS].find_one({"_id": oid})
