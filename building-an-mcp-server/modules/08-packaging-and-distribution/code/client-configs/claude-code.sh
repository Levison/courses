# Claude Code: local stdio server from PyPI (after publishing), or from a local wheel/path
claude mcp add depintel -- uvx depintel-mcp
claude mcp add depintel-dev -- uv run --directory /abs/path/to/depintel-mcp depintel-mcp
# Remote Streamable HTTP server (OAuth is discovered automatically from the 401 + PRM)
claude mcp add --transport http notes https://mcp.example.com/mcp
