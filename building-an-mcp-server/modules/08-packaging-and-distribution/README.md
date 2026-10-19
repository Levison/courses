# Module 08: Packaging, distribution and connecting to hosts

**Goal:** turn `depintel` into an installable package that users run with one command (`uvx depintel-mcp`), describe it
for the **MCP Registry**, know when to ship an **MCPB** bundle or a **remote URL** instead, and wire it into the major hosts.
**Time:** ~2 h. **Code:** [`code/`](code/)

## Concepts

- **Three ways to distribute, chosen by who runs the process:**
  | Form | User runs | Good for | Trade-offs |
  |---|---|---|---|
  | Package (PyPI/npm/NuGet/crates/OCI) + stdio | `uvx depintel-mcp` / `npx …` | Developer tools, local data | Runs with the user's privileges; needs a runtime |
  | **MCPB bundle** (`.mcpb`, formerly DXT) | Double-click in Claude Desktop | Non-developers, local servers | Desktop-host specific; you ship the runtime/deps |
  | **Remote** Streamable HTTP | Paste a URL; OAuth | Multi-user SaaS, central governance | You run infra and auth (module 05) |
- **Entry point.** `[project.scripts] depintel-mcp = "depintel_mcp.server:main"` gives `uvx depintel-mcp` with no clone and no venv.
  Keep stdout clean (stdio), and offer `--http` for local HTTP.
- **Pin the SDK major:** `mcp>=2.3,<3`. SDK v2 serves both protocol eras, so you do not need to stay on v1 for old clients.
- **MCP Registry** (`registry.modelcontextprotocol.io`, still labelled *preview*) is a **metaregistry**: it stores `server.json`
  metadata that points at packages hosted elsewhere, plus `remotes` for hosted servers. Downstream registries and hosts consume it.
  - Namespace auth: `io.github.<user>/*` via GitHub login, or `com.example/*` via DNS/HTTP proof.
  - **Ownership check for PyPI:** your package README (the PyPI description) must contain `mcp-name: <server name>`. For npm it is
    `"mcpName"` in `package.json`.
  - `description` ≤ 100 chars. Only `_meta["io.modelcontextprotocol.registry/publisher-provided"]` survives publishing.
  - Allowed package hosts are the public registries only: pypi.org, registry.npmjs.org, NuGet, crates.io, Docker Hub/GHCR/etc., and GitHub/GitLab releases for MCPB.
  - The current schema is `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`.
- **Supply-chain hygiene for consumers:** a registry listing proves namespace control, not safety. Pin versions in host
  configs (`uvx depintel-mcp@0.8.0`), and run module 07's auditor and pinning before trusting a server.

## Tutorial

```bash
cd modules/08-packaging-and-distribution/code/depintel-mcp
uv build                                        # dist/depintel_mcp-0.8.0-py3-none-any.whl + sdist
uvx --from dist/depintel_mcp-0.8.0-py3-none-any.whl depintel-mcp      # stdio; Ctrl-C
uvx --from dist/depintel_mcp-0.8.0-py3-none-any.whl depintel-mcp --http --port 8000
mcp-publisher validate server.json              # ✅ server.json is valid
cd .. && uv run pytest -q                       # builds the wheel, runs it via uvx over stdio and HTTP
```

Install `mcp-publisher` (v1.8.1 at time of writing): `brew install mcp-publisher`, or download the release tarball. See the
[registry quickstart](https://modelcontextprotocol.io/registry/quickstart).

**Publishing (not done in this course; it needs your accounts):**
1. Replace `your-github-user` in `server.json` and `README.md`, then publish the wheel to PyPI (`uv publish`).
2. `mcp-publisher login github` (device flow), then `mcp-publisher publish`.
3. Verify: `curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.<you>/depintel-mcp"`.
4. In CI, use `mcp-publisher login github-oidc` from GitHub Actions instead of a personal login.

**Connect to hosts** (files in [`code/client-configs/`](code/client-configs/)):
- Claude Code: `claude mcp add depintel -- uvx depintel-mcp`; remote: `claude mcp add --transport http notes https://…/mcp`
- Cursor: `.cursor/mcp.json` under `mcpServers` (`command`/`args`, or `url` for remote)
- VS Code: `.vscode/mcp.json` under **`servers`**, each with a `type` (`stdio` | `http`); needs Agent mode
- Claude Desktop: `claude_desktop_config.json` with **absolute** paths (the host's PATH is minimal). `uv run mcp install server.py`
  writes it for you for single-file servers.

**Remote deploy:** `Dockerfile` (not built in the verification run; there is no Docker on the box) runs
`uvicorn depintel_mcp.server:app --proxy-headers` as a non-root user. Set `MCP_ALLOWED_HOSTS` for your hostname. I verified that a
wrong `Host` gets `421 Invalid Host header` and an allowed one connects at `2026-07-28`. Add module 05's auth before exposing it.

## Exercises

1. Publish to **TestPyPI** and run `uvx --index-url https://test.pypi.org/simple/ depintel-mcp`.
2. Add a `remotes` entry to `server.json` for a hosted deployment, with a header requirement for an API key. Validate it.
3. Build an **MCPB** bundle: `npx @anthropic-ai/mcpb init` then `mcpb pack` (CLI v2.1.2 at time of writing). What does the manifest
   declare about user config and secrets?
4. Add a GitHub Actions job that, on tag, builds, publishes to PyPI with trusted publishing, then `mcp-publisher publish` via OIDC.
5. Write the user-facing README section on what data the server sends where (PyPI, OSV). This is your privacy and consent disclosure.

## Further reading
- [Registry quickstart](https://modelcontextprotocol.io/registry/quickstart), [registry repo docs](https://github.com/modelcontextprotocol/registry) (package types, official requirements, CLI commands)
- [MCPB](https://github.com/modelcontextprotocol/mcpb)
- SDK: [Connect to a real host](https://py.sdk.modelcontextprotocol.io/get-started/real-host/), [Running your server](https://py.sdk.modelcontextprotocol.io/run/), [ASGI / add to an existing app](https://py.sdk.modelcontextprotocol.io/run/asgi/)

**Verified 2026-10-19:** wheel built; `uvx --from <wheel> depintel-mcp` driven over stdio and HTTP (`pytest` 3/3); `mcp-publisher validate` passed; Host allowlist checked with uvicorn. **Not verified:** actual PyPI/Registry publishing, MCPB packing, Docker build, live host apps (Claude/Cursor/VS Code). The box has no GUI hosts.
