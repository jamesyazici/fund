import os
from datetime import datetime, timezone

_client = None


def _get():
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set.\n"
                "Find them in your Supabase project under Settings → API."
            )
        try:
            from supabase import create_client
        except ImportError:
            raise RuntimeError("supabase package not installed. Run: pip install supabase")
        _client = create_client(url, key)
    return _client


def configure(url: str, key: str) -> None:
    global _client
    from supabase import create_client
    _client = create_client(url, key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_member(alpaca_account_id: str):
    """
    Look up the member (student) row linked to this Alpaca account.

    Members are created by an admin via rqfc.Admin().add_member(...). A
    student's trades/snapshots are only recorded once their account is linked.

    Returns {id, pod_id, name, asset_class} or None if not yet registered.
    """
    try:
        res = (
            _get().table("members")
            .select("id, pod_id, name, pods(asset_class)")
            .eq("alpaca_account_id", alpaca_account_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        row = res.data[0]
        pod = row.get("pods")
        asset_class = (pod.get("asset_class") if isinstance(pod, dict) else None) or "equities"
        return {
            "id":          row["id"],
            "pod_id":      row["pod_id"],
            "name":        row.get("name"),
            "asset_class": asset_class,
        }
    except Exception as e:
        print(f"[rqfc] Warning: could not resolve member: {e}")
        return None


def log_trade(member, trade: dict) -> None:
    if not member:
        return
    try:
        _get().table("trades").insert({
            "pod_id":      member["pod_id"],
            "member_id":   member["id"],
            "asset_class": member.get("asset_class", "equities"),
            **trade,
        }).execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not log trade: {e}")


def log_snapshot(member, equity: float, cash: float) -> None:
    if not member:
        return
    try:
        _get().table("member_snapshots").insert({
            "member_id":   member["id"],
            "pod_id":      member["pod_id"],
            "equity":      equity,
            "cash":        cash,
            "recorded_at": _now(),
        }).execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not log snapshot: {e}")


def sync_positions(member, positions: list) -> None:
    """Replace this member's stored open positions with the current set."""
    if not member:
        return
    try:
        client = _get()
        if positions:
            now = _now()
            rows = [{
                "pod_id":          member["pod_id"],
                "member_id":       member["id"],
                "symbol":          p["symbol"],
                "quantity":        p["quantity"],
                "avg_entry_price": p["avg_entry_price"],
                "current_price":   p.get("current_price"),
                "market_value":    p.get("market_value"),
                "unrealized_pnl":  p.get("unrealized_pnl"),
                "updated_at":      now,
            } for p in positions]
            client.table("positions").upsert(rows, on_conflict="member_id,symbol").execute()

        # Drop positions the student no longer holds.
        held = [p["symbol"] for p in positions]
        delete_q = client.table("positions").delete().eq("member_id", member["id"])
        if held:
            delete_q = delete_q.not_.in_("symbol", held)
        delete_q.execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not sync positions: {e}")
