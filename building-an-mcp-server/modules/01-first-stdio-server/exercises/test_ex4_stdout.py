"""Ex 4: stdout is the protocol on stdio."""

import json
import subprocess
import sys

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}


def test_explained():
    require_answer(WS, 4, mentions=(("stdout", "standard output"), ("json", "protocol", "framing", "parse")))


def test_print_removed_stdout_is_clean():
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}}
    proc = subprocess.run([sys.executable, str(WS / "textkit_server.py")], input=json.dumps(req) + "\n",
                          capture_output=True, text=True, timeout=30)
    first = proc.stdout.splitlines()[0] if proc.stdout else ""
    try:
        msg = json.loads(first)
    except json.JSONDecodeError:
        raise AssertionError(f"first stdout line is not JSON-RPC: {first[:80]!r}. Remove the print().")
    assert msg.get("id") == 1
