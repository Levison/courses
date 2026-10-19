"""Run the conformance harness against every course server that speaks stdio."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from conformance import check_server  # noqa: E402

from mcp import StdioServerParameters  # noqa: E402

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "course_kit").is_dir())
SERVERS = ["01-first-stdio-server/code/textkit_server.py", "02-resources-and-prompts/code/runbook_server.py",
           "03-wrapping-a-real-api/code/depintel_server.py", "04-human-in-the-loop-and-state/code/changes_server.py"]


@pytest.mark.anyio
@pytest.mark.parametrize("server", SERVERS)
async def test_conformance(server):
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "modules" / server)])
    assert await check_server(params) == []
