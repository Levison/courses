# Module 01: Your first stdio server, and the wire under it

**Goal:** ship a 3-tool server, call it as a host would, and read the raw 2026-07-28 JSON-RPC traffic.
**Time:** ~1.5 h. **Code:** [`code/`](code/)

## Concepts

- **Roles.** A *host* (Claude Code, Cursor, VS Code, your agent) runs one *client* per *server*. Over stdio the
  host spawns your server as a child process and owns its stdin/stdout. **stdout is the protocol**: any stray
  `print()` corrupts it. Log to stderr; the default `logging` config already does.
- **Stateless core (2026-07-28).** There is no `initialize` handshake. Each request carries
  `_meta["io.modelcontextprotocol/protocolVersion"]` and `.../clientCapabilities`. `server/discover` is optional and
  returns versions, capabilities and instructions. Every result has `resultType` (`complete` or `input_required`) and the
  server's identity in `_meta["io.modelcontextprotocol/serverInfo"]`.
- **Schema from type hints.** `MCPServer` derives `inputSchema` from the signature (pydantic). `Annotated[int, Field(ge=1)]`
  becomes `minimum: 1`, enforced server-side before your function runs. A pydantic return type becomes `outputSchema` +
  `structuredContent`; primitives are wrapped as `{"result": ...}`.
- **Two kinds of failure.**
  - `ToolError("...")`: the model sees `isError: true` plus your message, so it can self-correct.
  - Any other exception: the model sees a generic "Error executing tool X" and the details stay in your log.
  - `MCPError`: a *protocol* error. It goes to the client application, never to the model.
- **Annotations** (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) are hints that hosts use for
  consent UX. The spec says clients must treat them as untrusted unless the server is trusted. Declare them honestly anyway.
- **Deterministic order.** Servers SHOULD list tools in a stable order (2026-07-28) so that clients and upstream LLM prompt caches stay warm.

## Tutorial

```bash
make start 01                          # copies code/ to workspace/01-first-stdio-server/ (your copy)
cd workspace/01-first-stdio-server
uv run python textkit_server.py         # sits silently waiting on stdin: correct. Ctrl-C.
uv run python client.py                 # spawns it over stdio, lists tools, calls two
uv run python wire_peek.py              # raw JSON-RPC: server/discover, tools/list, tools/call
uv run pytest -q                        # in-memory + real-stdio tests
```

1. Read [`textkit_server.py`](code/textkit_server.py). Note `MCPServer(...)` (v1's `FastMCP` was renamed), and that the
   module-level object is called `mcp`. `mcp run` / `mcp dev` look for `mcp`, `server` or `app`.
2. Run `client.py`. `Client(StdioServerParameters(...))` probes `server/discover`, so `client.protocol_version` prints
   `2026-07-28`.
3. Run `wire_peek.py` and study the output. There is no session and no handshake, and `ttlMs`/`cacheScope` appear on
   discover and list results. The integer list from `roll_dice` arrives as both `content` (one text block per item) and
   `structuredContent`.
4. Open it in the Inspector:
   ```bash
   # Web UI (pins your installed SDK version in a fresh uv env)
   uv run mcp dev textkit_server.py
   # CLI (Node >= 22.19)
   npx @modelcontextprotocol/inspector --cli uv run python textkit_server.py --protocol-era modern --method tools/list
   ```
   `--protocol-era modern` matters. Without it, Inspector 2.11 negotiated **2025-11-25** with this server in my run.

## Exercises

Work in your copy, `workspace/01-first-stdio-server/` (create it with `make start 01`); never edit `code/`.
Discussion answers go in `workspace/01-first-stdio-server/NOTES.md` under the matching `## Exercise N` heading.
Check your work with `make check 01`; `make progress` updates `PROGRESS.md`.
Reference answers are in [`solutions/`](solutions/) (spoilers).

1. Add a `count_tokens_estimate(text) -> int` tool (about 4 characters per token, minimum 1) with
   `annotations=ToolAnnotations(readOnlyHint=True)` to `workspace/01-first-stdio-server/textkit_server.py`, and test it
   in `workspace/01-first-stdio-server/test_textkit.py` (that whole file must pass, so update the catalog test too).
2. Make `slugify` return a pydantic model `{slug, length}`. Run your `wire_peek.py` and look at how `outputSchema` changes.
3. Add a `crash_test()` tool that raises a plain `RuntimeError("db password is hunter2")`. Confirm the client sees only
   "Error executing tool …". Why is that the right default? (Answer in NOTES.md.)
4. Add `print("hi")` at import time in your `textkit_server.py` and connect with `client.py`. What breaks, and why?
   Answer in NOTES.md, then remove the print (the check verifies stdout is clean again).
5. In your `wire_peek.py`, send `tools/list` with `protocolVersion: "2099-01-01"`. Which error code comes back?
   Record the code and the error `data` in NOTES.md. (Hint: `UnsupportedProtocolVersion`.)

## Further reading
- [Spec: Overview](https://modelcontextprotocol.io/specification/2026-07-28) and [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Python SDK: Get started](https://py.sdk.modelcontextprotocol.io/get-started/), [Tools](https://py.sdk.modelcontextprotocol.io/servers/tools/), [Handling errors](https://py.sdk.modelcontextprotocol.io/servers/handling-errors/)

**Verified 2026-10-19:** `pytest` 5/5; `client.py`, `wire_peek.py` and the Inspector CLI (`tools/list --strict`, `tools/call`) were all run.
