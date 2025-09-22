import json
import time
from typing import Callable, Dict, List, Optional, Any, cast

import pyotp
from SmartApi import SmartConnect  # pip install smartapi-python
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from src.config import Config
from src.logger import get_logger

logger = get_logger("angel")

# 1 => NSE-CM (equity) as per SmartAPI docs
EXCHANGE_TYPE_NSE_CM = 1
# WebSocket V2 mode mapping
MODE_MAP = {"LTP": 1, "QUOTE": 2, "FULL": 3}


class AngelOneSession:
    def __init__(self) -> None:
        self.api_key: str = cast(str, Config.ANGEL_API_KEY)
        self.client_id: str = cast(str, Config.ANGEL_CLIENT_ID)
        self.password: str = cast(str, Config.ANGEL_PIN)
        self.totp_secret: str = cast(str, Config.ANGEL_TOTP_SECRET)

        self._sc: Optional[SmartConnect] = None
        self.feed_token: Optional[str] = None  # used by some builds
        self.auth_token: Optional[str] = None  # jwtToken, used by others
        self._sws: Optional[Any] = None  # Any for cross-version callback signatures
        self._subscribed_batches: List[List[str]] = []

    def login(self, retries: int = 5, backoff_sec: float = 2.0) -> None:
        attempt = 0
        while attempt < retries:
            try:
                logger.info(
                    "Logging in to Angel One SmartAPI (attempt %d)...", attempt + 1
                )
                self._sc = SmartConnect(api_key=self.api_key)
                totp = pyotp.TOTP(self.totp_secret).now()
                resp = self._sc.generateSession(self.client_id, self.password, totp)

                # Normalize resp to a dict before calling .get (avoids bytes.get warnings)
                resp_dict: Dict[str, Any] = {}
                if isinstance(resp, dict):
                    resp_dict = resp
                elif isinstance(resp, (bytes, bytearray, str)):
                    try:
                        text = (
                            resp.decode("utf-8", errors="ignore")
                            if isinstance(resp, (bytes, bytearray))
                            else str(resp)
                        )
                        obj = json.loads(text)
                        if isinstance(obj, dict):
                            resp_dict = obj
                    except Exception:
                        resp_dict = {}
                else:
                    resp_dict = {}

                data: Dict[str, Any] = resp_dict.get("data") or {}

                # Capture both tokens; different WS builds need different tokens
                jwt = data.get("jwtToken")
                ft_from_data = data.get("feedToken")
                self.auth_token = jwt if isinstance(jwt, str) and jwt else None

                # Prefer SmartConnect.getfeedToken(); fall back to response if present
                ft = self._sc.getfeedToken()
                if not ft and isinstance(ft_from_data, str) and ft_from_data:
                    ft = ft_from_data
                self.feed_token = ft if isinstance(ft, str) and ft else None

                if not (self.auth_token or self.feed_token):
                    raise RuntimeError("Failed to obtain auth_token/feed_token")

                logger.info(
                    "Login successful (auth_token=%s, feed_token=%s)",
                    "yes" if self.auth_token else "no",
                    "yes" if self.feed_token else "no",
                )
                return
            except Exception as e:
                logger.error("Login failed: %s", str(e))
                time.sleep(backoff_sec * (2**attempt))
                attempt += 1
        raise RuntimeError("Unable to login after retries")

    def logout(self) -> None:
        try:
            if self._sc is not None:
                self._sc.terminateSession(self.client_id)
        except Exception:
            pass

    def _ensure_ws(self) -> Any:
        """
        Create SmartWebSocketV2 in a version-agnostic way.
        Tries variants (auth_token, feed_token, both) to support different releases.
        """
        if not (self.auth_token or self.feed_token):
            raise RuntimeError("Must login before starting websocket (no token)")

        if self._sws is not None:
            return self._sws

        SWSClass = cast(Any, SmartWebSocketV2)
        errors: List[str] = []

        # Try with both named
        try:
            self._sws = SWSClass(
                api_key=self.api_key,
                client_code=self.client_id,
                auth_token=self.auth_token,
                feed_token=self.feed_token,
            )
            logger.info("SmartWebSocketV2 initialized with auth_token + feed_token")
            return self._sws
        except TypeError as e:
            errors.append(f"both(auth_token+feed_token) failed: {e}")

        # Try auth_token only
        if self.auth_token:
            try:
                self._sws = SWSClass(
                    api_key=self.api_key,
                    client_code=self.client_id,
                    auth_token=self.auth_token,
                )
                logger.info("SmartWebSocketV2 initialized with auth_token")
                return self._sws
            except TypeError as e:
                errors.append(f"auth_token failed: {e}")

        # Try feed_token only
        if self.feed_token:
            try:
                self._sws = SWSClass(
                    api_key=self.api_key,
                    client_code=self.client_id,
                    feed_token=self.feed_token,
                )
                logger.info("SmartWebSocketV2 initialized with feed_token")
                return self._sws
            except TypeError as e:
                errors.append(f"feed_token failed: {e}")

        # Try positional (jwt or feed as 3rd arg)
        try:
            token3 = self.auth_token or self.feed_token
            self._sws = SWSClass(self.api_key, self.client_id, token3)
            logger.info("SmartWebSocketV2 initialized with positional token")
            return self._sws
        except TypeError as e:
            errors.append(f"positional failed: {e}")

        raise RuntimeError(
            "SmartWebSocketV2 init failed. Errors: " + " | ".join(errors)
        )

    @staticmethod
    def _chunk_tokens(tokens: List[str], chunk_size: int) -> List[List[str]]:
        return [tokens[i : i + chunk_size] for i in range(0, len(tokens), chunk_size)]

    def start_stream(
        self,
        tokens: List[str],
        on_tick: Callable[[Dict[str, Any]], None],
        mode: str = "FULL",
        chunk_size: Optional[int] = None,
    ) -> None:
        """
        Start SmartWebSocketV2 stream.
        - tokens: list of instrument tokens as strings (e.g., "3045")
        - on_tick: callback to receive individual tick dicts
        - mode: "LTP", "QUOTE", or "FULL"
        """
        sws_any = cast(Any, self._ensure_ws())
        use_mode = MODE_MAP.get(mode.upper(), MODE_MAP["FULL"])
        chunk = chunk_size if chunk_size is not None else Config.WS_SUB_CHUNK_SIZE

        token_batches = self._chunk_tokens(tokens, chunk)
        self._subscribed_batches = token_batches

        # Typed helper: parse message into dict or None
        def _parse_ws_message(message: Any) -> Optional[Dict[str, Any]]:
            if isinstance(message, dict):
                return cast(Dict[str, Any], message)
            if isinstance(message, (bytes, bytearray)):
                try:
                    text = message.decode("utf-8", errors="ignore")
                except Exception:
                    return None
                try:
                    obj = json.loads(text)
                except Exception:
                    return None
                return cast(Dict[str, Any], obj) if isinstance(obj, dict) else None
            if isinstance(message, str):
                try:
                    obj = json.loads(message)
                except Exception:
                    return None
                return cast(Dict[str, Any], obj) if isinstance(obj, dict) else None
            return None

        def _emit_ticks_from_dict(data_dict: Dict[str, Any]) -> None:
            payload = (
                data_dict.get("data")
                or data_dict.get("message")
                or data_dict.get("msg")
            )
            if isinstance(payload, list):
                ticks = payload
            elif isinstance(payload, dict):
                ticks = [payload]
            else:
                ticks = (
                    [data_dict]
                    if (
                        "token" in data_dict
                        or "ltp" in data_dict
                        or "last_traded_price" in data_dict
                    )
                    else []
                )

            topic = data_dict.get("topic") or data_dict.get("symbol")
            derived_token: Optional[str] = None
            if isinstance(topic, str) and "|" in topic:
                derived_token = topic.split("|", 1)[1].strip()

            for tick in ticks:
                if not isinstance(tick, dict):
                    continue
                tok = tick.get("token")
                if tok is None and derived_token:
                    tok = derived_token
                if tok is None:
                    continue
                try:
                    tick["token"] = str(tok)
                except Exception:
                    continue
                if "exchange_type" not in tick and "exchangeType" in tick:
                    tick["exchange_type"] = tick["exchangeType"]
                on_tick(tick)

        # Pylance expects param name "data" for on_data
        def _on_data(wsapp, data):
            try:
                data_dict = _parse_ws_message(data)
                if data_dict is None:
                    return
                _emit_ticks_from_dict(data_dict)
            except Exception as e:
                logger.error("on_data handler error: %s", str(e))

        def _subscribe_batch(batch_idx: int, batch: List[str]) -> None:
            """
            Handle different subscribe signatures across versions:
            - subscribe(correlation_id, mode, token_list)
            - subscribe(correlation_id=..., mode=..., token_list=...)
            - subscribe(payload_dict)
            """
            token_list = [{"exchangeType": EXCHANGE_TYPE_NSE_CM, "tokens": batch}]
            corr_id = f"corr-{batch_idx}"

            # Try payload dict first
            try:
                sws_any.subscribe(
                    {
                        "correlationID": corr_id,
                        "action": 1,
                        "params": {"mode": use_mode, "tokenList": token_list},
                    }
                )
                return
            except TypeError:
                pass
            except Exception as e:
                logger.debug("Subscribe via payload failed: %s", e)

            # Try named args
            try:
                sws_any.subscribe(
                    correlation_id=corr_id, mode=use_mode, token_list=token_list
                )
                return
            except TypeError:
                pass
            except Exception as e:
                logger.debug("Subscribe via named args failed: %s", e)

            # Try positional args
            sws_any.subscribe(corr_id, use_mode, token_list)

        def _on_open(wsapp):
            logger.info(
                "WebSocket opened, subscribing to %d tokens in %d batch(es)",
                len(tokens),
                len(token_batches),
            )
            for i, batch in enumerate(token_batches, start=1):
                try:
                    _subscribe_batch(i, batch)
                    logger.info("Subscribed batch %d (%d tokens)", i, len(batch))
                except Exception as e:
                    logger.error("Subscribe failed for batch %d: %s", i, str(e))

        def _on_error(wsapp, error):
            logger.error("WebSocket error: %s", str(error))

        def _on_close(wsapp):
            logger.warning("WebSocket closed")

        # Assign callbacks
        sws_any.on_open = _on_open
        sws_any.on_data = _on_data
        sws_any.on_error = _on_error
        sws_any.on_close = _on_close

        sws_any.connect()
