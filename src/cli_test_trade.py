import argparse
import hashlib
import json
import os
from datetime import datetime
from typing import Any

from src.logger import get_logger
from src.db.mongo import init_mongo, ensure_indexes
from src.db.users import create_user, get_user_by_username
from src.db.portfolios import (
    create_portfolio,
    get_portfolio_by_user_id,
    get_portfolio_ledger,
)
from src.db.trades import find_trades_by_user
from src.db.trade_service import execute_trade
from src.utils.csv_loader import load_stocks_csv

logger = get_logger("cli_test_trade")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def json_dumps(obj: Any) -> str:
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    return json.dumps(obj, default=default, indent=2)


def pick_instrument(args):
    if args.token and args.symbol:
        return {
            "symbol": args.symbol,
            "token": args.token,
            "name": args.symbol,
            "exchange": "NSE",
        }
    csv_path = args.csv or os.path.join("data", "stocks.csv")
    rows = load_stocks_csv(csv_path)
    if not rows:
        raise RuntimeError(f"No NSE -EQ rows found in {csv_path}")
    if args.symbol:
        for r in rows:
            if r["symbol"] == args.symbol:
                return r
        raise RuntimeError(f"Symbol {args.symbol} not found in {csv_path}")
    return rows[0]


def latest_quote_price_rupees(token: str):
    from src.db.mongo import get_quotes_collection

    col = get_quotes_collection()
    doc = col.find_one(
        {"token": token, "price": {"$ne": None}}, sort=[("timestamp", -1)]
    )
    return float(doc["price"]) if doc else None


def main():
    parser = argparse.ArgumentParser(
        description="CLI test for Module 2 without requiring replica set."
    )
    parser.add_argument("--username", type=str, default="demo")
    parser.add_argument("--password", type=str, default="demo123")
    parser.add_argument("--initial-cash", type=float, default=100000.0)
    parser.add_argument("--quantity", type=int, default=2)
    parser.add_argument("--sell-qty", type=int, default=1)
    parser.add_argument("--price", type=float, default=None)
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--token", type=str, default=None)
    parser.add_argument("--csv", type=str, default=os.path.join("data", "stocks.csv"))
    parser.add_argument("--trades-limit", type=int, default=5)
    args = parser.parse_args()

    init_mongo()
    ensure_indexes()

    user = get_user_by_username(args.username)
    if not user:
        user = create_user(args.username, sha256(args.password))
        logger.info("Created user: %s", args.username)
    portfolio = get_portfolio_by_user_id(user["_id"])
    if not portfolio:
        portfolio = create_portfolio(user["_id"], initial_cash=args.initial_cash)
        logger.info(
            "Created portfolio for user %s | initial cash=%.2f",
            args.username,
            float(args.initial_cash),
        )

    instrument = pick_instrument(args)
    token = instrument["token"]
    symbol = instrument["symbol"]
    logger.info("Using instrument: %s (%s)", symbol, token)

    buy_price = args.price or latest_quote_price_rupees(token) or 100.0
    sell_qty = min(args.sell_qty, args.quantity)
    sell_price = round(buy_price * 1.01, 2)

    print("\n--- Executing Trades ---")
    print(f"BUY  {args.quantity} x {symbol} @ {buy_price:.2f} INR")
    buy_trade = execute_trade(
        user_id=user["_id"],
        token=token,
        symbol=symbol,
        side="BUY",
        quantity=int(args.quantity),
        price=float(buy_price),
    )

    print(f"SELL {sell_qty} x {symbol} @ {sell_price:.2f} INR")
    sell_trade = execute_trade(
        user_id=user["_id"],
        token=token,
        symbol=symbol,
        side="SELL",
        quantity=int(sell_qty),
        price=float(sell_price),
    )

    portfolio_after = get_portfolio_by_user_id(user["_id"])

    # Prefer trades collection; if empty (fallback mode), read from portfolio ledger
    recent_trades = find_trades_by_user(user["_id"], limit=int(args.trades_limit))
    if not recent_trades:
        recent_trades = get_portfolio_ledger(user["_id"], limit=int(args.trades_limit))

    print("\n--- Portfolio (after trades) ---")
    print(json_dumps(portfolio_after))

    print("\n--- Recent Trades ---")
    for t in recent_trades:
        print(json_dumps(t))

    print("\nDone.\n")


if __name__ == "__main__":
    main()
