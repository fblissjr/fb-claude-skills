last updated: 2026-03-13

# skill-dashboard

Interactive ext-apps MCP App dashboard for the fb-claude-skills project. Discovers all skills and plugins, runs quality checks, and renders results in an interactive UI with pass/fail indicators and token budget bars. Click any skill row to see a per-file token breakdown.

## skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| skill-dashboard | "show skill dashboard", "skill status", "which skills are over budget?" | Interactive quality check dashboard |

## architecture

TypeScript MCP App using the ext-apps SDK (same pattern as mece-decomposer). All check logic is native TypeScript -- no Python dependency.

```
mcp-app/
  main.ts              # Dual transport (stdio + HTTP on port 3002)
  server.ts            # MCP tools + resource registration
  src/
    utils/checks.ts    # Discovery, validation, measurement, hygiene checks
    skill-dashboard-app.tsx   # Main React view with sidebar state
    components/        # SummaryBar, SkillTable, PluginTable, RepoChecks, StatusDot, TokenBudgetBar, SkillSidebar, FileBreakdownTable
```

## MCP tools

### skill-quality-check

Discovers all skills and plugins under the repo root, runs checks, returns structured results.

- **Input**: `{ filter?: string }` -- optional skill name substring filter
- **Output**: structuredContent with skills, plugins, repo checks, summary, meta
- **Text fallback**: "Quality check: N passed, M failed across X skills, Y plugins"

### skill-measure

Per-file token breakdown for a single skill. Visible to both model and app.

- **Input**: `{ skillName: string }`
- **Output**: structuredContent with per-file breakdown (path, chars, tokens, pctOfTotal), totalTokens, budget thresholds
- **Text fallback**: "skill-name: N tokens across M files (file1: X, file2: Y, ...)"


## building

```bash
cd apps/skill-dashboard/mcp-app
bun install
bun run build
```

## running

### stdio (for .mcp.json / Claude Code)

```bash
node apps/skill-dashboard/mcp-app/dist/index.cjs --stdio
```

### HTTP (for development)

```bash
node apps/skill-dashboard/mcp-app/dist/index.cjs
# Server on http://localhost:3002/mcp
```

### environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3002` | HTTP server port |
| `SKILL_DASHBOARD_ROOT` | auto-detected | Override repo root path |

## what it checks

### per-skill (4 checks)
- Spec compliance (name format, required fields, allowed fields, description constraints)
- Token budget (sum .md chars/4, warn >4000, critical >8000)
- Body size (line count, warn >500)
- Description quality (WHAT verb + WHEN trigger presence)

### per-plugin (3 checks)
- Manifest fields (name, version, description, author, repository)
- Marketplace listing (in root marketplace.json)
- README exists

### repo hygiene (5+ checks)
- No blanket .claude/ gitignore
- No broad ambient hooks on high-frequency events
- State files gitignored
- No duplicate skill names
- best_practices.md provenance join (annotation hashes vs tracked upstream)
