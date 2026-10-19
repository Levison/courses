"""End-to-end over real HTTP: spawns uvicorn on a free port."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import httpx2
import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import dev_issuer  # noqa: E402

from mcp import Client  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = free_port()
    resource = f"http://127.0.0.1:{port}/mcp"
    dev_issuer.private_key()  # make sure the key exists before the server reads it
    env = {**os.environ, "MCP_RESOURCE_URL": resource}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "notes_http_server:app", "--port", str(port), "--log-level", "warning"],
        cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            if httpx.get(f"{base}/healthz").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield base, resource
    proc.terminate()
    proc.wait(5)


def test_prm_and_401(server):
    base, resource = server
    prm = httpx.get(f"{base}/.well-known/oauth-protected-resource/mcp").json()
    assert prm["resource"] == resource
    r = httpx.post(f"{base}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401 and "resource_metadata=" in r.headers["www-authenticate"]


def test_wrong_audience_rejected(server):
    base, _ = server
    tok = dev_issuer.mint("mallory", "notes:read", audience="https://other.example")
    r = httpx.post(f"{base}/mcp", json={}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_expired_rejected(server):
    base, resource = server
    tok = dev_issuer.mint("alice", "notes:read", audience=resource, ttl=-120)
    r = httpx.post(f"{base}/mcp", json={}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_sdk_client_scopes(server):
    base, resource = server
    rw = httpx2.AsyncClient(headers={"Authorization": f"Bearer {dev_issuer.mint('alice', 'notes:read notes:write', audience=resource)}"})
    async with Client(streamable_http_client(f"{base}/mcp", http_client=rw)) as c:
        assert c.protocol_version == "2026-07-28"
        assert (await c.call_tool("add_note", {"text": "x"})).structured_content == {"result": 1}
        who = (await c.call_tool("whoami", {})).structured_content
        assert who["subject"] == "alice" and "notes:write" in who["scopes"]

    ro = httpx2.AsyncClient(headers={"Authorization": f"Bearer {dev_issuer.mint('bob', 'notes:read', audience=resource)}"})
    async with Client(streamable_http_client(f"{base}/mcp", http_client=ro), mode="legacy") as c:
        # Legacy (2025-era) clients send no Mcp-Name header, so the in-tool check is the backstop.
        r = await c.call_tool("add_note", {"text": "nope"})
        assert r.is_error and "notes:write" in r.content[0].text
    async with Client(streamable_http_client(f"{base}/mcp", http_client=httpx2.AsyncClient(headers=ro.headers))) as c:
        # Modern clients are stopped at the HTTP layer with 403 insufficient_scope (step-up signal).
        with pytest.raises(Exception):
            await c.call_tool("add_note", {"text": "nope"})
        assert (await c.call_tool("list_notes", {})).structured_content == {"result": []}  # per-subject isolation


def test_step_up_403_on_mcp_name(server):
    base, resource = server
    tok = dev_issuer.mint("bob", "notes:read", audience=resource)
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "add_note", "arguments": {"text": "x"}, "_meta": meta}}
    r = httpx.post(
        f"{base}/mcp", json=body,
        headers={"Authorization": f"Bearer {tok}", "Mcp-Method": "tools/call", "Mcp-Name": "add_note",
                 "MCP-Protocol-Version": "2026-07-28", "Accept": "application/json, text/event-stream"},
    )
    assert r.status_code == 403
    assert 'error="insufficient_scope"' in r.headers["www-authenticate"]
    assert 'scope="notes:read notes:write"' in r.headers["www-authenticate"]


@pytest.mark.anyio
async def test_legacy_client_still_served(server):
    base, resource = server
    h = httpx2.AsyncClient(headers={"Authorization": f"Bearer {dev_issuer.mint('carol', 'notes:read', audience=resource)}"})
    async with Client(streamable_http_client(f"{base}/mcp", http_client=h), mode="legacy") as c:
        assert c.protocol_version == "2025-11-25"
        assert (await c.call_tool("whoami", {})).structured_content["subject"] == "carol"


def test_spoofed_mcp_name_cannot_bypass_step_up(server):
    """Lie in the header to dodge the HTTP-layer check: the SDK's header/body cross-check stops it."""
    base, resource = server
    tok = dev_issuer.mint("eve", "notes:read", audience=resource)
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "add_note", "arguments": {"text": "x"}, "_meta": meta}}
    r = httpx.post(
        f"{base}/mcp", json=body,
        headers={"Authorization": f"Bearer {tok}", "Mcp-Method": "tools/call", "Mcp-Name": "whoami",
                 "MCP-Protocol-Version": "2026-07-28", "Accept": "application/json, text/event-stream"},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == -32020
