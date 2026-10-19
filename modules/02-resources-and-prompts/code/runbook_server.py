"""Module 2: resources (static + templated), prompts, completions, cache hints,
and change notifications via subscriptions/listen.

Domain: an on-call runbook library. Resources are *application/user-controlled
context*; tools are *model-controlled actions*; prompts are *user-invoked
templates* (think slash commands). Pick the primitive by who is in control.
"""

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.server.mcpserver.prompts.base import AssistantMessage, Message, UserMessage
from mcp.types import (
    Completion,
    EmbeddedResource,
    PromptReference,
    ResourceTemplateReference,
    TextResourceContents,
)

RUNBOOKS: dict[str, dict[str, str]] = {
    "db-failover": {
        "title": "Primary database failover",
        "body": "1. Confirm replica lag < 5s\n2. Promote replica\n3. Repoint app via feature flag DB_PRIMARY",
    },
    "cert-expiry": {
        "title": "TLS certificate expiry",
        "body": "1. Check cert-manager logs\n2. Force renewal\n3. Verify with openssl s_client",
    },
    "queue-backlog": {
        "title": "Queue backlog > 10k",
        "body": "1. Scale consumers\n2. Check poison messages\n3. Enable DLQ replay",
    },
}
NOTES: dict[str, list[str]] = {slug: [] for slug in RUNBOOKS}

mcp = MCPServer(
    "runbooks",
    version="0.2.0",
    # 2026-07-28: list/read results carry ttlMs + cacheScope (SEP-2549). The
    # catalog rarely changes, so let clients cache tools/list for 5 minutes.
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "prompts/list": CacheHint(ttl_ms=300_000, scope="public"),
        "resources/list": CacheHint(ttl_ms=30_000, scope="private"),
    },
)


# ---------- Resources ----------
@mcp.resource("runbook://index", mime_type="text/markdown", title="Runbook index")
def index() -> str:
    """Every runbook slug and title."""
    return "\n".join(f"- `{slug}`: {rb['title']}" for slug, rb in sorted(RUNBOOKS.items()))


@mcp.resource("runbook://{slug}", mime_type="text/markdown")
def runbook(slug: str) -> str:
    """A single runbook, with any on-call notes appended."""
    if slug not in RUNBOOKS:
        # ResourceNotFoundError -> JSON-RPC -32602 with the URI in error.data (2026-07-28;
        # was -32002 before). Any other exception becomes an opaque -32603.
        raise ResourceNotFoundError(f"Unknown runbook {slug!r}")
    rb = RUNBOOKS[slug]
    notes = "\n".join(f"> {n}" for n in NOTES[slug])
    return f"# {rb['title']}\n\n{rb['body']}\n\n{notes}".rstrip()


# RFC 6570 query expansion: {?format} is optional, so the parameter needs a default.
@mcp.resource("runbook://{slug}/checklist{?format}", mime_type="application/json")
def checklist(slug: str, format: str = "json") -> dict:
    """Runbook steps as a checklist (JSON)."""
    if slug not in RUNBOOKS:
        raise ResourceNotFoundError(f"Unknown runbook {slug!r}")
    steps = [line.split(". ", 1)[1] for line in RUNBOOKS[slug]["body"].splitlines()]
    return {"slug": slug, "format": format, "steps": [{"step": s, "done": False} for s in steps]}


# ---------- A tool that mutates a resource and notifies listeners ----------
@mcp.tool()
async def add_note(slug: str, note: str, ctx: Context) -> str:
    """Append an on-call note to a runbook."""
    if slug not in RUNBOOKS:
        raise ToolError(f"Unknown runbook {slug!r}. Read runbook://index for valid slugs.")
    NOTES[slug].append(note)
    # Delivered on any open subscriptions/listen stream that opted in to this URI.
    await ctx.notify_resource_updated(f"runbook://{slug}")
    return f"noted on {slug} ({len(NOTES[slug])} notes)"


# ---------- Prompts ----------
@mcp.prompt(title="Draft a postmortem")
def postmortem(slug: str, impact: str, audience: str = "engineering") -> list[Message]:
    """Start a postmortem for an incident handled with the given runbook."""
    return [
        UserMessage(
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(uri=f"runbook://{slug}", mime_type="text/markdown", text=runbook(slug)),
            )
        ),
        UserMessage(
            f"We followed the runbook above. Impact: {impact}. "
            f"Draft a blameless postmortem for a {audience} audience: timeline, root cause, action items."
        ),
        AssistantMessage("Understood. First, a few clarifying questions about the timeline:"),
    ]


# ---------- Completions (argument autocomplete for prompts and templates) ----------
@mcp.completion()
async def complete(ref, argument, context):
    if argument.name == "slug" and isinstance(ref, (PromptReference, ResourceTemplateReference)):
        matches = [s for s in sorted(RUNBOOKS) if s.startswith(argument.value)]
        return Completion(values=matches, total=len(matches), has_more=False)
    if argument.name == "audience":
        return Completion(values=[a for a in ("engineering", "executive", "customer") if a.startswith(argument.value)])
    return None


if __name__ == "__main__":
    mcp.run()
