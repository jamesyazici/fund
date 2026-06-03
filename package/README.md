# rqfc

Python trading package for the RQFC student quant fund. Built on Alpaca's paper trading API — every student gets their own simulated portfolio with real market data. All trades are logged to a shared Supabase database so the admin can track everyone's performance.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [One-Time Setup](#one-time-setup)
  - [1. Create a Supabase project](#1-create-a-supabase-project)
  - [2. Create the database tables](#2-create-the-database-tables)
  - [3. Get your Supabase keys](#3-get-your-supabase-keys)
  - [4. Get Alpaca API keys](#4-get-alpaca-api-keys)
- [Student Guide](#student-guide)
  - [Environment setup](#environment-setup)
  - [Initializing your account](#initializing-your-account)
  - [Trading](#trading)
  - [Viewing your portfolio](#viewing-your-portfolio)
  - [Metrics](#metrics)
  - [Market data](#market-data)
  - [Market hours](#market-hours)
- [Admin Guide](#admin-guide)
  - [Environment setup](#environment-setup-admin)
  - [Initializing the admin client](#initializing-the-admin-client)
  - [Viewing all trades](#viewing-all-trades)
  - [Student summary](#student-summary)
  - [Leaderboard](#leaderboard)
  - [Per-student deep dive](#per-student-deep-dive)
- [Environment Variable Reference](#environment-variable-reference)

---

## Prerequisites

- Python 3.9 or later
- A free [Alpaca](https://alpaca.markets) account (paper trading, no money needed)
- Access to the shared Supabase project (the admin will give you the URL and key)

---

## Installation

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install alpaca-py pandas numpy supabase
```

---

## One-Time Setup

> This section is for the **admin** setting up the project for the first time.
> Students only need to follow the [Student Guide](#student-guide).

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and sign in.
2. Click **New project**.
3. Give it a name (e.g. `rqfc`), choose a region, and set a database password.
4. Wait ~2 minutes for it to provision.

### 2. Create the database tables

In your Supabase project, go to **SQL Editor** and run the following:

```sql
-- Student accounts (one row per student, keyed by Alpaca account ID)
create table public.accounts (
  id           text primary key,
  display_name text,
  created_at   timestamptz default now()
);

-- Every order submitted by any student
create table public.trades (
  id               uuid default gen_random_uuid() primary key,
  account_id       text references public.accounts(id) on delete cascade,
  alpaca_order_id  text,
  symbol           text not null,
  side             text not null,
  order_type       text not null,
  qty              float,
  notional         float,
  limit_price      float,
  filled_qty       float,
  filled_avg_price float,
  status           text,
  created_at       timestamptz default now()
);

-- Daily equity snapshots (used for Sharpe, drawdown, PnL in the admin view)
create table public.portfolio_snapshots (
  id          uuid default gen_random_uuid() primary key,
  account_id  text references public.accounts(id) on delete cascade,
  equity      float not null,
  cash        float,
  recorded_at timestamptz default now()
);

-- Indexes for common query patterns
create index on public.trades(account_id);
create index on public.trades(symbol);
create index on public.portfolio_snapshots(account_id, recorded_at);
```

### 3. Get your Supabase keys

In your Supabase project go to **Settings → API**. You will find:

| Key | Who needs it | Where to find it |
|---|---|---|
| **Project URL** | Everyone | Settings → API → Project URL |
| **anon / public key** | Students | Settings → API → Project API keys → `anon` |
| **service_role key** | Admin only | Settings → API → Project API keys → `service_role` |

> Keep the `service_role` key secret — it bypasses all database security rules.

Share the **Project URL** and **anon key** with your students. Keep the service_role key for yourself.

### 4. Get Alpaca API keys

Every participant (including the admin, if you want your own account) needs their own Alpaca paper trading keys.

1. Go to [alpaca.markets](https://alpaca.markets) and create a free account.
2. In the dashboard, click **Paper Trading** in the top-left to switch to the paper environment.
3. Go to **Your Account → API Keys** and click **Generate New Key**.
4. Copy the **API Key ID** and the **Secret Key** — the secret is only shown once.

---

## Student Guide

### Environment setup

Create a `.env` file in your project folder (or set these variables in your shell/notebook):

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...   # the anon key from your admin
```

Then load them in Python before importing rqfc:

```python
from dotenv import load_dotenv
load_dotenv()
```

Or set them directly (fine for quick testing, not recommended for scripts you share):

```python
import os
os.environ["SUPABASE_URL"] = "https://xxxxxxxxxxxx.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJ..."
```

### Initializing your account

```python
import rqfc

account = rqfc.init(
    api_key="PKXXXXXXXXXXXXXXXXXXXXXXXX",   # your Alpaca API Key ID
    secret_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # your Alpaca Secret Key
    name="Alice",    # optional — shows up in the admin leaderboard
)
# rqfc initialized — PAPER | account: PA3XKJF92ABC (Alice)
```

Your Alpaca account ID (e.g. `PA3XKJF92ABC`) is your identifier in the system. You don't need a separate username or password — your Alpaca credentials are your identity.

`rqfc.init()` automatically:
- Connects to your Alpaca paper trading account
- Registers you in the Supabase `accounts` table
- Logs your current portfolio value as a snapshot

**Call `account.log_snapshot()` at the start of each session** so the admin can track your equity curve over time:

```python
account = rqfc.init("PK...", "secret...")
account.log_snapshot()   # already called by init, but call it again each session
```

---

### Trading

#### Buy and sell by share count

```python
account.buy("AAPL", 10)                  # market buy 10 shares
account.sell("AAPL", 5)                  # market sell 5 shares

account.buy("MSFT", 10, order_type="limit", limit_price=410.00)   # limit buy
account.sell("MSFT", 10, order_type="limit", limit_price=430.00)  # limit sell
```

#### Buy and sell by dollar amount

```python
account.dollar_buy("NVDA", 5000)    # buy $5,000 worth of NVDA
account.dollar_sell("NVDA", 2500)   # sell $2,500 worth of NVDA
```

#### Short selling

```python
account.short("TSLA", 5)   # short 5 shares (bet the price drops)
account.cover("TSLA", 5)   # buy back 5 shares to close the short
```

#### Advanced orders

```python
# Bracket order: enter with automatic take-profit and stop-loss
account.bracket_order(
    symbol="AAPL",
    qty=10,
    side="buy",
    take_profit=210.00,   # exits the trade with a gain at $210
    stop_loss=185.00,     # exits the trade with a capped loss at $185
)

# Trailing stop: follows the price up, triggers if it drops X% from the peak
account.trailing_stop("AAPL", qty=10, trail_percent=5.0)
```

#### Managing orders

```python
open_orders = account.get_open_orders()          # see pending orders
account.cancel_order("some-order-uuid")          # cancel one order
account.cancel_all_orders()                      # cancel everything
history = account.get_order_history(limit=50)    # past filled/cancelled orders
```

#### Portfolio rebalancing

```python
# Set target weights — positions not listed here will be closed
account.rebalance({
    "AAPL": 0.30,
    "MSFT": 0.25,
    "NVDA": 0.25,
    "SPY":  0.20,
})
```

---

### Viewing your portfolio

```python
account.get_portfolio_value()     # float: total value in dollars
account.get_buying_power()        # float: cash available to trade

account.get_pnl()
# {"unrealized_pnl": 142.50, "realized_pnl": 310.00, "total_pnl": 452.50}

account.get_position("AAPL")      # one stock: qty, avg entry, current price, P&L
account.get_all_positions()       # list of all open positions

account.get_portfolio_summary()   # DataFrame: symbol, qty, entry, current, P&L%, weight
account.get_concentration()       # DataFrame: symbol, market_value, pct_of_portfolio

account.close_position("AAPL")    # market-sell entire AAPL position
account.close_all_positions()     # liquidate everything

# Equity curve (time-indexed DataFrame)
account.get_portfolio_history(days=30)
account.get_portfolio_history(start="2024-01-01", end="2024-06-01")

account.get_win_rate()
# {"wins": 7, "losses": 3, "total_trades": 10, "win_rate": 70.0}
```

---

### Metrics

All metrics default to the last 252 calendar days (~1 trading year).

```python
account.get_sharpe()                      # Annualized Sharpe ratio (portfolio)
account.get_sharpe(days=90)               # last 90 days
account.get_sortino()                     # Sortino (penalizes only downside vol)
account.get_max_drawdown()                # e.g. -0.12 means worst drop was -12%
account.get_max_drawdown(days=60)

account.get_volatility("AAPL", days=30)  # annualized vol of a stock, e.g. 0.28 = 28%
account.get_beta("AAPL")                 # beta vs SPY
account.get_beta("TSLA", benchmark="QQQ")
```

---

### Market data

```python
account.get_price("AAPL")        # float: latest trade price
account.get_quote("AAPL")        # dict: bid, ask, sizes, spread

# OHLCV history
bars = account.get_bars("AAPL", timeframe="1D", days=30)
bars = account.get_bars("AAPL", timeframe="1H", start="2024-01-01")
# Returns a pandas DataFrame with columns: open, high, low, close, volume, vwap
# Supported timeframes: "1Min", "5Min", "15Min", "30Min", "1H", "4H", "1D", "1W"

account.get_snapshot("AAPL")     # full snapshot: price, OHLCV, change_pct
account.get_snapshots(["AAPL", "MSFT", "NVDA"])   # multiple tickers at once

account.get_news("AAPL", limit=5)     # recent headlines
account.get_top_movers(n=5)           # {"gainers": DataFrame, "losers": DataFrame}

account.get_assets()              # all tradeable US equities
account.is_tradeable("AAPL")     # True/False — always check before automated orders
```

---

### Market hours

```python
account.is_market_open()     # True or False

clock = account.get_market_clock()
# {
#   "is_open": False,
#   "current_time": datetime(...),
#   "next_open": datetime(...),
#   "next_close": datetime(...),
#   "time_to_open": "14h 32m until open",
#   "time_to_close": "Market is closed"
# }
```

---

## Admin Guide

### Environment setup (Admin)

Set these in your environment (or `.env` file):

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

> Use `SUPABASE_SERVICE_ROLE_KEY`, not the anon key. The service role key has
> unrestricted read access across all student rows.

### Initializing the admin client

```python
import rqfc

admin = rqfc.Admin()
# Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment automatically.

# Or pass credentials directly:
admin = rqfc.Admin(
    supabase_url="https://xxxxxxxxxxxx.supabase.co",
    service_role_key="eyJ...",
)
```

---

### Viewing all trades

```python
# All trades from every student (newest first)
admin.get_all_trades()

# Filter to one student
admin.get_all_trades(account_id="PA3XKJF92ABC")

# Filter to one ticker
admin.get_all_trades(symbol="AAPL")

# Both
admin.get_all_trades(account_id="PA3XKJF92ABC", symbol="NVDA", limit=100)
```

Returns a DataFrame with columns:
`account_id`, `display_name`, `symbol`, `side`, `order_type`, `qty`, `notional`,
`filled_qty`, `filled_avg_price`, `status`, `created_at`

---

### Student summary

```python
summary = admin.get_student_summary()
print(summary)
```

Returns one row per student:

| account_id | display_name | joined | trade_count | win_rate | wins | losses |
|---|---|---|---|---|---|---|
| PA3XKJF92 | Alice | 2024-09-01 | 42 | 61.9 | 26 | 16 |
| PA7MNBQ11 | Bob | 2024-09-01 | 28 | 53.6 | 15 | 13 |

---

### Leaderboard

```python
board = admin.get_leaderboard(days=30)
print(board)
```

Returns all students ranked by total PnL, including:

| name | total_pnl | total_return_pct | sharpe | win_rate | trade_count |
|---|---|---|---|---|---|
| Alice | $1,240.50 | 12.4% | 1.82 | 61.9% | 42 |
| Bob | $310.00 | 3.1% | 0.74 | 53.6% | 28 |

The `days` parameter controls the lookback window for the Sharpe calculation (not for PnL, which is computed from first to latest snapshot).

---

### Per-student deep dive

```python
ALICE = "PA3XKJF92ABC"

# PnL from portfolio snapshots
admin.get_pnl(ALICE)
# {
#   "account_id": "PA3XKJF92ABC",
#   "start_equity": 100000.0,
#   "latest_equity": 101240.50,
#   "total_pnl": 1240.50,
#   "total_return_pct": 1.24
# }

# Risk metrics from snapshots
admin.get_sharpe(ALICE, days=30)           # Sharpe over last 30 days
admin.get_sortino(ALICE, days=30)
admin.get_max_drawdown(ALICE, days=30)

# Win rate from trade history
admin.get_win_rate(ALICE)
# {"wins": 26, "losses": 16, "win_rate": 61.9}

# Full equity curve as a DataFrame
curve = admin.get_equity_curve(ALICE)
curve.plot(y="equity", title="Alice equity curve")
```

> **Note on accuracy:** Sharpe, drawdown, and PnL are all computed from
> `portfolio_snapshots`. The more often students call `account.log_snapshot()`,
> the more accurate these will be. A snapshot is logged automatically on every
> `rqfc.init()` call, so at minimum you get one data point per session.
> For intraday accuracy, students can call `account.log_snapshot()` periodically
> in their trading loop.

---

## Environment Variable Reference

| Variable | Who sets it | Value |
|---|---|---|
| `SUPABASE_URL` | Everyone | Project URL from Supabase Settings → API |
| `SUPABASE_KEY` | Students | `anon` public key from Supabase Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin only | `service_role` key from Supabase Settings → API |
