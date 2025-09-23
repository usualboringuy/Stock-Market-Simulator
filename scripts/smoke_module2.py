import os

from bson import ObjectId

from app.db import connect_mongo, ensure_indexes
from app.instruments import instruments
from app.repositories import portfolios as portfolios_repo
from app.repositories import trades as trades_repo
from app.repositories import users as users_repo
from app.trading import execute_trade


def pick_symbol(default_symbol: str = "INDUSTOWER-EQ") -> str:
    env = os.environ.get("SYMBOL")
    if env:
        return env
    ins = instruments.find_by_symbol(default_symbol)
    if ins:
        return ins.symbol
    return default_symbol


def main():
    connect_mongo()
    ensure_indexes()

    username = os.environ.get("SMOKE_USER", "demo_user")
    password = os.environ.get("SMOKE_PASS", "demo_pass")
    user = users_repo.get_by_username(username)
    if not user:
        print(f"Creating user {username}")
        user = users_repo.create_user(username, password)
    else:
        print(f"Using existing user {username}")
    uid = user["_id"]

    pf = portfolios_repo.get_or_create(uid, initial_cash=100000.0)
    print(f"Initial portfolio cash: {pf['cash']}, positions: {pf.get('positions', {})}")

    symbol = pick_symbol()
    print(f"Trading symbol: {symbol}")

    pf_after, trade1 = execute_trade(uid, symbol=symbol, side="BUY", quantity=5)
    print(
        "BUY trade:",
        {k: trade1[k] for k in ["symbol", "side", "quantity", "price", "amount"]},
    )
    print(
        f"Portfolio cash after BUY: {pf_after['cash']}, positions: {pf_after['positions']}"
    )

    pf_after2, trade2 = execute_trade(uid, symbol=symbol, side="SELL", quantity=2)
    print(
        "SELL trade:",
        {
            k: trade2[k]
            for k in ["symbol", "side", "quantity", "price", "amount", "realized_pl"]
        },
    )
    print(
        f"Portfolio cash after SELL: {pf_after2['cash']}, realized_pl: {pf_after2['realized_pl']}, positions: {pf_after2['positions']}"
    )

    recents = trades_repo.list_recent(uid, limit=5)
    print(f"Recent trades count: {len(recents)}")


if __name__ == "__main__":
    main()
