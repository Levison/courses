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
cd modules/06-testing-and-debugging/code
uv run pytest -q                                  # contract tests
uv run python catalog_lock.py                     # exit 1 on drift
./inspector_smoke.sh                              # Node >= 22.19 required; cds to repo root itself
```

Then break things on purpose:
1. Edit a tool docstring in `../../03-wrapping-a-real-api/code/depintel_server.py`, then run `pytest` and watch the catalog test fail.
   Re-pin with `python catalog_lock.py --write`.
2. Remove `max_length` from `audit_requirements`. `test_input_schemas_constrain_strings` fails.
3. Read `inspector_smoke.sh`: each check asserts an exact exit code (including expected failures, `5`).

[`ci.example.yml`](code/ci.example.yml) wires it all into GitHub Actions (not active: the repo has no remote yet).

## Exercises

1. Add a test that `audit_requirements` reports progress (pass `progress_callback=` and count calls).
2. Write a fixture that starts *any* module's server over real stdio and runs the same contract assertions (a generic conformance harness).
3. Add an **LLM-in-the-loop eval**: give a model the catalog plus 20 user intents and measure tool-selection accuracy before and after
   rewriting descriptions. (Needs an API key; the course does not ship one.)
4. Fuzz `package_info` with Hypothesis over arbitrary strings. Assert it never makes an HTTP request for names that fail the pattern.
5. Configure an OTel console exporter and read the server spans for one `tools/call`.

## Further reading
- SDK: [Testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/), [Troubleshooting](https://py.sdk.modelcontextprotocol.io/troubleshooting/), [OpenTelemetry](https://py.sdk.modelcontextprotocol.io/run/opentelemetry/)
- [Inspector CLI docs](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector/cli), [Inspector repo](https://github.com/modelcontextprotocol/inspector)
- [OWASP MCP cheat sheet: hash-pin full tool definitions](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)

**Verified 2026-10-19:** `pytest` 5/5; `catalog_lock.py` ok; `inspector_smoke.sh` all 9 checks passed with Inspector 2.11.0 on Node 22.23.
