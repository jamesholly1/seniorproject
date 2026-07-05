import sys
import types

# Mock streamlit so stooq_data / finance_data_improved import without a running Streamlit app
_st = types.ModuleType("streamlit")

def _cache_data(func=None, *, ttl=None, show_spinner=True, **_kw):
    if func is not None:
        return func
    def decorator(f):
        return f
    return decorator

_st.cache_data = _cache_data
_st.session_state = {}
for _name in ("error", "warning", "success", "info", "write", "spinner"):
    setattr(_st, _name, lambda *a, **kw: None)

sys.modules["streamlit"] = _st

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt

from database import (
    authenticate_user, create_user, get_user_by_username,
    get_user_tickers, add_user_ticker, remove_user_ticker, clear_user_tickers,
)
from stooq_data import get_stock_info, get_historical_data

SECRET_KEY = os.getenv("JWT_SECRET", "jrg-trading-secret-2024")
ALGORITHM = "HS256"

app = FastAPI(title="JRG Trading API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    username: str
    password: str

class RegisterBody(BaseModel):
    username: str
    email: str
    password: str

class AddTickerBody(BaseModel):
    ticker: str


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _create_token(user_id: int, username: str) -> str:
    return jwt.encode({"user_id": user_id, "username": username}, SECRET_KEY, algorithm=ALGORITHM)


def _current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginBody):
    user_id = authenticate_user(body.username, body.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _create_token(user_id, body.username)
    return {"token": token, "user_id": user_id, "username": body.username}


@app.post("/api/auth/register")
def register(body: RegisterBody):
    success, message = create_user(body.username, body.email, body.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@app.get("/api/auth/me")
def me(user: dict = Depends(_current_user)):
    data = get_user_by_username(user["username"])
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


# ── Portfolio routes ──────────────────────────────────────────────────────────

@app.get("/api/portfolio")
def get_portfolio(user: dict = Depends(_current_user)):
    tickers = get_user_tickers(user["user_id"])
    return {"tickers": tickers}


@app.post("/api/portfolio/add")
def add_to_portfolio(body: AddTickerBody, user: dict = Depends(_current_user)):
    ticker = body.ticker.upper().strip()
    success = add_user_ticker(user["user_id"], ticker)
    if not success:
        raise HTTPException(status_code=400, detail="Ticker may already be in portfolio")
    return {"success": True, "ticker": ticker}


@app.delete("/api/portfolio/{ticker}")
def remove_from_portfolio(ticker: str, user: dict = Depends(_current_user)):
    success = remove_user_ticker(user["user_id"], ticker.upper())
    return {"success": success}


@app.delete("/api/portfolio")
def clear_portfolio(user: dict = Depends(_current_user)):
    success = clear_user_tickers(user["user_id"])
    return {"success": success}


# ── Stock routes ──────────────────────────────────────────────────────────────

@app.get("/api/stocks/{ticker}")
def stock_info(ticker: str, user: dict = Depends(_current_user)):
    return get_stock_info(ticker.upper())


@app.get("/api/stocks/{ticker}/history")
def stock_history(ticker: str, period: str = "1mo", user: dict = Depends(_current_user)):
    df = get_historical_data(ticker.upper(), period)
    if df.empty:
        return {"data": []}
    df = df.reset_index()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    return {"data": df.to_dict(orient="records")}


# ── Chart routes ──────────────────────────────────────────────────────────────

@app.get("/api/charts/sp500")
def sp500_history(period: str = "1mo", user: dict = Depends(_current_user)):
    df = get_historical_data("GSPC", period)
    if df.empty:
        return {"data": []}
    df = df.reset_index()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    return {"data": df.to_dict(orient="records")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
