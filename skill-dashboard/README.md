last updated: 2026-02-25

# skill-dashboard

Project-scoped MCP App that renders a live HTML dashboard of all skills in the project. Shows health status, token budgets, freshness, and version info.

This is a reference implementation demonstrating the Python-native MCP App pattern using the mcp-ui SDK (rawHtml approach) -- no Node.js or build step required.

## skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| skill-dashboard | "show skill dashboard", "skill status", "which skills are stale?" | Renders HTML dashboard of all skills |

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

- All skills auto-discovered from `**/SKILL.md` files
- Status (fresh / stale / critical) based on `metadata.last_verified` -- color-coded
- Version from SKILL.md frontmatter
- Last verified date from SKILL.md frontmatter
- Token budget estimated from file sizes in skill directory

## data sources

1. `**/SKILL.md` -- auto-discovered skill files (frontmatter for name, version, last_verified)
2. Skill directories -- file size scan for token budget estimation

## Python MCP App pattern

This plugin demonstrates the mcp-ui rawHtml approach:

- Server: pure Python (FastMCP + mcp-ui-server SDK)
- UI: self-contained HTML with Tailwind CDN + Alpine.js CDN
- No build step, no Node.js
- Limitation: no bidirectional tool calls from UI back to server (that requires the ext-apps AppBridge, which is TypeScript-only)
- Best for: dashboards, reports, explorers -- not interactive forms with server roundtrips

See `docs/analysis/mcp_apps_and_ui_development.md` for the full comparison of MCP App approaches.
