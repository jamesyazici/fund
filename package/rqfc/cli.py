"""``rqfc`` command-line interface.

    rqfc deploy strategy.py --pod "Vol Arb"     upload a strategy to a pod
    rqfc deploy ./my_strategy/  --pod "Vol Arb"  (directory must contain strategy.py)
    rqfc status --pod "Vol Arb"                  the pod's current strategy + state
    rqfc logs   --pod "Vol Arb"                  recent strategy logs
    rqfc stop   --pod "Vol Arb"                  stop the pod's strategy

Auth: pass ``--api-key`` or set ``RQFC_API_KEY``.
Backend: ``--backend`` or ``RQFC_BACKEND_URL`` (defaults to the production backend).

The server side of these commands (the ``/strategies*`` endpoints) is added in a
later phase; the CLI targets that contract now so it is ready when the backend
catches up.
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import sys
import zipfile

import requests

from . import DEFAULT_BACKEND_URL

_SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".mypy_cache", ".pytest_cache"}


def _resolve(args) -> tuple[str, dict]:
    backend = (
        args.backend or os.environ.get("RQFC_BACKEND_URL") or DEFAULT_BACKEND_URL
    ).rstrip("/")
    api_key = args.api_key or os.environ.get("RQFC_API_KEY")
    if not api_key:
        sys.exit("No API key. Pass --api-key or set RQFC_API_KEY.")
    return backend, {"Authorization": f"Bearer {api_key}"}


def _bundle(path: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(path):
            if not os.path.exists(os.path.join(path, "strategy.py")):
                sys.exit("A strategy directory must contain a strategy.py entrypoint.")
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                for name in files:
                    if name.endswith((".pyc", ".pyo")):
                        continue
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, path))
        else:
            if not path.endswith(".py"):
                sys.exit("Strategy file must be a .py file.")
            zf.write(path, "strategy.py")
    return buf.getvalue()


def deploy(args) -> None:
    backend, headers = _resolve(args)
    bundle = _bundle(args.path)
    name = args.name or os.path.basename(os.path.abspath(args.path.rstrip("/\\")))
    payload = {
        "pod": args.pod,
        "name": name,
        "bundle_b64": base64.b64encode(bundle).decode(),
        "capital": args.capital,
    }
    resp = requests.post(f"{backend}/strategies", json=payload, headers=headers, timeout=60)
    if resp.status_code >= 400:
        sys.exit(f"[{resp.status_code}] {_detail(resp)}")
    data = resp.json()
    cap_note = f", capped at ${args.capital:,.0f}" if args.capital else ""
    print(
        f"Deployed '{name}' to pod {args.pod} "
        f"(id {data.get('id', '?')}, status {data.get('status', '?')}, "
        f"{len(bundle)} bytes{cap_note})."
    )


def _simple(args, method: str, path: str) -> None:
    backend, headers = _resolve(args)
    resp = requests.request(
        method, f"{backend}{path}", headers=headers, params={"pod": args.pod}, timeout=30
    )
    if resp.status_code >= 400:
        sys.exit(f"[{resp.status_code}] {_detail(resp)}")
    print(resp.text.strip() or "ok")


def _detail(resp: requests.Response) -> str:
    try:
        return resp.json().get("detail", resp.text)
    except Exception:
        return resp.text


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--pod", required=True, help="pod name or UUID")
    sp.add_argument("--backend", default=None)
    sp.add_argument("--api-key", default=None)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="rqfc", description="RQFC strategy deployment CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dp = sub.add_parser("deploy", help="upload a strategy file or directory to a pod")
    dp.add_argument("path", help="path to strategy.py or a directory containing it")
    dp.add_argument("--name", default=None, help="display name (defaults to the file/dir name)")
    dp.add_argument(
        "--capital", type=float, default=None,
        help="dollar cap on this strategy's buy orders (unset = no cap)",
    )
    _add_common(dp)
    dp.set_defaults(func=deploy)

    for cmd, method, path in (
        ("status", "GET", "/strategies/current"),
        ("logs", "GET", "/strategies/logs"),
        ("stop", "POST", "/strategies/stop"),
    ):
        sp = sub.add_parser(cmd)
        _add_common(sp)
        sp.set_defaults(func=lambda a, _m=method, _p=path: _simple(a, _m, _p))

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
