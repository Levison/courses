#!/usr/bin/env bash
# Ex 1: run hardened_server.py over stdio in a locked-down container.
#   ./sandbox.sh                      # then point a host at this script as the stdio command
# Build needs the network once (to install mcp); the run has none.
set -euo pipefail
cd "$(dirname "$0")"
docker build -q -t hardened-mcp -f - . >/dev/null <<'DOCKERFILE'
FROM python:3.13-slim
RUN pip install --no-cache-dir "mcp[cli]==2.3.0" "httpx>=0.28"
WORKDIR /app
COPY hardened_server.py /app/
USER 65534:65534
ENTRYPOINT ["python", "/app/hardened_server.py"]
DOCKERFILE
exec docker run --rm -i \
  --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m --pids-limit 64 --memory 256m \
  -v "$PWD/docs:/app/docs:ro" \
  hardened-mcp
