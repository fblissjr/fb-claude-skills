last updated: 2026-02-19

# skill-dashboard

Project-scoped MCP App that renders a live HTML dashboard of all tracked skills. Shows health status, token budgets, freshness, and source dependencies.

This is a reference implementation demonstrating the Python-native MCP App pattern using the mcp-ui SDK (rawHtml approach) -- no Node.js or build step required.

## skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| skill-dashboard | "show skill dashboard", "skill status", "which skills are stale?" | Renders HTML dashboard of all tracked skills |

## installation

This plugin is project-scoped and not installable from the marketplace. It runs automatically when this repo is open in Claude Code via `.mcp.json`.

To load it manually:

```bash
claude --mcp-config skill-dashboard/.mcp.json
```

## invocation

```
/skill-dashboard
```

Or natural language: "show skill dashboard", "skill status", "which skills are stale?"

## what it shows

- All skills from `skill-maintainer/config.yaml`
- Status (fresh / stale / critical) -- color-coded
- Version from SKILL.md frontmatter
- Last checked timestamp (from DuckDB if available, file mtime fallback)
- Token budget bar (from DuckDB v_skill_budget, requires `measure_content.py`)
- Source dependencies

## data sources

1. `skill-maintainer/config.yaml` -- skill registry (always available)
2. `*/skills/*/SKILL.md` -- version from frontmatter (file scan)
3. `skill-maintainer/state/skill_maintainer.duckdb` -- freshness + budget (if available)

To populate DuckDB data:

```bash
uv run python skill-maintainer/scripts/docs_monitor.py   # populate freshness
uv run python skill-maintainer/scripts/measure_content.py # populate token budgets
```

## Python MCP App pattern

This plugin demonstrates the mcp-ui rawHtml approach:

- Server: pure Python (FastMCP + mcp-ui-server SDK)
- UI: self-contained HTML with Tailwind CDN + Alpine.js CDN
- No build step, no Node.js
- Limitation: no bidirectional tool calls from UI back to server (that requires the ext-apps AppBridge, which is TypeScript-only)
- Best for: dashboards, reports, explorers -- not interactive forms with server roundtrips

See `docs/analysis/mcp_apps_and_ui_development.md` for the full comparison of MCP App approaches.
