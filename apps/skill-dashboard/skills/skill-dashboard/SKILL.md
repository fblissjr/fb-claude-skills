---
name: skill-dashboard
description: >
  Show an interactive dashboard of all tracked skills, plugins, and repo hygiene in this project.
  Use when the user says "show skill dashboard", "skill status", "show me skill health",
  "what skills are stale", "check skill freshness", "skill budget overview", "show dashboard",
  or "run quality checks". Renders an interactive MCP App with pass/fail indicators for spec
  compliance, description quality, token budgets, freshness, plugin checks, and repo hygiene.
metadata:
  author: fblissjr
  version: 1.1.0
  last_verified: 2026-04-02
---

# skill-dashboard

Interactive ext-apps MCP App dashboard for the fb-claude-skills project. Discovers all skills and plugins, runs quality checks, and renders results as an interactive dashboard.

## Invocation

```
/skill-dashboard
```

Or trigger via natural language: "show skill dashboard", "skill status", "which skills are stale?"

## MCP tool

The `skill-quality-check` tool accepts an optional `filter` parameter (skill name substring) and returns structured content with:

- Per-skill checks: spec compliance, description quality, freshness, token budget, body size
- Per-plugin checks: manifest fields, marketplace listing, README existence
- Repo hygiene: gitignore rules, ambient hooks, state files, duplicate names, best_practices.md freshness
- Summary: passed/failed/total counts
- Meta: generation timestamp, budget thresholds (warn: 4000, critical: 8000)

## What it shows

### Skills table

| Column | Source | Notes |
|--------|--------|-------|
| Skill name | SKILL.md frontmatter | auto-discovered |
| Spec compliance | Agent Skills spec validation | green/red dot |
| Description quality | WHAT verb + WHEN trigger check | green/red dot, detail on hover |
| Freshness | metadata.last_verified | days since verified |
| Token budget | .md file size estimate | bar chart, warn >4k, crit >8k |
| Body size | SKILL.md line count | warn >500 lines |

### Plugins table

| Column | Source | Notes |
|--------|--------|-------|
| Plugin name | .claude-plugin/plugin.json | auto-discovered |
| Manifest | required fields check | green/red dot |
| Marketplace | marketplace.json listing | green/red dot |
| README | file existence check | green/red dot |

### Repo hygiene

Pass/fail list: gitignore rules, ambient hooks, state files, duplicate names, best_practices.md freshness, version alignment.

## Server

TypeScript ext-apps MCP App at `apps/skill-dashboard/mcp-app/`. Build with `bun run build`, run with `node dist/index.cjs --stdio` or as HTTP server on port 3002.
