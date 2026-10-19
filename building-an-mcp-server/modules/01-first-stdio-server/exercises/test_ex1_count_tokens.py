"""Ex 1: count_tokens_estimate tool + your own test for it."""

import pytest

from course_kit.exercise import load, run_pytest, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_tool_listed_read_only_and_works():
    server = load(WS, "textkit_server.py").mcp
    async with Client(server) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert "count_tokens_estimate" in tools, "add a count_tokens_estimate tool"
        ann = tools["count_tokens_estimate"].annotations
        assert ann is not None and ann.read_only_hint is True, "declare readOnlyHint=True"
        text = "The quick brown fox jumps over the lazy dog. " * 4
        r = await c.call_tool("count_tokens_estimate", {"text": text})
        assert not r.is_error, r.content
        n = r.structured_content["result"]
        assert isinstance(n, int) and 1 <= n <= len(text), f"implausible estimate {n} for {len(text)} chars"


def test_you_wrote_a_test_and_it_passes():
    tests = WS / "test_textkit.py"
    assert "count_tokens_estimate" in tests.read_text(), "add a test for the new tool to test_textkit.py"
    proc = run_pytest(tests)
    assert proc.returncode == 0, f"your test_textkit.py fails:\n{proc.stdout[-2000:]}"
