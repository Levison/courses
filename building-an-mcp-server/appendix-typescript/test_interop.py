"""Cross-language check: drive the TypeScript server with the Python SDK client.

Requires: Node >= 20 on PATH (set NODE=/path/to/node to override), `npm install && npx tsc`.
Run from the repo root: pytest appendix-typescript
"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from mcp import Client, StdioServerParameters

HERE = Path(__file__).parent
NODE = os.environ.get("NODE") or shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE or not (HERE / "dist" / "server.js").exists(), reason="build the TS appendix first")


@pytest.mark.anyio
async def test_ts_stdio():
    async with Client(StdioServerParameters(command=NODE, args=[str(HERE / "dist" / "server.js")])) as c:
        assert c.protocol_version == "2026-07-28"
        r = await c.call_tool("word_stats", {"text": "MCP in TypeScript. MCP!"})
        assert r.structured_content["top_words"][0] == {"word": "mcp", "count": 2}
        bad = await c.call_tool("slugify", {"title": "!!!"})
        assert bad.is_error
        about = await c.read_resource("textkit://about")
        assert "SDK v2" in about.contents[0].text


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_ts_http(mode):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([NODE, str(HERE / "dist" / "http.js")], env={**os.environ, "PORT": str(port)},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{port}/")
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        kw = {"mode": "legacy"} if mode == "legacy" else {}
        async with Client(f"http://127.0.0.1:{port}/mcp", **kw) as c:
            assert c.protocol_version == ("2025-11-25" if mode == "legacy" else "2026-07-28")
            r = await c.call_tool("slugify", {"title": "Hello TS"})
            assert r.content[0].text == "hello-ts"
    finally:
        proc.terminate()
        proc.wait(5)
