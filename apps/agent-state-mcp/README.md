last updated: 2026-04-19

# agent-state-mcp

MCP server (stdio) exposing `~/.claude/agent_state.duckdb` to Claude Code as
read-only, ergonomic tools. Claude should reach for these instead of shelling
out to the `agent-state` CLI.

## rationale

Claude currently invokes `agent-state status`, `agent-state runs`, etc. via
Bash. MCP tools are a better fit:

- **Structured output** -- every response is `{rows|data, _meta}` instead of
  human-readable text that needs parsing.
- **Permission-managed** -- hosts can allowlist MCP tools per-plugin rather
  than allowlisting `Bash(agent-state:*)` broadly.
- **Faster** -- no subprocess spawn per query; the DuckDB connection is
  short-lived but in-process.
- **Discoverable** -- named after questions ("list_recent_runs") rather
  than raw tables ("SELECT ... FROM fact_run").

The server is **read-only by design**. Writes go through the existing
`agent-state` CLI (`init`, `migrate`) or the `RunContext` API in the host
pipeline.

## installation

Installed automatically when you install this marketplace's plugin:

```bash
/plugin install agent-state-mcp@fb-claude-skills
```

Python deps come from the repo's uv workspace:

```bash
cd /path/to/fb-claude-skills
uv sync --all-packages
```

## enabling

The server is declared in the repo's root `.mcp.json` under `mcpServers`,
but opt-in. To enable, uncomment the entry (or add it):

```jsonc
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

Reload the session (`/mcp` in Claude Code) to pick it up.

### environment

| Variable | Purpose |
|----------|---------|
| `AGENT_STATE_DB` | Override the DuckDB path (default: `~/.claude/agent_state.duckdb`). |

### smoke test

```bash
uv run agent-state-mcp --list-tools
uv run agent-state-mcp --help
```

## tools

All tools are read-only. All return `{rows: [...]}` or `{data: {...}}`
plus a `_meta` envelope (`row_count`, `duration_ms`, `schema_version`,
optional `hint`).

| Tool | Purpose | CLI equivalent |
|------|---------|----------------|
| `list_recent_runs` | Most recent rows from fact_run, newest first. | `agent-state runs` |
| `get_run` | Full fact_run row for one run_id. | -- |
| `get_run_tree` | Hierarchical run tree (recursive CTE). | `agent-state tree` |
| `get_run_messages` | Structured log for a run (fact_run_message). | -- |
| `find_failed_runs` | Failed/partial runs in the last N days. | -- |
| `find_restartable_failures` | Rows from v_restartable_failures. | -- |
| `get_database_status` | Totals by status/type, watermark & skill counts. | `agent-state status` |
| `get_watermark_status` | Current v_latest_watermark values. | `agent-state watermarks` |
| `get_watermark_history` | Historical values for one watermark source. | -- |
| `get_run_watermark_changes` | Watermarks a specific run advanced. | -- |
| `list_skills_by_domain` | Active skills in a routing domain. | -- |
| `list_skill_versions` | Version history for a skill. | -- |
| `get_active_skill_version` | Latest active version of a named skill. | -- |
| `resolve_skill_version_by_hash` | Look up a skill by content hash. | -- |
| `list_tracked_domains` | Distinct domains with active skill counts. | -- |
| `get_flywheel_metrics` | Producer -> skill version -> consumer chain. | `agent-state flywheel` |
| `list_run_sources` | dim_run_source rows with run counts. | -- |
| `list_watermark_sources` | dim_watermark_source rows. | -- |

## architecture

```
Claude Code
   |
   v  (stdio, MCP)
agent-state-mcp server  <-- apps/agent-state-mcp/
   |
   v  (Python import)
agent-state package     <-- tools/agent-state/
   |
   v  (DuckDB file open)
~/.claude/agent_state.duckdb  (schema v2)
```

This app does not touch the schema. It re-exports query helpers from
`agent_state.query`, `agent_state.watermarks`, and `agent_state.skill_versions`
as MCP tools, adds small conveniences (`list_tracked_domains`,
`find_failed_runs` with windowed filters), and standardises output envelopes.

## not implemented / out of scope

- Writes -- all tools are read-only. Use the CLI (`agent-state init`,
  `agent-state migrate`) or the `RunContext` API.
- HTTP/SSE transport -- stdio only for now.
- Multi-database federation -- one DB per server process. Override the path
  via `AGENT_STATE_DB` or `--db`.

## see also

- `tools/agent-state/README.md` -- schema, migrations, Python API.
- `tools/agent-state/BACKLOG.md` -- future subcommands (some of which are
  already satisfied by this MCP: `list_skills_by_domain`,
  `list_tracked_domains`).
