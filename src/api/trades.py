# src/api/trades.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from src.api.deps import get_current_user
from src.api.models import TradeIn, TradeOut
from src.db.trade_service import execute_trade
from src.db.trades import find_trades_by_user
from src.db.portfolios import get_portfolio_ledger

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=List[TradeOut])
def list_trades(
    token: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    rows = find_trades_by_user(current_user["_id"], limit=int(limit), token=token)
    if not rows:
        # Fallback to embedded ledger if using OCC mode w/o replica set
        rows = get_portfolio_ledger(current_user["_id"], limit=int(limit))
    # Normalize ids for response model
    out = []
    for t in rows:
        t["_id"] = str(t.get("_id", ""))
        out.append(t)
    return out


@router.post("", response_model=TradeOut)
def create_trade(
    payload: TradeIn, current_user: Dict[str, Any] = Depends(get_current_user)
):
    if payload.side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    if payload.quantity <= 0 or payload.price <= 0:
        raise HTTPException(status_code=400, detail="quantity and price must be > 0")
    trade = execute_trade(
        user_id=current_user["_id"],
        token=payload.token,
        symbol=payload.symbol,
        side=payload.side,
        quantity=int(payload.quantity),
        price=float(payload.price),
    )
    trade["_id"] = str(trade.get("_id", ""))
    return trade
