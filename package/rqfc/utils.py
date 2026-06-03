from alpaca.trading.client import TradingClient


def is_market_open(client: TradingClient) -> bool:
    """Returns True if the US stock market is currently open."""
    return client.get_clock().is_open


def get_market_clock(client: TradingClient) -> dict:
    """Current market status and time to next open/close."""
    clock = client.get_clock()
    now = clock.timestamp
    if clock.is_open:
        delta = clock.next_close - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        time_to_open = "Market is open"
        time_to_close = f"{hours}h {minutes}m until close"
    else:
        delta = clock.next_open - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        time_to_open = f"{hours}h {minutes}m until open"
        time_to_close = "Market is closed"
    return {
        "is_open":       clock.is_open,
        "current_time":  clock.timestamp,
        "next_open":     clock.next_open,
        "next_close":    clock.next_close,
        "time_to_open":  time_to_open,
        "time_to_close": time_to_close,
    }
