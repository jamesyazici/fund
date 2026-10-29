"""Keep each pod's daily NAV history and metrics current.

Daily NAV used to be written only when someone called /sync, so the dashboard
had no daily history and computed Sharpe from 1-minute marks. Every
DAILY_METRICS_SECONDS (default an hour) this
copies each pod's daily equity from Alpaca's portfolio history (which goes back
to when the account opened) into nav_history and recomputes its metrics row.

Only pods with their own Alpaca keys are refreshed. Pods on the shared fallback
keys would all get the same account's history.
"""
import logging
import threading
import time

from . import alpaca_client as alp
from . import db, metrics
from .config import get_settings

logger = logging.getLogger(__name__)


def refresh_pod(pod_id: str) -> tuple[int, dict | None]:
    """Write the pod's daily NAV rows and latest metrics. Returns (days, metrics)."""
    nav_rows = [r for r in alp.get_nav_history(pod_id) if r["nav"] > 0]
    db.upsert_nav(pod_id, nav_rows)
    m = metrics.compute(nav_rows, trade_count=db.count_trades(pod_id))
    if m:
        db.upsert_metrics(pod_id, m)
    return len(nav_rows), m


def _loop(interval: int) -> None:
    while True:
        try:
            pods = [p for p in db.list_pods_admin() if p.get("has_alpaca")]
        except Exception as e:
            logger.warning("Daily metrics could not list pods: %s", e)
            pods = []
        for pod in pods:
            try:
                refresh_pod(pod["id"])
            except Exception as e:
                logger.warning("Daily metrics failed for pod %s: %s", pod.get("name"), e)
        time.sleep(interval)


def start() -> None:
    interval = get_settings().daily_metrics_seconds
    if interval <= 0:
        logger.info("Daily metrics refresh disabled (DAILY_METRICS_SECONDS=%s)", interval)
        return
    threading.Thread(target=_loop, args=(interval,), name="daily-metrics", daemon=True).start()
    logger.info("Daily metrics refresh started, every %ss", interval)
