"""Client-side MCP catalog auditor: flag tool poisoning before you trust a server.

    python audit_catalog.py stdio -- python some_server.py
    python audit_catalog.py http https://mcp.example.com/mcp --header "Authorization: Bearer ..."
    python audit_catalog.py stdio --pin pins.json -- python some_server.py   # rug-pull detection

Heuristic, not a proof. It reads names, descriptions, schemas and annotations,
i.e. everything a model reads. Pair it with human review and hash pinning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import anyio
import httpx2

from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|do not (tell|mention|inform)|"
    r"<\s*important\s*>|system prompt|you must|before using this tool|otherwise the tool will not work",
    re.I,
)
SENSITIVE_PATHS = re.compile(r"~/\.ssh|id_rsa|\.aws/credentials|\.env\b|/etc/passwd|\.config/gh|keychain", re.I)
EXFIL_PARAMS = {"sidenote", "context", "conversation_history", "history", "notes", "metadata", "debug", "feedback"}
DESTRUCTIVE_WORDS = re.compile(r"\b(delete|drop|remove|destroy|wipe|truncate|overwrite|transfer|send)\b", re.I)


@dataclass
class Finding:
    severity: str  # high | medium | low
    tool: str
    issue: str


def hidden_chars(s: str) -> list[str]:
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat == "Cf" or 0xE0000 <= ord(ch) <= 0xE007F:
            out.append(f"U+{ord(ch):04X}")
    return out


def tool_digest(tool) -> str:
    d = tool.model_dump(by_alias=True, exclude_none=True, mode="json")
    d.pop("_meta", None)
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def audit(tools, other_names: set[str]) -> list[Finding]:
    f: list[Finding] = []
    for t in tools:
        text = " ".join([t.name, t.title or "", t.description or "", json.dumps(t.input_schema)])
        if hc := hidden_chars(text):
            f.append(Finding("high", t.name, f"invisible/format characters: {', '.join(sorted(set(hc)))[:120]}"))
        if m := INJECTION.search(text):
            f.append(Finding("high", t.name, f"instruction-like text: {m.group(0)!r}"))
        if m := SENSITIVE_PATHS.search(text):
            f.append(Finding("high", t.name, f"references sensitive file: {m.group(0)!r}"))
        mentioned = {n for n in other_names if n != t.name and re.search(rf"\b{re.escape(n)}\b", t.description or "")}
        if mentioned:
            f.append(Finding("medium", t.name, f"description references other tools (shadowing?): {sorted(mentioned)}"))
        params = set(t.input_schema.get("properties", {}))
        if sus := params & EXFIL_PARAMS:
            f.append(Finding("medium", t.name, f"side-channel-looking parameters: {sorted(sus)}"))
        if len(t.description or "") > 1000:
            f.append(Finding("low", t.name, f"very long description ({len(t.description)} chars)"))
        ann = t.annotations
        if DESTRUCTIVE_WORDS.search(f"{t.name} {t.description}") and not (ann and ann.destructive_hint):
            f.append(Finding("low", t.name, "sounds destructive but declares no destructiveHint"))
    return f


async def run(args) -> int:
    if args.transport == "stdio":
        target = StdioServerParameters(command=args.cmd[0], args=args.cmd[1:])
    else:
        headers = dict(h.split(": ", 1) for h in args.header)
        target = streamable_http_client(args.cmd[0], http_client=httpx2.AsyncClient(headers=headers))
    async with Client(target) as c:
        tools = (await c.list_tools()).tools
        server = c.server_info.name if c.server_info else "?"

    # Common tool names from other servers a host might have connected.
    known = {t.name for t in tools} | {"send_email", "read_file", "write_file", "execute", "bash"}
    findings = audit(tools, known)

    if args.pin:
        pin_path = Path(args.pin)
        live = {t.name: tool_digest(t) for t in tools}
        if pin_path.exists():
            pinned = json.loads(pin_path.read_text())
            for name in sorted(live.keys() | pinned.keys()):
                if live.get(name) != pinned.get(name):
                    what = "added" if name not in pinned else "removed" if name not in live else "CHANGED"
                    findings.append(Finding("high", name, f"tool definition {what} since pinning (rug pull?)"))
        else:
            pin_path.write_text(json.dumps(live, indent=2))
            print(f"pinned {len(live)} tool definitions to {pin_path}")

    print(f"server {server!r}: {len(tools)} tools, {len(findings)} findings")
    for x in sorted(findings, key=lambda x: ["high", "medium", "low"].index(x.severity)):
        print(f"  [{x.severity:6}] {x.tool}: {x.issue}")
    if args.json:
        print(json.dumps([x.__dict__ for x in findings]))
    return 1 if any(x.severity == "high" for x in findings) else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("transport", choices=["stdio", "http"])
    p.add_argument("--header", action="append", default=[])
    p.add_argument("--pin", help="JSON file of pinned tool hashes (created if missing)")
    p.add_argument("--json", action="store_true")
    p.add_argument("cmd", nargs="+", help="stdio: command and args (after --); http: URL")
    sys.exit(anyio.run(run, p.parse_args()))


if __name__ == "__main__":
    main()
