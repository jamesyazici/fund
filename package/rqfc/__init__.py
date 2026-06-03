# rqfc — Alpaca trading wrapper for the RQFC student quant fund
#
# Trades and portfolio data sync to a shared Supabase backend that powers
# the Fund dashboard. Each student is a "member" of a "pod" (strategy team);
# an admin registers members and links their Alpaca account first.
#
# Student usage:
#   import rqfc
#   account = rqfc.init("PKXXX...", "your_secret_key")
#   account.buy("AAPL", 10)     # trades log to the dashboard automatically
#   account.sync()              # push equity + open positions to the dashboard
#
# Admin usage:
#   import rqfc
#   admin = rqfc.Admin()
#   pod = admin.create_pod("Alpha Equities", "equities", starting_capital=100000)
#   admin.add_member(pod, "Alice", alpaca_account_id="PKXXXX", role="pm")
#   admin.rebuild()             # roll snapshots up into pod NAV + metrics
#   admin.get_leaderboard()

from .client import init, Account
from .admin import Admin

__version__ = "0.3.0"

__all__ = ["init", "Account", "Admin"]
