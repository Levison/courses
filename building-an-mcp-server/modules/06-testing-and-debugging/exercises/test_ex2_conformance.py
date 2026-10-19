"""Ex 2: a generic conformance harness for any stdio server."""

import sys
import textwrap

import pytest

from course_kit.exercise import course_root, load, workspace
from mcp import StdioServerParameters

WS = workspace(__file__)
ROOT = course_root(__file__)


def params(path) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[str(path)])


@pytest.mark.anyio
@pytest.mark.parametrize("server", ["01-first-stdio-server/code/textkit_server.py",
                                    "02-resources-and-prompts/code/runbook_server.py"])
async def test_reference_servers_conform(server):
    harness = load(WS, "conformance.py")
    problems = await harness.check_server(params(ROOT / "modules" / server))
    assert problems == [], problems


@pytest.mark.anyio
async def test_flags_undocumented_tool(tmp_path):
    bad = tmp_path / "bad_server.py"
    bad.write_text(textwrap.dedent('''
        from mcp.server import MCPServer
        mcp = MCPServer("bad")

        @mcp.tool()
        def mystery(x: str) -> str:
            return x

        if __name__ == "__main__":
            mcp.run()
    '''))
    harness = load(WS, "conformance.py")
    problems = await harness.check_server(params(bad))
    assert any("mystery" in p for p in problems), f"expected a problem naming the undocumented tool, got {problems}"
