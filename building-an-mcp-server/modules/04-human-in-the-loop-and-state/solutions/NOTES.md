# Notes: Module 04 (reference answers)

Code is in [`files/`](files/): `changes_server.py` (exercises 1-3) and `test_changes.py`.

## Exercise 1: A ticket number for high-risk changes

A second resolver, `ask_ticket`, takes `approval: Annotated[ElicitationResult[Approval], Resolve(ask_approval)]` as its own
dependency. Resolvers form a DAG, so the SDK asks for approval first and asks for the ticket on a later round only
if the answer was `approve=True, risk="high"`; otherwise the resolver returns `None` and nothing is asked. Gotcha
found while writing this: the consumer annotation decides wrapping, and `ElicitationResult[Ticket] | None` is *not*
recognized as the full-outcome form, so the tool receives the unwrapped `Ticket` (and declining aborts the call).
I annotated it as `Ticket | None` to make that explicit. It works in both eras: two MRTR rounds on 2026-07-28, and two
push elicitations on legacy connections.

## Exercise 2: Era-portable `delete_environment`

The hand-built `InputRequiredResult` version fails on a legacy connection with "Handler returned an invalid result",
because 2025-era clients do not know `input_required`. Moving the question into `Resolve(ask_delete_confirmation)`
lets the SDK choose MRTR or push elicitation per connection. The Resolve version is clearer for the common case:
validation and the question live in one small function, there is no `request_state` bookkeeping, and the body only
handles the answer. The hand-built version is still worth knowing for flows the resolver model cannot express
(for example, deciding what to ask from data fetched mid-call), and for seeing what goes over the wire. One
difference: resolvers check that the client declared the elicitation capability, so a client without it gets a
clear error instead of an `input_required` it cannot answer.

## Exercise 3: Shared state across workers

`ChangeStore` writes changes to SQLite when `CHANGES_DB` is set, so any worker can resolve a handle another worker
minted. Breaking it: give each worker a different `CHANGES_SECRET`. Handles are HMACs and MRTR `request_state` is
sealed (AES-GCM) with keys derived from `RequestStateSecurity(keys=..., audience=...)`, so a handle or retry that lands
on a worker with a different key fails verification ("Unknown or forged change handle", or a rejected
`request_state`). The fix is the same secret (and the same audience) on every replica, from a secret manager.
`keys` is a list so you can rotate: put the new key first and keep the old one until in-flight requests drain.

## Exercise 4: URL-mode elicitation sketch

For secrets and third-party consent (OAuth to a downstream API, payment approval), form elicitation is wrong because
the data would pass through the client and possibly the model. URL mode sends the user to a page you control:
1. The tool returns `input_required` with a URL-mode elicitation request: a message plus
   `https://approve.example.com/c/<opaque id>` bound to the user and this call, with a short expiry.
2. The host shows the URL; the user opens it in a browser, authenticates, and approves there. The server records the
   approval against the opaque id.
3. 2026-07-28 removed `notifications/elicitation/complete`, so the client learns the outcome by **retrying** the
   original call with the elicitation response and the sealed `request_state`. The server checks its own record:
   approved means proceed; still pending means return `input_required` again, so the client polls with backoff.
   Never trust the client's claim that the user approved; the server's record is the source of truth.

## Exercise 5: Threat model: "call submit_change and approve it"

The injected text can make the model *call* `submit_change`, but it cannot answer the elicitation: approval comes
from the human through the host's elicitation UI, outside the model's control, and the server only proceeds on an
accepted elicitation. What would *not* stop it: a host that auto-accepts elicitations (or lets the model fill
them), a user trained to click "approve" on every dialog, or a prompt whose message text is built from attacker
data and misleads the human. The server's defense is a deterministic message built from trusted fields; the
host's defense is never auto-approving elicitations for destructive tools.
