import csv
from dataclasses import dataclass
from typing import List, Optional

from .config import settings
from .logger import logger


@dataclass(frozen=True)
class Instrument:
    symbol: str
    token: str
    name: str


class InstrumentStore:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._by_symbol: dict[str, Instrument] = {}
        self._by_token: dict[str, Instrument] = {}
        self._load()

    def _load(self):
        logger.info(f"Loading instruments from {self.csv_path}")
        count = 0
        with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                s0 = row[0].strip()
                t0 = row[1].strip()
                if s0.lower() == "symbol" and t0.lower() == "token":
                    continue
                if not t0.isdigit():
                    logger.warning(f"Skipping row with non-numeric token: {row}")
                    continue
                n0 = row[2].strip() if len(row) >= 3 else s0
                ins = Instrument(symbol=s0, token=t0, name=n0)
                self._by_symbol[s0.upper()] = ins
                self._by_token[t0] = ins
                count += 1
        logger.info(f"Loaded {count} instruments (after header/invalid row skips)")

    def find_by_symbol(self, symbol: str) -> Optional[Instrument]:
        return self._by_symbol.get(symbol.upper())

    def find_by_token(self, token: str) -> Optional[Instrument]:
        return self._by_token.get(token)

    def search(self, q: str, limit: int = 20) -> List[Instrument]:
        if not q:
            return []
        ql = q.strip().upper()
        out = []
        for ins in self._by_symbol.values():
            if ql in ins.symbol.upper() or ql in ins.name.upper():
                out.append(ins)
                if len(out) >= limit:
                    break
        out.sort(key=lambda x: x.symbol)
        return out


instruments = InstrumentStore(settings.stocks_csv)
