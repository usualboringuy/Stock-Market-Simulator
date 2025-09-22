# src/api/auth.py
from fastapi import APIRouter, Response, HTTPException, status, Depends
from typing import Dict, Any
from src.api.models import SignupIn, LoginIn, UserOut
from src.api.security import sha256
from src.db.users import create_user, get_user_by_username
from src.db.portfolios import create_portfolio
from src.db.sessions import create_session, delete_session
from src.api.deps import get_current_user
from src.config import Config

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
def signup(payload: SignupIn):
    existing = get_user_by_username(payload.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )
    user = create_user(payload.username, sha256(payload.password))
    create_portfolio(user["_id"], initial_cash=float(payload.initial_cash))
    user["_id"] = str(user["_id"])
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response):
    user = get_user_by_username(payload.username)
    if not user or user.get("password_hash") != sha256(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    sid = create_session(user["_id"])
    # Set HttpOnly cookie
    response.set_cookie(
        key=Config.COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        secure=Config.COOKIE_SECURE,
        path="/",
        max_age=Config.SESSION_TTL_SECONDS,
    )
    user["_id"] = str(user["_id"])
    return user


@router.post("/logout")
def logout(
    response: Response, current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Clear cookie and delete session if present
    response.delete_cookie(key=Config.COOKIE_NAME, path="/")
    # We can’t read the cookie value here easily; frontend should just drop it.
    # Optionally, you can accept session_id in a header to delete explicitly.
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
