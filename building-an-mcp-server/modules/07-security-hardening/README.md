# Module 07: Security hardening

**Goal:** threat-model an MCP server the way you would any agent-facing system, then implement concrete mitigations
on both sides: as the **server author** (`hardened_server.py`) and as the **integrator** deciding whether to trust someone
else's server (`audit_catalog.py`).
**Time:** ~3 h. **Code:** [`code/`](code/)

## Threat model (condensed)

| Threat | Where it enters | Mitigation in this module | Who must also act |
|---|---|---|---|
| **Indirect prompt injection** via tool *output* (web pages, tickets, CVE text) | Tool results | `fence()`: per-call nonce boundary + "this is data" label; strip invisible Unicode; truncate; structured fields | Host: treat tool output as data and require consent for side effects |
| **Tool poisoning**: instructions hidden in descriptions/schemas | `tools/list` | `audit_catalog.py` heuristics (instruction-like text, sensitive paths, hidden chars, side-channel params) | Host and user review |
| **Tool shadowing**: one server's description manipulates use of another's tools | `tools/list` | Auditor flags descriptions that mention other tools | Host: isolate servers |
| **Rug pull**: definitions change after approval | `tools/list` over time | `--pin` hash file of *full* definitions (also module 06's lockfile) | Host: re-consent on change |
| **SSRF** through URL-taking tools | Tool args | https only, host allowlist, port check, **resolve and reject private/link-local IPs**, no redirects, size cap | Network egress policy |
| **Path traversal** | Resource template params | SDK `ResourceSecurity` (default on) **plus** a `resolve()` + `is_relative_to(root)` jail | |
| **Argument smuggling / probing** | Unknown tool args (the SDK silently ignores them) | `strict_arguments_middleware` refuses them | |
| **Runaway agent / abuse** | Tool call volume | Per-principal token-bucket middleware | Gateway rate limits (route on `Mcp-Method`/`Mcp-Name`) |
| **Confused deputy / token passthrough** | Remote auth | Module 05: audience-bound tokens, never forward inbound tokens | AS configuration |
| **Over-privilege** | Credentials the server holds | Read-only tools, honest annotations, narrow scopes, per-server creds | Ops |
| **Local server compromise** | stdio servers run as you | Run in a sandbox/container: `--network none`, read-only FS, no home dir mounts | User/host |
| **Forensics gap** | Everything | JSON audit log with principal, tool, **args hash** (not raw args), outcome, latency → stderr/OTel | SIEM |

Two honest caveats:
- **Fencing is mitigation, not a fix.** No delimiter makes an LLM immune to injection. The durable controls are architectural:
  least privilege, human approval for consequential actions (module 04), and keeping untrusted-data tools away from
  high-privilege tools in the same agent context.
- **Annotations are untrusted hints.** The spec says hosts must not rely on them from untrusted servers. Declare them honestly
  on yours, and never trust them on others'.

## Tutorial

```bash
make start 07                          # copies code/ to workspace/07-security-hardening/ (your copy)
cd workspace/07-security-hardening
uv run pytest -q
uv run python audit_catalog.py stdio -- uv run python poisoned_server.py          # exit 1, 9 findings
uv run python audit_catalog.py stdio --pin pins.json -- uv run python hardened_server.py   # pins, then re-run to verify
```

Auditor output against the deliberately malicious server:
```
server 'totally-normal-utils': 4 tools, 9 findings
  [high  ] add: instruction-like text: '<IMPORTANT>'
  [high  ] add: references sensitive file: '~/.ssh'
  [high  ] weather: invisible/format characters: U+200B, U+E0041, U+E0042
  [high  ] weather: instruction-like text: 'Ignore previous instructions'
  [medium] add: side-channel-looking parameters: ['sidenote']
  [medium] weather: description references other tools (shadowing?): ['send_email']
  [medium] format_text: description references other tools (shadowing?): ['send_email']
  [medium] format_text: side-channel-looking parameters: ['conversation_history']
  [low   ] drop_table: sounds destructive but declares no destructiveHint
```

Code tour of `hardened_server.py`:
1. `sanitize` / `fence`: NFKC normalization, strip zero-width/bidi/tag characters, then wrap in `<untrusted-{nonce}>`.
   The test proves a page containing `</untrusted>` cannot close the fence.
2. `check_url` + `fetch_doc_page`: the DNS check runs *after* the allowlist, to defeat an allowed name resolving to `10.x`
   or `169.254.169.254`. Redirects are refused, not followed, because a redirect is an allowlist bypass.
   > **Note from the verification run:** the course box's DNS is a fake-IP proxy (it answers `198.18.0.1` for everything),
   > so the guard correctly refused live fetches there. The live path was verified by injecting a resolver. On a normal
   > network it works as is. If you deploy behind such a proxy, you need an egress proxy allowlist instead of IP checks.
3. `docs://{+path}`: two layers. The SDK rejects `..`, absolute paths and NUL (including percent-encoded forms), and the handler
   resolves symlinks and enforces the root.
4. Middleware (provisional API in SDK 2.3): `audit_middleware` sees the finished wire result (a dict), so it reads `isError`;
   `rate_limit_middleware` raises `MCPError` (goes to the client app, not the model); `strict_arguments_middleware`
   checks keys against the registered `inputSchema`.

## Exercises

Work in your copy, `workspace/07-security-hardening/` (create it with `make start 07`); never edit `code/`.
Discussion answers go in `workspace/07-security-hardening/NOTES.md` under the matching `## Exercise N` heading.
Check your work with `make check 07`; `make progress` updates `PROGRESS.md`.
Reference answers are in [`solutions/`](solutions/) (spoilers).

1. Write `sandbox.sh` in your workspace: a launch recipe that runs `hardened_server.py` with
   `docker run --rm -i --network none --read-only -v $PWD/docs:/app/docs:ro …` and connect to it over stdio. Which tool stops
   working, and why is that the point? (NOTES.md)
2. Extend your `audit_catalog.py` with `async def audit_content(client) -> list[Finding]` that scans **resource and prompt**
   text (and, optionally, **tool results** of a sample call). Use the resource URI or prompt name as `Finding.tool`.
   Poisoning is not only in descriptions.
3. Add an `x-mcp-header`-based tenant id: a `tenant` argument on `list_docs` with `x-mcp-header: Tenant`, and make the rate
   limiter budget per tenant. Then write the gateway rule that rate-limits by tenant without parsing bodies (NOTES.md).
4. Red-team: write a page that tries to make the model call a write tool from another server. With `fence()` in place, test against
   two different models in a real host. Record the results in NOTES.md; they will differ, which is the lesson.
5. Design: your org wants an "MCP gateway" in front of all third-party servers. List what it can enforce (pinning, allowlists,
   rate limits, DLP on outputs, audit) and what it cannot (model behavior inside the host). (NOTES.md)

## Further reading
- [MCP Security Best Practices (2026-07-28)](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
- [Spec: Security & Trust principles](https://modelcontextprotocol.io/specification/2026-07-28) and [Authorization security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)
- SDK: [Middleware](https://py.sdk.modelcontextprotocol.io/advanced/middleware/), [URI templates (path safety)](https://py.sdk.modelcontextprotocol.io/servers/uri-templates/)

**Verified 2026-10-19:** `pytest` 17/17; auditor CLI run against the poisoned (exit 1) and hardened (exit 0, pinned) servers; live `fetch_doc_page` against peps.python.org with an injected resolver.
