"""
Combined jugaad-data + nsepython Stock Data Ingestion Client with concurrency
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Dict, List

from jugaad_data.nse import NSELive
from mongo_handler import MongoHandler

try:
    from nsepython import nse_quote, nse_quote_ltp

    NSEPYTHON_AVAILABLE = True
except ImportError:
    NSEPYTHON_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JugaadNSEClient:
    def __init__(self, max_workers: int = 5):
        self.jugaad_client = NSELive()
        self.mongo_handler = MongoHandler()
        self.quotes_col = self.mongo_handler.get_collection("quotes")
        self.max_workers = max_workers
        logger.info(
            f"JugaadNSEClient initialized. NSEPYTHON_AVAILABLE = {NSEPYTHON_AVAILABLE}"
        )

    def get_nsepython_volume(self, symbol: str) -> int:
        """
        Fetch live traded volume from nsepython's nse_quote for the symbol
        Returns integer volume or 0 if unavailable
        """
        if not NSEPYTHON_AVAILABLE:
            return 0
        try:
            func = globals().get("nse_quote")
            if func is None:
                logger.warning("nse_quote function not available")
                return 0

            quote = func(symbol)
            if isinstance(quote, dict) and quote is not None:
                volume = quote.get("totalTradedVolume", 0)
                if isinstance(volume, int):
                    return volume
                elif isinstance(volume, str) and volume.isdigit():
                    return int(volume)
            return 0
        except Exception as e:
            logger.warning(f"Failed to fetch volume from nsepython for {symbol}: {e}")
            return 0

    def get_jugaad_data(self, symbol: str) -> Dict:
        try:
            raw = self.jugaad_client.stock_quote(symbol)
            price_info = raw.get("priceInfo", {})
            pre_open = raw.get("preOpenMarket", {})

            return {
                "symbol": symbol,
                "lastPrice": price_info.get("lastPrice", 0),
                "change": price_info.get("change", 0),
                "pChange": price_info.get("pChange", 0),
                "previousClose": price_info.get("previousClose", 0),
                "open": price_info.get("open", 0),
                "close": price_info.get("close", 0),
                "vwap": price_info.get("vwap", 0),
                "upperCP": price_info.get("upperCP"),
                "lowerCP": price_info.get("lowerCP"),
                "tickSize": price_info.get("tickSize"),
                "intraDayHighLow": price_info.get("intraDayHighLow", {}),
                "weekHighLow": price_info.get("weekHighLow", {}),
                "preOpenVolume": pre_open.get("totalTradedVolume", 0),
                "timestamp": datetime.now(UTC),
            }
        except Exception as e:
            logger.error(f"Failed to fetch jugaad data for {symbol}: {e}")
            return {}

    def fetch_and_store_quote(self, symbol: str) -> bool:
        jugaad_data = self.get_jugaad_data(symbol)
        if not jugaad_data:
            return False

        volume = self.get_nsepython_volume(symbol)
        jugaad_data["live_volume"] = volume

        try:
            self.quotes_col.update_one(
                {"symbol": symbol}, {"$set": jugaad_data}, upsert=True
            )
            logger.info(f"Stored quote for {symbol} with live volume: {volume}")
            return True
        except Exception as e:
            logger.error(f"MongoDB insert error for {symbol}: {e}")
            return False

    def fetch_and_store_multiple(self, symbols: List[str]) -> int:
        success_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.fetch_and_store_quote, sym): sym for sym in symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error fetching/storing {sym}: {e}")
        logger.info(f"Fetched and stored {success_count}/{len(symbols)} quotes")
        return success_count

    def close(self):
        self.mongo_handler.close()


if __name__ == "__main__":
    symbols = ["TATASTEEL", "TCS", "TATAMOTORS"]
    client = JugaadNSEClient(max_workers=10)
    client.fetch_and_store_multiple(symbols)
    client.close()
