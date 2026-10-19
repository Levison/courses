"""Ex 4: create_runbook notifies resources list_changed; your own listen() test."""

import anyio
import pytest

from course_kit.exercise import load, run_pytest, workspace
from mcp import Client

WS = workspace(__file__)


@pytest.mark.anyio
async def test_create_runbook_notifies_list_changed():
    async with Client(load(WS, "runbook_server.py").mcp) as c:
        async with c.listen(resources_list_changed=True) as sub:
            r = await c.call_tool("create_runbook", {"slug": "dns-outage", "title": "DNS outage", "body": "1. Check resolvers"})
            assert not r.is_error, r.content
            with anyio.fail_after(5):
                await sub.__anext__()
        body = await c.read_resource("runbook://dns-outage")
        assert "Check resolvers" in body.contents[0].text
        index = await c.read_resource("runbook://index")
        assert "dns-outage" in index.contents[0].text


def test_your_listen_test():
    tests = WS / "test_runbooks.py"
    assert "resources_list_changed" in tests.read_text(), "add a test using client.listen(resources_list_changed=True)"
    proc = run_pytest(tests)
    assert proc.returncode == 0, proc.stdout[-2000:]
