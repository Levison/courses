"""Ex 3: pypi://{name}/{version}/metadata resource."""

import json

import httpx
import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client

WS = workspace(__file__)


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/pypi/jinja2/3.1.6/json":
        return httpx.Response(200, json={"info": {"name": "Jinja2", "version": "3.1.6", "requires_python": ">=3.7",
                                                  "license_expression": "BSD-3-Clause", "summary": "templates"}})
    return httpx.Response(404)


@pytest.mark.anyio
async def test_metadata_resource():
    server = load(WS, "depintel_server.py").create_server(httpx.MockTransport(handler))
    async with Client(server) as c:
        templates = {t.uri_template for t in (await c.list_resource_templates()).resource_templates}
        assert "pypi://{name}/{version}/metadata" in templates
        res = await c.read_resource("pypi://jinja2/3.1.6/metadata")
        data = json.loads(res.contents[0].text)
        assert data["version"] == "3.1.6" and data["requires_python"] == ">=3.7"


def test_when_is_a_resource_better():
    require_answer(WS, 3, min_words=25, mentions=(("host", "user", "application", "attach", "cache"),))
