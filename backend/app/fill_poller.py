"""Copy Alpaca orders the backend didn't place into `trades`.

Strategies running on QuantConnect trade a pod's Alpaca account directly, so
/orders never logs them and the public feeds can't show them
(docs/LIVE_TRADING_PLAN.md, build step 2). Every FILL_POLL_SECONDS this reads
each pod's recently closed Alpaca orders and inserts one `trades` row for every
order that filled, fully or partly, and isn't logged yet. Those rows have no
trader_id; the public feed labels them "Strategy".

Only pods with their own Alpaca keys are polled. Pods on the shared fallback
keys would all see the same account's orders.
"""
from datetime import datetime, timedelta, timezone
import logging
import threading
import time

from . import alpaca_client as alp
from . import db
from .config import get_settings

logger = logging.getLogger(__name__)

LOOKBACK = timedelta(days=3)
# /orders logs its own row right after submitting. Skipping orders that filled
# moments ago means the poller never races it for the unique alpaca_order_id.
SETTLE = timedelta(seconds=30)


def trade_row_from_fill(order, asset_class: str) -> dict:
    """A `trades` row for what an Alpaca order actually filled."""
    order_type = getattr(order, "order_type", None) or getattr(order, "type", None)
    label = (order_type.value if hasattr(order_type, "value") else str(order_type or "market")).upper()
    row = alp.to_trade_row(order, label, asset_class)
    qty = alp._num(order.filled_qty)
    price = alp._num(order.filled_avg_price)
    status = order.status.value if hasattr(order.status, "value") else str(order.status)
    row.update({
        "quantity": qty,
        "price": price,
        "notional": round(abs(qty * price * row["multiplier"]), 2) if price is not None else None,
        # A closed order that isn't "filled" (cancelled, expired) only partly filled.
        "status": "filled" if status == "filled" else "partially_filled",
        "executed_at": order.filled_at.isoformat(),
    })
    return row


def sync_pod(pod: dict, now: datetime = None) -> int:
    """Insert `trades` rows for the pod's filled orders that aren't logged yet."""
    now = now or datetime.now(timezone.utc)
    filled = [
        o for o in alp.get_closed_orders(pod["id"], after=now - LOOKBACK)
        if (alp._num(o.filled_qty) or 0) > 0 and o.filled_at and o.filled_at <= now - SETTLE
    ]
    if not filled:
        return 0
    known = db.existing_alpaca_order_ids([str(o.id) for o in filled])
    rows = [trade_row_from_fill(o, pod["asset_class"]) for o in filled if str(o.id) not in known]
    db.insert_synced_trades(pod["id"], rows)
    return len(rows)


def _loop(interval: int) -> None:
    while True:
        try:
            pods = [p for p in db.list_pods_admin() if p.get("has_alpaca")]
        except Exception as e:
            logger.warning("Fill poller could not list pods: %s", e)
            pods = []
        for pod in pods:
            try:
                added = sync_pod(pod)
                if added:
                    logger.info("Fill poller logged %s trade(s) for pod %s", added, pod.get("name"))
            except Exception as e:
                logger.warning("Fill poller failed for pod %s: %s", pod.get("name"), e)
        time.sleep(interval)


def start() -> None:
    interval = get_settings().fill_poll_seconds
    if interval <= 0:
        logger.info("Fill poller disabled (FILL_POLL_SECONDS=%s)", interval)
        return
    threading.Thread(target=_loop, args=(interval,), name="fill-poller", daemon=True).start()
    logger.info("Fill poller started, every %ss", interval)
