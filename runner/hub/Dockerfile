# Build context = repo root (fund/):
#   docker build -f runner/hub/Dockerfile -t rqfc-hub .
FROM python:3.12-slim-bookworm

WORKDIR /app
COPY runner/hub/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runner/hub/hub.py .

CMD ["python", "-u", "hub.py"]
