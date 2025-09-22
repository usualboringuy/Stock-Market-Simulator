import csv
from typing import Dict, List


def load_stocks_csv(path: str) -> List[Dict[str, str]]:
    """
    Expecting a CSV with headers: symbol,token,name
    Returns a list of dicts with keys: symbol, token, name, exchange
    Filters to NSE equities where symbol ends with '-EQ'.
    """
    out: List[Dict[str, str]] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("symbol") or not row.get("token"):
                continue
            symbol = row["symbol"].strip()
            token = str(row["token"]).strip()
            name = (row.get("name") or "").strip()
            if not symbol.endswith("-EQ"):
                continue
            out.append(
                {
                    "symbol": symbol,
                    "token": token,
                    "name": name,
                    "exchange": "NSE",
                }
            )
    return out
