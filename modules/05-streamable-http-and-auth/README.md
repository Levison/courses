# Module 05: Remote servers: Streamable HTTP and OAuth 2.1

**Goal:** serve MCP over HTTP to many users, as a proper OAuth **resource server**: verify audience-bound JWTs, advertise
Protected Resource Metadata, enforce scopes per tool (including step-up 403s routed on `Mcp-Name`), and lock down `Host`.
**Time:** ~3 h. **Code:** [`code/`](code/)

## Concepts

**Streamable HTTP at 2026-07-28**
- One endpoint (`/mcp`). A client POSTs one JSON-RPC request and gets back either `application/json` or an SSE stream
  (for progress and request-scoped notifications). There is **no session**: the SDK never sets `Mcp-Session-Id` for modern
  requests, so any worker can serve any request. Change notifications use a separate long-lived `subscriptions/listen` POST.
- **Required headers:** `MCP-Protocol-Version`, `Mcp-Method`, and for `tools/call`, `prompts/get` and `resources/read`, `Mcp-Name`.
  The server **cross-checks headers against the body** and answers `-32020 HeaderMismatch` on disagreement. That check is
  what makes header-based routing and authorization safe for gateways, WAFs, rate limiters and this module's step-up middleware.
- **No resumability:** `Last-Event-ID` redelivery was removed. A dropped stream means re-issuing the request with a new id.
- The same `streamable_http_app()` also serves **2025-era clients** (handshake, sessions). Those still need sticky sessions
  unless you set `stateless_http=True` (a legacy-only knob).

**Authorization (spec: Authorization 2026-07-28)**
- Your MCP server is a **resource server (RS)**. It never logs anyone in. The **authorization server (AS)** is your IdP.
- Discovery chain: `401` + `WWW-Authenticate: Bearer resource_metadata="…"` → **RFC 9728 PRM** document → `authorization_servers`
  → AS metadata → OAuth 2.1 + PKCE, with the **RFC 8707 `resource`** parameter naming your MCP URL → token.
- **Audience binding is the core control.** Accept only tokens issued *for this server* (`aud`/`resource` == your canonical URL).
  This is what stops **token passthrough** and the confused deputy. Never forward the client's token to a downstream API: get your
  own downstream token (on-behalf-of, token exchange, or your own credentials).
- **Client registration in 2026:** Client ID Metadata Documents (CIMD) are the SHOULD. DCR is **deprecated**. Clients must
  validate `iss` in the authorization response (RFC 9207), and credentials are bound to their issuer. Those are AS/client concerns,
  but know them when you choose an IdP.
- **Scopes:** a global floor (`required_scopes`, enforced by the SDK with 401/403), plus per-tool checks. The spec's
  **step-up** flow expects `403` + `WWW-Authenticate: Bearer error="insufficient_scope", scope="…"`.
  The Python SDK 2.3 has no per-tool scope-challenge API (the TS SDK has `scopeChallenge`), so this module implements it as ASGI
  middleware keyed on `Mcp-Name`, with an in-tool check as the backstop for legacy clients that send no header.

**Production checklist (from the SDK's [Deploy & scale](https://py.sdk.modelcontextprotocol.io/run/deploy/))**
- `TransportSecuritySettings(allowed_hosts=[...])`. The default allows only localhost, which gives **421 Invalid Host** behind a
  real hostname (DNS-rebinding protection).
- Behind a TLS proxy run `uvicorn --proxy-headers --forwarded-allow-ips=…`, or redirects downgrade to http and the client refuses them.
- With multiple workers, share `RequestStateSecurity(keys=[...])` **and** keep the same server name/audience (module 04).
- Cross-replica `subscriptions/listen` needs your own `SubscriptionBus`.
- `@mcp.custom_route("/healthz")` is never authenticated. Use it for liveness only.

## Tutorial

```bash
cd modules/05-streamable-http-and-auth/code
uv run uvicorn notes_http_server:app --port 8765      # terminal 1
uv run python http_walkthrough.py                     # terminal 2
uv run pytest -q                                      # spawns its own server on a free port
```

`dev_issuer.py` stands in for your IdP: it keeps an RSA key (gitignored) and mints RS256 JWTs with `iss`, `aud`, `scope`
and `exp`. `JWTVerifier` checks signature, `iss`, `aud`, `exp` and required claims, and pins `algorithms=["RS256"]`. For a real IdP, swap the
static key for `jwt.PyJWKClient(jwks_uri)`.

Walkthrough output (2026-10-19, abridged):
```
1) PRM: {'resource': 'http://127.0.0.1:8765/mcp', 'authorization_servers': ['https://auth.dev.example/'], 'scopes_supported': ['notes:read'], ...}
2) No token -> 401 | WWW-Authenticate: Bearer error="invalid_token", ..., resource_metadata=".../.well-known/oauth-protected-resource/mcp"
3) Token for a different audience -> 401
4) Good token, Mcp-Method/Mcp-Name headers -> 200 application/json
5) Mcp-Name header disagrees with body -> 400 {"error":{"code":-32020, ...}}
6) SDK client protocol: 2026-07-28; add_note -> {'result': 1}
7) modern client, read-only token, add_note -> 403 insufficient_scope (surfaces as MCPError without an OAuth provider)
8) legacy client (no Mcp-Name header) -> in-tool backstop: "Missing scope 'notes:write'"
```

Inspector against the running server:
```bash
TOK=$(uv run python dev_issuer.py mint --scope "notes:read notes:write")
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8765/mcp --header "Authorization: Bearer $TOK" --method tools/call --tool-name add_note --tool-arg text=hello
```
Without a header and without a TTY, the Inspector CLI exits **3** (`auth_required`). For a real OAuth AS it can run the
interactive flow, or reuse tokens from the web inspector with `--use-stored-auth` / `--stored-auth-only`.

## Exercises

1. Point the verifier at a real IdP (Auth0, Entra, Keycloak or Okta free tier) using `PyJWKClient`. Make the PRM advertise it.
   Connect from Claude Code with `claude mcp add --transport http notes <url>` and watch the discovery dance.
2. Add `notes:admin` and a `purge_notes` tool. Require step-up via `TOOL_SCOPES` and add `destructiveHint=True`.
3. Implement token **introspection** (RFC 7662) instead of local JWT verification. What do you gain (revocation) and lose (latency)?
4. Your notes tool must call a downstream API on the user's behalf. Sketch an RFC 8693 token-exchange flow and explain why
   forwarding the inbound token is forbidden.
5. Run `uvicorn --workers 4` and confirm a 2026 client works with no stickiness, then confirm `mode="legacy"` clients break without it.

## Further reading
- Spec: [Transports](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports), [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization), [Authorization security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)
- SDK: [Authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/), [Deploy & scale](https://py.sdk.modelcontextprotocol.io/run/deploy/), [OAuth clients](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/), [Header parameters](https://py.sdk.modelcontextprotocol.io/advanced/header-parameters/), [Serving legacy clients](https://py.sdk.modelcontextprotocol.io/run/legacy-clients/)
- [Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) (confused deputy, token passthrough)

**Verified 2026-10-19:** `pytest` 7/7 against a live uvicorn (PRM, 401, wrong audience, expired, scopes, step-up 403, header spoofing, legacy client); walkthrough and Inspector CLI (`tools/list`, `tools/call` with bearer) were run.
