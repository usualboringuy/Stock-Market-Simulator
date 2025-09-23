from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Literal, Tuple

from bson import ObjectId

from .candles import fallback_daily_if_empty
from .instruments import instruments
from .logger import logger
from .repositories import portfolios as portfolios_repo
from .repositories import trades as trades_repo
from .timeutils import IST, now_ist

Side = Literal["BUY", "SELL"]


def _today_ist_at(h: int, m: int, s: int = 0) -> datetime:
    now = now_ist()
    return now.replace(hour=h, minute=m, second=s, microsecond=0, tzinfo=IST)


def _is_market_open_like(now_dt: datetime) -> bool:
    wd = now_dt.weekday()
    if wd >= 5:
        return False
    t = now_dt.timetz()
    return (t.hour, t.minute) >= (9, 0) and (t.hour, t.minute) <= (15, 30)


def _derive_fill_price(token: str, side: Side) -> float:
    now = now_ist()
    if _is_market_open_like(now):
        start = _today_ist_at(9, 0)
        end = now
        raw = fallback_daily_if_empty("NSE", token, "ONE_MINUTE", start, end)
    else:
        end = now
        start = end - timedelta(days=60)
        raw = fallback_daily_if_empty("NSE", token, "ONE_DAY", start, end)
    if not raw:
        raise RuntimeError("No price data available for fill")
    last = raw[-1]
    price = float(last[4])  # close
    return round(price, 2)


def execute_trade(
    user_id: ObjectId | str,
    *,
    symbol: str | None = None,
    token: str | None = None,
    side: Side,
    quantity: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    ins = None
    if symbol:
        ins = instruments.find_by_symbol(symbol)
    if not ins and token:
        ins = instruments.find_by_token(token)
    if not ins:
        raise ValueError("Instrument not found in CSV")
    token = ins.token
    symbol = ins.symbol

    price = _derive_fill_price(token, side)

    from .repositories import portfolios as pr

    uid = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
    for _ in range(5):
        p = pr.get_or_create(uid)
        cash = float(p["cash"])
        realized_pl = float(p.get("realized_pl", 0.0))
        positions = dict(p.get("positions", {}))
        pos = dict(
            positions.get(token, {"symbol": symbol, "quantity": 0, "avg_price": 0.0})
        )
        qty_old = int(pos.get("quantity", 0))
        avg_old = float(pos.get("avg_price", 0.0))

        if side == "BUY":
            cost = round(quantity * price, 2)
            if cash < cost:
                raise ValueError("Insufficient cash")
            qty_new = qty_old + quantity
            avg_new = round(((qty_old * avg_old) + cost) / qty_new, 4)
            pos.update({"symbol": symbol, "quantity": qty_new, "avg_price": avg_new})
            positions[token] = pos
            new_fields = {
                "cash": round(cash - cost, 2),
                "positions": positions,
                "realized_pl": realized_pl,
            }
            success = pr.compare_and_swap(uid, p["rev"], new_fields)
            if success:
                trade = {
                    "user_id": uid,
                    "token": token,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "amount": round(cost, 2),
                    "realized_pl": 0.0,
                }
                tdoc = trades_repo.insert_trade(trade)
                updated_pf = pr.get(uid)
                if not updated_pf:
                    raise RuntimeError("Portfolio not found after update")
                return updated_pf, tdoc
        else:
            if qty_old < quantity:
                raise ValueError("Insufficient quantity")
            proceeds = round(quantity * price, 2)
            realized = round((price - avg_old) * quantity, 2)
            qty_new = qty_old - quantity
            if qty_new == 0:
                positions.pop(token, None)
            else:
                pos.update(
                    {"symbol": symbol, "quantity": qty_new, "avg_price": avg_old}
                )
                positions[token] = pos
            new_fields = {
                "cash": round(cash + proceeds, 2),
                "positions": positions,
                "realized_pl": round(realized_pl + realized, 2),
            }
            success = pr.compare_and_swap(uid, p["rev"], new_fields)
            if success:
                trade = {
                    "user_id": uid,
                    "token": token,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "amount": round(proceeds, 2),
                    "realized_pl": realized,
                }
                tdoc = trades_repo.insert_trade(trade)
                updated_pf = pr.get(uid)
                if not updated_pf:
                    raise RuntimeError("Portfolio not found after update")
                return updated_pf, tdoc
        # OCC conflict, retry
        logger.warning("Portfolio OCC conflict; retrying...")
    raise RuntimeError("Concurrent update; please retry")
