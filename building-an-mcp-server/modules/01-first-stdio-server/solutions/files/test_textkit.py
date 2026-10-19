import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from textkit_server import mcp  # noqa: E402

from mcp import Client, StdioServerParameters  # noqa: E402


@pytest.fixture
async def client():
    # In-memory: no subprocess, no port. Same Client class you use in production.
    async with Client(mcp, raise_exceptions=True) as c:
        yield c


@pytest.mark.anyio
async def test_lists_tools(client):
    names = [t.name for t in (await client.list_tools()).tools]
    assert names == ["word_stats", "roll_dice", "slugify", "count_tokens_estimate", "crash_test"]  # stable order


@pytest.mark.anyio
async def test_word_stats_structured(client):
    r = await client.call_tool("word_stats", {"text": "a b a. c!", "top_n": 1})
    assert not r.is_error
    assert r.structured_content == {"words": 4, "unique_words": 3, "sentences": 2, "top_words": [["a", 2]]}


@pytest.mark.anyio
async def test_schema_validation_rejects_bad_args(client):
    r = await client.call_tool("roll_dice", {"count": 0})
    assert r.is_error  # pydantic Field(ge=1) enforced server-side


@pytest.mark.anyio
async def test_tool_error_reaches_model(client):
    r = await client.call_tool("slugify", {"title": "!!!"})
    assert r.is_error and "no slug-able characters" in r.content[0].text


@pytest.mark.anyio
async def test_over_real_stdio():
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("textkit_server.py"))])
    async with Client(params) as c:
        assert c.protocol_version == "2026-07-28"
        r = await c.call_tool("slugify", {"title": "Hello, MCP World"})
        assert r.structured_content == {"slug": "hello-mcp-world", "length": 15}


@pytest.mark.anyio
async def test_count_tokens_estimate(client):
    tool = next(t for t in (await client.list_tools()).tools if t.name == "count_tokens_estimate")
    assert tool.annotations.read_only_hint
    r = await client.call_tool("count_tokens_estimate", {"text": "x" * 400})
    assert r.structured_content == {"result": 100}
    assert (await client.call_tool("count_tokens_estimate", {"text": "hi"})).structured_content == {"result": 1}
