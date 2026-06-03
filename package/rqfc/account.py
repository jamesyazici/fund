from collections import deque
from datetime import datetime, timedelta

import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest, GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus, OrderSide
from . import trading as _trading


def get_account(client: TradingClient):
    return client.get_account()


def get_portfolio_value(client: TradingClient) -> float:
    return float(get_account(client).portfolio_value)


def get_buying_power(client: TradingClient) -> float:
    return float(get_account(client).buying_power)


def get_pnl(client: TradingClient) -> dict:
    positions = client.get_all_positions()
    unrealized = sum(float(p.unrealized_pl) for p in positions)
    acct = get_account(client)
    realized = float(acct.equity) - float(acct.last_equity) - unrealized
    return {
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl":   round(realized, 2),
        "total_pnl":      round(unrealized + realized, 2),
    }


def get_position(client: TradingClient, symbol: str):
    return client.get_open_position(symbol.upper())


def get_all_positions(client: TradingClient):
    return client.get_all_positions()


def get_portfolio_summary(client: TradingClient) -> pd.DataFrame:
    positions = client.get_all_positions()
    if not positions:
        print("No open positions.")
        return pd.DataFrame()
    total_value = get_portfolio_value(client)
    rows = []
    for p in positions:
        mv = float(p.market_value)
        rows.append({
            "symbol":           p.symbol,
            "qty":              float(p.qty),
            "avg_entry":        float(p.avg_entry_price),
            "current_price":    float(p.current_price),
            "market_value":     round(mv, 2),
            "pct_of_portfolio": round(mv / total_value * 100, 2),
            "unrealized_pnl":   round(float(p.unrealized_pl), 2),
            "unrealized_pnl_pct": round(float(p.unrealized_plpc) * 100, 2),
        })
    return (
        pd.DataFrame(rows)
        .sort_values("market_value", ascending=False)
        .reset_index(drop=True)
    )


def close_position(client: TradingClient, symbol: str):
    client.close_position(symbol.upper())
    print(f"Closed position: {symbol.upper()}")


def close_all_positions(client: TradingClient):
    client.close_all_positions(cancel_orders=True)
    print("All positions closed.")


def get_concentration(client: TradingClient) -> pd.DataFrame:
    summary = get_portfolio_summary(client)
    if summary.empty:
        return summary
    return summary[["symbol", "market_value", "pct_of_portfolio"]]


def get_portfolio_history(client: TradingClient, days: int = None,
                          start: str = None, end: str = None) -> pd.DataFrame:
    if days:
        date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        req = GetPortfolioHistoryRequest(date_start=date_start, timeframe="1D")
    elif start:
        date_end = end if end else datetime.now().strftime("%Y-%m-%d")
        req = GetPortfolioHistoryRequest(date_start=start, date_end=date_end, timeframe="1D")
    else:
        req = GetPortfolioHistoryRequest(period="all", timeframe="1D")
    history = client.get_portfolio_history(req)
    df = pd.DataFrame({
        "timestamp":       pd.to_datetime(history.timestamp, unit="s"),
        "equity":          history.equity,
        "profit_loss":     history.profit_loss,
        "profit_loss_pct": [round(x * 100, 4) if x else None for x in history.profit_loss_pct],
    })
    return df.set_index("timestamp")


def get_portfolio_returns(client: TradingClient, days: int = None,
                          start: str = None, end: str = None) -> pd.Series:
    history = get_portfolio_history(client, days=days, start=start, end=end)
    return history["equity"].pct_change().dropna().rename("portfolio_returns")


def get_win_rate(client: TradingClient) -> dict:
    orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=500))
    filled = [o for o in orders if o.filled_avg_price is not None and o.filled_at is not None]
    filled.sort(key=lambda o: o.filled_at)
    by_symbol: dict = {}
    for o in filled:
        sym = o.symbol
        if sym not in by_symbol:
            by_symbol[sym] = {"buys": deque(), "sells": deque()}
        if o.side == OrderSide.BUY:
            by_symbol[sym]["buys"].append(float(o.filled_avg_price))
        else:
            by_symbol[sym]["sells"].append(float(o.filled_avg_price))
    wins, losses = 0, 0
    for trades in by_symbol.values():
        buys, sells = trades["buys"], trades["sells"]
        while buys and sells:
            if sells.popleft() > buys.popleft():
                wins += 1
            else:
                losses += 1
    total = wins + losses
    return {
        "wins":         wins,
        "losses":       losses,
        "total_trades": total,
        "win_rate":     round(wins / total * 100, 2) if total > 0 else 0.0,
    }


def rebalance(client: TradingClient, member, target_weights: dict):
    total_value = get_portfolio_value(client)
    positions = {p.symbol: float(p.market_value) for p in get_all_positions(client)}
    for sym in list(positions.keys()):
        if sym.upper() not in {k.upper() for k in target_weights}:
            close_position(client, sym)
    positions = {p.symbol: float(p.market_value) for p in get_all_positions(client)}
    for symbol, weight in target_weights.items():
        sym = symbol.upper()
        target_value = total_value * weight
        current_value = positions.get(sym, 0.0)
        diff = target_value - current_value
        if abs(diff) < 1.0:
            continue
        if diff > 0:
            print(f"  BUY  ${diff:,.2f} of {sym}")
            _trading.dollar_buy(client, member, sym, diff)
        else:
            print(f"  SELL ${abs(diff):,.2f} of {sym}")
            _trading.dollar_sell(client, member, sym, abs(diff))
    print("Rebalance complete.")
