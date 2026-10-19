"""Ex 3: handoff prompt embedding two resources."""

import pytest

from course_kit.exercise import load, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_handoff_embeds_runbook_and_checklist():
    async with Client(load(WS, "runbook_server.py").mcp) as c:
        names = [p.name for p in (await c.list_prompts()).prompts]
        assert "handoff" in names
        p = await c.get_prompt("handoff", {"slug": "db-failover"})
        uris = [str(m.content.resource.uri) for m in p.messages if m.content.type == "resource"]
        assert "runbook://db-failover" in uris, uris
        assert any(u.startswith("runbook://db-failover/checklist") for u in uris), uris
        assert "Promote replica" in str(p.messages)
