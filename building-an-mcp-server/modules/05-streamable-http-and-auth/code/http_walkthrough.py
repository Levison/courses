"""Walk the HTTP surface by hand, then with the SDK client.

Start the server first:  uvicorn notes_http_server:app --port 8765
Then:                    python http_walkthrough.py
"""

from __future__ import annotations

import json

import anyio
import httpx
import httpx2

import dev_issuer
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

BASE = "http://127.0.0.1:8765"
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "walkthrough", "version": "0"},
}
MODERN_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2026-07-28",
}


def raw() -> None:
    with httpx.Client(base_url=BASE) as h:
        print("1) Protected Resource Metadata (RFC 9728):")
        print("  ", h.get("/.well-known/oauth-protected-resource/mcp").json())

        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}}
        r = h.post("/mcp", json=body, headers={**MODERN_HEADERS, "Mcp-Method": "tools/list"})
        print("2) No token ->", r.status_code, "| WWW-Authenticate:", r.headers.get("www-authenticate"))

        wrong_aud = dev_issuer.mint("mallory", "notes:read", audience="https://some-other-api.example")
        r = h.post(
            "/mcp", json=body,
            headers={**MODERN_HEADERS, "Mcp-Method": "tools/list", "Authorization": f"Bearer {wrong_aud}"},
        )
        print("3) Token for a different audience ->", r.status_code)

        tok = dev_issuer.mint("alice", "notes:read")
        call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "whoami", "arguments": {}, "_meta": META}}
        r = h.post(
            "/mcp", json=call,
            headers={**MODERN_HEADERS, "Authorization": f"Bearer {tok}", "Mcp-Method": "tools/call", "Mcp-Name": "whoami"},
        )
        print("4) Good token, Mcp-Method/Mcp-Name headers ->", r.status_code, r.headers.get("content-type"))
        print("  ", r.text[:400])

        r = h.post(
            "/mcp", json=call,
            headers={**MODERN_HEADERS, "Authorization": f"Bearer {tok}", "Mcp-Method": "tools/call", "Mcp-Name": "list_notes"},
        )
        print("5) Mcp-Name header disagrees with body ->", r.status_code, r.text[:200])


async def sdk() -> None:
    tok = dev_issuer.mint("alice", "notes:read notes:write")
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {tok}"})
    async with Client(streamable_http_client(f"{BASE}/mcp", http_client=http)) as c:
        print("6) SDK client protocol:", c.protocol_version)
        print("   add_note ->", (await c.call_tool("add_note", {"text": "ship module 5"})).structured_content)
        print("   list_notes ->", (await c.call_tool("list_notes", {})).structured_content)

    ro_headers = {"Authorization": f"Bearer {dev_issuer.mint('bob', 'notes:read')}"}
    async with Client(streamable_http_client(f"{BASE}/mcp", http_client=httpx2.AsyncClient(headers=ro_headers))) as c:
        try:
            await c.call_tool("add_note", {"text": "should fail"})
        except Exception as e:  # 403 insufficient_scope from the ScopeChallenge middleware
            print("7) modern client, read-only token, add_note ->", type(e).__name__, str(e)[:120])
    async with Client(
        streamable_http_client(f"{BASE}/mcp", http_client=httpx2.AsyncClient(headers=ro_headers)), mode="legacy"
    ) as c:
        r = await c.call_tool("add_note", {"text": "should fail"})
        print("8) legacy client (no Mcp-Name header) -> in-tool backstop:", r.is_error, "|", r.content[0].text)


if __name__ == "__main__":
    raw()
    anyio.run(sdk)
