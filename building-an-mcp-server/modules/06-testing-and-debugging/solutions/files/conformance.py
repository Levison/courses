"""Ex 2: a generic conformance harness. Point it at any stdio server.

    python conformance.py python ../01-first-stdio-server/textkit_server.py
"""

from __future__ import annotations

import sys

import anyio

from mcp import Client, StdioServerParameters

PROTOCOL = "2026-07-28"


async def check_server(params: StdioServerParameters) -> list[str]:
    """Return a list of human-readable problems; empty means the server conforms."""
    problems: list[str] = []
    async with Client(params) as c:
        if c.protocol_version != PROTOCOL:
            problems.append(f"negotiated {c.protocol_version}, expected {PROTOCOL}")
        first = (await c.list_tools()).tools
        second = (await c.list_tools()).tools
        names = [t.name for t in first]
        if names != [t.name for t in second]:
            problems.append("tools/list order is not stable between calls")
        if len(names) != len(set(names)):
            problems.append(f"duplicate tool names: {names}")
        for t in first:
            if not (t.description or "").strip():
                problems.append(f"{t.name}: no description (the model cannot know when to use it)")
            if t.input_schema.get("type") != "object":
                problems.append(f"{t.name}: inputSchema type must be 'object'")
            for pname, prop in t.input_schema.get("properties", {}).items():
                if not isinstance(prop, dict):
                    problems.append(f"{t.name}.{pname}: boolean schema (strict clients reject it)")
        caps = c.server_capabilities
        if caps and caps.resources:
            await c.list_resources()  # must not error when advertised
        if caps and caps.prompts:
            await c.list_prompts()
    return problems


async def main() -> int:
    problems = await check_server(StdioServerParameters(command=sys.argv[1], args=sys.argv[2:]))
    for p in problems:
        print("FAIL", p)
    print("conformant" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(anyio.run(main))
