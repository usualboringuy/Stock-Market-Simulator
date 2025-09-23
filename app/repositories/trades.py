from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..db import TRADES, get_db


def insert_trade(doc: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    if "executed_at" not in doc:
        doc["executed_at"] = datetime.now(timezone.utc)
    res = db[TRADES].insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def list_recent(user_id, limit: int = 20) -> List[Dict[str, Any]]:
    db = get_db()
    cur = db[TRADES].find({"user_id": user_id}).sort("executed_at", -1).limit(limit)
    return list(cur)
