# src/api/models.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SignupIn(BaseModel):
    username: str
    password: str
    initial_cash: float = 0.0


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str = Field(..., alias="_id")
    username: str


class TradeIn(BaseModel):
    token: str
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    price: float


class TradeOut(BaseModel):
    id: str = Field(..., alias="_id")
    token: str
    symbol: str
    side: str
    quantity: int
    price: float
    amount: float
    realized_pl: float
    executed_at: datetime


class PositionOut(BaseModel):
    token: str
    symbol: str
    quantity: int
    avg_price: float
    last_price: Optional[float] = None
    unrealized_pl: Optional[float] = None


class PortfolioOut(BaseModel):
    cash: float
    realized_pl: float
    positions: List[PositionOut]
    totals: Dict[str, Any]


class QuoteOut(BaseModel):
    symbol: str
    token: str
    price: Optional[float] = None
    timestamp: Optional[datetime] = None
    percent_change: Optional[float] = None


class TopGainerOut(BaseModel):
    symbol: str
    token: str
    price: Optional[float] = None
    percent_change: Optional[float] = None
    timestamp: Optional[datetime] = None
