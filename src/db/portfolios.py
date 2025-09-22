from typing import Optional, Dict, Any, Union, List
from datetime import datetime, timezone
from bson import ObjectId

from src.db.mongo import get_portfolios_collection
from src.logger import get_logger

logger = get_logger("portfolios_repo")


def to_object_id(id_or_str: Union[str, ObjectId]) -> ObjectId:
    if isinstance(id_or_str, ObjectId):
        return id_or_str
    return ObjectId(id_or_str)


def create_portfolio(
    user_id: Union[str, ObjectId], initial_cash: float = 0.0
) -> Dict[str, Any]:
    col = get_portfolios_collection()
    oid = to_object_id(user_id)
    now = datetime.now(tz=timezone.utc)
    doc = {
        "user_id": oid,
        "cash": float(initial_cash),
        "realized_pl": 0.0,
        "positions": {},
        "ledger": [],  # embedded trade history (tail-capped)
        "rev": 0,  # optimistic concurrency counter
        "created_at": now,
        "updated_at": now,
    }
    col.insert_one(doc)
    return doc


def get_portfolio_by_user_id(user_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    col = get_portfolios_collection()
    oid = to_object_id(user_id)
    return col.find_one({"user_id": oid})


def get_portfolio_ledger(
    user_id: Union[str, ObjectId], limit: int = 20
) -> List[Dict[str, Any]]:
    col = get_portfolios_collection()
    oid = to_object_id(user_id)
    # Fetch only the last N entries from ledger
    doc = col.find_one({"user_id": oid}, {"ledger": {"$slice": -int(limit)}})
    if not doc:
        return []
    return list(doc.get("ledger") or [])
