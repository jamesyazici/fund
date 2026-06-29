"""
RQFC Live Strategy Runner
--------------------------
Runs a strategy file against your real pod. The same run(date, acct) function
you write for backtesting works here unchanged — the only difference is that
acct.buy() / acct.sell() etc. place real orders through the backend.

Usage
-----
Run once (execute strategy right now and exit):
    python run_live.py test2.py
    python run_live.py test2.py "my pod name"

Keep-alive mode (loops, runs once per trading day at market open):
    python run_live.py test2.py --schedule

For the 24/7 PC, the recommended setup is Windows Task Scheduler calling
the one-shot form daily at 9:31 AM ET — see the deployment guide.

Environment — put these in a .env file next to run_live.py:
    RQFC_API_KEY     = rqfc_...                              (required)
    RQFC_BACKEND_URL = https://your-app.up.railway.app       (required)
    RQFC_POD         = my pod name                           (optional)
"""

import importlib.util
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo  # stdlib since Python 3.9

# ── Load .env if present ──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; set env vars another way if needed

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("run_live.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("rqfc.live")

ET = ZoneInfo("America/New_York")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_run_fn(strategy_file: str):
    path = Path(strategy_file).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")
    spec = importlib.util.spec_from_file_location("_live_strategy", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise AttributeError(f"{path.name} must define:  run(date, acct) -> None")
    return mod.run


def _is_weekday() -> bool:
    return datetime.now(ET).weekday() < 5  # Mon=0 … Fri=4


def _seconds_until_market_open() -> float:
    """Seconds until 9:31 AM ET. Returns 0 if we're already past open today."""
    now    = datetime.now(ET)
    target = now.replace(hour=9, minute=31, second=0, microsecond=0)
    delta  = (target - now).total_seconds()
    return max(delta, 0)


def _run_strategy(run_fn, acct, today_str: str) -> None:
    log.info(f"Running strategy for {today_str} …")
    try:
        # Reload strategy file on each run so edits take effect without restart
        run_fn(today_str, acct)
        log.info("Strategy complete.")
    except Exception as exc:
        log.error(f"Strategy raised an error: {exc}", exc_info=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args     = [a for a in sys.argv[1:] if a != "--schedule"]
    schedule = "--schedule" in sys.argv

    if not args:
        print(__doc__)
        sys.exit(1)

    strategy_file = args[0]
    pod_name      = args[1] if len(args) > 1 else os.environ.get("RQFC_POD")
    api_key       = os.environ.get("RQFC_API_KEY")
    backend_url   = os.environ.get("RQFC_BACKEND_URL")

    if not api_key:
        log.error("RQFC_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)
    if not backend_url:
        log.error("RQFC_BACKEND_URL is not set. Add it to your .env file.")
        sys.exit(1)

    import rqfc
    rqfc.configure(backend_url)
    rqfc.login(api_key=api_key, summary=False)

    if pod_name:
        acct = rqfc.pod(pod_name)
    else:
        me   = rqfc.whoami()
        pods = me.get("pods", [])
        if not pods:
            log.error("Your account is not assigned to any pod.")
            sys.exit(1)
        acct = rqfc.pod(pods[0]["pods"]["name"])
        log.info(f"Using pod: {pods[0]['pods']['name']}")

    # Load strategy (re-loaded fresh on each run_fn call below)
    run_fn = _load_run_fn(strategy_file)

    if not schedule:
        # One-shot: run immediately and exit
        _run_strategy(run_fn, acct, date.today().isoformat())
        return

    # ── Scheduled mode: run once per trading day at market open ──────────────
    log.info(f"Scheduled mode started. Strategy: {strategy_file}")
    last_run: date | None = None

    while True:
        today = date.today()

        if today != last_run and _is_weekday():
            wait = _seconds_until_market_open()
            if wait > 0:
                h, m = divmod(int(wait), 3600)
                m  //= 60
                log.info(f"Waiting {h}h {m}m until market open (9:31 AM ET) …")
                time.sleep(wait)

            # Reload run_fn so any edits to the strategy file are picked up
            try:
                run_fn = _load_run_fn(strategy_file)
            except Exception as exc:
                log.error(f"Failed to reload strategy: {exc}")

            today = date.today()
            if _is_weekday():
                _run_strategy(run_fn, acct, today.isoformat())
                last_run = today
        else:
            # Weekend or already ran today — check again in 30 minutes
            time.sleep(1800)


if __name__ == "__main__":
    main()
