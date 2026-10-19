# Building an MCP Server (Oct 2026 edition)

> **As of 2026-10-19.** Targets MCP spec **2026-07-28** (latest), Python SDK **`mcp` 2.3.0**,
> TypeScript SDK **`@modelcontextprotocol/server` 2.3.1**, MCP Inspector **2.11.0**,
> `mcp-publisher` **1.8.1**. This course is meant to go stale. Re-check the
> [spec changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) and SDK release notes
> before you reuse it.

A hands-on course for experienced engineers. You build eight working servers, each verified by tests:
stdio first, then HTTP with OAuth, then security hardening and distribution. No time is spent on
"what is an LLM".

## Why this edition is different from most MCP tutorials online

Most MCP material on the web (including the well-known courses listed below) was written for the
2024-11 to 2025-11 spec revisions. The **2026-07-28** revision changed the core protocol:

| Old (≤ 2025-11-25) | Now (2026-07-28) |
|---|---|
| `initialize` / `initialized` handshake, `Mcp-Session-Id` sessions | **Stateless.** Every request carries protocol version + client capabilities in `_meta`. Optional `server/discover`. |
| Server→client requests (`sampling/createMessage`, `elicitation/create`, `roots/list`) over a held-open stream | **Multi Round-Trip Requests (MRTR).** The tool returns `resultType: "input_required"` and the client retries with `inputResponses`. |
| HTTP GET SSE stream + `resources/subscribe` | One opt-in **`subscriptions/listen`** stream |
| JSON body is the only routing signal | **`Mcp-Method` / `Mcp-Name` headers** are required on Streamable HTTP, so gateways can route and authorize without parsing bodies |
| No caching semantics | `tools/list` etc. carry **`ttlMs` + `cacheScope`** |
| Tasks experimental in core | Tasks is an **extension** (`io.modelcontextprotocol/tasks`), alongside MCP Apps and Enterprise-Managed Authorization |
| Dynamic Client Registration (DCR) | **DCR deprecated** in favor of Client ID Metadata Documents (CIMD). RFC 9207 `iss` validation is required. |
| Sampling, Roots, Logging | **Deprecated** (12-month window). `ping` and `logging/setLevel` are removed. |
| Python: `from mcp.server.fastmcp import FastMCP` | Python SDK v2: **`from mcp.server import MCPServer`** (FastMCP was renamed; the old import raises) |
| TS: `@modelcontextprotocol/sdk` | TS SDK v2: split packages, **`@modelcontextprotocol/server`** / `client` |

See [docs/whats-changed.md](docs/whats-changed.md) for how to read older tutorials against the current spec.

## Prerequisites

- Python ≥ 3.10 and [`uv`](https://docs.astral.sh/uv/). The course was verified on Python 3.13.5 and uv 0.13.
- Node ≥ 22.19 for the MCP Inspector (v2 requires it). Node ≥ 20 is enough for the TypeScript appendix.
- Comfortable with async Python, pytest, HTTP and OAuth basics (bearer tokens, audiences, scopes).

```bash
uv sync                      # installs mcp[cli]==2.3.0, httpx, pyjwt, pytest, hypothesis
make test                    # reference tests for every module (58 + 1 opt-in live test, ~10 s, offline except module 08's uvx build)
```

`make` is GNU Make; every target is a thin wrapper around `uv run python course_kit/kit.py …` if you prefer not to use it.

## How to take this course

The course content under `modules/` is **read-only**: lessons, reference code, exercise checks and solutions. Your work
lives in `workspace/`, which is ignored on `main`, so finishing the course never leaves a mess in the content and course
updates merge cleanly.

```bash
make learner-branch NAME=chris   # once: creates learner/chris, where workspace/ and PROGRESS.md are tracked
make start 01                    # copies modules/01-*/code/ to workspace/01-first-stdio-server/ + a NOTES.md
#   ...do the module's tutorial and exercises in workspace/01-first-stdio-server/...
make check 01                    # runs module 01's exercise checks against your copy
make progress                    # writes PROGRESS.md: a checklist of every exercise in every module
git add -A && git commit -m "module 01"
git merge main                   # later: pull in course updates; main never touches workspace/ or PROGRESS.md
```

| Command | What it does |
|---|---|
| `make start NN` | Copies `modules/NN-*/code/` to `workspace/NN-*/` (skipping caches, `node_modules`, `dist`, keys) and creates `NOTES.md` with a section per exercise. Never overwrites existing work (`FORCE=1` recopies code). `make start typescript` for the appendix. |
| `make check NN` | Runs `modules/NN-*/exercises/test_exN_*.py` against your workspace copy and prints ✔/✘ per exercise. Exit status 0 only when all pass. |
| `make progress` | Runs every exercise check and writes `PROGRESS.md`. Unstarted modules show as "not started". |
| `make test` | Runs the reference tests in `modules/*/code` and `appendix-typescript/code`; they must stay green. |
| `make solve NN FORCE=1` | Spoiler: copies `solutions/files/` over your copy and `solutions/NOTES.md` over your notes (the old notes are kept as `NOTES.before-solve.md`). |
| `make list` | Lists modules, exercise counts and which ones you have started. |

Exercise checks skip when the module has not been started. Coding exercises are tested against your copy (often by importing
your server and calling it in-memory or over real stdio/HTTP). Discussion exercises check that the matching
`## Exercise N` section of your `NOTES.md` has a substantive answer touching the key idea; they cannot judge
whether it is right, so compare with `solutions/NOTES.md`. Exercises that need things the checks cannot see (a real IdP,
a real host, TestPyPI, an LLM API key, Docker) are graded on what you record in `NOTES.md`, which is self-attested.

## Module map

| # | Module | You build | Key ideas |
|---|---|---|---|
| 01 | [First stdio server](modules/01-first-stdio-server/) | `textkit`: 3 tools | `MCPServer`, schema from type hints, structured output, `ToolError`, annotations, the raw stateless wire protocol |
| 02 | [Resources & prompts](modules/02-resources-and-prompts/) | `runbooks` | Static and RFC 6570 templated resources, prompts with embedded resources, completions, cache hints, `subscriptions/listen` |
| 03 | [Wrapping a real API](modules/03-wrapping-a-real-api/) | `depintel` (PyPI + OSV.dev) | Lifespan-managed clients, strict input patterns, upstream error mapping, truncation, bounded concurrency, progress, offline tests with `MockTransport` |
| 04 | [Human-in-the-loop & state](modules/04-human-in-the-loop-and-state/) | `changes` | MRTR via `Resolve`/`Elicit`, hand-built `InputRequiredResult`, sealed `request_state`, HMAC handles instead of sessions |
| 05 | [Streamable HTTP + OAuth](modules/05-streamable-http-and-auth/) | `notes` (remote) | Resource-server role, JWT verification with audience binding, RFC 9728 PRM, per-tool scopes, `Mcp-Method`/`Mcp-Name`, Host allowlist, scaling notes |
| 06 | [Testing & debugging](modules/06-testing-and-debugging/) | Test harness for `depintel` | In-memory `Client`, contract tests, catalog lockfile, Inspector CLI `--strict` in CI, both protocol eras |
| 07 | [Security hardening](modules/07-security-hardening/) | `hardened` + `audit_catalog.py` | Output fencing against indirect injection, SSRF guard, path jail, strict-args, rate limiting and audit middleware, tool-poisoning scanner, rug-pull pinning |
| 08 | [Packaging & distribution](modules/08-packaging-and-distribution/) | `depintel-mcp` wheel | `uvx` entry point, `server.json` + MCP Registry, MCPB, host configs (Claude Code/Desktop, Cursor, VS Code), container deploy |
| A | [TypeScript appendix](appendix-typescript/) | `textkit-ts` | `McpServer` + zod v4, `serveStdio`, `createMcpHandler`, interop with the Python client |

Suggested pace: one module per sitting (1.5–3 h each). Modules 05 and 07 are the longest.

## Learning outcomes

By the end you can:

1. Explain the 2026-07-28 stateless protocol at the wire level and say what it implies for load balancing, caching and gateways.
2. Choose the right primitive (tool, resource or prompt) by who is in control: the model, the application or the user.
3. Build production-shaped tools: validated inputs, structured outputs, honest annotations, errors the model can recover from, and bounded outputs.
4. Implement human-in-the-loop confirmation that works on stateless infrastructure (MRTR), and carry state across calls without sessions.
5. Deploy a remote server as an OAuth 2.1 resource server that validates audience, issuer and expiry and enforces scopes per tool, and avoid token passthrough.
6. Test servers in-memory, black-box (Inspector CLI) and contractually (catalog pinning), across both protocol eras.
7. Threat-model an MCP server (indirect prompt injection, tool poisoning and shadowing, rug pulls, SSRF, path traversal, confused deputy) and apply concrete mitigations.
8. Package, publish (MCP Registry) and connect a server to the major hosts.

## Curated external resources (verified 2026-10-19)

**Official, current (2026-07-28 era): read these first**

| Resource | Date | Why |
|---|---|---|
| [MCP Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) | 2026-07-28 | The source of truth. Read Overview, Transports, Tools, Authorization. |
| [Key Changes (changelog) 2025-11-25 → 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | 2026-07-28 | Every breaking change with its SEP number, plus deprecations. |
| [The 2026-07-28 Specification (blog)](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | 2026-07-28 | Maintainers' explanation of why the protocol went stateless, MRTR and header routing. 12-minute read. |
| [Multi Round-Trip Requests pattern](https://modelcontextprotocol.io/specification/draft/basic/patterns/mrtr) | draft (live) | The MRTR mechanics used in module 04. |
| [Authorization (spec)](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) + [Security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations) | 2026-07-28 | PRM, audience binding, CIMD, RFC 9207. |
| [Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | 2026-07-28 | Confused deputy, token passthrough, SSRF, session hijacking, local-server compromise. |
| [Python SDK v2 docs](https://py.sdk.modelcontextprotocol.io/) and [What's new in v2](https://py.sdk.modelcontextprotocol.io/whats-new/) | v2.x (2026) | Excellent docs. The [Dependencies](https://py.sdk.modelcontextprotocol.io/handlers/dependencies/), [Deploy & scale](https://py.sdk.modelcontextprotocol.io/run/deploy/), [Authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/) and [Testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/) pages map directly onto modules 04, 05 and 06. |
| [Python SDK migration guide](https://py.sdk.modelcontextprotocol.io/migration/) | v2.x | Use it whenever you meet v1 (`FastMCP`) code. |
| [TypeScript SDK v2 docs](https://ts.sdk.modelcontextprotocol.io/v2/) and [Supporting 2026-07-28](https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28.html) | v2.x (2026) | Note that TS v2 does not speak 2026-07-28 unless you opt in, via `serveStdio` or `createMcpHandler`. |
| [MCP Inspector docs](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector) and [CLI](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector/cli) / [repo](https://github.com/modelcontextprotocol/inspector) | v2.11 | Web, CLI, TUI. The CLI's `--strict` flag and its stable exit codes make it a good CI gate. |
| [MCP Registry quickstart](https://modelcontextprotocol.io/registry/quickstart) and [repo](https://github.com/modelcontextprotocol/registry) | live (registry still "preview") | `server.json`, `mcp-publisher`, namespace and ownership verification. |
| [MCPB (MCP Bundles)](https://github.com/modelcontextprotocol/mcpb) | updated 2026-05 | One-click local server install (formerly DXT). |

**Security (beyond the spec)**

| Resource | Why |
|---|---|
| [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) | The best single checklist: tool poisoning, rug pulls, shadowing, hash-pinning full tool definitions, sandboxing, HITL. Module 07 implements several of its items. |

**Ecosystem**

| Resource | Date | Note |
|---|---|---|
| [FastMCP 4 (standalone, PrefectHQ) — What's new](https://gofastmcp.com/getting-started/whats-new) / [v4.0.0 release](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.0.0) | 2026-08-31 | The *independent* FastMCP framework (`pip install fastmcp`, now 4.1.1). It is not the SDK's old `FastMCP` class. It adds composition, proxies, background tasks and enterprise auth on top of the official SDK. Worth knowing; this course sticks to the official SDK. |
| [panaversity/learn-stateless-mcp](https://github.com/panaversity/learn-stateless-mcp) | 2026-08 | Small community repo that builds the stateless revision twice (Python v2 and TS v2), lesson by lesson. A good companion to modules 01 and 04. |
| [Video: "MCP 2026-07-28 Changes Everything" (Coding Crash Courses)](https://www.youtube.com/watch?v=V1qjiZcG0p0) | 2026-08-03 | Community video walkthrough of the new spec. Useful as a quick overview; I verified the title and date, not the full content. |

**Well-known courses: conceptually good, technically pre-2026-07-28**

| Course | Status / note |
|---|---|
| [DeepLearning.AI: MCP: Build Rich-Context AI Apps with Anthropic](https://www.deeplearning.ai/courses/mcp-build-rich-context-ai-apps-with-anthropic) | Good short intro to host/client/server architecture. Teaches v1 `FastMCP` and the handshake/session model. |
| [Anthropic Academy: Introduction to MCP](https://anthropic.skilljar.com/introduction-to-model-context-protocol) and [MCP: Advanced Topics](https://anthropic.skilljar.com/model-context-protocol-advanced-topics) | Solid on primitives. "Advanced Topics" covers sampling, roots, logging notifications and the init handshake, all of which are now deprecated or removed. Read it for history and legacy-client support. |
| [Hugging Face MCP Course](https://huggingface.co/learn/mcp-course/unit0/introduction) ([repo](https://github.com/huggingface/mcp-course)) | Free, broad, with certificates. Repo active as of 2026-10, but its units predate the stateless revision. Good for the Gradio/HF ecosystem angle. |

## How the code was verified

Everything in `modules/*/code` and `appendix-typescript/code` was run on 2026-10-19 (see each module's "Verified" note):
`make test` gives 58 passed, 1 skipped (a live-network test you can enable with `LIVE=1`). Module 06's
`inspector_smoke.sh` passes against modules 01–04, and `inspector --strict` passes on every server.

The exercise checks were verified the same day for all 42 exercises: they skip with no workspace, fail on a fresh
`make start` copy, and pass after `make solve` applies the reference solutions.

## Layout

```
README.md                    this file
Makefile                     start / check / progress / test / solve / list / learner-branch
course_kit/                  kit.py (workspace + progress), exercise.py (test helpers), NOTES.template.md
docs/whats-changed.md        reading 2025-era tutorials against 2026-07-28
modules/NN-*/README.md       concepts, tutorial, exercises, further reading
modules/NN-*/code/           reference servers, clients, tests (read-only; `make test`)
modules/NN-*/exercises/      one check per exercise: test_exN_*.py (`make check NN`)
modules/NN-*/solutions/      NOTES.md (answer per exercise) + files/ (solved workspace)
appendix-typescript/         same layout for the TS SDK v2 version of module 01
pyproject.toml, conftest.py  one uv project for all modules
workspace/, PROGRESS.md      yours; ignored on main, tracked on your learner branch
```
