"""Ex 2: a remotes entry in server.json, validated."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from course_kit.exercise import workspace

WS = workspace(__file__)
SERVER_JSON = WS / "depintel-mcp" / "server.json"


def test_remote_with_secret_header():
    sj = json.loads(SERVER_JSON.read_text())
    remotes = sj.get("remotes") or []
    assert remotes, "add a remotes entry"
    r = remotes[0]
    assert r.get("type") == "streamable-http" and r.get("url", "").startswith("https://"), r
    headers = r.get("headers") or []
    assert any(h.get("isRequired") and h.get("isSecret") for h in headers), "declare a required, secret API-key header"
    assert sj.get("packages"), "keep the PyPI package entry too"


def test_mcp_publisher_validate():
    exe = shutil.which("mcp-publisher") or str(Path.home() / ".local/bin/mcp-publisher")
    if not os.access(exe, os.X_OK):
        pytest.skip("mcp-publisher not installed; structure checked above")
    proc = subprocess.run([exe, "validate"], cwd=SERVER_JSON.parent, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
