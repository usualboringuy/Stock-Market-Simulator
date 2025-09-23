from __future__ import annotations

from typing import Literal, Optional, cast

from fastapi import Response

from .config import settings


def _samesite_value() -> Literal["lax", "strict", "none"]:
    val = settings.cookie_samesite.lower()
    if val not in ("lax", "strict", "none"):
        val = "lax"
    # tell the type checker this is one of the allowed literals
    return cast(Literal["lax", "strict", "none"], val)


def set_session_cookies(response: Response, session_id: str, csrf_token: str) -> None:
    domain: Optional[str] = settings.cookie_domain or None
    samesite = _samesite_value()
    max_age = int(settings.session_ttl_seconds)
    secure = bool(settings.cookie_secure)

    # HttpOnly session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=max_age,
        expires=None,
        path="/",
        domain=domain,
        secure=secure,
        httponly=True,
        samesite=samesite,
    )
    # Non-HttpOnly CSRF cookie (double-submit)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max_age,
        expires=None,
        path="/",
        domain=domain,
        secure=secure,
        httponly=False,
        samesite=samesite,
    )


def clear_session_cookies(response: Response) -> None:
    domain: Optional[str] = settings.cookie_domain or None
    samesite = _samesite_value()
    for key in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            key=key,
            path="/",
            domain=domain,
            samesite=samesite,
        )
