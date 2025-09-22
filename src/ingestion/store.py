from typing import Dict, List, Any
from threading import Lock
from src.ingestion.normalizer import normalize_tick
from src.db.mongo import insert_many_quotes
from src.logger import get_logger

logger = get_logger("store")


class QuoteBuffer:
    """
    Keeps the latest raw tick per token and periodically flushes normalized records to DB.
    """

    def __init__(self, token_to_meta: Dict[str, Dict[str, Any]]):
        self._lock = Lock()
        self._latest_raw_by_token: Dict[str, Dict[str, Any]] = {}
        self._token_to_meta = token_to_meta

    def push_raw(self, token: str, raw: Dict[str, Any]) -> None:
        with self._lock:
            self._latest_raw_by_token[token] = raw

    def flush(self) -> int:
        """
        Normalize and flush all current latest ticks to Mongo.
        Returns number of records inserted.
        """
        with self._lock:
            items = list(self._latest_raw_by_token.items())
        docs: List[Dict[str, Any]] = []
        for token, raw in items:
            meta = self._token_to_meta.get(token)
            if not meta:
                continue
            try:
                doc = normalize_tick(raw, meta)
                if doc.get("price") is not None:
                    docs.append(doc)
            except Exception as e:
                logger.error("Normalization failed for token %s: %s", token, str(e))
        if docs:
            insert_many_quotes(docs)
        return len(docs)
