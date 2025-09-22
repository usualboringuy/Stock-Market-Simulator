# src/api/portfolio.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pymongo import DESCENDING
from src.api.deps import get_current_user
from src.db.portfolios import get_portfolio_by_user_id
from src.db.mongo import get_quotes_collection
from src.api.models import PortfolioOut, PositionOut

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _latest_prices_for_tokens(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    col = get_quotes_collection()
    pipeline = [
        {"$match": {"token": {"$in": tokens}, "price": {"$ne": None}}},
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$token", "price": {"$first": "$price"}}},
    ]
    out = {}
    for row in col.aggregate(pipeline):
        out[row["_id"]] = float(row["price"])
    return out


@router.get("", response_model=PortfolioOut)
def get_portfolio(current_user: Dict[str, Any] = Depends(get_current_user)):
    p = get_portfolio_by_user_id(current_user["_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    positions: Dict[str, Any] = p.get("positions") or {}

    tokens = list(positions.keys())
    price_map = _latest_prices_for_tokens(tokens)

    pos_out: List[PositionOut] = []
    total_unrealized = 0.0
    market_value = 0.0

    for token, pos in positions.items():
        qty = int(pos.get("quantity", 0))
        avg = float(pos.get("avg_price", 0.0))
        last = price_map.get(token)
        unreal = None
        if last is not None:
            unreal = round((last - avg) * qty, 4)
            total_unrealized += unreal
            market_value += last * qty
        pos_out.append(
            PositionOut(
                token=token,
                symbol=pos.get("symbol", ""),
                quantity=qty,
                avg_price=avg,
                last_price=last,
                unrealized_pl=unreal,
            )
        )

    totals = {
        "cash": float(p.get("cash", 0.0)),
        "realized_pl": float(p.get("realized_pl", 0.0)),
        "market_value": round(market_value, 4),
        "total_unrealized_pl": round(total_unrealized, 4),
        "net_liquidation": round(float(p.get("cash", 0.0)) + market_value, 4),
    }

    return PortfolioOut(
        cash=float(p.get("cash", 0.0)),
        realized_pl=float(p.get("realized_pl", 0.0)),
        positions=pos_out,
        totals=totals,
    )
