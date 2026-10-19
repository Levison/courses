"""Ex 1: count_tokens_estimate in the TypeScript server, driven by the Python client."""

import os
import shutil
import subprocess

import pytest

from course_kit.exercise import workspace
from mcp import Client, StdioServerParameters

WS = workspace(__file__)
NODE = os.environ.get("NODE") or shutil.which("node")


@pytest.fixture(scope="module")
def built():
    assert NODE, "Node >= 20 must be on PATH (or set NODE=/path/to/node)"
    assert (WS / "node_modules").is_dir(), "run `npm ci` in workspace/appendix-typescript first"
    tsc = WS / "node_modules" / ".bin" / "tsc"
    proc = subprocess.run([NODE, str(tsc.resolve())], cwd=WS, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"tsc failed:\n{proc.stdout}{proc.stderr}"
    return WS / "dist" / "server.js"


@pytest.mark.anyio
async def test_ts_count_tokens(built):
    async with Client(StdioServerParameters(command=NODE, args=[str(built)])) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert "count_tokens_estimate" in tools
        assert tools["count_tokens_estimate"].annotations.read_only_hint is True
        r = await c.call_tool("count_tokens_estimate", {"text": "x" * 400})
        assert not r.is_error
        assert r.structured_content == {"tokens": 100}, r.structured_content
