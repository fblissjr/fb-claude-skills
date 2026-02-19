last updated: 2026-02-19

# skill-dashboard

Project-scoped MCP App that renders a live HTML dashboard of all tracked skills. Shows health status, token budgets, freshness, and source dependencies.

This is a reference implementation demonstrating the Python-native MCP App pattern using the mcp-ui SDK (rawHtml approach) -- no Node.js or build step required.

## skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| skill-dashboard | "show skill dashboard", "skill status", "which skills are stale?" | Renders HTML dashboard of all tracked skills |

## loading the MCP server

The `.mcp.json` is in the `skill-dashboard/` subdirectory, so it does not auto-load. You need to connect it explicitly depending on your surface.

### Claude Code (CLI)

```bash
claude --mcp-config skill-dashboard/.mcp.json
```

Or add to a root-level `.mcp.json` in this repo:

```json
{
  "mcpServers": {
    "skill-dashboard": {
      "command": "uv",
      "args": ["run", "python", "skill-dashboard/server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Claude Code renders text only -- no visual UI panel.

### Claude Desktop / Cowork

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skill-dashboard": {
      "command": "uv",
      "args": ["run", "python", "skill-dashboard/server.py"],
      "cwd": "/Users/fredbliss/claude/fb-claude-skills"
    }
  }
}
```

Note: use an absolute path for `cwd` -- `${workspaceFolder}` is Claude Code-only.

Restart Claude Desktop after adding. The server will be available in both Desktop and Cowork.

### Cowork UI rendering

Cowork renders MCP App UIs. Whether the rawHtml format from the mcp-ui SDK renders as an interactive panel (vs falling back to text) depends on whether Cowork recognizes the `ui://` URI scheme from this SDK. The ext-apps SDK is the officially documented approach; mcp-ui is a compatible but separate implementation.

**To verify:** after connecting the server in Claude Desktop, open Cowork and say "show skill dashboard". If a visual panel appears, rawHtml is supported. If you get a text response, the server is working but Cowork is not rendering the resource format.

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
