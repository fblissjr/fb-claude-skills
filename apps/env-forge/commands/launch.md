---
description: "Materialize and start a generated or catalog environment (Phase 2)"
argument-hint: "<environment name or scenario>"
---

# /env-forge:launch

> Phase 2 -- not yet implemented. This command will materialize and start a FastAPI+MCP server for a generated or catalog environment.

## Planned Behavior

```
/env-forge:launch volunteer_match
/env-forge:launch e_commerce_33
```

1. Check if environment exists at `.env-forge/environments/<name>/`
2. If not, materialize it (from catalog or check for forge output)
3. Install dependencies: `cd .env-forge/environments/<name> && uv sync`
4. Start the server: `uv run python server.py`
5. Print MCP connection URL: `http://127.0.0.1:<port>/mcp`
6. Print available tools (operation_ids)

## Current Workaround

Start environments manually:

```bash
cd .env-forge/environments/<name>
uv run python server.py
```

The MCP endpoint will be at `http://127.0.0.1:8000/mcp` (default port).

## Phase 2 Additions

- Process management: start/stop/restart servers
- Port allocation: auto-assign available ports
- MCP config generation: write `.mcp.json` entry for Claude Code
- Health check: verify server responds before reporting success
- Reset: copy `db/initial.db` -> `db/current.db` to reset state
