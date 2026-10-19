"""Ex 3: persist CHANGES to SQLite so any worker can continue a change."""

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_two_workers_share_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CHANGES_DB", str(tmp_path / "changes.db"))
    monkeypatch.setenv("CHANGES_SECRET", "x" * 64)
    worker_a = load(WS, "changes_server.py")  # two fresh module instances = two workers
    worker_b = load(WS, "changes_server.py")
    async with Client(worker_a.mcp) as a:
        r = await a.call_tool("open_change", {"service": "search", "summary": "reindex"})
        handle = r.structured_content["handle"]
        await a.call_tool("add_step", {"handle": handle, "step": "pause writes"})
    async with Client(worker_b.mcp) as b:
        r = await b.call_tool("add_step", {"handle": handle, "step": "rebuild index"})
        assert not r.is_error, f"worker B could not see worker A's change: {r.content}"
        assert r.structured_content["result"] == 2


def test_key_mismatch_explained():
    require_answer(WS, 3, min_words=30, mentions=(("key", "secret"),))
