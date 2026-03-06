---
name: skill-dashboard
description: >
  Show a live dashboard of all tracked skills, plugins, and repo hygiene in this project.
  Use when the user says "show skill dashboard", "skill status", "show me skill health",
  "what skills are stale", "check skill freshness", "skill budget overview", "show dashboard",
  or "run tests dashboard". Renders an HTML dashboard with pass/fail indicators for spec
  compliance, description quality, token budgets, freshness, plugin checks, and repo hygiene.
metadata:
  author: fblissjr
  version: 0.3.0
  last_verified: 2026-03-03
---

# skill-dashboard

Python-native MCP App dashboard for the fb-claude-skills project. Runs the full `run_tests.py` suite (skills, plugins, repo hygiene) and renders results as a self-contained HTML dashboard.

## Invocation

```
/skill-dashboard
```

Or trigger via natural language: "show skill dashboard", "skill status", "which skills are stale?"

## What it shows

### Skills table

| Column | Source | Notes |
|--------|--------|-------|
| Skill name | SKILL.md frontmatter | auto-discovered |
| Spec compliance | skills-ref validator | green/red dot |
| Description quality | WHAT verb + WHEN trigger check | green/red dot, detail on hover |
| Freshness | metadata.last_verified | days since verified |
| Token budget | file size estimate | bar chart, warn >4k, crit >8k |
| Body size | SKILL.md line count | warn >500 lines |

### Plugins table

| Column | Source | Notes |
|--------|--------|-------|
| Plugin name | .claude-plugin/plugin.json | auto-discovered |
| Manifest | required fields check | green/red dot |
| Marketplace | marketplace.json listing | green/red dot |
| README | file existence check | green/red dot |

### Repo hygiene

Pass/fail list: gitignore rules, ambient hooks, state files, duplicate names, best_practices.md freshness.

## Server

Runs as a local stdio MCP server via root `.mcp.json`. Start/stop is managed by Claude Code automatically.
