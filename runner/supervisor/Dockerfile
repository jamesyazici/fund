# Build context = repo root (fund/):
#   docker build -f runner/supervisor/Dockerfile -t rqfc-supervisor .
#
# This container is trusted (it holds the Docker socket) — unlike the
# per-pod sandboxes, it runs no student code.
FROM docker:27-cli AS dockercli

FROM python:3.12-slim-bookworm
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app
COPY runner/supervisor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runner/supervisor/supervisor.py .

CMD ["python", "-u", "supervisor.py"]
