---
name: agent-state-mcp
description: Query the agent-state DuckDB (~/.claude/agent_state.duckdb) via MCP tools instead of the `agent-state` CLI. Use when you need run history, watermarks, skill versions, or flywheel metrics. TRIGGER on thoughts like "let me run agent-state status", "I'll check the agent_state database", "show me recent runs", "agent-state runs", "agent-state tree", "agent-state watermarks", "agent-state flywheel", "what failed recently", or "list skills by domain". The MCP tools are structured, faster, and permission-managed; the CLI is for interactive debugging only.
metadata:
  author: Fred Bliss
  version: 0.1.3
  last_verified: "2026-04-19"
---

# agent-state-mcp

Read-only MCP access to `~/.claude/agent_state.duckdb` (Kimball star schema:
`fact_run`, `fact_run_message`, `fact_watermark`, `dim_run_source`,
`dim_skill_version`, `dim_watermark_source`).

## use the MCP, not the CLI

When you catch yourself about to run `agent-state ...` via Bash, stop and use
the MCP tool instead. The CLI prints human-readable text; the MCP returns
structured rows with a `_meta` envelope (row count, duration, schema
version). Structured beats parsing every time.

Exceptions -- Bash the CLI only for:
- `agent-state init` (one-time DB creation)
- `agent-state migrate` (bulk import from `changes.jsonl`)
- Writes in general (this MCP is read-only by design)

## tool map (question -> tool)

| If you're thinking... | Call |
|--|--|
| "show me recent runs" / "agent-state runs" | `list_recent_runs` |
| "details for this run_id" | `get_run` |
| "run tree" / "how do these runs relate" / "agent-state tree" | `get_run_tree` |
| "logs for this run" / "what did it say" | `get_run_messages` |
| "what failed recently" / "show failures in the last week" | `find_failed_runs` |
| "what can I retry" | `find_restartable_failures` |
| "database summary" / "agent-state status" | `get_database_status` |
| "current watermarks" / "agent-state watermarks" | `get_watermark_status` |
| "watermark history for X" | `get_watermark_history` |
| "did this run advance any watermarks" | `get_run_watermark_changes` |
| "skills in the extraction domain" | `list_skills_by_domain` |
| "version history for skill X" | `list_skill_versions` |
| "current active version of skill X" | `get_active_skill_version` |
| "look up this skill by version_hash" | `resolve_skill_version_by_hash` |
| "what domains are tracked" | `list_tracked_domains` |
| "producer -> consumer chain" / "agent-state flywheel" | `get_flywheel_metrics` |
| "where are runs coming from" | `list_run_sources` |
| "what are we tracking watermarks on" | `list_watermark_sources` |

## output contract

Every tool returns:

```json
{
  "rows": [ {...}, {...} ],
  "_meta": {
    "row_count": 2,
    "duration_ms": 3,
    "schema_version": 2
  }
}
```

Scalar/single-row tools return `data` instead of `rows`. If the database
doesn't exist yet, you'll get `rows: []` plus `_meta.hint` telling you to run
`agent-state init` via Bash.

## enabling the server

The server is declared in this repo's root `.mcp.json` but may be commented
out by default. To enable it:

```jsonc
// .mcp.json
{
  "mcpServers": {
    "agent-state": {
      "command": "uv",
      "args": ["run", "agent-state-mcp"],
      "type": "stdio"
    }
  }
}
```

Then reload the Claude Code session.

## schema reference

See `tools/agent-state/README.md` for the full schema (tables, views,
migration history). This MCP server is a thin read-only layer over that
package -- it does not define any schema of its own.
