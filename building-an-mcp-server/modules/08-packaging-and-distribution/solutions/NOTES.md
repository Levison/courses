# Notes: Module 08 (reference answers)

Files are in [`files/`](files/): `depintel-mcp/server.json` (2), `depintel-mcp/manifest.json` + `.mcpbignore` (3),
`release.yml` (4), and `depintel-mcp/README.md` (5).

## Exercise 1: TestPyPI

Not run for this edition, since it needs a TestPyPI account and a unique package name. The steps and what to record:
rename the project (TestPyPI names are global, e.g. `depintel-mcp-yourname`), `uv build`, then
`uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-...` (or trusted publishing), then
`uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ depintel-mcp-yourname`.
The extra index matters: `mcp` and `httpx` are not on TestPyPI, so without it the install fails on dependency
resolution. Record the package URL on test.pypi.org and the first `tools/list` you get through uvx.

## Exercise 2: `remotes` in server.json

```json
"remotes": [{"type": "streamable-http", "url": "https://depintel.example.com/mcp",
             "headers": [{"name": "X-API-Key", "description": "API key for the hosted depintel service",
                          "isRequired": true, "isSecret": true}]}]
```

`mcp-publisher validate` passed (2026-10-19, publisher 1.8.1, schema 2025-12-11). A server can list both `packages`
(run it yourself) and `remotes` (use the hosted one). `isSecret` tells clients to store the value in a secret store
and mask it in the UI. For OAuth-protected remotes you declare no header; the client discovers auth through PRM (module 05).

## Exercise 3: MCPB bundle

`npx @anthropic-ai/mcpb@2.1.2 init --yes` writes a `manifest_version: "0.2"` Node skeleton. For Python I used `0.4`
(experimental in CLI 2.1.2), which adds `server.type: "uv"`: the host runs `uv run --directory ${__dirname} depintel-mcp`,
so the bundle ships source plus `pyproject.toml` instead of vendored dependencies. `mcpb validate` passes and
`mcpb pack` produced a 6.2 kB `.mcpb`. User config and secrets: the manifest declares `user_config` entries (type,
title, description, required, default, and `sensitive: true` for secrets). The host renders a settings form,
stores sensitive values in the OS keychain, and injects them where the manifest references
`${user_config.<key>}`, typically in `mcp_config.env`, so the server reads them from its environment and they never
appear in the manifest or the conversation. depintel needs no configuration, so its manifest declares none.

## Exercise 4: Release workflow

`release.yml` triggers on `v*` tags. Job 1 checks that the tag, `pyproject.toml` and `server.json` versions agree,
builds with uv, and publishes with `pypa/gh-action-pypi-publish` using **trusted publishing** (`id-token: write`, no
stored token). Job 2 runs after it (the registry checks the PyPI package's README for `mcp-name:`), installs the
pinned `mcp-publisher` release, then runs `validate`, `login github-oidc` and `publish`. GitHub OIDC proves ownership
of `io.github.<owner>/*` names. Not run: it needs the real repository, a PyPI trusted-publisher entry and a tag.

## Exercise 5: Privacy disclosure

See the "Privacy and data flows" section in `files/depintel-mcp/README.md`: which service receives what (pypi.org gets
package names and versions; api.osv.dev gets name, ecosystem and version for each pinned line), what is *not* sent
(paths, comments, unpinned lines, prompts, credentials), what the services can observe (IP, User-Agent), caching (60 s,
in memory) and how to avoid leaking internal package names. The registry's `privacy_policies` field in the MCPB manifest
points at it.
