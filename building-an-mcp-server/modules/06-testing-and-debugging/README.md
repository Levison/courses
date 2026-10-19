# Module 06: Testing and debugging

**Goal:** a test pyramid for MCP servers: in-memory unit tests, contract tests on the tool catalog, black-box checks
with the official Inspector CLI, and coverage of both protocol eras. All of it runs in CI.
**Time:** ~2 h. **Code:** [`code/`](code/) (tests module 03's `depintel` server)

## Concepts

- **In-memory `Client(server)`** is the workhorse: no subprocess, no port, the same `Client` class you use in production.
  It is era-neutral by default (negotiates 2026-07-28). Pass `mode="legacy"` to exercise 2025 semantics. Use
  `raise_exceptions=True` in tests so crashes *outside* tool bodies surface with their real message rather than a
  sanitized `-32603`. A `ToolError` is still a normal `is_error` result either way.
- **What the in-memory client skips:** HTTP, auth, Host checks and headers. Those need a real server (module 05 spawns uvicorn).
- **Your tool catalog is an API and a prompt.** Changing a description changes model behavior. A flipped `readOnlyHint` can
  change host consent UX. Pin it: `catalog_lock.py` hashes each tool's full definition into `catalog.lock.json`, and the test
  fails on drift. Intentional changes are one `--write` plus a reviewed diff. The same mechanism on the client side detects
  rug pulls (module 07).
- **Contract properties** worth asserting for every tool: a description of sensible length, annotations present, structured
  output, and bounded string inputs (`pattern`/`maxLength`). Also assert that both eras see the same catalog.
- **Inspector CLI v2** gives stable exit codes for CI: `0` ok, `1` usage, `3` auth required, `4` unreachable, **`5` tool
  error / unknown tool**, **`6` `--strict` schema-portability error**. `--strict` flags JSON-Schema constructs some shipping
  clients refuse (e.g. bare `false`, which `z.tuple()` emits; see the TS appendix). Use `--protocol-era modern` to force 2026-07-28.
- **Debugging tips:**
  - A stdio server that "doesn't show up": run the launch command yourself. Silence is correct; a traceback is the bug. The usual
    suspects are relative paths, an un-restarted host, and stdout pollution.
  - HTTP 421 means the Host allowlist. 400 with `-32020` means a header/body mismatch. `-32022` means a protocol-version mismatch.
  - The Python SDK ships OpenTelemetry middleware **on by default** (a no-op until you configure an exporter). Trace context
    propagates in `_meta` when both ends use the SDK.

## Tutorial

```bash
make start 06                          # copies code/ to workspace/06-testing-and-debugging/ (your copy)
cd workspace/06-testing-and-debugging
uv run pytest -q                                  # contract tests
uv run python catalog_lock.py                     # exit 1 on drift
./inspector_smoke.sh                              # Node >= 22.19 required; cds to the course root itself
```

Then break things on purpose:
1. Copy module 03's server next to your tests (a local `depintel_server.py` takes precedence over the reference one):
   `cp ../../modules/03-wrapping-a-real-api/code/depintel_server.py .`. Edit a tool docstring in that copy, run `pytest`,
   and watch the catalog test fail. Re-pin with `python catalog_lock.py --write` (it writes your workspace lockfile).
2. In the same copy, remove `max_length` from `audit_requirements`. `test_input_schemas_constrain_strings` fails.
   Delete the copy when you are done.
3. Read `inspector_smoke.sh`: each check asserts an exact exit code (including expected failures, `5`).

[`ci.example.yml`](code/ci.example.yml) wires it all into GitHub Actions (not active: GitHub only runs workflows from `.github/workflows/` at the repository root).

## Exercises

Work in your copy, `workspace/06-testing-and-debugging/` (create it with `make start 06`); never edit `code/`.
Discussion answers go in `workspace/06-testing-and-debugging/NOTES.md` under the matching `## Exercise N` heading.
Check your work with `make check 06`; `make progress` updates `PROGRESS.md`.
Reference answers are in [`solutions/`](solutions/) (spoilers).

1. Add a test in your workspace (e.g. `test_progress.py`, test name containing `progress`) that `audit_requirements` reports
   progress: pass `progress_callback=` to `call_tool` and count the calls.
2. Write `conformance.py` in your workspace with `async def check_server(params: StdioServerParameters) -> list[str]`: start
   *any* server over real stdio and return a list of contract problems (empty = conformant). It must pass the module 01 and
   02 servers and flag a tool with no description (a generic conformance harness).
3. Add an **LLM-in-the-loop eval**: write `eval_intents.json` (at least 20 `{"intent", "expected_tool"}` cases covering every
   tool; `"none"` for out-of-scope), give a model the catalog, and measure tool-selection accuracy before and after
   rewriting descriptions. Record the numbers in NOTES.md. (Needs an API key for a real model; the course does not ship one.)
4. Fuzz `package_info` with Hypothesis over arbitrary strings (test name containing `fuzz`). Assert it never makes an HTTP
   request for names that fail the pattern.
5. Configure an OTel console exporter and read the server spans for one `tools/call`. Paste the span names and
   attributes into NOTES.md and note what you would alert on.

## Further reading
- SDK: [Testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/), [Troubleshooting](https://py.sdk.modelcontextprotocol.io/troubleshooting/), [OpenTelemetry](https://py.sdk.modelcontextprotocol.io/run/opentelemetry/)
- [Inspector CLI docs](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector/cli), [Inspector repo](https://github.com/modelcontextprotocol/inspector)
- [OWASP MCP cheat sheet: hash-pin full tool definitions](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)

**Verified 2026-10-19:** `pytest` 5/5; `catalog_lock.py` ok; `inspector_smoke.sh` all 9 checks passed with Inspector 2.11.0 on Node 22.23.
