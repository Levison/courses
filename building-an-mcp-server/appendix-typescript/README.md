# Appendix A: The same server in TypeScript (SDK v2)

**As of 2026-10-19:** `@modelcontextprotocol/server` 2.3.1, `@modelcontextprotocol/node` 2.1.1, zod 4, TypeScript 7.0.

## What is different from Python

- **Packages split in v2:** `@modelcontextprotocol/server`, `@modelcontextprotocol/client`, plus framework adapters
  (`/node`, `/express`, `/hono`, `/fastify`). The monolithic `@modelcontextprotocol/sdk` is v1. Migrate with
  `npx @modelcontextprotocol/codemod@latest v1-to-v2 .`
- **Opt-in to 2026-07-28.** A hand-constructed `McpServer` connected to a transport keeps speaking the 2025-era protocol.
  You get the stateless revision through the entry points: **`serveStdio(factory)`** for stdio and **`createMcpHandler(factory)`**
  for HTTP. Both take a *factory* and serve both eras. `createMcpHandler` defaults to `legacy: 'stateless'`.
- `createMcpHandler` is fetch-shaped (`Request → Response`, so it runs on Workers, Deno and Bun). On Node, wrap it with `toNodeHandler()`.
- Schemas are **zod v4** (`z.object({...})`). The SDK validates inputs before your handler runs. A raw shape (`{a: z.string()}`) is deprecated.
- Per-tool OAuth step-up exists natively: `registerTool(name, { scopeChallenge }, cb)`. Module 05 had to hand-roll it in Python.
- The HTTP server has no built-in Host allowlist in this minimal example, so `src/http.ts` adds a tiny one. With the
  `/express` or `/hono` adapters, use their host-validation middleware.

## Run it

```bash
cd appendix-typescript
npm install && npx tsc
node dist/server.js                                  # stdio
PORT=8770 node dist/http.js                          # http://127.0.0.1:8770/mcp
npx @modelcontextprotocol/inspector --cli node dist/server.js --protocol-era modern --method tools/list --strict
cd .. && uv run pytest appendix-typescript -q        # Python client ↔ TS server, stdio + HTTP, both eras
```

## A lesson found while verifying

The first version declared `top_words: z.array(z.tuple([z.string(), z.number()]))`. It compiled and worked with the Python
client, but **`inspector --strict` exited 6**: zod emits `items: false` for tuples, a bare boolean schema that some
shipping clients refuse. The fix is an array of objects (`{word, count}`). Run `--strict` in CI.

**Verified 2026-10-19:** `tsc` clean; `pytest appendix-typescript` 3/3 on Node 22.23 and Node 20.19; Inspector `--strict` exit 0.
