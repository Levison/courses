"""See the 2026-07-28 wire protocol with no SDK client in the way.

stdio framing = one JSON-RPC message per line on stdin/stdout. There is no
initialize handshake: every request carries its protocol version and client
capabilities in params._meta. server/discover is optional.
"""

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).with_name("textkit_server.py")
# Ex 5: `python wire_peek.py 2099-01-01` -> -32022 "Unsupported protocol version",
# with error.data = {"supported": ["2026-07-28"], "requested": "2099-01-01"}.
PROTOCOL = sys.argv[1] if len(sys.argv) > 1 else "2026-07-28"
META = {
    "io.modelcontextprotocol/protocolVersion": PROTOCOL,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "wire-peek", "version": "0.0.1"},
}

REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": META}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": META}},
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "roll_dice", "arguments": {"count": 3, "sides": 20}, "_meta": META},
    },
]


def main() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert proc.stdin and proc.stdout
    for req in REQUESTS:
        print(">>>", json.dumps(req)[:160])
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        print("<<<", json.dumps(json.loads(line), indent=2)[:1500], "\n")
    proc.stdin.close()
    proc.wait(timeout=5)


if __name__ == "__main__":
    main()
