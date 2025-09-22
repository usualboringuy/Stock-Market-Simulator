import csv
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/instruments", tags=["instruments"])

CSV_PATH = os.path.join("data", "stocks.csv")


@lru_cache(maxsize=1)
def _load_instruments() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not os.path.exists(CSV_PATH):
        return out
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("symbol") or not row.get("token"):
                continue
            symbol = row["symbol"].strip()
            token = str(row["token"]).strip()
            name = (row.get("name") or "").strip()
            if symbol.endswith("-EQ"):
                out.append(
                    {"symbol": symbol, "token": token, "name": name, "exchange": "NSE"}
                )
    return out


@router.get("/search")
def search_instruments(
    q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)
):
    ql = q.lower()
    items = _load_instruments()
    hits = [
        it for it in items if ql in it["symbol"].lower() or ql in it["name"].lower()
    ][:limit]
    return hits


@router.get("/by-symbol")
def by_symbol(symbol: str):
    items = _load_instruments()
    for it in items:
        if it["symbol"] == symbol:
            return it
    raise HTTPException(status_code=404, detail="Symbol not found")


@router.get("/by-token")
def by_token(token: str):
    items = _load_instruments()
    for it in items:
        if it["token"] == token:
            return it
    raise HTTPException(status_code=404, detail="Token not found")
