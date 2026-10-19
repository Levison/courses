"""Ex 4: audit_requirements uses OSV /v1/querybatch (one request)."""

import json

import httpx
import pytest

from course_kit.exercise import load, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_one_batch_request():
    osv_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.osv.dev":
            return httpx.Response(404)
        osv_paths.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path == "/v1/querybatch":
            res = [{"vulns": [{"id": "GHSA-462w-v97r-4m45", "modified": "2024-01-01T00:00:00Z"}]}
                   if q["package"]["name"].lower() == "jinja2" else {} for q in body["queries"]]
            return httpx.Response(200, json={"results": res})
        return httpx.Response(200, json={})

    server = load(WS, "depintel_server.py").create_server(httpx.MockTransport(handler))
    async with Client(server) as c:
        r = await c.call_tool("audit_requirements", {"requirements": "jinja2==2.4.1\nrequests==2.32.3\nurllib3==2.2.2\nflask\n"})
        rows = r.structured_content["result"]
    assert osv_paths == ["/v1/querybatch"], f"expected exactly one POST /v1/querybatch, got {osv_paths}"
    assert rows[0]["vulnerable"] is True and rows[0]["ids"] == ["GHSA-462w-v97r-4m45"]
    assert rows[1]["vulnerable"] is False and rows[2]["vulnerable"] is False
    assert rows[3]["error"], "unpinned lines still report an error"
