from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.db.mongo import get_users_collection
from src.logger import get_logger

logger = get_logger("users_repo")


def to_object_id(id_or_str: Union[str, ObjectId]) -> ObjectId:
    if isinstance(id_or_str, ObjectId):
        return id_or_str
    return ObjectId(id_or_str)


def create_user(username: str, password_hash: str) -> Dict[str, Any]:
    """
    Create a user with a unique username.
    Store only a password hash (hashing performed by upper layers).
    """
    now = datetime.now(tz=timezone.utc)
    doc = {
        "username": username,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
    }
    col = get_users_collection()
    try:
        result = col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc
    except DuplicateKeyError:
        raise ValueError("Username already exists")


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    col = get_users_collection()
    return col.find_one({"username": username})


def get_user_by_id(user_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    col = get_users_collection()
    oid = to_object_id(user_id)
    return col.find_one({"_id": oid})
