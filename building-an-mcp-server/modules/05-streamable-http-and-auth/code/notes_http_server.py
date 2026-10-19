"""Module 5: a remote MCP server over Streamable HTTP, protected as an OAuth 2.1
resource server.

    uvicorn notes_http_server:app --port 8765          # or: python notes_http_server.py

What you get:
  POST /mcp                                        the MCP endpoint (2026-07-28 + legacy clients)
  GET  /.well-known/oauth-protected-resource/mcp   RFC 9728 Protected Resource Metadata
  GET  /healthz                                    unauthenticated liveness probe
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import jwt
from pydantic import AnyHttpUrl, BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

import dev_issuer

RESOURCE = os.environ.get("MCP_RESOURCE_URL", dev_issuer.RESOURCE)
ISSUER = os.environ.get("MCP_ISSUER", dev_issuer.ISSUER)


class JWTVerifier(TokenVerifier):
    """Verify RS256 JWT access tokens: signature, issuer, expiry, and AUDIENCE.

    Audience binding is the core defence against token passthrough / confused
    deputy: a token minted for some other API must not work here. For a real IdP,
    swap the static key for `jwt.PyJWKClient(jwks_uri)` and keep everything else.
    """

    def __init__(self, public_key_pem: bytes, issuer: str, audience: str):
        self.key, self.issuer, self.audience = public_key_pem, issuer, audience

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = jwt.decode(
                token,
                self.key,
                algorithms=["RS256"],  # never accept "none"/HS* confusion
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
                leeway=30,
            )
        except jwt.PyJWTError:
            return None
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", "unknown"),
            scopes=claims.get("scope", "").split(),
            expires_at=claims["exp"],
            resource=self.audience,  # we verified aud == our resource
            subject=claims["sub"],
            claims={"iss": claims["iss"]},
        )


mcp = MCPServer(
    "notes",
    version="0.5.0",
    token_verifier=JWTVerifier(dev_issuer.public_key_pem(), ISSUER, RESOURCE),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER),
        resource_server_url=AnyHttpUrl(RESOURCE),
        required_scopes=["notes:read"],  # floor for every request
        validate_token_resource=True,
    ),
)

NOTES: dict[str, list[str]] = {}  # per-subject notebooks


def caller() -> AccessToken:
    tok = get_access_token()
    if tok is None:  # stdio / in-memory: no HTTP auth layer at all
        raise ToolError("This server requires an authenticated HTTP connection.")
    return tok


def require_scope(scope: str) -> AccessToken:
    tok = caller()
    if scope not in tok.scopes:
        # Per-tool authorization beyond the global floor.
        raise ToolError(f"Missing scope {scope!r}. Re-authorize with that scope.")
    return tok


class Identity(BaseModel):
    subject: str | None
    client_id: str
    scopes: list[str]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def whoami() -> Identity:
    """Who is calling, per the verified access token."""
    t = caller()
    return Identity(subject=t.subject, client_id=t.client_id, scopes=t.scopes)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_notes() -> list[str]:
    """List the caller's notes."""
    return NOTES.get(caller().subject or "", [])


@mcp.tool()
def add_note(text: str) -> int:
    """Add a note to the caller's notebook. Requires notes:write."""
    t = require_scope("notes:write")
    NOTES.setdefault(t.subject or "", []).append(text)
    return len(NOTES[t.subject or ""])


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


# ---------- Step-up authorization at the HTTP layer, routed on the Mcp-Name header ----------
# 2026-07-28 requires Mcp-Method/Mcp-Name headers and the SDK rejects a header that
# disagrees with the body (-32020), so a gateway or middleware can authorize per tool
# without parsing JSON. Answering 403 insufficient_scope (RFC 6750) lets an OAuth-capable
# client run the spec's step-up flow and re-authorize with the missing scope.
TOOL_SCOPES = {"add_note": {"notes:read", "notes:write"}}


class ScopeChallenge:
    def __init__(self, app, verifier: TokenVerifier):
        self.app, self.verifier = app, verifier

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST":
            h = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            needed = TOOL_SCOPES.get(h.get("mcp-name", "")) if h.get("mcp-method") == "tools/call" else None
            auth = h.get("authorization", "")
            if needed and auth.lower().startswith("bearer "):
                tok = await self.verifier.verify_token(auth[7:])
                if tok is not None and not needed <= set(tok.scopes):
                    challenge = (
                        f'Bearer error="insufficient_scope", scope="{" ".join(sorted(needed))}", '
                        f'resource_metadata="{PRM_URL}"'
                    )
                    await send({"type": "http.response.start", "status": 403,
                                "headers": [(b"www-authenticate", challenge.encode()), (b"content-type", b"application/json")]})
                    await send({"type": "http.response.body", "body": b'{"error":"insufficient_scope"}'})
                    return
        await self.app(scope, receive, send)


_u = urlsplit(RESOURCE)
PRM_URL = f"{_u.scheme}://{_u.netloc}/.well-known/oauth-protected-resource{_u.path}"

# Host/Origin allowlist (DNS-rebinding protection). Defaults to localhost only;
# set MCP_ALLOWED_HOSTS="mcp.example.com,mcp.example.com:*" when you deploy.
allowed = os.environ.get("MCP_ALLOWED_HOSTS")
security = (
    TransportSecuritySettings(allowed_hosts=allowed.split(","), allowed_origins=[]) if allowed else None
)
app = ScopeChallenge(mcp.streamable_http_app(transport_security=security), mcp._token_verifier)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
