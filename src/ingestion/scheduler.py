import threading
from typing import Dict, List, Any
from src.config import Config
from src.logger import get_logger
from src.ingestion.angel_client import AngelOneSession, EXCHANGE_TYPE_NSE_CM
from src.ingestion.store import QuoteBuffer

logger = get_logger("scheduler")


class IngestionScheduler:
    def __init__(self, stocks: List[Dict[str, Any]]):
        """
        stocks: list of dicts with symbol, token, name, exchange = 'NSE'
        """
        self.stocks = stocks
        self.session = AngelOneSession()
        self.token_to_meta: Dict[str, Dict[str, Any]] = {
            s["token"]: {
                "symbol": s["symbol"],
                "token": s["token"],
                "name": s.get("name"),
                "exchange": s.get("exchange", "NSE"),
            }
            for s in stocks
        }
        self.buffer = QuoteBuffer(self.token_to_meta)
        self._stop = threading.Event()

    def _on_tick(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming WS messages and push to buffer.
        SmartWebSocketV2 commonly includes "token" and optionally "exchange_type".
        """
        token = str(message.get("token") or "")
        if not token:
            return
        ex_type = message.get("exchange_type") or message.get("exchangeType")
        if ex_type not in (None, EXCHANGE_TYPE_NSE_CM):
            return
        self.buffer.push_raw(token, message)

    def _flush_loop(self) -> None:
        interval = max(1, min(5, Config.INGEST_INTERVAL_SEC))
        logger.info("Starting flush loop (every %ds)", interval)
        while not self._stop.is_set():
            try:
                inserted = self.buffer.flush()
                logger.debug("Flushed %d quotes", inserted)
            except Exception as e:
                logger.error("Flush error: %s", str(e))
            self._stop.wait(interval)

    def start(self) -> None:
        # Login
        self.session.login()

        # Start flush thread
        t = threading.Thread(target=self._flush_loop, name="flush-thread", daemon=True)
        t.start()

        # Start WS stream (blocking)
        tokens = [s["token"] for s in self.stocks]
        logger.info("Starting WebSocket stream for %d NSE equity tokens", len(tokens))
        self.session.start_stream(tokens=tokens, on_tick=self._on_tick, mode="FULL")

    def stop(self) -> None:
        self._stop.set()
        try:
            self.session.logout()
        except Exception:
            pass
