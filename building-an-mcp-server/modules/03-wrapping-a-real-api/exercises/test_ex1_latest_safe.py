"""Ex 1: latest_safe_version combines PyPI releases with OSV fixed_in."""

import json

import httpx
import pytest

from course_kit.exercise import load, workspace
from mcp import Client

WS = workspace(__file__)
VULN = {"vulns": [{"id": "GHSA-462w-v97r-4m45", "summary": "sandbox escape",
                   "affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "2.10.1"}]}]}]}]}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "pypi.org" and request.url.path == "/pypi/jinja2/json":
        rel = {v: [] for v in ["2.4.1", "2.10", "2.10.1", "2.11.3", "3.1.6"]}
        return httpx.Response(200, json={"info": {"name": "Jinja2", "version": "3.1.6"}, "releases": rel})
    if request.url.host == "api.osv.dev":
        body = json.loads(request.content)
        queries = body.get("queries", [body])
        hits = [VULN if q.get("version") in ("2.4.1", "2.10") else {} for q in queries]
        return httpx.Response(200, json={"results": hits} if "queries" in body else hits[0])
    return httpx.Response(404)


@pytest.mark.anyio
@pytest.mark.parametrize("current,expected", [("2.4.1", "2.10.1"), ("2.11.3", "2.11.3")])
async def test_suggests_lowest_safe_upgrade(current, expected):
    server = load(WS, "depintel_server.py").create_server(httpx.MockTransport(handler))
    async with Client(server) as c:
        r = await c.call_tool("latest_safe_version", {"name": "jinja2", "current": current})
        assert not r.is_error, r.content
        assert r.structured_content["suggested"] == expected
