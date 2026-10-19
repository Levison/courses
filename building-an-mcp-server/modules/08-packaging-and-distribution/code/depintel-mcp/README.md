# depintel-mcp

An MCP server that gives agents read-only dependency intelligence:
PyPI package metadata and OSV.dev vulnerability lookups. No API keys.

```bash
uvx depintel-mcp            # stdio (for Claude Code, Cursor, VS Code, Claude Desktop)
uvx depintel-mcp --http     # Streamable HTTP on 127.0.0.1:8000/mcp
```

Tools: `package_info`, `check_vulnerabilities`, `audit_requirements`.
Resource template: `pypi://{name}/releases`.

<!-- mcp-name: io.github.your-github-user/depintel-mcp -->
