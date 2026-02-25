---
name: skill-dashboard
description: >
  Show a live dashboard of all tracked skills in this project. Use when the user says
  "show skill dashboard", "skill status", "show me skill health", "what skills are stale",
  "check skill freshness", "skill budget overview", or "show dashboard". Renders an HTML
  dashboard with color-coded freshness, token budget status, and last-checked timestamps
  for every skill in the project.
metadata:
  author: fblissjr
  version: 0.2.0
  last_verified: 2026-02-25
---

# skill-dashboard

Python-native MCP App skill dashboard for the fb-claude-skills project. Auto-discovers skills by walking SKILL.md files, reads `last_verified` from frontmatter, estimates token budgets, and renders a self-contained HTML dashboard.

## Invocation

```
/skill-dashboard
```

Or trigger via natural language: "show skill dashboard", "skill status", "which skills are stale?"

## What it shows

| Column | Source | Notes |
|--------|--------|-------|
| Skill name | SKILL.md frontmatter | auto-discovered |
| Version | SKILL.md frontmatter | parsed at runtime |
| Status | metadata.last_verified | fresh/stale/critical |
| Last verified | SKILL.md frontmatter | YYYY-MM-DD date |
| Token budget | file size estimate | warn >4k, crit >8k |

## Color coding

- green: verified within 14 days, budget OK
- amber: verified 14-30 days ago or budget >4k tokens
- red: verified >30 days ago, SKILL.md missing, or budget >8k tokens

## Server

Runs as a local stdio MCP server via `.mcp.json`. Start/stop is managed by Claude Code automatically when this plugin is loaded.

The server reads from:
1. `**/SKILL.md` -- auto-discovered skill files (frontmatter for version, last_verified)
2. Skill directories -- file size scan for token budget estimation
