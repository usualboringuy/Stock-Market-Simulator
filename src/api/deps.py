# src/api/deps.py
from fastapi import Cookie, HTTPException, status
from typing import Optional, Dict, Any
from bson import ObjectId

from src.db.sessions import get_session
from src.db.users import get_user_by_id
from src.config import Config


def get_current_user(
    session_id: Optional[str] = Cookie(default=None, alias=Config.COOKIE_NAME)
) -> Dict[str, Any]:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    sdoc = get_session(session_id)
    if not sdoc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )
    user = get_user_by_id(sdoc["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    # Normalize _id to str for responses if needed
    user["_id"] = str(user["_id"])
    return user
