"""Ex 3: RFC 7662 token introspection verifier."""

import base64
from urllib.parse import parse_qs

import httpx
import pytest

from course_kit.exercise import load, require_answer, workspace

WS = workspace(__file__)
RESOURCE = "http://127.0.0.1:8765/mcp"
URL = "https://auth.dev.example/oauth2/introspect"


def introspection_endpoint(active_tokens: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and str(request.url) == URL
        assert request.headers["authorization"] == "Basic " + base64.b64encode(b"notes-rs:s3cret").decode()
        token = parse_qs(request.content.decode())["token"][0]
        return httpx.Response(200, json=active_tokens.get(token, {"active": False}))

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_introspection_verifier():
    mod = load(WS, "notes_http_server.py")
    assert hasattr(mod, "IntrospectionVerifier"), "add an IntrospectionVerifier class to notes_http_server.py"
    tokens = {
        "good": {"active": True, "sub": "alice", "client_id": "cli", "scope": "notes:read notes:write",
                 "aud": RESOURCE, "exp": 4102444800, "iss": "https://auth.dev.example"},
        "other-aud": {"active": True, "sub": "mallory", "scope": "notes:read", "aud": "https://other.example", "exp": 4102444800},
    }
    v = mod.IntrospectionVerifier(URL, "notes-rs", "s3cret", RESOURCE, transport=introspection_endpoint(tokens))
    ok = await v.verify_token("good")
    assert ok is not None and ok.subject == "alice" and ok.scopes == ["notes:read", "notes:write"]
    assert await v.verify_token("revoked") is None, "inactive tokens must be rejected"
    assert await v.verify_token("other-aud") is None, "audience binding still applies"


def test_trade_offs():
    require_answer(WS, 3, min_words=25, mentions=(("revoc", "revok"), ("latency", "round trip", "round-trip", "network")))
