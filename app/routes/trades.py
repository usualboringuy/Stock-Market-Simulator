from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..deps import current_user, require_csrf
from ..repositories import trades as trades_repo
from ..schemas import TradeOut, TradeRequest
from ..trading import execute_trade

router = APIRouter(prefix="/api", tags=["trades"])


def _trade_out(doc) -> TradeOut:
    ea = doc.get("executed_at")
    iso = ea.isoformat() if isinstance(ea, datetime) else str(ea)
    return TradeOut(
        symbol=doc["symbol"],
        token=doc["token"],
        side=doc["side"],
        quantity=int(doc["quantity"]),
        price=float(doc["price"]),
        amount=float(doc["amount"]),
        realized_pl=float(doc.get("realized_pl", 0.0)),
        executed_at=iso,
    )


@router.post(
    "/trades",
    response_model=TradeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_trade(payload: TradeRequest, user=Depends(current_user)):
    if not payload.symbol and not payload.token:
        raise HTTPException(status_code=400, detail="symbol or token is required")
    try:
        _, trade_doc = execute_trade(
            user["_id"],
            symbol=payload.symbol,
            token=payload.token,
            side=payload.side,  # type: ignore
            quantity=payload.quantity,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _trade_out(trade_doc)


@router.get("/trades/recent", response_model=List[TradeOut])
def list_recent_trades(
    user=Depends(current_user), limit: int = Query(20, ge=1, le=100)
):
    docs = trades_repo.list_recent(user["_id"], limit=limit)
    return [_trade_out(d) for d in docs]
