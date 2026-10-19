"""Ex 2: delete_environment works in both protocol eras via Resolve(...)."""

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client
from mcp.types import ElicitResult

WS = workspace(__file__)


def confirm(text: str):
    async def cb(context, params) -> ElicitResult:
        return ElicitResult(action="accept", content={"typed_name": text})

    return cb


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_delete_both_eras(mode):
    mod = load(WS, "changes_server.py")
    mod.ENVIRONMENTS["dev-erin"] = "running"
    kw = {"mode": "legacy"} if mode == "legacy" else {}
    async with Client(mod.mcp, elicitation_callback=confirm("dev-erin"), **kw) as c:
        r = await c.call_tool("delete_environment", {"name": "dev-erin"})
        assert not r.is_error and "Deleted dev-erin" in r.content[0].text, r.content
    assert "dev-erin" not in mod.ENVIRONMENTS


@pytest.mark.anyio
async def test_still_safe():
    mod = load(WS, "changes_server.py")
    mod.ENVIRONMENTS["dev-finn"] = "running"
    async with Client(mod.mcp, elicitation_callback=confirm("oops"), mode="legacy") as c:
        r = await c.call_tool("delete_environment", {"name": "dev-finn"})
        assert "did not match" in r.content[0].text
        prod = await c.call_tool("delete_environment", {"name": "prod"})
        assert prod.is_error
    assert "dev-finn" in mod.ENVIRONMENTS and "prod" in mod.ENVIRONMENTS


def test_which_is_clearer():
    require_answer(WS, 2, min_words=20, mentions=(("resolve", "resolver"),))
