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
import os
import secrets
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
from mcp.types import (
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
    InputRequiredResult,
    ToolAnnotations,
)

# Shared secret so any replica can verify handles and MRTR request_state.
# In production: inject from a secret manager. >= 32 bytes.
SECRET = os.environ.get("CHANGES_SECRET", secrets.token_hex(32))

mcp = MCPServer(
    "changes",
    version="0.4.0",
    # Needed as soon as you run >1 worker: same keys AND same name/audience everywhere.
    request_state_security=RequestStateSecurity(keys=[SECRET], audience="changes"),
)

# Toy persistence. In real life: a database keyed by handle.
CHANGES: dict[str, dict] = {}
ENVIRONMENTS = {"dev-alice": "running", "staging": "running", "prod": "running"}


# ---------- explicit handles instead of session state ----------
def mint_handle(change_id: str) -> str:
    """Opaque, tamper-evident handle: id + HMAC. The model sees and threads it."""
    sig = hmac.new(SECRET.encode(), change_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"chg_{change_id}.{sig}"


def open_handle(handle: str) -> dict:
    try:
        prefix, sig = handle.removeprefix("chg_").split(".", 1)
    except ValueError:
        raise ToolError("Malformed change handle. Use the handle returned by open_change.")
    good = hmac.new(SECRET.encode(), prefix.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, good) or prefix not in CHANGES:
        raise ToolError("Unknown or forged change handle.")
    return CHANGES[prefix]


class ChangeOpened(BaseModel):
    handle: str = Field(description="Pass this to add_step / submit_change")
    service: str


@mcp.tool()
def open_change(service: str, summary: str) -> ChangeOpened:
    """Open a change request. Returns a handle to use in later calls."""
    cid = secrets.token_hex(6)
    CHANGES[cid] = {"service": service, "summary": summary, "steps": [], "status": "draft", "at": time.time()}
    return ChangeOpened(handle=mint_handle(cid), service=service)


@mcp.tool()
def add_step(handle: str, step: str) -> int:
    """Add a step to an open change. Returns the step count."""
    change = open_handle(handle)
    if change["status"] != "draft":
        raise ToolError(f"Change is {change['status']}; cannot edit.")
    change["steps"].append(step)
    return len(change["steps"])


# ---------- HITL via Resolve + Elicit (era-portable) ----------
class Approval(BaseModel):
    approve: bool = Field(description="Approve this change?")
    risk: Literal["low", "medium", "high"] = Field(description="Your risk assessment")


async def ask_approval(handle: str) -> Elicit[Approval]:
    # Deterministic question built only from arguments: required, because the
    # resolver re-runs on each round and the answer is matched to the question.
    change = open_handle(handle)
    steps = "; ".join(change["steps"]) or "(no steps)"
    return Elicit(f"Approve change to {change['service']}: {change['summary']}. Steps: {steps}", Approval)


@mcp.tool()
async def submit_change(
    handle: str,
    approval: Annotated[ElicitationResult[Approval], Resolve(ask_approval)],
) -> str:
    """Submit a change for execution. A human must approve it first."""
    change = open_handle(handle)
    if not isinstance(approval, AcceptedElicitation):
        return f"Not submitted: user chose to {approval.action}."
    if not approval.data.approve:
        change["status"] = "rejected"
        return "Rejected by the user."
    change["status"] = "approved"
    return f"Approved (risk={approval.data.risk}); {len(change['steps'])} steps queued."


# ---------- HITL by hand: return InputRequiredResult yourself ----------
CONFIRM_SCHEMA = {
    "type": "object",
    "properties": {"typed_name": {"type": "string", "description": "Type the environment name to confirm"}},
    "required": ["typed_name"],
}


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True))
async def delete_environment(name: str, ctx: Context) -> str | InputRequiredResult:
    """Delete an environment. Requires the user to type its name to confirm."""
    if name not in ENVIRONMENTS:
        raise ToolError(f"No environment {name!r}.")
    if name == "prod":
        raise ToolError("Refusing to delete prod from an MCP tool. Use the break-glass process.")

    if ctx.input_responses is None:  # round 1: ask
        return InputRequiredResult(
            input_requests={
                "confirm": ElicitRequest(
                    params=ElicitRequestFormParams(
                        message=f"Type '{name}' to permanently delete it.", requested_schema=CONFIRM_SCHEMA
                    )
                )
            },
            # Opaque to the client; the SDK seals it (AES-GCM) and binds it to this call.
            request_state=f"delete:{name}",
        )

    # round 2: the retry carries the answers + our sealed state back
    if ctx.request_state != f"delete:{name}":
        raise ToolError("Confirmation does not match this request.")
    answer = ctx.input_responses.get("confirm")
    if not isinstance(answer, ElicitResult) or answer.action != "accept":
        return "Cancelled."
    if (answer.content or {}).get("typed_name") != name:
        return "Confirmation text did not match; nothing deleted."
    del ENVIRONMENTS[name]
    return f"Deleted {name}."


if __name__ == "__main__":
    mcp.run()
