from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from bson import ObjectId

from src.db.mongo import get_trades_collection
from src.logger import get_logger

logger = get_logger("trades_repo")


def to_object_id(id_or_str: Union[str, ObjectId]) -> ObjectId:
    if isinstance(id_or_str, ObjectId):
        return id_or_str
    return ObjectId(id_or_str)


def insert_trade(doc: Dict[str, Any], session=None) -> ObjectId:
    col = get_trades_collection()
    res = col.insert_one(doc, session=session)
    return res.inserted_id


def find_trades_by_user(
    user_id: Union[str, ObjectId], limit: int = 100, token: Optional[str] = None
) -> List[Dict[str, Any]]:
    col = get_trades_collection()
    oid = to_object_id(user_id)
    q: Dict[str, Any] = {"user_id": oid}
    if token:
        q["token"] = token
    cursor = col.find(q).sort("executed_at", -1).limit(limit)
    return list(cursor)
