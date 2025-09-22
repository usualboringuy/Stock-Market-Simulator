# src/api/quotes.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pymongo import DESCENDING
from src.db.mongo import get_quotes_collection
from src.api.models import QuoteOut, TopGainerOut

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
