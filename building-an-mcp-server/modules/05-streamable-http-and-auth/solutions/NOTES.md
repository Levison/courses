# Notes: Module 05 (reference answers)

Code is in [`files/`](files/): `notes_http_server.py` (exercises 2 and 3).

## Exercise 1: A real IdP

The course author did not run this one: it needs an IdP tenant, and this edition was built without one. Here is what a
completed answer records, with Keycloak as the example:

- `JWTVerifier` now takes `jwt.PyJWKClient("https://kc.example.com/realms/mcp/protocol/openid-connect/certs")` and calls
  `get_signing_key_from_jwt(token)` per request (PyJWKClient caches keys and handles `kid` rotation). The checks on
  `iss`, `aud` and `exp` and the RS256 pin stay the same.
- Env: `MCP_ISSUER=https://kc.example.com/realms/mcp`, `MCP_RESOURCE_URL=https://notes.example.com/mcp`, plus a
  `MCP_ALLOWED_HOSTS` that matches.
- PRM (`/.well-known/oauth-protected-resource/mcp`):
  `{"resource": "https://notes.example.com/mcp", "authorization_servers": ["https://kc.example.com/realms/mcp"], "scopes_supported": ["notes:read"], ...}`
- The discovery dance seen from `claude mcp add --transport http notes https://notes.example.com/mcp`: 401 with
  `resource_metadata`, then PRM, then AS metadata, then the browser login with PKCE and `resource=`, then calls with the token.
  The usual snag: the IdP must put the MCP URL in `aud` (Keycloak needs an audience mapper; Entra uses the App ID URI
  unless configured otherwise).

## Exercise 2: `notes:admin` and `purge_notes`

`TOOL_SCOPES["purge_notes"] = {"notes:read", "notes:admin"}` makes the middleware answer `403` with
`WWW-Authenticate: Bearer error="insufficient_scope", scope="notes:admin notes:read"` for modern clients. That is the
step-up signal: an OAuth-capable client re-authorizes with the extra scope. `require_scope("notes:admin")` inside the
tool covers legacy clients, which send no `Mcp-Name`. `destructiveHint=True` lets hosts insist on confirmation.

## Exercise 3: Token introspection (RFC 7662)

`IntrospectionVerifier` POSTs `token=...` to the AS introspection endpoint with the RS's own client credentials (Basic
auth), and accepts the token only if `active` is true and `aud` contains our resource. Audience binding still applies.
Gain: **revocation** is immediate (a logged-out user or a stolen token stops working on the next request), and
tokens can be opaque, so no claims leak to clients. Lose: a network **round trip** to the AS on every request
(added latency, and the AS becomes a hard runtime dependency, so its outage is yours). The usual compromise is to
cache positive results for a few seconds, keyed by a token hash. It fails closed on any AS error.

## Exercise 4: Calling a downstream API on the user's behalf (RFC 8693)

Use RFC 8693 token exchange. Forwarding the inbound token is forbidden (token passthrough): it was issued with `aud` = this MCP server, so a
correct downstream API rejects it. A downstream that accepts it is not checking audience, which lets anyone holding a
token for any service call it. That is a confused deputy, and it also erases the audit trail of who called what. Instead:
1. The MCP server receives the user's token (aud = notes MCP server) and validates it as usual.
2. It calls the AS token endpoint with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`,
   `subject_token=<inbound token>`, `subject_token_type=...:access_token`, `resource`/`audience=https://calendar.api.example`,
   a narrow `scope`, and authenticates as itself (client credentials, or better, private_key_jwt).
3. The AS applies policy (is this RS allowed to act for this user against that API?) and returns a new short-lived token
   with `aud` = the downstream API, `sub` = the user, and an `act` claim naming the MCP server (delegation, visible in audit).
4. The MCP server calls the downstream API with that token and caches it until expiry, per user and audience.
Entra's on-behalf-of flow is the vendor-specific version of the same idea.

## Exercise 5: Multiple workers

Measured on 2026-10-19 with `uvicorn notes_http_server:app --workers 4`: 5/5 modern (2026-07-28) client connections
succeeded, each making 4 calls with no stickiness, because every request is self-contained and the protocol has no session.
With `mode="legacy"` only 1 of 5 connections survived. A 2025-era client gets an `Mcp-Session-Id` from the worker
that handled `initialize`, and the next request lands on a worker that has never seen that session. Legacy
clients need sticky sessions at the load balancer (hash on `Mcp-Session-Id`), or `stateless_http=True` for the legacy path.
