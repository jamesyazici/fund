import re
from datetime import datetime, timedelta

import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
    StockSnapshotRequest,
    NewsRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus


def _parse_timeframe(tf: str) -> TimeFrame:
    mapping = {
        "1MIN": TimeFrame.Minute, "1D": TimeFrame.Day,
        "1H": TimeFrame.Hour, "1W": TimeFrame.Week, "1MONTH": TimeFrame.Month,
    }
    key = tf.upper().replace("MIN", "MIN").replace("HOUR", "H")
    if key in mapping:
        return mapping[key]
    match = re.match(r"(\d+)(MIN|H|HOUR|DAY)", key)
    if match:
        amount = int(match.group(1))
        unit_map = {
            "MIN": TimeFrameUnit.Minute, "H": TimeFrameUnit.Hour,
            "HOUR": TimeFrameUnit.Hour, "DAY": TimeFrameUnit.Day,
        }
        return TimeFrame(amount, unit_map[match.group(2)])
    raise ValueError(f"Unknown timeframe '{tf}'. Examples: '1D', '1H', '5Min', '15Min', '1W'")


def _resolve_dates(days, start, end):
    if days:
        return datetime.now() - timedelta(days=days), datetime.now()
    elif start:
        return datetime.fromisoformat(start), (datetime.fromisoformat(end) if end else datetime.now())
    return datetime.now() - timedelta(days=365), datetime.now()


def get_price(data_client: StockHistoricalDataClient, symbol: str) -> float:
    sym = symbol.upper()
    trade = data_client.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=sym))
    return float(trade[sym].price)


def get_quote(data_client: StockHistoricalDataClient, symbol: str) -> dict:
    sym = symbol.upper()
    quote = data_client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=sym))
    q = quote[sym]
    return {
        "symbol":   sym,
        "bid":      float(q.bid_price),
        "bid_size": q.bid_size,
        "ask":      float(q.ask_price),
        "ask_size": q.ask_size,
        "spread":   round(float(q.ask_price) - float(q.bid_price), 4),
    }


def get_bars(data_client: StockHistoricalDataClient, symbol: str, timeframe: str = "1D",
             days: int = None, start: str = None, end: str = None) -> pd.DataFrame:
    start_dt, end_dt = _resolve_dates(days, start, end)
    sym = symbol.upper()
    req = StockBarsRequest(
        symbol_or_symbols=sym,
        timeframe=_parse_timeframe(timeframe),
        start=start_dt,
        end=end_dt,
    )
    bars = data_client.get_stock_bars(req)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[sym]
    return df


def get_snapshot(data_client: StockHistoricalDataClient, symbol: str) -> dict:
    sym = symbol.upper()
    snap = data_client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=sym))
    s = snap[sym]
    prev_close = float(s.prev_daily_bar.close)
    close = float(s.daily_bar.close)
    return {
        "symbol":     sym,
        "price":      float(s.latest_trade.price),
        "bid":        float(s.latest_quote.bid_price),
        "ask":        float(s.latest_quote.ask_price),
        "open":       float(s.daily_bar.open),
        "high":       float(s.daily_bar.high),
        "low":        float(s.daily_bar.low),
        "close":      close,
        "prev_close": prev_close,
        "volume":     s.daily_bar.volume,
        "change_pct": round((close - prev_close) / prev_close * 100, 2),
    }


def get_snapshots(data_client: StockHistoricalDataClient, symbols: list) -> pd.DataFrame:
    syms = [s.upper() for s in symbols]
    snaps = data_client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=syms))
    rows = []
    for sym, s in snaps.items():
        try:
            prev_close = float(s.prev_daily_bar.close)
            close = float(s.daily_bar.close)
            rows.append({
                "symbol":     sym,
                "price":      float(s.latest_trade.price),
                "bid":        float(s.latest_quote.bid_price),
                "ask":        float(s.latest_quote.ask_price),
                "open":       float(s.daily_bar.open),
                "high":       float(s.daily_bar.high),
                "low":        float(s.daily_bar.low),
                "close":      close,
                "volume":     s.daily_bar.volume,
                "change_pct": round((close - prev_close) / prev_close * 100, 2),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def get_news(data_client: StockHistoricalDataClient, symbol: str, limit: int = 10) -> pd.DataFrame:
    news = data_client.get_news(NewsRequest(symbols=[symbol.upper()], limit=limit))
    return pd.DataFrame([{
        "headline":  n.headline,
        "source":    n.source,
        "published": n.created_at,
        "url":       n.url,
    } for n in news])


_SCAN_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "UNH",
    "XOM", "MA", "JNJ", "PG", "HD", "CVX", "MRK", "ABBV", "PEP", "KO", "COST",
    "AVGO", "WMT", "BAC", "LLY", "TMO", "CSCO", "ACN", "ABT", "CRM", "DHR",
    "TXN", "NEE", "NKE", "QCOM", "UPS", "BMY", "RTX", "SPGI", "LIN", "AMGN",
    "INTC", "SBUX", "INTU", "ADBE", "GILD", "AMD", "MU", "NOW", "PYPL", "NFLX",
    "DIS", "BA", "GS", "MS", "BLK", "AXP", "TGT", "DE", "CAT", "IBM", "F", "GM",
    "UBER", "LYFT", "SNAP", "SHOP", "SPOT", "COIN", "PLTR", "SOFI", "RIVN", "LCID",
]


def get_top_movers(data_client: StockHistoricalDataClient, n: int = 10) -> dict:
    df = get_snapshots(data_client, _SCAN_UNIVERSE)
    if df.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame()}
    df = df.sort_values("change_pct", ascending=False)
    return {
        "gainers": df.head(n).reset_index(drop=True),
        "losers":  df.tail(n).sort_values("change_pct").reset_index(drop=True),
    }


def get_assets(trading_client: TradingClient, asset_class: str = "us_equity") -> list:
    cls = AssetClass.US_EQUITY if asset_class.lower() == "us_equity" else AssetClass.CRYPTO
    return trading_client.get_all_assets(GetAssetsRequest(asset_class=cls, status=AssetStatus.ACTIVE))


def is_tradeable(trading_client: TradingClient, symbol: str) -> bool:
    try:
        return trading_client.get_asset(symbol.upper()).tradable
    except Exception:
        return False
