---
name: enable
description: >-
  Enable the agent-state MCP server in this repo's .mcp.json by promoting the
  entry from `_available_servers` into `mcpServers`. Use when user says "enable
  agent-state mcp", "turn on agent-state", "wire up the DuckDB MCP", "enable
  agent state", or "activate agent-state-mcp". Invoke with /agent-state-mcp:enable.
metadata:
  author: Fred Bliss
  version: 0.2.0
  last_verified: 2026-04-19
---

# Enable agent-state MCP

One-shot activation of the agent-state MCP server in this repo. Moves the entry from the opt-in `_available_servers` block into the active `mcpServers` block of `.mcp.json`, verifies the server starts, and tells the user to restart Claude Code for the change to take effect.

## Why this exists

`.mcp.json` ships with `agent-state` under `_available_servers` (an opt-in convention) so the default experience doesn't auto-start an MCP server most users don't need. Enabling requires a manual JSON edit. This skill is the ergonomic replacement.

## Preconditions

- `.mcp.json` exists at the repo root.
- The `_available_servers.agent-state` block is present (otherwise the plugin isn't installed in this repo, or it's already enabled).
- `uv` is on PATH (the MCP entry uses `uv run agent-state-mcp`).

## Step 1 -- Inspect current state

```bash
jq '. | {available: ._available_servers | keys, active: .mcpServers | keys}' .mcp.json
```

If `agent-state` already appears in `active`, stop and report "Already enabled -- nothing to do." Exit.

If `agent-state` isn't in `available` either, stop and ask the user whether they want to install the plugin first.

## Step 2 -- Promote the entry

Use `jq` to move the block atomically. The outer `if` guards against
double-runs: if there's nothing to promote the file passes through
unchanged rather than nullifying `mcpServers["agent-state"]`.

```bash
jq 'if ._available_servers["agent-state"] then
      .mcpServers["agent-state"] = ._available_servers["agent-state"]
      | del(.mcpServers["agent-state"]._note)
      | del(._available_servers["agent-state"])
    else . end' \
   .mcp.json > .mcp.json.tmp && mv .mcp.json.tmp .mcp.json
```

Notes:
- The `_note` key is stripped from the active block -- it was documentation for the opt-in pattern, not a real MCP field.
- If `_available_servers` is now empty, leave the empty object in place rather than deleting the key; users may want to add other opt-in entries later.

## Step 3 -- Verify

Confirm the server starts and registers its tools:

```bash
uv run agent-state-mcp --list-tools
```

Expected output: 18 tool names (list_recent_runs, get_run_tree, find_failed_runs, etc.). If the command errors, `.mcp.json` is probably still correct but the workspace sync is stale. Run `uv sync --all-packages` and retry.

## Step 4 -- Report and prompt for restart

Print to the user:

```
agent-state MCP enabled in .mcp.json.
Restart Claude Code (or run `/mcp reconnect`) to load the server.
Test with: "What are the most recent runs in agent-state?"
```

Do NOT commit. Changing `.mcp.json` is a user-affecting decision; let them decide when.

## Guardrails

- **Idempotent**: running twice on an already-enabled repo is a no-op with a clear message.
- **Non-destructive**: the promotion preserves the original connection config (command, args, type). Only the `_note` helper gets dropped.
- **No commit**: the user commits if they want the team to share the config.

## Reverse

To disable later: move the block back manually, or delete it from `mcpServers`. A `/agent-state-mcp:disable` companion skill isn't warranted at the current scale.
