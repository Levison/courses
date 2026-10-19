"""Pin your tool catalog: a lockfile of sha256 hashes over each tool's FULL
definition (name, description, inputSchema, outputSchema, annotations).

Why: tools/list is your public API *and* prompt text that a model reads. A
silent change to a description or a flipped readOnlyHint changes agent
behaviour. Same idea a client uses to detect "rug pulls" (module 7).

    python catalog_lock.py --write     # regenerate after an intentional change
    python catalog_lock.py             # exit 1 if the live catalog drifted
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import anyio

from mcp import Client

sys.path.insert(0, str(Path(__file__).parents[2] / "03-wrapping-a-real-api" / "code"))
from depintel_server import create_server  # noqa: E402

LOCK = Path(__file__).with_name("catalog.lock.json")


def canonical(tool) -> dict:
    d = tool.model_dump(by_alias=True, exclude_none=True, mode="json")
    d.pop("_meta", None)  # volatile, not part of the contract
    return d


def digest(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


async def current() -> dict[str, str]:
    async with Client(create_server()) as c:
        tools = (await c.list_tools()).tools
    return {t.name: digest(canonical(t)) for t in tools}


async def main() -> int:
    live = await current()
    if "--write" in sys.argv:
        LOCK.write_text(json.dumps(live, indent=2) + "\n")
        print(f"wrote {LOCK.name}: {len(live)} tools")
        return 0
    pinned = json.loads(LOCK.read_text())
    drift = {k for k in live.keys() | pinned.keys() if live.get(k) != pinned.get(k)}
    for name in sorted(drift):
        print(f"DRIFT {name}: pinned={pinned.get(name, '-')[:12]} live={live.get(name, '-')[:12]}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(anyio.run(main))
