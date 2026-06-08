"""Portfolio accounting for public transparency.

Authoritative inputs are Alpaca fills when available, with recorded trades as a
fallback. Live market data marks remaining positions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re


OCC_RE = re.compile(r"^(?P<underlying>[A-Z]{1,6})(?P<date>\d{6})(?P<type>[CP])(?P<strike>\d{8})$")


def parse_instrument(symbol: str, asset_class: str | None = None) -> dict:
    sym = (symbol or "").upper().replace(" ", "")
    match = OCC_RE.match(sym)
    if match:
        date = match.group("date")
        strike = int(match.group("strike")) / 1000
        return {
            "instrument_type": "option",
            "underlying_symbol": match.group("underlying"),
            "option_expiration": f"20{date[0:2]}-{date[2:4]}-{date[4:6]}",
            "option_type": "call" if match.group("type") == "C" else "put",
            "option_strike": strike,
            "multiplier": 100.0,
        }
    normalized = (asset_class or "").lower()
    return {
        "instrument_type": "option" if normalized == "options" else "equity",
        "underlying_symbol": None,
        "option_expiration": None,
        "option_type": None,
        "option_strike": None,
        "multiplier": 100.0 if normalized == "options" else 1.0,
    }


def fill_from_trade(row: dict) -> dict | None:
    qty = row.get("filled_qty") or row.get("quantity")
    price = row.get("price") or row.get("limit_price")
    if qty is None or price is None:
        return None
    instrument = parse_instrument(row.get("symbol"), row.get("asset_class"))
    quantity = abs(float(qty))
    fill_price = float(price)
    multiplier = float(row.get("multiplier") or instrument["multiplier"])
    return {
        "trade_id": row.get("id"),
        "alpaca_order_id": row.get("alpaca_order_id") or row.get("id"),
        "fill_id": row.get("fill_id") or row.get("alpaca_order_id") or row.get("id"),
        "symbol": str(row.get("symbol") or "").upper(),
        "side": row.get("side"),
        "quantity": quantity,
        "price": fill_price,
        "multiplier": multiplier,
        "notional": abs(quantity * fill_price * multiplier),
        "fees": float(row.get("fees") or 0),
        "filled_at": row.get("filled_at") or row.get("executed_at") or row.get("created_at"),
        "trader_id": row.get("trader_id"),
        "asset_class": row.get("asset_class"),
        **instrument,
    }


@dataclass
class PositionState:
    symbol: str
    instrument_type: str
    multiplier: float
    underlying_symbol: str | None = None
    quantity: float = 0.0
    cost: float = 0.0
    realized_pnl: float = 0.0
    fees: float = 0.0

    @property
    def avg_entry_price(self) -> float:
        return abs(self.cost / self.quantity / self.multiplier) if self.quantity else 0.0


@dataclass
class PortfolioState:
    positions: dict[str, PositionState] = field(default_factory=dict)
    realized_pnl: float = 0.0
    fees: float = 0.0


def apply_fill(state: PortfolioState, fill: dict) -> float:
    symbol = fill["symbol"]
    side = fill["side"]
    qty = abs(float(fill["quantity"]))
    price = float(fill["price"])
    multiplier = float(fill.get("multiplier") or 1)
    signed_qty = qty if side == "buy" else -qty

    pos = state.positions.setdefault(
        symbol,
        PositionState(
            symbol=symbol,
            instrument_type=fill.get("instrument_type") or "equity",
            underlying_symbol=fill.get("underlying_symbol"),
            multiplier=multiplier,
        ),
    )
    pos.multiplier = multiplier
    pos.fees += float(fill.get("fees") or 0)
    state.fees += float(fill.get("fees") or 0)

    realized = 0.0
    if pos.quantity == 0 or (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
        pos.quantity += signed_qty
        pos.cost += signed_qty * price * multiplier
        return 0.0

    avg = pos.avg_entry_price
    close_qty = min(abs(pos.quantity), qty)
    if pos.quantity > 0 and signed_qty < 0:
        realized = (price - avg) * close_qty * multiplier
        pos.cost -= avg * close_qty * multiplier
        pos.quantity -= close_qty
    elif pos.quantity < 0 and signed_qty > 0:
        realized = (avg - price) * close_qty * multiplier
        pos.cost += avg * close_qty * multiplier
        pos.quantity += close_qty

    remainder = qty - close_qty
    if remainder > 1e-9:
        remainder_signed = remainder if signed_qty > 0 else -remainder
        pos.quantity += remainder_signed
        pos.cost += remainder_signed * price * multiplier

    if abs(pos.quantity) < 1e-9:
        pos.quantity = 0.0
        pos.cost = 0.0

    pos.realized_pnl += realized
    state.realized_pnl += realized
    return realized


def build_portfolio(fills: list[dict]) -> PortfolioState:
    state = PortfolioState()
    ordered = sorted(fills, key=lambda f: str(f.get("filled_at") or ""))
    for fill in ordered:
        if fill.get("side") in {"buy", "sell"} and float(fill.get("quantity") or 0) != 0:
            apply_fill(state, fill)
    return state


def mark_positions(state: PortfolioState, prices: dict[str, float]) -> tuple[list[dict], dict]:
    rows = []
    totals = {
        "gross_notional": 0.0,
        "net_notional": 0.0,
        "realized_pnl": state.realized_pnl - state.fees,
        "unrealized_pnl": 0.0,
        "total_pnl": state.realized_pnl - state.fees,
        "fees": state.fees,
    }
    for symbol, pos in state.positions.items():
        if abs(pos.quantity) < 1e-9:
            continue
        current = float(prices.get(symbol) or pos.avg_entry_price)
        market_value = pos.quantity * current * pos.multiplier
        cost_basis = pos.quantity * pos.avg_entry_price * pos.multiplier
        unrealized = (current - pos.avg_entry_price) * pos.quantity * pos.multiplier
        total = pos.realized_pnl + unrealized - pos.fees
        totals["gross_notional"] += abs(market_value)
        totals["net_notional"] += market_value
        totals["unrealized_pnl"] += unrealized
        totals["total_pnl"] += unrealized
        rows.append({
            "symbol": symbol,
            "instrument_type": pos.instrument_type,
            "underlying_symbol": pos.underlying_symbol,
            "quantity": round(pos.quantity, 6),
            "avg_entry_price": round(pos.avg_entry_price, 4),
            "current_price": round(current, 4),
            "multiplier": pos.multiplier,
            "market_value": round(market_value, 2),
            "cost_basis": round(cost_basis, 2),
            "realized_pnl": round(pos.realized_pnl - pos.fees, 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_pnl": round(total, 2),
            "source": "fills_and_market_data",
        })
    return rows, {k: round(v, 2) for k, v in totals.items()}


def iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"
