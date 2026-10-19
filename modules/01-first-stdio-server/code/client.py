"""Drive the server the way a host would: spawn it as a stdio subprocess."""

import sys
from pathlib import Path

import anyio

from mcp import Client, StdioServerParameters

SERVER = Path(__file__).with_name("textkit_server.py")


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:
        print("protocol:", client.protocol_version)
        print("server:  ", client.server_info)
        tools = await client.list_tools()
        for t in tools.tools:
            print(f"- {t.name}: {t.description}  annotations={t.annotations}")

        r = await client.call_tool("word_stats", {"text": "MCP is a protocol. MCP is stateless now!"})
        print("word_stats ->", r.structured_content)

        r = await client.call_tool("slugify", {"title": "!!!"})
        print("slugify(!!!) is_error:", r.is_error, "|", r.content[0].text)


if __name__ == "__main__":
    anyio.run(main)
