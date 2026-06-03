"""Alpaca access, per pod.

Each pod has its own Alpaca (paper) account. Credentials come from
pod_alpaca_credentials; if a pod has no row, we fall back to the ALPACA_API_KEY /
ALPACA_API_SECRET env vars so a single pod can be validated end-to-end without
storing secrets in the DB.

This is the ONLY place Alpaca keys are used. They never leave the backend.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetPortfolioHistoryRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from .config import get_settings
from . import db


# ── Credential resolution ────────────────────────────────────────────────────

def _resolve_creds(pod_id: str):
    creds = db.get_pod_alpaca(pod_id)
    if creds and creds.get("api_key") and creds.get("api_secret"):
        return creds["api_key"], creds["api_secret"]
    s = get_settings()
    if s.alpaca_api_key and s.alpaca_api_secret:
        return s.alpaca_api_key, s.alpaca_api_secret
    raise HTTPException(
        status_code=400,
        detail=("Pod has no Alpaca credentials. Set them via "
                "POST /admin/pods/{id}/alpaca, or set ALPACA_API_KEY/SECRET in the backend env."),
    )


def trading_client(pod_id: str) -> TradingClient:
    key, secret = _resolve_creds(pod_id)
    return TradingClient(key, secret, paper=get_settings().alpaca_paper)


def data_client(pod_id: str) -> StockHistoricalDataClient:
    key, secret = _resolve_creds(pod_id)
    return StockHistoricalDataClient(key, secret)


# ── Orders ───────────────────────────────────────────────────────────────────

def _tif(value: str) -> TimeInForce:
    return TimeInForce(value.lower())


def submit_order(pod_id: str, *, symbol: str, side: str, qty: float = None,
                 notional: float = None, order_type: str = "market",
                 limit_price: float = None, time_in_force: str = "day"):
    tc = trading_client(pod_id)
    sym = symbol.upper()
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    if order_type.lower() == "limit":
        if limit_price is None:
            raise HTTPException(400, "limit_price is required for limit orders.")
        req = LimitOrderRequest(symbol=sym, qty=qty, side=order_side,
                                time_in_force=_tif(time_in_force), limit_price=limit_price)
    else:
        req = MarketOrderRequest(symbol=sym, qty=qty, notional=notional,
                                 side=order_side, time_in_force=_tif(time_in_force))
    try:
        return tc.submit_order(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Alpaca rejected the order: {e}")


def to_trade_row(order, order_type_label: str, asset_class: str) -> dict:
    """Map an Alpaca order onto the `trades` table columns."""
    qty          = float(order.qty) if order.qty else None
    filled_qty   = float(order.filled_qty) if order.filled_qty else None
    filled_price = float(order.filled_avg_price) if order.filled_avg_price else None
    limit_price  = float(order.limit_price) if getattr(order, "limit_price", None) else None

    quantity = qty if qty is not None else filled_qty
    price    = filled_price if filled_price is not None else limit_price
    notional = float(order.notional) if order.notional else (
        round(quantity * price, 2) if (quantity and price) else None
    )
    submitted = getattr(order, "submitted_at", None) or getattr(order, "created_at", None)
    executed_at = submitted.isoformat() if submitted else datetime.now(timezone.utc).isoformat()

    return {
        "alpaca_order_id": str(order.id),
        "symbol":          order.symbol,
        "side":            order.side.value.lower(),
        "order_type":      order_type_label,
        "quantity":        quantity,
        "price":           price,
        "notional":        notional,
        "limit_price":     limit_price,
        "filled_qty":      filled_qty,
        "status":          order.status.value if order.status else None,
        "asset_class":     asset_class,
        "executed_at":     executed_at,
    }


def cancel_order(pod_id: str, order_id: str) -> None:
    trading_client(pod_id).cancel_order_by_id(order_id)


# ── Account, positions, history ──────────────────────────────────────────────

def get_account(pod_id: str) -> dict:
    acct = trading_client(pod_id).get_account()
    return {
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
        "status": str(acct.status),
    }


def get_positions(pod_id: str) -> list:
    positions = trading_client(pod_id).get_all_positions()
    return [{
        "symbol":          p.symbol,
        "quantity":        float(p.qty),
        "avg_entry_price": float(p.avg_entry_price),
        "current_price":   float(p.current_price) if p.current_price else None,
        "market_value":    float(p.market_value) if p.market_value else None,
        "unrealized_pnl":  float(p.unrealized_pl) if p.unrealized_pl else None,
    } for p in positions]


def get_nav_history(pod_id: str, days: int = 365) -> list:
    """Daily NAV rows from Alpaca's portfolio history."""
    tc = trading_client(pod_id)
    date_start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    hist = tc.get_portfolio_history(
        GetPortfolioHistoryRequest(date_start=date_start, timeframe="1D")
    )
    rows = []
    prev_equity = None
    for ts, equity in zip(hist.timestamp, hist.equity):
        if equity is None:
            continue
        equity = float(equity)
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        daily_return = ((equity / prev_equity - 1) if prev_equity else None)
        rows.append({
            "date": date,
            "nav": round(equity, 2),
            "cash": 0,
            "daily_return": round(daily_return, 6) if daily_return is not None else None,
        })
        prev_equity = equity
    return rows


# ── Market data ──────────────────────────────────────────────────────────────

def get_price(pod_id: str, symbol: str) -> float:
    dc = data_client(pod_id)
    req = StockLatestTradeRequest(symbol_or_symbols=symbol.upper())
    trade = dc.get_stock_latest_trade(req)[symbol.upper()]
    return float(trade.price)


def get_bars(pod_id: str, symbol: str, days: int = 30) -> list:
    dc = data_client(pod_id)
    start = (datetime.now(timezone.utc) - timedelta(days=days))
    req = StockBarsRequest(symbol_or_symbols=symbol.upper(),
                           timeframe=TimeFrame.Day, start=start)
    bars = dc.get_stock_bars(req).data.get(symbol.upper(), [])
    return [{
        "date": b.timestamp.strftime("%Y-%m-%d"),
        "open": float(b.open), "high": float(b.high),
        "low": float(b.low), "close": float(b.close), "volume": float(b.volume),
    } for b in bars]
