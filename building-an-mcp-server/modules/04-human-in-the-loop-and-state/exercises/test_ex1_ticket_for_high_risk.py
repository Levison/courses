"""Ex 1: high-risk approvals need a second elicitation for a ticket number."""

import pytest

from course_kit.exercise import load, workspace
from mcp import Client
from mcp.types import ElicitResult

WS = workspace(__file__)


def answering(risk: str):
    seen: list[str] = []

    async def cb(context, params) -> ElicitResult:
        seen.append(params.message)
        if "ticket" in params.message.lower():
            return ElicitResult(action="accept", content={"ticket": "CHG-4242"})
        return ElicitResult(action="accept", content={"approve": True, "risk": risk})

    cb.seen = seen  # type: ignore[attr-defined]
    return cb


async def submit(risk: str, **kw):
    server = load(WS, "changes_server.py").mcp
    cb = answering(risk)
    async with Client(server, elicitation_callback=cb, **kw) as c:
        r = await c.call_tool("open_change", {"service": "billing", "summary": "rotate DB creds"})
        r = await c.call_tool("submit_change", {"handle": r.structured_content["handle"]})
    return r, cb.seen


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_high_risk_asks_for_ticket(mode):
    r, seen = await submit("high", **({"mode": "legacy"} if mode == "legacy" else {}))
    assert not r.is_error, r.content
    assert len(seen) == 2 and "ticket" in seen[1].lower(), f"expected approval then a ticket question, got {seen}"
    assert "CHG-4242" in r.content[0].text, "include the ticket number in the result"


@pytest.mark.anyio
async def test_low_risk_asks_once():
    r, seen = await submit("low")
    assert len(seen) == 1 and "Approved" in r.content[0].text
