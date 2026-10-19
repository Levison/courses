# Notes: Module 06 (reference answers)

Code is in [`files/`](files/): `test_progress.py`, `conformance.py` + `test_conformance.py`, `eval_intents.json` +
`eval_tool_selection.py` + `descriptions_v2.json`, and `test_fuzz.py`.

## Exercise 1: Progress test

`call_tool(..., progress_callback=on_progress)` makes the client send a `progressToken`, and the server's
`ctx.report_progress(done, total, message)` calls arrive as `(progress, total, message)`. With three pinned lines and a
`MockTransport` OSV, the test sees exactly three events, progress 1..3 of total 3. (After module 03's batch
exercise the counts change; this test pins the reference server.)

## Exercise 2: Generic conformance harness

`check_server(params)` connects over real stdio and checks: the negotiated protocol is 2026-07-28; `tools/list` order is
stable across two calls; names are unique; every tool has a description; `inputSchema.type == "object"`; no boolean
property schemas (the `z.tuple` lesson from the TS appendix); `resources/list` and `prompts/list` work when advertised.
It returns strings instead of asserting, so one run reports every problem. `test_conformance.py` runs it over modules 01-04.

## Exercise 3: Tool-selection eval

`eval_intents.json` has 22 intents: 6 per tool plus 4 out-of-scope (including the near miss "Is left-pad vulnerable on
npm?", which should be `none` because the server only knows PyPI). No API key was available when this edition was built,
so `eval_tool_selection.py` ships an offline keyword-overlap chooser as a stand-in model; the loop is the point. Results
on 2026-10-19: **41% accuracy (9/22) with the shipped descriptions, 64% (14/22) with `descriptions_v2.json`**. The
rewrite names the user's vocabulary ("Is one exact version … vulnerable?", "whole requirements.txt or lockfile",
"which Python versions it supports"). A real model will score much higher in absolute terms, but run the same
before/after: look at the confusions (`check_vulnerabilities` vs `audit_requirements` is the hard pair) and fix those
descriptions, rather than adding instructions to the system prompt.

## Exercise 4: Hypothesis fuzzing

`test_fuzz.py` mixes `st.text()` with strategies biased toward path and query characters. For any name that fails
`PKG_NAME`, it asserts the result is an error and the `MockTransport` saw **zero** requests: validation happens in the
input schema, before your code. 150 examples run in about 2 s. Hypothesis shrinks any failure to a minimal input, which is
exactly what you want for an injection boundary.

## Exercise 5: OTel spans

With `opentelemetry-sdk` and a `ConsoleSpanExporter` (`uv run --with opentelemetry-sdk ...`), one in-memory `slugify`
call produced these server spans (2026-10-19):

```
server/discover     kind=SERVER  mcp.method.name=server/discover  mcp.protocol.version=2026-07-28  jsonrpc.request.id=1
tools/call slugify  kind=SERVER  mcp.method.name=tools/call  gen_ai.operation.name=execute_tool  gen_ai.tool.name=slugify  jsonrpc.request.id=2
tools/list          kind=SERVER  mcp.method.name=tools/list  jsonrpc.request.id=3
```

The span name is `"{method} {tool}"` and the attributes follow the OTel GenAI conventions (`gen_ai.tool.name`), so per-tool
latency and error dashboards need no custom code. The trailing `tools/list` is the client fetching the catalog to validate
structured output. What I would alert on: error rate per `gen_ai.tool.name`, p95 latency of `tools/call` spans, and
unexpected `mcp.protocol.version` values (old clients).
