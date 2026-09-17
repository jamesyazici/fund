"""Strategy supervisor: polls the backend for deployed strategies and runs
each one in its own sandbox container.

This is the one trusted, non-sandboxed component on the VM — it holds the
Docker socket (via a bind mount in docker-compose.yml) so it can start/stop
containers on the host. It never runs student code itself; it only manages
the containers that do.

Loop, every POLL_SECONDS:
  1. GET  /internal/strategies/pending  -> new deploys to start
  2. for each: get a trader-session token, download + extract the bundle,
     (re)build the sandbox image if needed, `docker run` a fresh container
     for that pod (replacing any previous one), report status.
  3. for each strategy it's tracking: check the container is still running;
     forward new log lines; if it exited, report status=failed with the
     tail of its logs.

Known limitation (acceptable for now): if the supervisor itself restarts, it
stops tracking already-running containers (they keep running fine, just
without log-forwarding / crash-detection) until the pod is redeployed.

Environment
-----------
RAILWAY_BACKEND_URL     backend base URL (required)
INTERNAL_SHARED_SECRET  must match the backend's INTERNAL_SHARED_SECRET (required)
HOST_REPO_DIR           absolute path to the `fund` repo ON THE HOST (required) —
                        `docker run`/`docker build` issued from in here are
                        executed by the host's Docker daemon via the mounted
                        socket, so every path they reference must be a real
                        host path, not a path inside this container.
HOST_BUNDLES_DIR        absolute host path where extracted bundles live
                        (required; same directory is bind-mounted into this
                        container at /data/bundles so writes here are visible
                        to the host at HOST_BUNDLES_DIR).
SANDBOX_CPU             cpu limit per sandbox container (default 0.5)
SANDBOX_MEM             memory limit per sandbox container (default 512m)
RQFC_EVENT_TIMEOUT_MS   passed through to each sandbox (default 30000)
POLL_SECONDS            poll interval (default 10)
"""
from __future__ import annotations

import base64
import io
import os
import subprocess
import sys
import time
import zipfile

import requests

BACKEND_URL = os.environ.get("RAILWAY_BACKEND_URL", "").rstrip("/")
INTERNAL_SECRET = os.environ.get("INTERNAL_SHARED_SECRET", "")
HOST_REPO_DIR = os.environ.get("HOST_REPO_DIR", "")
HOST_BUNDLES_DIR = os.environ.get("HOST_BUNDLES_DIR", "")
BUNDLES_ROOT = "/data/bundles"  # this container's view of HOST_BUNDLES_DIR

SANDBOX_CPU = os.environ.get("SANDBOX_CPU", "0.5")
SANDBOX_MEM = os.environ.get("SANDBOX_MEM", "512m")
EVENT_TIMEOUT_MS = os.environ.get("RQFC_EVENT_TIMEOUT_MS", "30000")
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "10"))

HEADERS = {"X-Internal-Secret": INTERNAL_SECRET}


def _fatal(msg: str) -> None:
    print(f"[supervisor] FATAL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def _check_config() -> None:
    missing = [
        name for name, val in (
            ("RAILWAY_BACKEND_URL", BACKEND_URL),
            ("INTERNAL_SHARED_SECRET", INTERNAL_SECRET),
            ("HOST_REPO_DIR", HOST_REPO_DIR),
            ("HOST_BUNDLES_DIR", HOST_BUNDLES_DIR),
        ) if not val
    ]
    if missing:
        _fatal(f"missing required env var(s): {', '.join(missing)}")


# ── backend HTTP ──────────────────────────────────────────────────────────

def get_pending() -> list[dict]:
    r = requests.get(f"{BACKEND_URL}/internal/strategies/pending", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def get_token(strategy_id: str) -> dict:
    r = requests.post(f"{BACKEND_URL}/internal/strategies/{strategy_id}/token", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def get_bundle(strategy_id: str) -> dict:
    r = requests.get(f"{BACKEND_URL}/internal/strategies/{strategy_id}/bundle", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def set_status(strategy_id: str, status: str, detail: str | None = None) -> None:
    try:
        requests.post(
            f"{BACKEND_URL}/internal/strategies/{strategy_id}/status",
            headers=HEADERS, json={"status": status, "detail": detail}, timeout=15,
        )
    except Exception as exc:
        print(f"[supervisor] failed to report status for {strategy_id}: {exc}", flush=True)


def post_log(strategy_id: str, line: str) -> None:
    try:
        requests.post(
            f"{BACKEND_URL}/internal/strategies/{strategy_id}/logs",
            headers=HEADERS, json={"line": line[:4000]}, timeout=10,
        )
    except Exception:
        pass  # log forwarding is best-effort, never worth crashing the loop over


# ── docker (via the mounted host socket) ─────────────────────────────────

def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def container_name(pod_id: str) -> str:
    return f"rqfc-strategy-{pod_id[:8]}"


_sandbox_image_ready = False


def ensure_sandbox_image() -> None:
    global _sandbox_image_ready
    if _sandbox_image_ready:
        return
    print("[supervisor] building sandbox image…", flush=True)
    r = _run([
        "docker", "build",
        "-f", f"{HOST_REPO_DIR}/runner/sandbox/Dockerfile",
        "-t", "rqfc-sandbox",
        HOST_REPO_DIR,
    ], timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"sandbox image build failed: {r.stderr[-1500:]}")
    _sandbox_image_ready = True
    print("[supervisor] sandbox image ready", flush=True)


def extract_bundle(strategy_id: str, bundle_b64: str) -> str:
    """Extract the bundle under BUNDLES_ROOT; return its HOST path for -v."""
    target = os.path.join(BUNDLES_ROOT, strategy_id)
    os.makedirs(target, exist_ok=True)
    data = base64.b64decode(bundle_b64)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(target)
    if not os.path.exists(os.path.join(target, "strategy.py")):
        raise RuntimeError("bundle has no strategy.py at its root")
    return f"{HOST_BUNDLES_DIR}/{strategy_id}"


def start_container(pod_id: str, token: str, bundle_host_dir: str) -> None:
    name = container_name(pod_id)
    _run(["docker", "rm", "-f", name])  # ignore failure if it doesn't exist
    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "--network", "rqfc",
        "--cpus", SANDBOX_CPU,
        "--memory", SANDBOX_MEM,
        "-v", f"{bundle_host_dir}:/strategy:ro",
        "-e", f"RQFC_BACKEND_URL={BACKEND_URL}",
        "-e", f"RQFC_STRATEGY_TOKEN={token}",
        "-e", f"RQFC_POD_ID={pod_id}",
        "-e", f"RQFC_EVENT_TIMEOUT_MS={EVENT_TIMEOUT_MS}",
        "rqfc-sandbox",
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"docker run failed: {r.stderr[-1500:]}")


def container_state(name: str) -> str | None:
    r = _run(["docker", "inspect", "-f", "{{.State.Status}}", name])
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def container_logs(name: str, since: str | None = None, tail: int | None = None) -> str:
    # `since` is a Unix timestamp (seconds) — unambiguous for `docker logs
    # --since`, unlike relying on it to parse an ISO-8601 string.
    cmd = ["docker", "logs"]
    if since:
        cmd += ["--since", since]
    if tail:
        cmd += ["--tail", str(tail)]
    cmd.append(name)
    r = _run(cmd)
    return (r.stdout or "") + (r.stderr or "")


# ── main loop ──────────────────────────────────────────────────────────────

def deploy(strategy: dict, tracked: dict) -> None:
    sid, pod_id = strategy["id"], strategy["pod_id"]
    print(f"[supervisor] deploying strategy {sid} to pod {pod_id}", flush=True)
    token = get_token(sid)["token"]
    bundle_host_dir = extract_bundle(sid, get_bundle(sid)["bundle_b64"])
    ensure_sandbox_image()
    start_container(pod_id, token, bundle_host_dir)
    set_status(sid, "running")
    tracked[pod_id] = {"strategy_id": sid, "since": str(int(time.time()))}
    print(f"[supervisor] {container_name(pod_id)} started for strategy {sid}", flush=True)


def check_running(tracked: dict) -> None:
    for pod_id, info in list(tracked.items()):
        name = container_name(pod_id)
        state = container_state(name)
        sid = info["strategy_id"]

        if state is None:
            set_status(sid, "failed", "sandbox container is missing")
            del tracked[pod_id]
            continue

        new_logs = container_logs(name, since=info["since"])
        info["since"] = str(int(time.time()))
        for line in new_logs.splitlines():
            if line.strip():
                post_log(sid, line)

        if state != "running":
            tail = container_logs(name, tail=50)
            set_status(sid, "failed", f"container state={state}: {tail[-1500:]}")
            del tracked[pod_id]


def main() -> None:
    _check_config()
    os.makedirs(BUNDLES_ROOT, exist_ok=True)
    print(f"[supervisor] starting, backend={BACKEND_URL}, poll={POLL_SECONDS}s", flush=True)
    tracked: dict[str, dict] = {}

    while True:
        try:
            for strategy in get_pending():
                try:
                    deploy(strategy, tracked)
                except Exception as exc:
                    print(f"[supervisor] deploy {strategy.get('id')} failed: {exc}", flush=True)
                    set_status(strategy["id"], "failed", str(exc)[:2000])
            check_running(tracked)
        except Exception as exc:
            print(f"[supervisor] poll error: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
