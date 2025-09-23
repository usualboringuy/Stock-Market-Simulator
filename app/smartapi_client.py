import json
import threading
import time
from typing import Any, Dict, Literal, Optional, cast

import pyotp
from SmartApi import SmartConnect

from .config import settings
from .logger import logger

SessionType = Literal["historical", "trading"]


class _SessionState:
    def __init__(self, api_key: str, label: str):
        self.api_key = api_key
        self.label = label
        self.client: Optional[SmartConnect] = None
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None

        self.login_lock = threading.Lock()
        self.call_lock = threading.Lock()
        self.min_interval_sec = 0.25
        self._last_call_ts = 0.0

    def throttle(self):
        with self.call_lock:
            now = time.time()
            elapsed = now - self._last_call_ts
            if elapsed < self.min_interval_sec:
                time.sleep(self.min_interval_sec - elapsed)
            self._last_call_ts = time.time()


class SmartAPIManager:
    def __init__(self):
        self.hist = _SessionState(settings.angel_hist_api_key, label="historical")
        self.trade = _SessionState(settings.angel_market_api_key, label="trading")

    @staticmethod
    def _ensure_dict_response(resp: Any, context: str) -> Dict[str, Any]:
        if isinstance(resp, (bytes, bytearray)):
            try:
                decoded = json.loads(resp.decode("utf-8"))
            except Exception as e:
                logger.error(f"{context}: bytes response not JSON-decodable: {e}")
                raise RuntimeError(f"{context}: unexpected non-JSON response")
            if not isinstance(decoded, dict):
                raise RuntimeError(f"{context}: unexpected JSON type (expected dict)")
            return cast(Dict[str, Any], decoded)
        if not isinstance(resp, dict):
            raise RuntimeError(f"{context}: unexpected response type (expected dict)")
        return cast(Dict[str, Any], resp)

    def _ensure_session(self, sess: _SessionState):
        if sess.client is not None:
            return
        with sess.login_lock:
            if sess.client is not None:
                return
            if not sess.api_key:
                logger.error(f"{sess.label} api_key is missing. Check .env")
                raise RuntimeError(f"{sess.label} api_key missing")
            logger.info(f"Logging in SmartAPI {sess.label} session")
            client = SmartConnect(sess.api_key)

            try:
                totp_str = pyotp.TOTP(settings.angel_totp_secret).now()
            except Exception as e:
                logger.error("Invalid Token: The provided token is not valid.")
                raise e

            raw = client.generateSession(
                settings.angel_client_id, settings.angel_pin, totp_str
            )
            data = self._ensure_dict_response(raw, f"{sess.label} generateSession")

            if not data or data.get("status") is False:
                logger.error(f"generateSession failed for {sess.label}: {data}")
                raise RuntimeError(f"SmartAPI {sess.label} login failed")

            try:
                payload = cast(Dict[str, Any], data["data"])
                sess.auth_token = cast(str, payload["jwtToken"])
                sess.refresh_token = cast(str, payload["refreshToken"])
            except Exception as e:
                logger.error(f"{sess.label} login payload missing fields: {e}")
                raise RuntimeError(f"SmartAPI {sess.label} login response malformed")

            try:
                sess.feed_token = client.getfeedToken()
            except Exception as e:
                logger.warning(f"getfeedToken failed for {sess.label}: {e}")
                sess.feed_token = None

            sess.client = client
            logger.info(f"SmartAPI {sess.label} login OK")

    def ensure_logged_in(self):
        if settings.angel_hist_api_key:
            self._ensure_session(self.hist)
        if settings.angel_market_api_key:
            self._ensure_session(self.trade)

    def get_candles(
        self, exchange: str, symboltoken: str, interval: str, fromdate: str, todate: str
    ) -> Dict[str, Any]:
        self._ensure_session(self.hist)
        params: Dict[str, Any] = {
            "exchange": exchange,
            "symboltoken": symboltoken,
            "interval": interval,
            "fromdate": fromdate,
            "todate": todate,
        }
        self.hist.throttle()
        try:
            assert self.hist.client is not None
            raw = self.hist.client.getCandleData(params)
            return self._ensure_dict_response(raw, "getCandleData")
        except Exception as e:
            logger.error(f"getCandleData failed: {e}")
            raise

    def terminate_all(self):
        for sess in (self.hist, self.trade):
            if sess.client:
                try:
                    sess.client.terminateSession(settings.angel_client_id)
                except Exception as e:
                    logger.warning(f"terminateSession failed for {sess.label}: {e}")
                finally:
                    sess.client = None


smart_mgr = SmartAPIManager()
