import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import changes_server  # noqa: E402
from changes_server import mcp  # noqa: E402

from mcp import Client  # noqa: E402
from mcp.types import ElicitResult  # noqa: E402


def answering(content: dict | None, action: str = "accept"):
    seen: list[str] = []

    async def cb(context, params) -> ElicitResult:
        seen.append(params.message)
        return ElicitResult(action=action, content=content)

    cb.seen = seen  # type: ignore[attr-defined]
    return cb


async def open_with_steps(c: Client) -> str:
    r = await c.call_tool("open_change", {"service": "billing", "summary": "rotate DB creds"})
    handle = r.structured_content["handle"]
    await c.call_tool("add_step", {"handle": handle, "step": "create new user"})
    return handle


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])  # 2026-07-28 MRTR vs 2025 push elicitation
async def test_submit_requires_approval(mode):
    cb = answering({"approve": True, "risk": "low"})
    kw = {"mode": "legacy"} if mode == "legacy" else {}
    async with Client(mcp, elicitation_callback=cb, **kw) as c:
        handle = await open_with_steps(c)
        r = await c.call_tool("submit_change", {"handle": handle})
        assert "Approved (risk=low); 1 steps queued." in r.content[0].text
        assert "rotate DB creds" in cb.seen[0]


@pytest.mark.anyio
async def test_decline():
    async with Client(mcp, elicitation_callback=answering(None, "decline")) as c:
        handle = await open_with_steps(c)
        r = await c.call_tool("submit_change", {"handle": handle})
        assert "decline" in r.content[0].text


@pytest.mark.anyio
async def test_forged_handle_rejected():
    async with Client(mcp) as c:
        r = await c.call_tool("add_step", {"handle": "chg_deadbeef.0000000000000000", "step": "x"})
        assert r.is_error and "forged" in r.content[0].text


@pytest.mark.anyio
async def test_manual_mrtr_delete():
    changes_server.ENVIRONMENTS["dev-bob"] = "running"
    async with Client(mcp, elicitation_callback=answering({"typed_name": "dev-bob"})) as c:
        r = await c.call_tool("delete_environment", {"name": "dev-bob"})
        assert r.content[0].text == "Deleted dev-bob."
    assert "dev-bob" not in changes_server.ENVIRONMENTS


@pytest.mark.anyio
async def test_manual_mrtr_wrong_confirmation():
    changes_server.ENVIRONMENTS["dev-carol"] = "running"
    async with Client(mcp, elicitation_callback=answering({"typed_name": "oops"})) as c:
        r = await c.call_tool("delete_environment", {"name": "dev-carol"})
        assert "did not match" in r.content[0].text


@pytest.mark.anyio
async def test_drive_the_loop_yourself():
    """Look under the hood: the raw input_required round trip."""
    changes_server.ENVIRONMENTS["dev-dan"] = "running"
    async with Client(mcp) as c:
        first = await c.session.call_tool("delete_environment", {"name": "dev-dan"}, allow_input_required=True)
        assert first.result_type == "input_required"
        assert "confirm" in first.input_requests
        assert first.request_state and "delete:dev-dan" not in first.request_state  # sealed, not plaintext
        final = await c.session.call_tool(
            "delete_environment",
            {"name": "dev-dan"},
            input_responses={"confirm": ElicitResult(action="accept", content={"typed_name": "dev-dan"})},
            request_state=first.request_state,
            allow_input_required=True,
        )
        assert final.content[0].text == "Deleted dev-dan."
