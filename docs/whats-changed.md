# Reading older MCP tutorials in 2026

Most blog posts, videos and courses about MCP were written between Nov 2024 and Jul 2026 against spec
revisions 2024-11-05 → 2025-11-25. Use this table to translate.

| You read... | Today (spec 2026-07-28, Python SDK 2.x) |
|---|---|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` (the old import raises a `ModuleNotFoundError` that tells you to migrate) |
| `mcp = FastMCP("x", port=9000)` | Transport options moved to `run()` / `streamable_http_app()`: `mcp.run("streamable-http", port=9000)` |
| `ctx = mcp.get_context()` | Declare a `ctx: Context` parameter |
| `await session.initialize()` | `async with Client(...) as c:`. The client probes `server/discover` and falls back to `initialize` for old servers. |
| `ctx.elicit(...)` mid-tool | Works only on legacy connections. Use `Resolve(fn)` returning `Elicit(...)`, which is era-portable, or return `InputRequiredResult` yourself (module 04). |
| `ctx.session.create_message(...)` (sampling) | Deprecated. Call your LLM provider directly, or use `Sample(...)` via `Resolve` if you must use the client's model. |
| `ctx.info(...)` (MCP logging) | Deprecated. Log to stderr (stdio) or use OpenTelemetry (built in as middleware). |
| Roots | Deprecated. Pass directories via tool parameters, resource URIs or config. |
| `Mcp-Session-Id`, sticky sessions | Gone on the modern path. Mint explicit handles (module 04). `stateless_http=True` affects only legacy clients. |
| SSE resumability, `Last-Event-ID` | Removed. A broken stream means re-issuing the request with a new id. |
| `resources/subscribe` / GET stream | `subscriptions/listen` (`client.listen(...)`, `ctx.notify_resource_updated(...)`) |
| Resource-not-found `-32002` | `-32602` with the URI in `error.data` |
| HTTP+SSE transport (`/sse`) | Deprecated since 2025-03-26 and formally scheduled for removal. Use Streamable HTTP. |
| Dynamic Client Registration | Deprecated in favor of Client ID Metadata Documents (CIMD) |
| Experimental `tasks/*` in core | `io.modelcontextprotocol/tasks` extension. The Python SDK 2.3 does **not** implement it yet. FastMCP 4 does, via `fastmcp-tasks`. |
| WebSocket transport (`mcp[ws]`) | Removed from the Python SDK (it was never in the spec) |
| `McpError` | `MCPError(code, message, data)`. Raising it inside a tool is a protocol error the model never sees; raise `ToolError` for errors the model should read. |
| TS `@modelcontextprotocol/sdk` + `StreamableHTTPServerTransport` | `@modelcontextprotocol/server` + `createMcpHandler(factory)`. Run `npx @modelcontextprotocol/codemod@latest v1-to-v2 .` |
| Inspector v1 CLI flags | Inspector v2: same flags, but exit codes and the `--` separator changed. Needs Node ≥ 22.19. |
