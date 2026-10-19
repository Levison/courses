# Notes: Module 01 (reference answers)

Code for exercises 1, 2, 3 and 5 is in [`files/`](files/): `textkit_server.py`, `test_textkit.py`, `wire_peek.py`.

## Exercise 1: Add a `count_tokens_estimate(text) -> int` tool

A plain function with a bounded `text` parameter and `annotations=ToolAnnotations(readOnlyHint=True)`. The
heuristic (about 4 characters per token, minimum 1) is honest about being an estimate in the docstring, which
is what the model reads. Adding a tool changes the catalog, so the "lists tools" test had to be updated too:
that test is a tiny catalog contract, and module 06 turns the idea into a lockfile.

## Exercise 2: Make `slugify` return a pydantic model `{slug, length}`

Returning `Slug(BaseModel)` instead of `str` changes `outputSchema` from a wrapped
`{"result": {"type": "string"}}` object to an object schema with `slug` and `length`, and `structuredContent`
becomes `{"slug": ..., "length": ...}`. Primitive return types are wrapped in `{"result": ...}` because
structured content must be a JSON object. The `ToolError` path is unchanged.

## Exercise 3: Unexpected exceptions stay generic

The client sees only `Error executing tool crash_test` with `isError: true`. That is the right default because
tool results go straight into the model's context, which you should treat as semi-public: exception messages
routinely contain secrets, connection strings, file paths and internal hostnames, and anything the model sees can
be echoed to the user or exfiltrated by a prompt injection. Unexpected errors are bugs for operators (log them
with full detail on stderr), while `ToolError` is the deliberate channel for messages the model should act on.

## Exercise 4: `print("hi")` at import time

On stdio, stdout is the protocol channel: every line must be one JSON-RPC message. `print` writes `hi` to stdout
before the server starts, so the client tries to parse `hi` as JSON. The Python client logs a parse error and
skips the line, and stricter hosts drop the connection or hang waiting for a valid response. Diagnostics belong
on stderr (`logging` defaults to stderr, or `print(..., file=sys.stderr)`). Over Streamable HTTP the same print
would be harmless, which is why this bug often appears only when a server is first wired into a desktop host.

## Exercise 5: Unsupported protocol version

`tools/list` with `protocolVersion: "2099-01-01"` in `_meta` returns JSON-RPC error **-32022** ("Unsupported
protocol version") with `data: {"supported": ["2026-07-28"], "requested": "2099-01-01"}`. With no handshake,
version negotiation happens per request: a client reads `supported` and retries with a version it speaks, or
falls back to the legacy `initialize` flow for 2025-era servers.
