---
name: skill-dashboard
description: >
  Show an interactive dashboard of all tracked skills, plugins, and repo hygiene in this project.
  Use when the user says "show skill dashboard", "skill status", "show me skill health",
  "skill budget overview", "show dashboard",
  or "run quality checks". Renders an interactive MCP App with pass/fail indicators for spec
  compliance, description quality, token budgets, plugin checks, and repo hygiene.
---

# skill-dashboard

Render the fb-claude-skills quality dashboard: every skill and plugin under the repo root, checked and shown with pass/fail indicators and token budget bars.

<tools>
Two MCP tools from the dashboard's server (`apps/skill-dashboard/mcp-app/`):

- `skill-quality-check({ filter? })`: runs every check and renders the dashboard. `filter` is a skill-name substring. Checks: per skill, spec compliance, description quality (a WHAT verb and a WHEN trigger), token budget and body size; per plugin, manifest fields, marketplace listing and README; repo hygiene (gitignore rules, ambient hooks, state files, duplicate names, `best_practices.md` provenance, version alignment).
- `skill-measure({ skillName })`: per-file token breakdown for one skill (characters, estimated tokens, share of total). Use it when the user asks why a skill is heavy or where its tokens go.

The token-budget pass/fail uses the same certainty band as `skill-maintain test`; the bar colours mark the thresholds in the tool's returned `meta`, which are display bands, not the gate.
</tools>

This plugin does not register the server. If neither tool is available, tell the user it is not connected and point them at the README's "running" section (`node apps/skill-dashboard/mcp-app/dist/index.cjs --stdio`, after `bun run build`).
