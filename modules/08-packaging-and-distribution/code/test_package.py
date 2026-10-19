"""Build the wheel, run it the way end users will (`uvx`), and drive it over stdio and HTTP."""

import glob
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from mcp import Client, StdioServerParameters

PKG = Path(__file__).parent / "depintel-mcp"
pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")


@pytest.fixture(scope="module")
def wheel() -> str:
    subprocess.run(["uv", "build", "-q", "--wheel", "--out-dir", "dist"], cwd=PKG, check=True)
    return str(sorted(glob.glob(str(PKG / "dist" / "depintel_mcp-*.whl")))[-1])


@pytest.mark.anyio
async def test_uvx_stdio(wheel):
    params = StdioServerParameters(command="uvx", args=["--quiet", "--from", wheel, "depintel-mcp"])
    async with Client(params) as c:
        assert c.server_info.name == "depintel"
        names = [t.name for t in (await c.list_tools()).tools]
        assert names == ["package_info", "check_vulnerabilities", "audit_requirements"]


@pytest.mark.anyio
async def test_uvx_http(wheel):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        ["uvx", "--quiet", "--from", wheel, "depintel-mcp", "--http", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                httpx.get(f"http://127.0.0.1:{port}/mcp")
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        async with Client(f"http://127.0.0.1:{port}/mcp") as c:
            assert c.protocol_version == "2026-07-28"
            assert len((await c.list_tools()).tools) == 3
    finally:
        proc.terminate()
        proc.wait(5)


def test_server_json_matches_package():
    import json
    import tomllib

    sj = json.loads((PKG / "server.json").read_text())
    pp = tomllib.loads((PKG / "pyproject.toml").read_text())["project"]
    assert sj["version"] == pp["version"] == sj["packages"][0]["version"]
    assert sj["packages"][0]["identifier"] == pp["name"]
    assert f"mcp-name: {sj['name']}" in (PKG / "README.md").read_text()  # registry ownership check
    assert len(sj["description"]) <= 100
