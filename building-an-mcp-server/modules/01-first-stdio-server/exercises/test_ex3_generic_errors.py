"""Ex 3: unexpected exceptions do not leak details to the model."""

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_crash_test_hides_details():
    async with Client(load(WS, "textkit_server.py").mcp) as c:
        names = [t.name for t in (await c.list_tools()).tools]
        assert "crash_test" in names, "add a crash_test tool that raises RuntimeError('db password is hunter2')"
        r = await c.call_tool("crash_test", {})
        assert r.is_error
        text = " ".join(getattr(b, "text", "") for b in r.content)
        assert "hunter2" not in text, "the secret reached the model"


def test_why():
    require_answer(WS, 3, mentions=(("leak", "secret", "sensitive", "password", "credential", "internal"),))
