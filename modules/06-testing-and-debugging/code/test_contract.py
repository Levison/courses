"""Contract tests: properties every tool in the catalog must keep."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[2] / "03-wrapping-a-real-api" / "code"))
import catalog_lock  # noqa: E402
from depintel_server import create_server  # noqa: E402

from mcp import Client  # noqa: E402


@pytest.fixture
async def tools():
    async with Client(create_server()) as c:
        return (await c.list_tools()).tools


@pytest.mark.anyio
async def test_catalog_matches_lockfile(tools):
    pinned = json.loads(catalog_lock.LOCK.read_text())
    live = {t.name: catalog_lock.digest(catalog_lock.canonical(t)) for t in tools}
    assert live == pinned, "Tool catalog changed. If intentional: python catalog_lock.py --write"


@pytest.mark.anyio
async def test_every_tool_is_documented_and_annotated(tools):
    for t in tools:
        assert t.description and 20 <= len(t.description) <= 300, t.name
        assert t.annotations is not None, f"{t.name}: declare read-only/destructive/open-world hints"
        assert t.output_schema is not None, f"{t.name}: prefer structured output"


@pytest.mark.anyio
async def test_input_schemas_constrain_strings(tools):
    """Every free-text string param should be bounded (pattern or maxLength)."""
    for t in tools:
        for pname, prop in t.input_schema.get("properties", {}).items():
            if prop.get("type") == "string":
                assert "pattern" in prop or "maxLength" in prop, f"{t.name}.{pname} is unbounded"


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_both_protocol_eras_see_same_catalog(mode, tools):
    kw = {"mode": "legacy"} if mode == "legacy" else {}
    async with Client(create_server(), **kw) as c:
        assert [t.name for t in (await c.list_tools()).tools] == [t.name for t in tools]
