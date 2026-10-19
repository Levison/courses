"""Live demo against real PyPI + OSV over stdio. Run: python demo_live.py"""

import sys
from pathlib import Path

import anyio

from mcp import Client, StdioServerParameters

REQS = """\
jinja2==2.4.1
requests==2.19.0
pydantic==2.12.0
not-pinned
"""


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("depintel_server.py"))])

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        print(f"  progress {progress:.0f}/{total:.0f} {message}")

    async with Client(params) as client:
        info = await client.call_tool("package_info", {"name": "mcp"})
        print("mcp on PyPI:", info.structured_content)
        audit = await client.call_tool(
            "audit_requirements", {"requirements": REQS}, progress_callback=on_progress
        )
        for row in audit.structured_content["result"]:
            print(row)


if __name__ == "__main__":
    anyio.run(main)
