# rqfc — Alpaca trading wrapper for the RQFC student quant fund
#
# Student usage:
#   import rqfc
#   account = rqfc.init("PKXXX...", "your_secret_key")
#   account.buy("AAPL", 10)
#
# Admin usage:
#   import rqfc
#   admin = rqfc.Admin()
#   admin.get_leaderboard()

from .client import init, Account
from .admin import Admin

__version__ = "0.2.0"

__all__ = ["init", "Account", "Admin"]
