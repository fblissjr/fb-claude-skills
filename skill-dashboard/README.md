last updated: 2026-03-03

# skill-dashboard

Project-scoped MCP App that renders a live HTML dashboard of the entire skill ecosystem. Runs the full `run_tests.py` suite and shows pass/fail results for skills, plugins, and repo hygiene.

This is a reference implementation demonstrating the Python-native MCP App pattern using the mcp-ui SDK (rawHtml approach) -- no Node.js or build step required.

## skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| skill-dashboard | "show skill dashboard", "skill status", "which skills are stale?" | Renders HTML dashboard with pass/fail indicators |

## loading the MCP server

The root `.mcp.json` auto-loads the server when Claude Code opens this project. No manual configuration needed.

### Claude Desktop / Cowork

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skill-dashboard": {
      "command": "uv",
      "args": ["run", "python", "skill-dashboard/server.py"],
      "cwd": "/path/to/fb-claude-skills"
    }
  }
}
```

Note: use an absolute path for `cwd` -- `${workspaceFolder}` is Claude Code-only.

### Cowork UI rendering

Cowork renders MCP App UIs. Whether the rawHtml format from the mcp-ui SDK renders as an interactive panel (vs falling back to text) depends on whether Cowork recognizes the `ui://` URI scheme from this SDK. The ext-apps SDK is the officially documented approach; mcp-ui is a compatible but separate implementation.

## invocation

```
/skill-dashboard
```

Or natural language: "show skill dashboard", "skill status", "which skills are stale?"

## what it shows

### skills (per-skill checks)
- Spec compliance (skills-ref validation)
- Description quality (WHAT verb + WHEN trigger)
- Freshness (days since last_verified)
- Token budget (warn >4k, critical >8k)
- Body size (line count, warn >500)

### plugins (per-plugin checks)
- Manifest fields (name, version, description, author, repository)
- Marketplace listing (in marketplace.json)
- README exists

### repo hygiene
- No blanket .claude/ gitignore
- No broad ambient hooks
- State files gitignored
- No duplicate skill names
- best_practices.md freshness

## data sources

All data comes from the `skill_maintainer` package -- the server imports and runs `test_skills()`, `test_plugins()`, and `test_repo_hygiene()` from `skill_maintainer.tests` directly.

## Python MCP App pattern

This plugin demonstrates the mcp-ui rawHtml approach:

- Server: pure Python (FastMCP + mcp-ui-server SDK)
- UI: self-contained HTML with Tailwind CDN + Alpine.js CDN
- No build step, no Node.js
- Limitation: no bidirectional tool calls from UI back to server (that requires the ext-apps AppBridge, which is TypeScript-only)
- Best for: dashboards, reports, explorers -- not interactive forms with server roundtrips

See `docs/analysis/mcp_apps_and_ui_development.md` for the full comparison of MCP App approaches.
