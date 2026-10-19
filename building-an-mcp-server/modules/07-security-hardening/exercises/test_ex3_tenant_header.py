"""Ex 3: tenant id mirrored into an Mcp-Param-Tenant header; per-tenant rate limits."""

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client, MCPError

WS = workspace(__file__)


async def call(c, tenant):
    try:
        r = await c.call_tool("list_docs", {"tenant": tenant})
        return not r.is_error
    except MCPError:
        return False


@pytest.mark.anyio
async def test_tenant_header_and_limits():
    server = load(WS, "hardened_server.py").create_server(per_minute=2)
    async with Client(server) as c:
        tool = next(t for t in (await c.list_tools()).tools if t.name == "list_docs")
        prop = tool.input_schema.get("properties", {}).get("tenant", {})
        assert str(prop.get("x-mcp-header", "")).lower() == "tenant", f"list_docs.tenant needs x-mcp-header: Tenant, got {prop}"
        assert [await call(c, "acme") for _ in range(3)] == [True, True, False], "acme should be limited after 2 calls"
        assert await call(c, "globex"), "another tenant must have its own budget"


def test_gateway_rule():
    require_answer(WS, 3, min_words=20, mentions=(("mcp-param-tenant",),))
