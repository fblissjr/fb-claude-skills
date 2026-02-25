# fb-claude-skills

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Includes property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Repo structure

```
fb-claude-skills/
  .claude-plugin/
    marketplace.json         # Root marketplace catalog (lists all installable plugins)
  mcp-apps/                  # Plugin: MCP Apps creation and migration
    .claude-plugin/plugin.json
    skills/                  # create-mcp-app, migrate-oai-app
    references/              # Upstream docs (offline copies)
  plugin-toolkit/            # Plugin: plugin analysis and management
    .claude-plugin/plugin.json
    skills/plugin-toolkit/   # SKILL.md + references/
    agents/                  # plugin-scanner, quality-checker
  web-tdd/                   # Plugin: TDD workflow for web apps
    .claude-plugin/plugin.json
    skills/web-tdd/          # SKILL.md
  cogapp-markdown/           # Plugin: auto-generate markdown sections
    .claude-plugin/plugin.json
    skills/cogapp-markdown/  # SKILL.md
  tui-design/                # Plugin: terminal UI design principles
    .claude-plugin/plugin.json
    skills/tui-design/       # SKILL.md + references/
  dimensional-modeling/      # Plugin: Kimball star schema patterns
    .claude-plugin/plugin.json
    skills/dimensional-modeling/  # SKILL.md + references/
  mece-decomposer/           # Plugin: MECE decomposition + MCP App
    .claude-plugin/plugin.json
    .mcp.json                # MCP server auto-configuration (stdio)
    commands/                # Slash commands: decompose, interview, validate, export
    skills/mece-decomposer/  # SKILL.md + references/ + scripts/
    mcp-app/                 # MCP App: interactive tree visualizer (React + bundled server)
  env-forge/                 # Plugin: database-backed MCP tool environment generator
    .claude-plugin/plugin.json
    commands/                # Slash commands: browse, forge, launch, verify
    skills/env-forge/        # SKILL.md + references/
    scripts/                 # catalog.py, materialize.py, validate_env.py
  heylook-monitor/           # Project-scoped: MCP App dashboard for local LLM server
  skill-dashboard/           # Project-scoped: Python MCP App skill dashboard (rawHtml reference impl)
    .claude-plugin/plugin.json
    .mcp.json                # MCP server auto-configuration (stdio)
    skills/skill-dashboard/  # SKILL.md
    server.py                # FastMCP + mcp-ui server
    templates/               # dashboard.html (Tailwind CDN + Alpine.js CDN)
  skill-maintainer/          # Project-scoped: maintenance tooling (not a skill)
    scripts/                 # quality_report, check_upstream, check_freshness, validate_skill, measure_content, query_log
    references/              # Best practices
    state/                   # upstream_hashes.json, changes.jsonl (auto-generated)
  docs/
    analysis/                # 16 domain reports (skills, plugins, MCP, hooks, agents, memory, etc.)
    reports/                 # Synthesis reports
    internals/               # API reference, schemas, troubleshooting
    claude-docs/             # Captured Claude Code official docs
    guides/                  # PDF guide source
  coderef/
    agentskills/             # Symlink -> ~/claude/agentskills (Agent Skills spec + skills-ref)
    ext-apps/                # MCP Apps SDK reference
    mcp/                     # MCP protocol spec, SDKs, inspector, registry, servers
    mcp-ui/                  # MCP UI SDK reference
  internal/log/              # Session logs (log_YYYY-MM-DD.md)
```

## Installation

### Installable plugins

This repo is a plugin marketplace. Add it and install plugins:

```bash
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install web-tdd@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
/plugin install tui-design@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
/plugin install mece-decomposer@fb-claude-skills
/plugin install env-forge@fb-claude-skills
```

After installing, skills are available as namespaced slash commands (e.g., `/mcp-apps:create-mcp-app`, `/web-tdd`).

To remove: `claude plugin uninstall <name>@fb-claude-skills`

### Project-scoped modules

heylook-monitor and skill-dashboard run from within this repo only. skill-dashboard is listed in marketplace.json as a reference but is not intended for external installation. skill-maintainer is project-scoped tooling (scripts + hooks), not a skill.

## Plugin development

Plugins bundle five component types: skills, agents, hooks, MCP servers, and LSP servers. Components in default directories (`skills/`, `agents/`) are auto-discovered -- do not list them in plugin.json.

Required structure:
```
plugin-name/
  .claude-plugin/
    plugin.json            # name, version, description, author, repository
  README.md                # last updated date, installation, skills table
  skills/
    skill-name/
      SKILL.md             # frontmatter: name, description, metadata.author/version
  agents/                  # optional: agent .md files
  references/              # optional: supporting docs loaded on demand
```

For full plugin architecture, schemas, and patterns, see `docs/analysis/plugin_system_architecture.md`.

## MCP development

MCP servers expose tools, resources, and prompts to Claude Code and other MCP clients. MCP Apps add interactive UIs rendered in hosts that support them (Cowork, Claude.ai).

- Protocol fundamentals: `docs/analysis/mcp_protocol_and_servers.md`
- Building UIs: `docs/analysis/mcp_apps_and_ui_development.md`
- Cross-surface compatibility: `docs/analysis/cross_surface_compatibility.md`

## Key patterns

### Progressive disclosure

SKILL.md stays under 500 lines. Heavy logic in `scripts/`, detailed docs in `references/`. Three levels: frontmatter (always loaded) -> SKILL.md body (loaded when relevant) -> linked files (on demand).

### Selection under constraint (design principle)

The unifying principle, using data analogies: **given more possibilities than you can evaluate, select the subset that matters, process it, combine results.** Every system implements five invariant operations: **decompose, route, prune, synthesize, verify**.

Skills are **view definitions + stored procedures**, not documentation. A skill defines a projection (what context to show) and controls the execution graph. The architecture is an **external query planner** for LLM I/O.

Three repos form a database-like component stack:
- **star-schema-llm-context/** -- storage engine / kernel
- **fb-claude-skills/** -- stored procedures / system catalog
- **ccutils/** -- client applications

See `docs/analysis/abstraction_analogies.md` for the full treatment.

### Catalog as exemplar

When generating new artifacts, first search existing catalogs for structurally similar examples. Use the closest match as a few-shot reference -- adapt patterns, don't copy verbatim. See `env-forge/commands/forge.md` step 2.

## How to keep things fresh

| Concern | Mechanism | Trigger |
|---------|-----------|---------|
| Spec compliance | Pre-commit git hook | Automatic on commit |
| Staleness awareness | PostToolUse hook on Skill tool | Automatic when any skill is used |
| Quality/budget/freshness | `uv run python skill-maintainer/scripts/quality_report.py` | On demand |
| Upstream change detection | `uv run python skill-maintainer/scripts/check_upstream.py` | On demand |
| Change history | `uv run python skill-maintainer/scripts/query_log.py` | On demand |

Other useful commands:

```bash
uv run python skill-maintainer/scripts/validate_skill.py --all    # validate all skills
uv run python skill-maintainer/scripts/measure_content.py          # token budget report
uv run python skill-maintainer/scripts/check_freshness.py          # staleness check
uv run skills-ref validate path/to/SKILL.md                        # validate a single skill
```

## State

- `skill-maintainer/state/upstream_hashes.json` -- page content hashes for upstream detection (auto-generated)
- `skill-maintainer/state/changes.jsonl` -- append-only audit log of quality reports and upstream checks
- `metadata.last_verified` in each SKILL.md frontmatter -- date the skill was last reviewed

## Documentation index

See [docs/README.md](docs/README.md) for the full documentation index (16 domain reports, synthesis, internals, captured docs).

## Cross-repo references

- **agentskills** (`coderef/agentskills/` -> `~/claude/agentskills`): Agent Skills open standard and `skills-ref` validator.
- **mlx-skills** (`~/claude/mlx-skills`): Semi-automated skill maintenance for MLX-related skills.

## Conventions

Conventions are in `.claude/rules/` and auto-loaded by Claude Code. These are author-side only -- they do not distribute with marketplace plugin installs.

## Dependencies

Managed via `pyproject.toml` with uv:
- `orjson` - fast JSON
- `httpx` - HTTP client for upstream change detection
- `pyyaml` - config parsing
- `huggingface-hub` - HF dataset access for env-forge catalog
- `skills-ref` - Agent Skills validator (editable install from `coderef/agentskills/skills-ref`)
- `mcp-ui-server` - MCP UI SDK Python server (editable install from `coderef/mcp-ui/sdks/python/server`)
