from typing import Dict, Any, Union, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from src.db.mongo import (
    get_client,
    get_portfolios_collection,
    get_trades_collection,
    server_supports_transactions,
    TXN_RC,
    TXN_WC,
    TXN_RP,
)
from src.db.errors import (
    InvalidOrderError,
    InsufficientFundsError,
    InsufficientQuantityError,
)
from src.logger import get_logger

logger = get_logger("trade_service")

LEDGER_MAX_LEN = 500  # keep last N trades in portfolio. Adjust if needed.


def to_object_id(id_or_str: Union[str, ObjectId]) -> ObjectId:
    if isinstance(id_or_str, ObjectId):
        return id_or_str
    return ObjectId(id_or_str)


def execute_trade(
    *,
    user_id: Union[str, ObjectId],
    token: str,
    symbol: str,
    side: str,  # "BUY" or "SELL"
    quantity: int,
    price: float,  # rupees
) -> Dict[str, Any]:
    if side not in ("BUY", "SELL"):
        raise InvalidOrderError("side must be 'BUY' or 'SELL'")
    if quantity <= 0:
        raise InvalidOrderError("quantity must be > 0")
    if price <= 0:
        raise InvalidOrderError("price must be > 0")

    if server_supports_transactions():
        return _execute_trade_transactional(
            user_id=user_id,
            token=token,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )
    else:
        logger.info(
            "Transactions not supported; using single-document atomic fallback with optimistic concurrency"
        )
        return _execute_trade_optimistic(
            user_id=user_id,
            token=token,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )


def _execute_trade_transactional(
    *,
    user_id: Union[str, ObjectId],
    token: str,
    symbol: str,
    side: str,
    quantity: int,
    price: float,
) -> Dict[str, Any]:
    client = get_client()
    portfolios = get_portfolios_collection()
    trades = get_trades_collection()
    uid = to_object_id(user_id)
    now = datetime.now(tz=timezone.utc)
    amount = float(quantity) * float(price)

    def txn_body(session):
        p = portfolios.find_one({"user_id": uid}, session=session)
        if not p:
            raise InvalidOrderError("Portfolio not found for user")

        cash: float = float(p.get("cash", 0.0))
        positions: Dict[str, Any] = dict(p.get("positions") or {})
        pos = positions.get(token) or {
            "symbol": symbol,
            "quantity": 0,
            "avg_price": 0.0,
        }
        qty_old: int = int(pos.get("quantity", 0))
        avg_old: float = float(pos.get("avg_price", 0.0))

        realized_pl_increment: float = 0.0

        if side == "BUY":
            if cash < amount:
                raise InsufficientFundsError("Insufficient cash to execute BUY")
            qty_new = qty_old + quantity
            avg_new = ((avg_old * qty_old) + amount) / qty_new if qty_new > 0 else 0.0
            positions[token] = {
                "symbol": symbol,
                "quantity": qty_new,
                "avg_price": round(avg_new, 6),
            }
            update_doc: Dict[str, Any] = {
                "$set": {"updated_at": now, f"positions.{token}": positions[token]},
                "$inc": {"cash": -amount},
            }
        else:
            if qty_old < quantity:
                raise InsufficientQuantityError("Insufficient quantity to SELL")
            qty_new = qty_old - quantity
            realized_pl_increment = (price - avg_old) * quantity
            update_doc = {
                "$set": {"updated_at": now},
                "$inc": {"cash": amount, "realized_pl": realized_pl_increment},
            }
            if qty_new == 0:
                update_doc["$unset"] = {f"positions.{token}": ""}
            else:
                positions[token] = {
                    "symbol": symbol,
                    "quantity": qty_new,
                    "avg_price": round(avg_old, 6),
                }
                update_doc["$set"][f"positions.{token}"] = positions[token]

        portfolios.update_one({"user_id": uid}, update_doc, session=session)

        trade_doc = {
            "user_id": uid,
            "token": token,
            "symbol": symbol,
            "side": side,
            "quantity": int(quantity),
            "price": float(price),
            "amount": float(amount),
            "realized_pl": float(realized_pl_increment) if side == "SELL" else 0.0,
            "executed_at": now,
        }
        res = trades.insert_one(trade_doc, session=session)
        trade_doc["_id"] = res.inserted_id
        return trade_doc

    with client.start_session() as session:
        return session.with_transaction(
            txn_body,
            read_concern=TXN_RC,
            write_concern=TXN_WC,
            read_preference=TXN_RP,
        )


def _execute_trade_optimistic(
    *,
    user_id: Union[str, ObjectId],
    token: str,
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    max_retries: int = 8,
) -> Dict[str, Any]:
    """
    Single-document atomic update on portfolio with optimistic concurrency:
    - Reads portfolio, validates, computes new state.
    - Updates cash/positions and pushes trade into embedded ledger in one findOneAndUpdate.
    - Uses 'rev' field as a CAS token; retries on concurrent modifications.
    - Then best-effort inserts into trades collection (non-atomic duplication).
    """
    portfolios = get_portfolios_collection()
    trades = get_trades_collection()
    uid = to_object_id(user_id)
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        p = portfolios.find_one({"user_id": uid})
        if not p:
            raise InvalidOrderError("Portfolio not found for user")

        now = datetime.now(tz=timezone.utc)
        rev = int(p.get("rev", 0))
        cash: float = float(p.get("cash", 0.0))
        positions: Dict[str, Any] = dict(p.get("positions") or {})
        pos = positions.get(token) or {
            "symbol": symbol,
            "quantity": 0,
            "avg_price": 0.0,
        }
        qty_old: int = int(pos.get("quantity", 0))
        avg_old: float = float(pos.get("avg_price", 0.0))

        amount = float(quantity) * float(price)
        realized_pl_increment: float = 0.0

        if side == "BUY":
            if cash < amount:
                raise InsufficientFundsError("Insufficient cash to execute BUY")
            qty_new = qty_old + quantity
            avg_new = ((avg_old * qty_old) + amount) / qty_new if qty_new > 0 else 0.0
            new_pos = {
                "symbol": symbol,
                "quantity": qty_new,
                "avg_price": round(avg_new, 6),
            }
            set_updates = {f"positions.{token}": new_pos}
            inc_updates = {"cash": -amount, "rev": 1}
            unset_updates: Optional[Dict[str, Any]] = None
        else:
            if qty_old < quantity:
                raise InsufficientQuantityError("Insufficient quantity to SELL")
            qty_new = qty_old - quantity
            realized_pl_increment = (price - avg_old) * quantity
            inc_updates = {
                "cash": amount,
                "rev": 1,
                "realized_pl": realized_pl_increment,
            }
            if qty_new == 0:
                set_updates = {}
                unset_updates = {f"positions.{token}": ""}
            else:
                new_pos = {
                    "symbol": symbol,
                    "quantity": qty_new,
                    "avg_price": round(avg_old, 6),
                }
                set_updates = {f"positions.{token}": new_pos}
                unset_updates = None

        trade_doc = {
            "user_id": uid,
            "token": token,
            "symbol": symbol,
            "side": side,
            "quantity": int(quantity),
            "price": float(price),
            "amount": float(amount),
            "realized_pl": float(realized_pl_increment) if side == "SELL" else 0.0,
            "executed_at": now,
        }

        update_ops: Dict[str, Any] = {
            "$set": {"updated_at": now, **set_updates},
            "$inc": inc_updates,
            "$push": {"ledger": {"$each": [trade_doc], "$slice": -LEDGER_MAX_LEN}},
        }
        if unset_updates:
            update_ops["$unset"] = unset_updates

        result = portfolios.find_one_and_update(
            filter={"user_id": uid, "rev": rev},
            update=update_ops,
            return_document=ReturnDocument.AFTER,
        )

        if result is None:
            # CAS conflict, retry with latest snapshot
            continue

        # Best-effort duplicate into trades collection (non-atomic)
        try:
            ins = trades.insert_one(trade_doc)
            trade_doc["_id"] = ins.inserted_id
        except PyMongoError as e:
            logger.warning("Best-effort trades insert failed (non-atomic): %s", e)

        return trade_doc

    raise RuntimeError(
        "Failed to execute trade due to concurrent modifications. Please retry."
    )
