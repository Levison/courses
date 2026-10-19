# depintel-mcp

An MCP server that gives agents read-only dependency intelligence:
PyPI package metadata and OSV.dev vulnerability lookups. No API keys.

```bash
uvx depintel-mcp            # stdio (for Claude Code, Cursor, VS Code, Claude Desktop)
uvx depintel-mcp --http     # Streamable HTTP on 127.0.0.1:8000/mcp
```

Tools: `package_info`, `check_vulnerabilities`, `audit_requirements`.
Resource template: `pypi://{name}/releases`.

## Privacy and data flows

depintel-mcp runs locally and has no telemetry, accounts or API keys. To answer a tool call it sends:

- **pypi.org** (PyPI JSON API): the package name, and for exact-version metadata the version. Sent by
  `package_info` and the `pypi://{name}/releases` resource.
- **api.osv.dev** (Google's OSV vulnerability database): package name, ecosystem (`PyPI`) and version for each
  pinned requirement you ask about. `audit_requirements` sends every pinned line of the requirements text you pass in.

It does **not** send file paths, comments, unpinned lines, your prompts or conversation, or any credentials. Both
services see your IP address and a `User-Agent: depintel-mcp/...` header and apply their own retention policies
(see the PyPI and Google privacy policies). Responses are cached in memory for 60 seconds and nothing is written to
disk. To keep dependency lists private, don't run audits on internal package names, or run the server behind your own mirror.

<!-- mcp-name: io.github.your-github-user/depintel-mcp -->
