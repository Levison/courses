# Module 02: Resources, prompts, completions, caching and change notifications

**Goal:** expose context (resources) and user-invoked workflows (prompts) properly, not as more tools.
**Time:** ~2 h. **Code:** [`code/runbook_server.py`](code/runbook_server.py)

## Concepts

- **Who controls it?** This is the design question for every capability.
  - **Tools** are *model-controlled*: the LLM decides to call them, and they may have side effects.
  - **Resources** are *application-controlled*: addressable read-only context (`runbook://db-failover`) that the host or user attaches.
  - **Prompts** are *user-controlled*: templates the user picks, often surfaced as slash commands, which can embed resources.
- **Templates are RFC 6570** in SDK v2: `{slug}`, `{+path}` (reserved expansion, allows `/`), `{?format}` (optional
  query; the parameter needs a default). Matching is exact, and **path traversal in extracted values is rejected by default**
  (`ResourceSecurity`).
- **Errors.** Raise `ResourceNotFoundError` for a missing resource. The client then gets `-32602` with the URI in
  `error.data` (this changed from `-32002` in 2026-07-28). Any other exception becomes an opaque `-32603`.
- **Completions** (`completion/complete`) give argument autocomplete for prompts and templates.
- **Cache hints (SEP-2549).** `tools/list`, `prompts/list`, `resources/list`, `resources/read` and `resources/templates/list` carry
  `ttlMs` and `cacheScope` (`public`: shareable across users; `private`: per authorization context). Set them per method
  with `MCPServer(cache_hints={...})`. The Python `Client` honors them with a built-in cache.
- **Change notifications.** `subscriptions/listen` replaces the GET stream and `resources/subscribe`. The client opts in
  per type (`toolsListChanged`, `resourceSubscriptions: [uri]`, …). The server publishes with
  `await ctx.notify_resource_updated(uri)`. Across replicas you need a shared `SubscriptionBus` (Redis/NATS; you implement it).

## Tutorial

```bash
make start 02                          # copies code/ to workspace/02-resources-and-prompts/ (your copy)
cd workspace/02-resources-and-prompts
uv run pytest -q
uv run mcp dev runbook_server.py      # Resources tab: runbook://index, templates; Prompts tab: postmortem
npx @modelcontextprotocol/inspector --cli uv run python runbook_server.py --method resources/read --uri runbook://db-failover
npx @modelcontextprotocol/inspector --cli uv run python runbook_server.py --method prompts/get --prompt-name postmortem --prompt-args slug=cert-expiry impact=none
```

Walk through the code in this order:
1. `index` (static) vs `runbook` (template) vs `checklist` (template with `{?format}`). Run `resources/list`: only the
   static one appears. Templates come from `resources/templates/list`.
2. `postmortem` returns `UserMessage(EmbeddedResource(...))` + text + an `AssistantMessage` prefill.
3. `add_note` mutates state and publishes `notify_resource_updated`. See `test_resource_update_notification` for
   `async with client.listen(resource_subscriptions=[...])`.
4. Look at `listed.ttl_ms` / `cache_scope` in the tests.

## Exercises

Work in your copy, `workspace/02-resources-and-prompts/` (create it with `make start 02`); never edit `code/`.
Discussion answers go in `workspace/02-resources-and-prompts/NOTES.md` under the matching `## Exercise N` heading.
Check your work with `make check 02`; `make progress` updates `PROGRESS.md`.
Reference answers are in [`solutions/`](solutions/) (spoilers).

1. In your `runbook_server.py`, add `runbook://{slug}/history` returning a JSON list of `{"note", "at"}` entries (ISO-8601
   timestamp) for notes added with `add_note`. Should it be `public` or `private` cache scope? Why? (NOTES.md)
2. Add a `files://{+path}` template that serves files from a `files/` directory next to your server, and create
   `files/hello.md`. Then try `files://..%2F..%2Fetc%2Fpasswd` and friends. Who stops it? (NOTES.md; module 07 adds a second layer.)
3. Add a prompt `handoff(slug)` that embeds *two* resources: `runbook://{slug}` and its checklist.
4. Add a `create_runbook(slug, title, body)` tool that calls `ctx.notify_resources_changed()`, and write a test in your
   `test_runbooks.py` using `client.listen(resources_list_changed=True)` (the whole file must pass).
5. Design question: you want the model to be able to search runbooks. Tool, resource or both? Defend the choice in NOTES.md.

## Further reading
- Spec: [Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources), [Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- SDK: [Resources](https://py.sdk.modelcontextprotocol.io/servers/resources/), [URI templates](https://py.sdk.modelcontextprotocol.io/servers/uri-templates/), [Prompts](https://py.sdk.modelcontextprotocol.io/servers/prompts/), [Completions](https://py.sdk.modelcontextprotocol.io/servers/completions/), [Subscriptions](https://py.sdk.modelcontextprotocol.io/handlers/subscriptions/), [Caching hints (client)](https://py.sdk.modelcontextprotocol.io/client/caching/)

**Verified 2026-10-19:** `pytest` 5/5; Inspector CLI `resources/read` and `prompts/get` were run.
