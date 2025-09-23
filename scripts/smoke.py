import csv
import os

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def first_symbol(csv_path: str):
    with open(csv_path, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row or len(row) < 2:
                continue
            sym = row[0].strip()
            tok = row[1].strip()
            if sym.lower() == "symbol" and tok.lower() == "token":
                continue
            return sym
    return None


def main():
    print("Health:")
    print(requests.get(f"{BASE}/api/health").json())

    stocks_csv = os.environ.get("STOCKS_CSV", "data/stocks.csv")
    sym = first_symbol(stocks_csv)
    if not sym:
        print("No symbol in CSV")
        return

    print(f"Searching for {sym} ...")
    sres = requests.get(f"{BASE}/api/instruments/search", params={"q": sym}).json()
    print(f"Search found {len(sres)} items")

    print(f"Fetch candles for {sym}")
    cres = requests.get(
        f"{BASE}/api/candles", params={"symbol": sym, "interval": "ONE_DAY"}
    ).json()
    print(f"Candles response keys: {list(cres.keys())}")
    print(f"Series length: {len(cres.get('series', []))}")


if __name__ == "__main__":
    main()
