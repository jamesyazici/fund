from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest,
    TrailingStopOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus
from . import db


def _tif(time_in_force: str) -> TimeInForce:
    return TimeInForce(time_in_force.lower())


def _to_log(order, order_type: str) -> dict:
    return {
        "alpaca_order_id":  str(order.id),
        "symbol":           order.symbol,
        "side":             order.side.value.lower(),
        "order_type":       order_type,
        "qty":              float(order.qty) if order.qty else None,
        "notional":         float(order.notional) if order.notional else None,
        "limit_price":      float(order.limit_price) if order.limit_price else None,
        "filled_qty":       float(order.filled_qty) if order.filled_qty else None,
        "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
        "status":           order.status.value if order.status else None,
    }


def buy(client: TradingClient, account_id: str, symbol: str, qty: float,
        order_type: str = "market", limit_price: float = None,
        time_in_force: str = "day"):
    sym = symbol.upper()
    if order_type.lower() == "limit":
        req = LimitOrderRequest(symbol=sym, qty=qty, side=OrderSide.BUY,
                                time_in_force=_tif(time_in_force), limit_price=limit_price)
    else:
        req = MarketOrderRequest(symbol=sym, qty=qty, side=OrderSide.BUY,
                                 time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, order_type.lower()))
    return order


def sell(client: TradingClient, account_id: str, symbol: str, qty: float,
         order_type: str = "market", limit_price: float = None,
         time_in_force: str = "day"):
    sym = symbol.upper()
    if order_type.lower() == "limit":
        req = LimitOrderRequest(symbol=sym, qty=qty, side=OrderSide.SELL,
                                time_in_force=_tif(time_in_force), limit_price=limit_price)
    else:
        req = MarketOrderRequest(symbol=sym, qty=qty, side=OrderSide.SELL,
                                 time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, order_type.lower()))
    return order


def short(client: TradingClient, account_id: str, symbol: str, qty: float,
          time_in_force: str = "day"):
    req = MarketOrderRequest(symbol=symbol.upper(), qty=qty, side=OrderSide.SELL,
                             time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "short"))
    return order


def cover(client: TradingClient, account_id: str, symbol: str, qty: float,
          time_in_force: str = "day"):
    req = MarketOrderRequest(symbol=symbol.upper(), qty=qty, side=OrderSide.BUY,
                             time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "cover"))
    return order


def dollar_buy(client: TradingClient, account_id: str, symbol: str, amount: float,
               time_in_force: str = "day"):
    req = MarketOrderRequest(symbol=symbol.upper(), notional=amount, side=OrderSide.BUY,
                             time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "dollar_buy"))
    return order


def dollar_sell(client: TradingClient, account_id: str, symbol: str, amount: float,
                time_in_force: str = "day"):
    req = MarketOrderRequest(symbol=symbol.upper(), notional=amount, side=OrderSide.SELL,
                             time_in_force=_tif(time_in_force))
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "dollar_sell"))
    return order


def bracket_order(client: TradingClient, account_id: str, symbol: str, qty: float,
                  side: str, take_profit: float, stop_loss: float,
                  time_in_force: str = "day"):
    req = MarketOrderRequest(
        symbol=symbol.upper(), qty=qty,
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=_tif(time_in_force),
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(limit_price=take_profit),
        stop_loss=StopLossRequest(stop_price=stop_loss),
    )
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "bracket"))
    return order


def trailing_stop(client: TradingClient, account_id: str, symbol: str, qty: float,
                  trail_percent: float, side: str = "sell"):
    req = TrailingStopOrderRequest(
        symbol=symbol.upper(), qty=qty,
        side=OrderSide.SELL if side.lower() == "sell" else OrderSide.BUY,
        time_in_force=TimeInForce.GTC,
        trail_percent=trail_percent,
    )
    order = client.submit_order(req)
    db.log_trade(account_id, _to_log(order, "trailing_stop"))
    return order


def get_open_orders(client: TradingClient):
    return client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))


def cancel_order(client: TradingClient, order_id: str):
    client.cancel_order_by_id(order_id)
    print(f"Order {order_id} cancelled.")


def cancel_all_orders(client: TradingClient):
    client.cancel_orders()
    print("All open orders cancelled.")


def get_order_history(client: TradingClient, limit: int = 100):
    return client.get_orders(GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=limit))
