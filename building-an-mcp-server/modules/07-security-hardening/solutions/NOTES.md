# Notes: Module 07 (reference answers)

Code is in [`files/`](files/): `sandbox.sh` (1), `audit_catalog.py` (2), `hardened_server.py` (3).

## Exercise 1: Sandboxed launch

`sandbox.sh` builds a small image (network needed once, to install `mcp`), then runs the server over stdio with
`--network none --read-only --cap-drop ALL --security-opt no-new-privileges`, a non-root user, a size-limited tmpfs, pid and
memory limits, and `docs/` mounted `:ro`. **`fetch_doc_page` stops working**: with no network, DNS resolution fails
and the tool returns "Fetch failed." That is the point: the container enforces least privilege even if the code
has a bug or the model is tricked, while `list_docs` and `docs://` keep working from the read-only mount. Run a
network-needing tool in a separate container with an egress proxy that applies the allowlist, not in the same
process as file access. Not verified on the build machine (no Docker there); `bash -n` checks the syntax only.

## Exercise 2: Audit resources, prompts and results

`text_findings(where, text)` factors the hidden-character, injection and sensitive-path checks out of `audit()`, and
`audit_content(client)` applies them to resource metadata and static resource contents, template descriptions, and
prompts rendered with placeholder arguments. With `--sample-calls` it also covers results of read-only tools that take
no arguments. A prompt that fails to render is reported as low severity instead of being skipped silently. On the
course servers it reports 0 high findings; on a server whose README resource says "Ignore previous instructions" it flags
`docs://readme`. Remember that a server can serve clean content to a scanner and poisoned content later, so pin
content hashes where you can and re-scan.

## Exercise 3: Tenant header and per-tenant limits

`list_docs` gets `tenant: Annotated[str, Field(..., json_schema_extra={"x-mcp-header": "Tenant"})]`. A 2026-07-28
client mirrors the argument into an **`Mcp-Param-Tenant`** header, and the server rejects a request whose header
disagrees with the body (the same cross-check as `Mcp-Name`), so the header is trustworthy for routing. Gateway rule
(nginx; an empty key is not limited, so only `tools/call` counts):

```nginx
map $http_mcp_method $tenant_key { "tools/call" $http_mcp_param_tenant; default ""; }
limit_req_zone $tenant_key zone=tenants:10m rate=60r/m;
location /mcp { limit_req zone=tenants burst=20 nodelay; limit_req_status 429; proxy_pass http://mcp_upstream; }
```

The gateway never parses JSON. In-server, the rate limiter keys on
`principal|tenant`. Caveat: the tenant is caller-supplied, so authorization (is this principal allowed to act for this
tenant?) still needs the token, typically a `tenant` claim compared to the header.

## Exercise 4: Red-team results

What to record: the page text, the host, the two models, and for each whether the model (a) treated the fenced content
as data, (b) mentioned the injection to the user, or (c) attempted the write-tool call, and whether the host's
confirmation dialog appeared. The course author could not run this for this edition (it needs real hosts and model
access), so there are no reference numbers. The expected lesson, from published evaluations of spotlighting: the
fence lowers the success rate but does not eliminate it, and results vary by model and by phrasing. The control that
holds regardless is the host requiring user confirmation for side-effecting tools, plus least-privilege tool sets per
task. Treat the untrusted boundary as one layer, not the defense.

## Exercise 5: What an MCP gateway can and cannot enforce

Can enforce (it sees every request and response): server and tool **allowlists**; **pinning** tool definitions by hash
and blocking catalog drift (rug pulls); authentication, audience checks and token exchange so servers never see user
tokens; per-principal, per-tenant and per-tool **rate limits** routed on `Mcp-Method`/`Mcp-Name`/`Mcp-Param-*` headers;
**DLP** on tool results and arguments (secrets, PII), plus size caps; protocol-version policy; full **audit** logs with
argument hashes; scanning resources and prompts for injection.
Cannot enforce: what the model does with content inside the host (whether an injected instruction persuades it), how
the host renders confirmations or whether the user reads them, data flows between servers that happen inside the
host's context window, local stdio servers that never go through the gateway, and semantic misuse of allowed tools with
valid arguments. Those need host-side controls (consent UX, tool scoping per task) and least privilege at each server.
