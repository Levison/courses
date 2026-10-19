"""Ex 2: slugify returns a structured model {slug, length}."""

import pytest

from course_kit.exercise import load, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_slugify_structured_output():
    async with Client(load(WS, "textkit_server.py").mcp) as c:
        tool = next(t for t in (await c.list_tools()).tools if t.name == "slugify")
        props = (tool.output_schema or {}).get("properties", {})
        assert {"slug", "length"} <= set(props), f"outputSchema should describe slug and length, got {tool.output_schema}"
        r = await c.call_tool("slugify", {"title": "Hello, MCP World"})
        assert r.structured_content == {"slug": "hello-mcp-world", "length": 15}
        bad = await c.call_tool("slugify", {"title": "!!!"})
        assert bad.is_error, "empty slugs must still be a ToolError"
