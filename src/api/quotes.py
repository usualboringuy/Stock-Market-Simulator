# src/api/quotes.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pymongo import DESCENDING

from src.api.models import QuoteOut, TopGainerOut
from src.db.mongo import get_quotes_collection

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/latest", response_model=QuoteOut)
def latest_quote(token: Optional[str] = None, symbol: Optional[str] = None):
    if not token and not symbol:
        raise HTTPException(status_code=400, detail="Provide token or symbol")
    q: Dict[str, Any] = {"price": {"$ne": None}}
    if token:
        q["token"] = token
    if symbol:
        q["symbol"] = symbol
    col = get_quotes_collection()
    doc = col.find_one(q, sort=[("timestamp", DESCENDING)])
    if not doc:
        raise HTTPException(status_code=404, detail="No quote found")
    return {
        "symbol": doc.get("symbol"),
        "token": doc.get("token"),
        "price": doc.get("price"),
        "timestamp": doc.get("timestamp"),
        "percent_change": doc.get("percent_change"),
    }


@router.get("/top-gainers", response_model=List[TopGainerOut])
def top_gainers(limit: int = Query(10, ge=1, le=50)):
    col = get_quotes_collection()
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$token",
                "symbol": {"$first": "$symbol"},
                "token": {"$first": "$token"},
                "price": {"$first": "$price"},
                "percent_change": {"$first": "$percent_change"},
                "timestamp": {"$first": "$timestamp"},
            }
        },
        {"$match": {"percent_change": {"$ne": None}}},
        {"$sort": {"percent_change": -1}},
        {"$limit": int(limit)},
    ]
    rows = list(col.aggregate(pipeline))
    return rows


@router.get("/history")
def history(
    token: Optional[str] = None,
    symbol: Optional[str] = None,
    minutes: int = Query(60, ge=1, le=24 * 60),
    interval: str = Query("1m", pattern="^(1m|5m|15m)$"),
):
    if not token and not symbol:
        raise HTTPException(status_code=400, detail="Provide token or symbol")
    col = get_quotes_collection()

    # Resolve token if only symbol is provided
    if not token and symbol:
        doc = col.find_one({"symbol": symbol}, sort=[("timestamp", DESCENDING)])
        if not doc:
            raise HTTPException(status_code=404, detail="No data for symbol")
        token = doc.get("token")

    assert token is not None
    now = datetime.now(tz=timezone.utc)
    since = now - timedelta(minutes=int(minutes))

    bin_min = {"1m": 1, "5m": 5, "15m": 15}[interval]

    pipeline = [
        {"$match": {"token": token, "timestamp": {"$gte": since}}},
        {"$sort": {"timestamp": 1}},
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$timestamp",
                        "unit": "minute",
                        "binSize": bin_min,
                    }
                },
                "open": {"$first": "$price"},
                "high": {"$max": "$price"},
                "low": {"$min": "$price"},
                "close": {"$last": "$price"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "timestamp": "$_id",
                "o": "$open",
                "h": "$high",
                "l": "$low",
                "c": "$close",
            }
        },
        {"$sort": {"timestamp": 1}},
    ]
    rows = list(col.aggregate(pipeline))
    return rows
