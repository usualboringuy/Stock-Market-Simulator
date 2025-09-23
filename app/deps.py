from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status

from .config import settings
from .repositories import sessions as sessions_repo
from .repositories import users as users_repo


def current_session(request: Request):
    sid = request.cookies.get(settings.session_cookie_name)
    if not sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    sess = sessions_repo.get_session(sid)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )
    exp = sess.get("expires_at")
    if isinstance(exp, datetime) and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not exp or exp <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )
    if settings.session_sliding:
        sessions_repo.touch_session(sid, settings.session_ttl_seconds)
    return sess


def current_user(session=Depends(current_session)):
    uid = session["user_id"]
    user = users_repo.get_by_id(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_csrf(request: Request, session=Depends(current_session)):
    if not settings.csrf_enabled:
        return True
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed"
        )
    sess_token = session.get("csrf_token")
    if sess_token and cookie_token != sess_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed"
        )
    return True
