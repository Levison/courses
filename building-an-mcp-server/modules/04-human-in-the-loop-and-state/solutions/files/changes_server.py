"""Module 4: human-in-the-loop and state, the 2026-07-28 way.

* No sessions: cross-call state lives in explicit, server-minted handles that the
  model passes back as ordinary tool arguments (SEP-2567).
* No server->client requests: a tool that needs the user returns
  resultType "input_required" and the client retries with the answers
  (Multi Round-Trip Requests, SEP-2322). The SDK's Resolve/Elicit does this for you
  and falls back to classic push elicitation for 2025-era clients.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver import (
    AcceptedElicitation,
    Context,
    Elicit,
    ElicitationResult,
    RequestStateSecurity,
    Resolve,
)
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

# Shared secret so any replica can verify handles and MRTR request_state.
# In production: inject from a secret manager. >= 32 bytes.
SECRET = os.environ.get("CHANGES_SECRET", secrets.token_hex(32))

mcp = MCPServer(
    "changes",
    version="0.4.0",
    # Needed as soon as you run >1 worker: same keys AND same name/audience everywhere.
    request_state_security=RequestStateSecurity(keys=[SECRET], audience="changes"),
)

# Ex 3: persistence shared by every worker when CHANGES_DB points at a SQLite file
# (in production: Postgres or similar). Without it, an in-process dict (one worker only).
class ChangeStore:
    def __init__(self, path: str | None):
        self.mem: dict[str, dict] = {}
        self.db = None
        if path:
            self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("CREATE TABLE IF NOT EXISTS changes (id TEXT PRIMARY KEY, doc TEXT NOT NULL)")

    def get(self, cid: str) -> dict | None:
        if self.db is None:
            return self.mem.get(cid)
        row = self.db.execute("SELECT doc FROM changes WHERE id = ?", (cid,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, cid: str, change: dict) -> None:
        if self.db is None:
            self.mem[cid] = change
        else:
            self.db.execute("INSERT OR REPLACE INTO changes (id, doc) VALUES (?, ?)", (cid, json.dumps(change)))


CHANGES = ChangeStore(os.environ.get("CHANGES_DB"))
ENVIRONMENTS = {"dev-alice": "running", "staging": "running", "prod": "running"}


# ---------- explicit handles instead of session state ----------
def mint_handle(change_id: str) -> str:
    """Opaque, tamper-evident handle: id + HMAC. The model sees and threads it."""
    sig = hmac.new(SECRET.encode(), change_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"chg_{change_id}.{sig}"


def open_handle(handle: str) -> tuple[str, dict]:
    try:
        prefix, sig = handle.removeprefix("chg_").split(".", 1)
    except ValueError:
        raise ToolError("Malformed change handle. Use the handle returned by open_change.")
    good = hmac.new(SECRET.encode(), prefix.encode(), hashlib.sha256).hexdigest()[:16]
    change = CHANGES.get(prefix) if hmac.compare_digest(sig, good) else None
    if change is None:
        raise ToolError("Unknown or forged change handle.")
    return prefix, change


class ChangeOpened(BaseModel):
    handle: str = Field(description="Pass this to add_step / submit_change")
    service: str


@mcp.tool()
def open_change(service: str, summary: str) -> ChangeOpened:
    """Open a change request. Returns a handle to use in later calls."""
    cid = secrets.token_hex(6)
    CHANGES.put(cid, {"service": service, "summary": summary, "steps": [], "status": "draft", "at": time.time()})
    return ChangeOpened(handle=mint_handle(cid), service=service)


@mcp.tool()
def add_step(handle: str, step: str) -> int:
    """Add a step to an open change. Returns the step count."""
    cid, change = open_handle(handle)
    if change["status"] != "draft":
        raise ToolError(f"Change is {change['status']}; cannot edit.")
    change["steps"].append(step)
    CHANGES.put(cid, change)
    return len(change["steps"])


# ---------- HITL via Resolve + Elicit (era-portable) ----------
class Approval(BaseModel):
    approve: bool = Field(description="Approve this change?")
    risk: Literal["low", "medium", "high"] = Field(description="Your risk assessment")


class Ticket(BaseModel):
    ticket: str = Field(description="Change ticket number, e.g. CHG-1234", min_length=3, max_length=40)


async def ask_approval(handle: str) -> Elicit[Approval]:
    # Deterministic question built only from arguments: required, because the
    # resolver re-runs on each round and the answer is matched to the question.
    _, change = open_handle(handle)
    steps = "; ".join(change["steps"]) or "(no steps)"
    return Elicit(f"Approve change to {change['service']}: {change['summary']}. Steps: {steps}", Approval)


# Ex 1: a resolver that depends on another resolver's outcome. The framework runs
# ask_approval first; on a second round this one asks for the ticket only if risk is high.
async def ask_ticket(
    handle: str, approval: Annotated[ElicitationResult[Approval], Resolve(ask_approval)]
) -> Elicit[Ticket] | None:
    if isinstance(approval, AcceptedElicitation) and approval.data.approve and approval.data.risk == "high":
        return Elicit(f"High-risk change to {open_handle(handle)[1]['service']}: enter the change ticket number.", Ticket)
    return None


@mcp.tool()
async def submit_change(
    handle: str,
    approval: Annotated[ElicitationResult[Approval], Resolve(ask_approval)],
    # Unwrapped: declining the ticket question aborts the call. None when no ticket was needed.
    ticket: Annotated[Ticket | None, Resolve(ask_ticket)],
) -> str:
    """Submit a change for execution. A human must approve it first."""
    cid, change = open_handle(handle)
    if not isinstance(approval, AcceptedElicitation):
        return f"Not submitted: user chose to {approval.action}."
    if not approval.data.approve:
        change["status"] = "rejected"
        CHANGES.put(cid, change)
        return "Rejected by the user."
    suffix = ""
    if approval.data.risk == "high":
        if ticket is None:
            return "Not submitted: high-risk changes need a ticket number."
        change["ticket"] = ticket.ticket
        suffix = f", ticket {ticket.ticket}"
    change["status"] = "approved"
    CHANGES.put(cid, change)
    return f"Approved (risk={approval.data.risk}{suffix}); {len(change['steps'])} steps queued."


# ---------- Ex 2: delete_environment, era-portable via Resolve ----------
# The hand-built InputRequiredResult version only works for 2026-07-28 clients; a
# resolver lets the SDK pick MRTR or classic push elicitation per connection.
class Confirm(BaseModel):
    typed_name: str = Field(description="Type the environment name to confirm")


async def ask_delete_confirmation(name: str) -> Elicit[Confirm]:
    # Validate before asking: never prompt a human about an action you would refuse anyway.
    if name not in ENVIRONMENTS:
        raise ToolError(f"No environment {name!r}.")
    if name == "prod":
        raise ToolError("Refusing to delete prod from an MCP tool. Use the break-glass process.")
    return Elicit(f"Type '{name}' to permanently delete it.", Confirm)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True))
async def delete_environment(
    name: str,
    confirmation: Annotated[ElicitationResult[Confirm], Resolve(ask_delete_confirmation)],
) -> str:
    """Delete an environment. Requires the user to type its name to confirm."""
    if not isinstance(confirmation, AcceptedElicitation):
        return "Cancelled."
    if confirmation.data.typed_name != name:
        return "Confirmation text did not match; nothing deleted."
    del ENVIRONMENTS[name]
    return f"Deleted {name}."


if __name__ == "__main__":
    mcp.run()
