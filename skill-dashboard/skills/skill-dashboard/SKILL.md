---
name: skill-dashboard
description: >
  Show a live dashboard of all tracked skills in this project. Use when the user says
  "show skill dashboard", "skill status", "show me skill health", "what skills are stale",
  "check skill freshness", "skill budget overview", or "show dashboard". Renders an HTML
  dashboard with color-coded freshness, token budget status, and last-checked timestamps
  for every skill tracked in config.yaml.
metadata:
  author: fblissjr
  version: 0.1.0
---

# skill-dashboard

Python-native MCP App skill dashboard for the fb-claude-skills project. Reads config.yaml and SKILL.md files, queries the DuckDB store if available, and renders a self-contained HTML dashboard.

## Invocation

```
/skill-dashboard
```

Or trigger via natural language: "show skill dashboard", "skill status", "which skills are stale?"

## What it shows

| Column | Source | Notes |
|--------|--------|-------|
| Skill name | config.yaml | linked to SKILL.md |
| Version | SKILL.md frontmatter | parsed at runtime |
| Status | DuckDB v_skill_freshness | fallback: file mtime |
| Last checked | DuckDB | freshness watermark |
| Token budget | DuckDB v_skill_budget | warn >4k, crit >8k |
| Sources | config.yaml | upstream dependencies |

## Color coding

- green: checked within 7 days, budget OK
- amber: checked 7-14 days ago or budget >4k tokens
- red: checked >14 days ago, SKILL.md missing, or budget >8k tokens

## Server

Runs as a local stdio MCP server via `.mcp.json`. Start/stop is managed by Claude Code automatically when this plugin is loaded.

The server reads from:
1. `skill-maintainer/config.yaml` -- skill registry
2. `*/skills/*/SKILL.md` -- skill frontmatter (version, description)
3. DuckDB store at `skill-maintainer/state/skill_maintainer.duckdb` (if present)

If DuckDB is not available, freshness falls back to file modification time.
