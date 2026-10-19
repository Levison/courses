# Remote deployment image for depintel-mcp (Streamable HTTP). Not built in the course run (no Docker on the box).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
COPY depintel-mcp/ /app/
RUN uv pip install --system --no-cache . && useradd -r -u 10001 mcp
USER mcp
EXPOSE 8000
# Bind 0.0.0.0 inside the container; set the Host allowlist in code/ENV for your real hostname.
CMD ["uvicorn", "depintel_mcp.server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
