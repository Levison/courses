"""Ex 1: runbook://{slug}/history resource with timestamps."""

import json

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_history_resource():
    async with Client(load(WS, "runbook_server.py").mcp) as c:
        templates = {t.uri_template for t in (await c.list_resource_templates()).resource_templates}
        assert "runbook://{slug}/history" in templates
        await c.call_tool("add_note", {"slug": "cert-expiry", "note": "renewed manually at 03:10"})
        res = await c.read_resource("runbook://cert-expiry/history")
        entries = json.loads(res.contents[0].text)
        assert isinstance(entries, list) and entries, "history should be a JSON list"
        assert entries[-1]["note"] == "renewed manually at 03:10"
        assert entries[-1].get("at"), "each entry needs an 'at' timestamp"


def test_cache_scope_reasoning():
    require_answer(WS, 1, min_words=20, mentions=(("private", "public"),))
