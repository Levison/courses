"""Ex 2: notes:admin + purge_notes with HTTP-layer step-up and destructiveHint (real HTTP)."""

import os
import socket
import subprocess
import sys
import time

import httpx
import httpx2
import pytest

from course_kit.exercise import load, workspace
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

WS = workspace(__file__)
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}


@pytest.fixture(scope="module")
def server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    resource = f"http://127.0.0.1:{port}/mcp"
    issuer = load(WS, "dev_issuer.py")
    issuer.private_key()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "notes_http_server:app", "--port", str(port), "--log-level", "warning"],
        cwd=WS, env={**os.environ, "MCP_RESOURCE_URL": resource}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{base}/healthz").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield base, resource, issuer
    proc.terminate()
    proc.wait(5)


def raw_call(base, token, tool):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": {}, "_meta": META}}
    return httpx.post(f"{base}/mcp", json=body, headers={
        "Authorization": f"Bearer {token}", "Mcp-Method": "tools/call", "Mcp-Name": tool,
        "MCP-Protocol-Version": "2026-07-28", "Accept": "application/json, text/event-stream"})


def test_step_up_403_names_admin_scope(server):
    base, resource, issuer = server
    r = raw_call(base, issuer.mint("bob", "notes:read notes:write", audience=resource), "purge_notes")
    assert r.status_code == 403, f"purge_notes without notes:admin should be a 403 step-up, got {r.status_code}"
    assert "notes:admin" in r.headers.get("www-authenticate", "")


@pytest.mark.anyio
async def test_admin_can_purge_and_tool_is_destructive(server):
    base, resource, issuer = server
    tok = issuer.mint("root", "notes:read notes:write notes:admin", audience=resource)
    async with Client(streamable_http_client(f"{base}/mcp", http_client=httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {tok}"}))) as c:
        tool = next(t for t in (await c.list_tools()).tools if t.name == "purge_notes")
        assert tool.annotations and tool.annotations.destructive_hint is True
        await c.call_tool("add_note", {"text": "temp"})
        r = await c.call_tool("purge_notes", {})
        assert not r.is_error, r.content
        assert (await c.call_tool("list_notes", {})).structured_content == {"result": []}


@pytest.mark.anyio
async def test_legacy_client_backstop(server):
    base, resource, issuer = server
    tok = issuer.mint("bob", "notes:read notes:write", audience=resource)
    async with Client(streamable_http_client(f"{base}/mcp", http_client=httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {tok}"})), mode="legacy") as c:
        r = await c.call_tool("purge_notes", {})
        assert r.is_error and "notes:admin" in r.content[0].text
