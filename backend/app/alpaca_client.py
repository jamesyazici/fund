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
    settings = get_settings()
    return TradingClient(
        key,
        secret,
        paper=settings.alpaca_paper,
        url_override=settings.alpaca_trading_base_url,
    )


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
        round(abs(quantity * price), 2) if (quantity is not None and price is not None) else None
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
    last_equity = float(acct.last_equity) if getattr(acct, "last_equity", None) else None
    equity = float(acct.equity)
    return {
        "equity": equity,
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
        "last_equity": last_equity,
        "session_return": ((equity / last_equity) - 1) if last_equity else None,
        "status": str(acct.status),
    }


def get_positions(pod_id: str) -> list:
    positions = trading_client(pod_id).get_all_positions()
    symbols = [p.symbol for p in positions]
    latest_prices = get_latest_prices(pod_id, symbols) if symbols else {}
    rows = []
    for p in positions:
        quantity = float(p.qty)
        avg_entry = float(p.avg_entry_price)
        latest_price = latest_prices.get(p.symbol)
        current_price = latest_price if latest_price is not None else (
            float(p.current_price) if p.current_price else None
        )
        market_value = (quantity * current_price) if current_price is not None else (
            float(p.market_value) if p.market_value else None
        )
        unrealized_pnl = ((current_price - avg_entry) * quantity) if current_price is not None else (
            float(p.unrealized_pl) if p.unrealized_pl else None
        )
        rows.append({
            "symbol":          p.symbol,
            "quantity":        quantity,
            "avg_entry_price": avg_entry,
            "current_price":   round(current_price, 4) if current_price is not None else None,
            "market_value":    round(market_value, 2) if market_value is not None else None,
            "unrealized_pnl":  round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
        })
    return rows


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


def get_intraday_nav_history(pod_id: str, minutes: int = 390) -> list:
    """Minute NAV rows from Alpaca portfolio history for live charts."""
    tc = trading_client(pod_id)
    minutes = max(1, min(int(minutes or 390), 1440))
    date_start = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%d")
    hist = tc.get_portfolio_history(
        GetPortfolioHistoryRequest(date_start=date_start, timeframe="1Min")
    )
    rows = []
    prev_equity = None
    for ts, equity in zip(hist.timestamp, hist.equity):
        if equity is None:
            continue
        equity = float(equity)
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        minute_return = ((equity / prev_equity - 1) if prev_equity else None)
        rows.append({
            "timestamp": timestamp,
            "nav": round(equity, 2),
            "minute_return": round(minute_return, 6) if minute_return is not None else None,
        })
        prev_equity = equity
    return rows


def get_position_notional_history(pod_id: str, minutes: int = 390) -> list:
    """Minute-level gross/net notional for current holdings using 1Min bars."""
    positions = trading_client(pod_id).get_all_positions()
    holdings = {p.symbol: float(p.qty) for p in positions if float(p.qty) != 0}
    if not holdings:
        return []

    dc = data_client(pod_id)
    minutes = max(1, min(int(minutes or 390), 1440))
    start = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    req = StockBarsRequest(
        symbol_or_symbols=list(holdings.keys()),
        timeframe=TimeFrame.Minute,
        start=start,
    )
    bars_by_symbol = dc.get_stock_bars(req).data
    by_ts: dict[str, dict] = {}
    for symbol, bars in bars_by_symbol.items():
        qty = holdings.get(symbol, 0)
        for bar in bars:
            ts = bar.timestamp.replace(second=0, microsecond=0).isoformat()
            row = by_ts.setdefault(ts, {"timestamp": ts, "gross_notional": 0.0, "net_notional": 0.0})
            value = qty * float(bar.close)
            row["gross_notional"] += abs(value)
            row["net_notional"] += value

    return [
        {
            "timestamp": row["timestamp"],
            "gross_notional": round(row["gross_notional"], 2),
            "net_notional": round(row["net_notional"], 2),
        }
        for row in sorted(by_ts.values(), key=lambda r: r["timestamp"])
    ]


# ── Market data ──────────────────────────────────────────────────────────────

def get_price(pod_id: str, symbol: str) -> float:
    dc = data_client(pod_id)
    req = StockLatestTradeRequest(symbol_or_symbols=symbol.upper())
    trade = dc.get_stock_latest_trade(req)[symbol.upper()]
    return float(trade.price)


def get_latest_prices(pod_id: str, symbols: list[str]) -> dict[str, float]:
    if not symbols:
        return {}
    dc = data_client(pod_id)
    upper = [s.upper() for s in symbols]
    try:
        trades = dc.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=upper))
        return {symbol: float(trades[symbol].price) for symbol in upper if symbol in trades}
    except Exception:
        prices = {}
        for symbol in upper:
            try:
                prices[symbol] = get_price(pod_id, symbol)
            except Exception:
                continue
        return prices


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
