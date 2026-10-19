# Module 03: A realistic server wrapping real APIs

**Goal:** go from toy to production-shaped. `depintel` wraps **PyPI's JSON API** and **OSV.dev** (Google's open
vulnerability DB). Both are public and need no keys, so you can run it for real.
**Time:** ~2.5 h. **Code:** [`code/depintel_server.py`](code/depintel_server.py)

## Concepts

- **Design tools for the model, not as a mirror of the API.** Three task-shaped tools
  (`package_info`, `check_vulnerabilities`, `audit_requirements`) work better than a generic `http_get`. Fewer, sharper tools
  with structured outputs mean less schema in context and fewer wrong calls.
- **Lifespan.** In SDK v2 the Streamable HTTP lifespan runs **once at startup** and is shared by all requests (in v1 it
  ran per session). Put pools and clients there and reach them via `ctx.request_context.lifespan_context`.
- **Validate at the edge.** `Field(pattern=PEP508_NAME)` means the model cannot smuggle `../` or `?x=` into the upstream URL.
  Validation errors come back to the model as `isError` results, so it can fix the call.
- **Map upstream failures to actionable `ToolError`s.** Write "Not found on PyPI. Check the spelling", not a stack trace.
  Distinguish retryable failures (timeouts) from permanent ones (404).
- **Bound everything.** Line limits (50 requirements), excerpt truncation (400 chars), a concurrency limiter (8). The
  truncation is also a security control: third-party `details` text is an **indirect prompt-injection channel**, so cap it
  and label it untrusted (module 07 goes further).
- **Progress.** `await ctx.report_progress(done, total, msg)` streams `notifications/progress` on the request's own
  response stream. Pass `progress_callback=` on the client side.
- **Testability.** A `create_server(transport=None)` factory lets tests inject `httpx.MockTransport`, so tests are
  offline, deterministic and fast. Keep one opt-in live test.
- **Annotations:** these tools are `readOnlyHint=True, openWorldHint=True` (they touch the outside world but change nothing).

## Tutorial

```bash
make start 03                          # copies code/ to workspace/03-wrapping-a-real-api/ (your copy)
cd workspace/03-wrapping-a-real-api
uv run pytest -q                       # offline (MockTransport)
LIVE=1 uv run pytest -q -k live        # hits real OSV
uv run python demo_live.py             # real PyPI + OSV over stdio, with progress
```

`demo_live.py` output on 2026-10-19 (abridged):
```
mcp on PyPI: {'name': 'mcp', 'latest_version': '2.3.0', 'license': 'MIT', 'requires_python': '>=3.10', ...}
  progress 1/4 checked not-pinned ...
{'requirement': 'jinja2==2.4.1', 'vulnerable': True, 'ids': ['GHSA-462w-v97r-4m45', ...18 ids]}
{'requirement': 'requests==2.19.0', 'vulnerable': True, 'ids': [...10 ids]}
{'requirement': 'pydantic==2.12.0', 'vulnerable': False, 'ids': []}
{'requirement': 'not-pinned', 'vulnerable': None, 'error': 'not pinned as name==version'}
```

Things to notice in the code:
1. `get_json` is the single choke point for upstream I/O: timeouts, error mapping, no redirects.
2. `audit_requirements` uses an `anyio` task group + `CapacityLimiter`. Partial failures become per-line `error`
   fields, not a failed call.
3. `httpx`'s INFO logs are silenced. On stdio they go to stderr (safe), but they are noise in host logs.

## Exercises

Work in your copy, `workspace/03-wrapping-a-real-api/` (create it with `make start 03`); never edit `code/`.
Discussion answers go in `workspace/03-wrapping-a-real-api/NOTES.md` under the matching `## Exercise N` heading.
Check your work with `make check 03`; `make progress` updates `PROGRESS.md`.
Reference answers are in [`solutions/`](solutions/) (spoilers).

1. In your `depintel_server.py`, add a `latest_safe_version(name, current)` tool that combines PyPI releases with OSV
   `fixed_in` to suggest an upgrade target. Return a model with a `suggested` field: the lowest release >= `current` with
   no known vulnerabilities (`current` itself if it is clean).
2. Add an in-memory TTL cache (60 s) in the lifespan state for PyPI lookups. Write a test in your `test_depintel.py`
   proving the second call makes no HTTP request (the whole file must pass).
3. Add a `pypi://{name}/{version}/metadata` resource. When is a resource better than `package_info`? (NOTES.md)
4. OSV supports `/v1/querybatch`. Rewrite `audit_requirements` to send one batch request instead of one query per line,
   and compare latency against the live API.
5. Make retryable upstream failures (429/503, honoring `Retry-After`) return an `isError` result with a *retry hint*, then
   observe in Claude Code or Cursor whether the model retries. Record what happened in NOTES.md.

## Further reading
- SDK: [Lifespan](https://py.sdk.modelcontextprotocol.io/handlers/lifespan/), [Structured output](https://py.sdk.modelcontextprotocol.io/servers/structured-output/), [Progress](https://py.sdk.modelcontextprotocol.io/handlers/progress/)
- APIs: [PyPI JSON API](https://docs.pypi.org/api/json/), [OSV API](https://google.github.io/osv.dev/api/)

**Verified 2026-10-19:** `pytest` 6 passed + live test passed; `demo_live.py` ran against real PyPI/OSV.
