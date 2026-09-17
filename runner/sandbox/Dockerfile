# The per-pod strategy sandbox image.
# Build context = repo root (fund/):
#   docker build -f runner/sandbox/Dockerfile -t rqfc-sandbox .
#
# The supervisor (later phase) runs one container per pod from this image with:
#   - the pod's strategy bundle mounted read-only at /strategy
#   - RQFC_BACKEND_URL / RQFC_STRATEGY_TOKEN / RQFC_POD_ID / NATS_URL in the env
#   - egress firewalled to {NATS, backend} only, cgroup CPU/mem caps, non-root
FROM python:3.12-slim-bookworm

RUN useradd --create-home --uid 10001 strategy
WORKDIR /app

COPY package/ /app/package/
RUN pip install --no-cache-dir "/app/package[runtime]"

USER strategy
ENV RQFC_STRATEGY_FILE=/strategy/strategy.py \
    NATS_URL=nats://nats:4222 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "rqfc._runtime"]
