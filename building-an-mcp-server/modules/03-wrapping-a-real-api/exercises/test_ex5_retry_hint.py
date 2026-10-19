"""Ex 5: retryable upstream failures carry a retry hint."""

import httpx
import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
@pytest.mark.parametrize("status", [429, 503])
async def test_retry_hint(status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"Retry-After": "7"})

    server = load(WS, "depintel_server.py").create_server(httpx.MockTransport(handler))
    async with Client(server) as c:
        r = await c.call_tool("package_info", {"name": "jinja2"})
    text = r.content[0].text
    assert r.is_error
    assert "retry" in text.lower() and "7" in text, f"tell the model it can retry, and when: {text!r}"


def test_observation():
    require_answer(WS, 5, min_words=20, mentions=(("retr",),))
