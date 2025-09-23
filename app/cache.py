import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float = 60.0, max_items: int = 1024):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: dict[Any, tuple[float, Any]] = {}

    def _prune(self):
        if len(self._store) > self.max_items:
            now = time.time()
            expired_keys = [
                k for k, (ts, _) in self._store.items() if now - ts > self.ttl
            ]
            for k in expired_keys:
                self._store.pop(k, None)
            if len(self._store) > self.max_items:
                oldest = sorted(self._store.items(), key=lambda kv: kv[1][0])[
                    : len(self._store) - self.max_items
                ]
                for k, _ in oldest:
                    self._store.pop(k, None)

    def get(self, key: Any):
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: Any, value: Any):
        self._store[key] = (time.time(), value)
        self._prune()
