from __future__ import annotations

from typing import Annotated, Dict, Literal, Optional

from pydantic import BaseModel, Field
from pydantic.types import StringConstraints

# Pydantic v2-friendly string constraints
Username = Annotated[
    str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
]
Password = Annotated[str, StringConstraints(min_length=6, max_length=128)]


class SignupRequest(BaseModel):
    username: Username
    password: Password


class LoginRequest(BaseModel):
    username: Username
    password: Password


class UserOut(BaseModel):
    username: str
    created_at: str


class PortfolioPosition(BaseModel):
    symbol: str
    quantity: int = Field(ge=0)
    avg_price: float


class PortfolioOut(BaseModel):
    cash: float
    realized_pl: float
    positions: Dict[str, PortfolioPosition]
    updated_at: str
    rev: int


Side = Literal["BUY", "SELL"]


class TradeRequest(BaseModel):
    symbol: Optional[str] = None
    token: Optional[str] = None
    side: Side
    quantity: int = Field(gt=0)


class TradeOut(BaseModel):
    symbol: str
    token: str
    side: Side
    quantity: int
    price: float
    amount: float
    realized_pl: float
    executed_at: str


# New: deposit request for adding cash
class DepositRequest(BaseModel):
    amount: Annotated[float, Field(gt=0, lt=1_000_000_000)]
