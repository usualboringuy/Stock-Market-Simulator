from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_user, require_csrf
from ..repositories import portfolios as portfolios_repo
from ..schemas import DepositRequest, PortfolioOut, PortfolioPosition

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


@router.post(
    "/portfolio/deposit",
    response_model=PortfolioOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def deposit(req: DepositRequest, user=Depends(current_user)):
    amt = float(req.amount)
    if amt <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amt > 1_000_000_000:
        raise HTTPException(status_code=400, detail="Amount too large")

    # OCC loop
    for _ in range(5):
        doc = portfolios_repo.get_or_create(user["_id"])
        new_cash = round(float(doc.get("cash", 0.0)) + amt, 2)
        if new_cash > 1_000_000_000_000:
            raise HTTPException(status_code=400, detail="Cash cap exceeded")
        ok = portfolios_repo.compare_and_swap(
            user["_id"], doc["rev"], {"cash": new_cash}
        )
        if ok:
            updated = portfolios_repo.get_or_create(user["_id"])
            return _portfolio_out(updated)
    raise HTTPException(status_code=409, detail="Concurrent update; please retry")
