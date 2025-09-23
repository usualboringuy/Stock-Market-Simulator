from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from ..auth import clear_session_cookies, set_session_cookies
from ..config import settings
from ..deps import current_user
from ..repositories import sessions as sessions_repo
from ..repositories import users as users_repo
from ..schemas import LoginRequest, SignupRequest, UserOut
from ..security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user_doc) -> UserOut:
    ca = user_doc.get("created_at")
    iso = ca.isoformat() if isinstance(ca, datetime) else str(ca)
    return UserOut(username=user_doc["username"], created_at=iso)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response):
    user = users_repo.get_by_username(payload.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )
    try:
        user = users_repo.create_user(payload.username, payload.password)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )
    sess = sessions_repo.create_session(
        user["_id"], ttl_seconds=settings.session_ttl_seconds
    )
    set_session_cookies(response, sess["session_id"], sess["csrf_token"])
    return _user_out(user)


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response):
    user = users_repo.get_by_username(payload.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    sess = sessions_repo.create_session(
        user["_id"], ttl_seconds=settings.session_ttl_seconds
    )
    set_session_cookies(response, sess["session_id"], sess["csrf_token"])
    return _user_out(user)


@router.post("/logout")
def logout(response: Response, request: Request):
    sid = request.cookies.get(settings.session_cookie_name)
    if sid:
        sessions_repo.delete_session(sid)
    clear_session_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return _user_out(user)
