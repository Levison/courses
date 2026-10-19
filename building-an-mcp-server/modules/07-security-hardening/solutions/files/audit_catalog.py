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


def text_findings(where: str, text: str) -> list[Finding]:
    """Checks that apply to ANY text a model will read: descriptions, resources, prompts, results."""
    f: list[Finding] = []
    if hc := hidden_chars(text):
        f.append(Finding("high", where, f"invisible/format characters: {', '.join(sorted(set(hc)))[:120]}"))
    if m := INJECTION.search(text):
        f.append(Finding("high", where, f"instruction-like text: {m.group(0)!r}"))
    if m := SENSITIVE_PATHS.search(text):
        f.append(Finding("high", where, f"references sensitive file: {m.group(0)!r}"))
    return f


def audit(tools, other_names: set[str]) -> list[Finding]:
    f: list[Finding] = []
    for t in tools:
        text = " ".join([t.name, t.title or "", t.description or "", json.dumps(t.input_schema)])
        f += text_findings(t.name, text)
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


def _content_text(content) -> str:
    """Text of a content block or resource contents (text, or text of an embedded resource)."""
    if getattr(content, "type", None) == "resource":
        content = content.resource
    return getattr(content, "text", "") or ""


async def audit_content(client: Client, sample_tool_calls: bool = False) -> list[Finding]:
    """Ex 2: scan what the model reads besides tool definitions: resource and template
    metadata, static resource contents, rendered prompts, and (opt-in) tool results.

    Prompts are rendered with placeholder values for required arguments; a prompt that
    fails to render is reported as low severity, not skipped silently.
    """
    f: list[Finding] = []
    for r in (await client.list_resources()).resources:
        uri = str(r.uri)
        f += text_findings(uri, f"{r.name} {r.title or ''} {r.description or ''}")
        try:
            for c in (await client.read_resource(uri)).contents:
                f += text_findings(uri, _content_text(c))
        except Exception as e:  # noqa: BLE001 - report, keep scanning
            f.append(Finding("low", uri, f"could not read: {type(e).__name__}"))
    for t in (await client.list_resource_templates()).resource_templates:
        f += text_findings(t.uri_template, f"{t.name} {t.title or ''} {t.description or ''}")
    for p in (await client.list_prompts()).prompts:
        f += text_findings(p.name, f"{p.title or ''} {p.description or ''} " + " ".join(
            f"{a.name} {a.description or ''}" for a in p.arguments or []))
        args = {a.name: "example" for a in p.arguments or [] if a.required}
        try:
            rendered = await client.get_prompt(p.name, args)
            f += text_findings(p.name, " ".join(_content_text(m.content) for m in rendered.messages))
        except Exception as e:  # noqa: BLE001
            f.append(Finding("low", p.name, f"could not render with placeholder args: {type(e).__name__}"))
    if sample_tool_calls:  # only for servers you are prepared to execute
        for t in (await client.list_tools()).tools:
            ro = t.annotations and t.annotations.read_only_hint
            if ro and not t.input_schema.get("required"):
                r = await client.call_tool(t.name, {})
                f += text_findings(f"{t.name}()", " ".join(_content_text(c) for c in r.content))
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
        content_findings = await audit_content(c, sample_tool_calls=args.sample_calls)

    # Common tool names from other servers a host might have connected.
    known = {t.name for t in tools} | {"send_email", "read_file", "write_file", "execute", "bash"}
    findings = audit(tools, known) + content_findings

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
    p.add_argument("--sample-calls", action="store_true", help="also call read-only no-arg tools and scan results")
    p.add_argument("cmd", nargs="+", help="stdio: command and args (after --); http: URL")
    sys.exit(anyio.run(run, p.parse_args()))


if __name__ == "__main__":
    main()
