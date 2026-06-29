# RQFC Python Client — Trader Reference

Everything you can do from the `rqfc` Python package, with examples and exact return shapes.

---

## Setup

```python
import rqfc

rqfc.login("you@email.com", "yourpassword", backend_url="http://localhost:8000")
acct = rqfc.pod("your pod name")   # or use the pod's UUID
```

After login, `acct` is your trading interface. Every call goes through the backend — your Alpaca keys never touch this script.

---

## Placing Orders

### `acct.buy(symbol, qty, order_type, limit_price, time_in_force)`

Buy shares at market or limit price.

```python
acct.buy("AAPL", 10)                                          # 10 shares, market
acct.buy("AAPL", 10, order_type="limit", limit_price=180.00)  # limit buy
acct.buy("AAPL", 10, time_in_force="gtc")                     # good till cancelled
```

**Returns:** `OrderResult` (dict subclass)
```python
{
  "order_id": "d820b3ba-...",
  "status":   "filled",           # filled | accepted | partially_filled | canceled
  "trade": {
    "symbol":         "AAPL",
    "side":           "buy",
    "order_type":     "market",
    "quantity":       10.0,
    "price":          189.34,      # fill price (None if not yet filled)
    "notional":       1893.40,
    "filled_qty":     10.0,
    "filled_at":      "2026-06-25T14:30:00+00:00",
    "executed_at":    "2026-06-25T14:29:59+00:00",
    "limit_price":    None,
    "status":         "filled",
    "asset_class":    "equities",
    "multiplier":     1.0,
    "instrument_type": "equity",
    # options fields (None for equities):
    "underlying_symbol": None,
    "option_expiration": None,
    "option_type":       None,
    "option_strike":     None,
  }
}
```

If rejected, prints a friendly message and returns `None` — your script keeps running.

---

### `acct.sell(symbol, qty, order_type, limit_price, time_in_force)`

Sell shares you hold.

```python
acct.sell("AAPL", 10)
acct.sell("AAPL", 10, order_type="limit", limit_price=200.00)
```

Returns the same `OrderResult` shape as `buy()`.

---

### `acct.short(symbol, qty, time_in_force)`

Short sell — borrow and sell shares you don't own. Close with `cover()`.

```python
acct.short("TSLA", 5)
```

Returns the same `OrderResult` shape.

---

### `acct.cover(symbol, qty, time_in_force)`

Buy back shares to close a short position.

```python
acct.cover("TSLA", 5)
```

Returns the same `OrderResult` shape.

---

### `acct.dollar_buy(symbol, amount, time_in_force)`

Buy by dollar amount instead of share count. Market orders only.

```python
acct.dollar_buy("NVDA", 5000)    # buy $5,000 worth of NVDA
```

Returns the same `OrderResult` shape. `quantity` in the result will be `None` until filled because Alpaca computes it at execution.

---

### `acct.dollar_sell(symbol, amount, time_in_force)`

Sell by dollar amount.

```python
acct.dollar_sell("NVDA", 5000)
```

Returns the same `OrderResult` shape.

---

### `acct.cancel(order_id)`

Cancel an open (unfilled) order.

```python
acct.cancel("d820b3ba-6315-4a51-9274-868e933b88a4")
```

**Returns:**
```python
{"cancelled": "d820b3ba-..."}
```

---

### Time-in-force options

| Value | Meaning |
|-------|---------|
| `"day"` | Cancel at market close if unfilled (default) |
| `"gtc"` | Good till cancelled — stays open across sessions |
| `"ioc"` | Immediate or cancel — fill what you can right now, cancel the rest |
| `"fok"` | Fill or kill — fill everything immediately or cancel entirely |
| `"opg"` | Market-on-open |
| `"cls"` | Market-on-close |

---

## Reading Your Portfolio

### `acct.positions()`

All currently open positions, live from Alpaca.

```python
positions = acct.positions()

# Access like a normal list
positions[0]                          # first position
positions[0]["symbol"]                # "AAPL"
positions[0]["unrealized_pnl"]        # -1.25

# Filter, sort, etc.
winners = [p for p in positions if p["unrealized_pnl"] > 0]
by_value = sorted(positions, key=lambda p: p["market_value"], reverse=True)
```

**Returns:** `PositionList` (list of dicts)
```python
[
  {
    "symbol":          "AAPL",
    "instrument_type": "equity",      # "equity" or "option"
    "underlying_symbol": None,        # for options: e.g. "AAPL"
    "quantity":        10.0,
    "avg_entry_price": 185.50,
    "current_price":   189.34,
    "market_value":    1893.40,       # current value (qty × price)
    "cost_basis":      1855.00,       # what you paid
    "multiplier":      1.0,           # 100 for options
    "unrealized_pnl":  38.40,         # mark-to-market gain/loss
  },
  ...
]
```

---

### `acct.account()`

Live account summary plus recent performance stats.

```python
a = acct.account()

a["portfolio_value"]           # total account value
a["cash"]                      # uninvested cash
a["buying_power"]              # available to trade
a["session_return"]            # today's return as a fraction (0.012 = +1.2%)
a["return_5d"]                 # 5-trading-day return as a fraction
a["sharpe_30d"]                # annualised Sharpe ratio over the past 30 days
a["recent_days"]               # list of last 5 NAV days (see below)
```

**Returns:** `AccountSummary` (dict)
```python
{
  "equity":          191234.56,
  "cash":            45000.00,
  "buying_power":    90000.00,
  "portfolio_value": 191234.56,
  "last_equity":     189500.00,
  "session_return":  0.00915,     # +0.92% today
  "status":          "ACTIVE",
  "return_5d":       0.02341,     # +2.34% over 5 days
  "sharpe_30d":      1.4821,      # annualised Sharpe
  "recent_days": [
    {"date": "2026-06-19", "nav": 187400.00, "daily_return": 0.00412},
    {"date": "2026-06-20", "nav": 188100.00, "daily_return": 0.00373},
    {"date": "2026-06-23", "nav": 189500.00, "daily_return": 0.00744},
    {"date": "2026-06-24", "nav": 190500.00, "daily_return": 0.00527},
    {"date": "2026-06-25", "nav": 191234.56, "daily_return": 0.00386},
  ]
}
```

---

### `acct.orders(status)`

Open or recent orders directly from Alpaca.

```python
acct.orders()             # open orders (default)
acct.orders("closed")     # recently filled/cancelled orders
acct.orders("all")        # everything

# Access like a list
open_orders = acct.orders()
open_orders[0]["symbol"]
open_orders[0]["status"]
```

**Returns:** `OrderList` (list of dicts)
```python
[
  {
    "order_id":      "17c05821-...",
    "symbol":        "SNAP",
    "side":          "buy",
    "order_type":    "market",
    "qty":           1.0,
    "notional":      None,
    "filled_qty":    0.0,
    "filled_price":  None,
    "limit_price":   None,
    "status":        "new",            # new | accepted | filled | canceled | expired
    "time_in_force": "day",
    "submitted_at":  "2026-06-25T02:16:25+00:00",
    "filled_at":     None,
  },
  ...
]
```

---

### `acct.history(limit, my_trades_only)`

Completed trades from the database.

```python
acct.history()                         # all pod trades, 100 most recent
acct.history(limit=50)                 # cap at 50
acct.history(my_trades_only=True)      # only trades YOU placed in this pod
```

**Returns:** `TradeHistory` (list of dicts)
```python
[
  {
    "id":            "uuid",
    "pod_id":        "uuid",
    "trader_id":     "uuid",
    "trader_name":   "Test Trader 2",
    "pod_name":      "test2 (index)",
    "symbol":        "VTI",
    "side":          "buy",
    "order_type":    "market",
    "quantity":      250.0,
    "filled_qty":    250.0,
    "price":         369.39,
    "notional":      92347.50,
    "realized_pnl":  None,            # None until position is closed
    "fees":          0.0,
    "status":        "filled",
    "asset_class":   "equities",
    "instrument_type": "equity",
    "executed_at":   "2026-06-20T14:30:01+00:00",
    "filled_at":     "2026-06-20T14:30:01+00:00",
  },
  ...
]
```

---

## Market Data

### `acct.price(symbol)`

Latest trade price for any symbol.

```python
acct.price("AAPL")
```

**Returns:**
```python
{"symbol": "AAPL", "price": 189.34}
```

---

### `acct.bars(symbol, days)`

Daily OHLCV bars. Default 30 days, max 365.

```python
acct.bars("AAPL")           # 30 days
acct.bars("AAPL", days=90)

# Use like a list
bars = acct.bars("AAPL")
bars[-1]               # today's bar
bars[-1]["close"]      # closing price
```

**Returns:** list of dicts
```python
[
  {
    "date":   "2026-06-24",
    "open":   187.20,
    "high":   190.10,
    "low":    186.50,
    "close":  189.34,
    "volume": 52341200.0,
  },
  ...
]
```

---

## Syncing the Dashboard

### `acct.sync()`

Pushes the pod's current positions and NAV from Alpaca into the Supabase database so the web dashboard updates. Also recomputes Sharpe, drawdown, and other metrics.

```python
result = acct.sync()
result["positions"]   # number of positions synced
result["nav_days"]    # number of historical NAV days recorded
result["metrics"]     # True if metrics were updated, False if not enough history
```

**Returns:** `SyncResult` (dict)
```python
{"positions": 2, "nav_days": 20, "metrics": True}
```

---

## Display Helpers

All return types (`PositionList`, `AccountSummary`, `OrderList`, `TradeHistory`, `OrderResult`) print formatted tables when passed to `print()`. If you want clean output without `print()`, use the show methods:

```python
acct.show_account()
acct.show_positions()
acct.show_orders()
acct.show_orders("closed")
acct.show_history()
acct.show_history(limit=25, my_trades_only=True)
```

---

## Example Workflow

```python
import rqfc

rqfc.login("you@email.com", "yourpassword", backend_url="http://localhost:8000")
acct = rqfc.pod("test2 (index)")

# Check the account before doing anything
acct.show_account()

# See what's currently open
acct.show_positions()

# Check for any pending orders
acct.show_orders()

# Place a trade
result = acct.buy("VTI", 10)
if result is not None:
    print("Filled at:", result["trade"]["price"])

# See your recent trades in this pod
acct.show_history(my_trades_only=True)

# Sync to dashboard
acct.sync()
```

---

## Session Utilities

```python
rqfc.whoami()                        # your profile and pod list
rqfc.pod("name or UUID")             # switch to a different pod
rqfc.configure("http://...")         # change backend URL mid-session
```
