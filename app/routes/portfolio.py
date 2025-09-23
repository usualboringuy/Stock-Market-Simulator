from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from ..deps import current_user
from ..repositories import portfolios as portfolios_repo
from ..schemas import PortfolioOut, PortfolioPosition

router = APIRouter(prefix="/api", tags=["portfolio"])


def _portfolio_out(doc) -> PortfolioOut:
    pos_in = doc.get("positions", {}) or {}
    positions = {}
    for tok, p in pos_in.items():
        positions[tok] = PortfolioPosition(
            symbol=p.get("symbol", ""),
            quantity=int(p.get("quantity", 0)),
            avg_price=float(p.get("avg_price", 0.0)),
        )
    ua = doc.get("updated_at")
    iso = ua.isoformat() if isinstance(ua, datetime) else str(ua)
    return PortfolioOut(
        cash=float(doc.get("cash", 0.0)),
        realized_pl=float(doc.get("realized_pl", 0.0)),
        positions=positions,
        updated_at=iso,
        rev=int(doc.get("rev", 0)),
    )


@router.get("/portfolio", response_model=PortfolioOut)
def get_my_portfolio(user=Depends(current_user)):
    doc = portfolios_repo.get_or_create(user["_id"])
    return _portfolio_out(doc)
