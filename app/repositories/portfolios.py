from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..db import PORTFOLIOS, get_db

DEFAULT_INITIAL_CASH = 1000000.0


def get(user_id) -> Optional[Dict[str, Any]]:
    db = get_db()
    return db[PORTFOLIOS].find_one({"user_id": user_id})


def get_required(user_id) -> Dict[str, Any]:
    doc = get(user_id)
    if not doc:
        raise RuntimeError("Portfolio not found")
    return doc


def get_or_create(
    user_id, initial_cash: float = DEFAULT_INITIAL_CASH
) -> Dict[str, Any]:
    db = get_db()
    doc = db[PORTFOLIOS].find_one({"user_id": user_id})
    if doc:
        return doc
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "cash": float(initial_cash),
        "realized_pl": 0.0,
        "positions": {},
        "rev": 0,
        "created_at": now,
        "updated_at": now,
    }
    res = db[PORTFOLIOS].insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def compare_and_swap(user_id, expected_rev: int, new_fields: Dict[str, Any]) -> bool:
    db = get_db()
    new_fields = dict(new_fields)
    new_fields["rev"] = expected_rev + 1
    new_fields["updated_at"] = datetime.now(timezone.utc)
    res = db[PORTFOLIOS].update_one(
        {"user_id": user_id, "rev": expected_rev},
        {"$set": new_fields},
    )
    return res.modified_count == 1
