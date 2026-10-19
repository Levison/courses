# Notes: Module 02 (reference answers)

Code for exercises 1-4 is in [`files/`](files/): `runbook_server.py`, `test_runbooks.py`, `files/hello.md`.

## Exercise 1: `runbook://{slug}/history`

`add_note` now also appends `{"note", "at"}` (ISO-8601 UTC) to a `HISTORY` store, and the template returns it as
JSON. Cache scope: **private**. On-call notes are operational data for this deployment and possibly this user;
they change whenever someone adds a note, and a `public` scope tells shared intermediaries (gateways, caches
serving many users or tenants) that they may reuse the response for everyone. Public fits data that is identical
for every caller and changes rarely, such as the tool catalog. Keep the TTL short too, or rely on the
`resources/updated` notification to invalidate.

## Exercise 2: `files://{+path}` and traversal

`{+path}` (RFC 6570 reserved expansion) lets the value contain `/`, which is exactly what makes traversal possible.
Every attack (`../`, `..%2F..%2F`, an absolute `/etc/passwd`, `sub/../../`) failed with "Unknown resource"
**before my handler ran**: the SDK's `ResourceSecurity` check rejects `..` segments (including percent-encoded
ones), absolute paths and NUL bytes when matching the template. I verified this with a naive handler that has no
containment check. The handler still resolves the path and checks `is_relative_to(root)`, because the SDK check
cannot see symlinks inside the directory that point outside it. That is defense in depth, and module 07 makes
it a rule.

## Exercise 3: `handoff(slug)` prompt

Two `EmbeddedResource` user messages (the runbook as markdown, the checklist as JSON), then the instruction. Embedding
the content means the host does not have to make extra `resources/read` calls, and the URIs let it show the
user where the context came from.

## Exercise 4: `create_runbook` and list_changed

The tool adds the runbook and calls `await ctx.notify_resources_changed()`. A client that opened
`client.listen(resources_list_changed=True)` gets the event on its `subscriptions/listen` stream, and should refetch
`resources/list` (or here, `runbook://index`). The test in `files/test_runbooks.py` opens the listener, calls the
tool, waits up to 5 s for the event, then checks the index.

## Exercise 5: Search as a tool or a resource?

A **tool**, possibly backed by resources. Search is model-initiated: the model decides mid-task that it needs a runbook
and chooses the query, which is what tools are for, since the model controls tool calls. A resource is
application-controlled context: the host or user picks it, and many hosts never let the model read resources
on its own, so `runbook://search{?q}` alone would often be invisible to the model. Best of both: a
`search_runbooks(query)` tool that returns slugs, titles and short snippets plus `runbook://{slug}` URIs (resource
links), so the model finds candidates through the tool and the host can attach the full runbooks as resources and cache them.
