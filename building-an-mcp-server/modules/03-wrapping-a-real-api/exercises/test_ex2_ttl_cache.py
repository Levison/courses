"""Ex 2: TTL cache for PyPI lookups in lifespan state."""

import httpx
import pytest

from course_kit.exercise import load, run_pytest, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_second_lookup_hits_cache():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"info": {"name": "Jinja2", "version": "3.1.6"}, "releases": {"3.1.6": []}})

    server = load(WS, "depintel_server.py").create_server(httpx.MockTransport(handler))
    async with Client(server) as c:
        for _ in range(3):
            r = await c.call_tool("package_info", {"name": "jinja2"})
            assert r.structured_content["latest_version"] == "3.1.6"
    assert len(calls) == 1, f"expected 1 upstream request for 3 identical lookups, got {len(calls)}"


def test_your_cache_test():
    tests = WS / "test_depintel.py"
    assert "cache" in tests.read_text().lower(), "add a test proving the second call makes no HTTP request"
    proc = run_pytest(tests)
    assert proc.returncode == 0, proc.stdout[-2000:]
