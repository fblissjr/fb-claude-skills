# fb-claude-skills

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Includes a self-updating maintenance system that detects upstream changes, validates against the Agent Skills spec, and produces diffs for human review.

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
  heylook-monitor/           # Project-scoped: MCP App dashboard for local LLM server
  skill-dashboard/           # Project-scoped: Python MCP App skill dashboard (rawHtml reference impl)
    .mcp.json                # MCP server auto-configuration (stdio)
    skills/skill-dashboard/  # SKILL.md
    server.py                # FastMCP + mcp-ui server
    templates/               # dashboard.html (Tailwind CDN + Alpine.js CDN)
  skill-maintainer/          # Project-scoped: maintains other skills (and itself)
    SKILL.md                 # Orchestrator: check, update, status, add-source
    config.yaml              # Source registry
    scripts/                 # Python automation (all run via uv run)
    references/              # Best practices, monitored sources
    state/                   # Versioned state: watermarks, page hashes, timestamps
  docs/
    analysis/                # 15 domain reports (skills, plugins, MCP, hooks, agents, memory, etc.)
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
```

After installing, skills are available as namespaced slash commands (e.g., `/mcp-apps:create-mcp-app`, `/web-tdd`).

To remove: `claude plugin uninstall <name>@fb-claude-skills`

### Project-scoped modules

skill-maintainer, heylook-monitor, and skill-dashboard run from within this repo only. skill-dashboard is listed in marketplace.json as a reference but is not intended for external installation.

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

### Docs CDC (Change Data Capture)

Three-layer pipeline in `docs_monitor.py`:

1. **DETECT** -- HEAD request on `llms-full.txt`, compare `Last-Modified` header. Zero bytes if unchanged.
2. **IDENTIFY** -- fetch `llms-full.txt`, split by `Source:` delimiters, hash each watched page, compare to stored hashes.
3. **CLASSIFY** -- keyword heuristic on diff text (breaking/additive/cosmetic).

### Source CDC

Git-based monitoring via `source_monitor.py`. Shallow-clones configured repos, checks commits since last run, extracts Python APIs via AST, scans for deprecation keywords.

### Closed-loop updates

detect -> classify -> apply -> validate -> user reviews diff. `apply_updates.py` supports three modes: `report-only`, `apply-local` (default), and `create-pr`. Always validates with skills-ref before any write.

### Progressive disclosure

SKILL.md stays under 500 lines. Heavy logic in `scripts/`, detailed docs in `references/`. Three levels: frontmatter (always loaded) -> SKILL.md body (loaded when relevant) -> linked files (on demand).

### Selection under constraint (design principle)

The unifying principle: **given more possibilities than you can evaluate, select the subset that matters, process it, combine results.** Every system implements five invariant operations: **decompose, route, prune, synthesize, verify**.

Skills are **view definitions + stored procedures**, not documentation. A skill defines a projection (what context to show) and controls the execution graph. The architecture is an **external query planner** for LLM I/O.

Three repos form a database-like component stack:
- **star-schema-llm-context/** -- storage engine / kernel
- **fb-claude-skills/** -- stored procedures / system catalog
- **ccutils/** -- client applications

See `docs/analysis/abstraction_analogies.md` for the full treatment.

### Dimensional model (DuckDB store)

skill-maintainer uses a Kimball-style dimensional model in DuckDB (`store.py`):

- **MD5 hash surrogate keys** on all dimensions (deterministic, no sequences)
- **SCD Type 2** on dimension tables (effective_from/to, is_current, hash_diff) -- no PRIMARY KEY constraints
- **No PKs on fact tables** (grain = composite dimension keys + timestamp)
- **Metadata columns** on all tables (record_source, session_id, inserted_at)
- **Session boundaries as events** in fact_session_event, not a separate table

See `docs/internals/duckdb_schema.md` for the full schema.

## How to keep things fresh

```bash
uv run python skill-maintainer/scripts/docs_monitor.py       # check doc changes
uv run python skill-maintainer/scripts/source_monitor.py      # check source changes
uv run python skill-maintainer/scripts/update_report.py       # generate unified report
uv run python skill-maintainer/scripts/apply_updates.py --skill <name>  # apply changes
uv run python skill-maintainer/scripts/check_freshness.py     # check staleness
uv run skills-ref validate path/to/SKILL.md                   # validate a skill
uv run python skill-maintainer/scripts/validate_skill.py --all # validate all skills
```

## Configuration

**Source registry**: `skill-maintainer/config.yaml`
- `sources`: each has a `type` (docs or source), detection method, and list of watched pages/files
- `skills`: tracked skills with paths, source dependencies, and auto_update flag

**State**: `skill-maintainer/state/state.json`
- `docs.{source}._watermark` -- Last-Modified/ETag for the detect layer
- `docs.{source}._pages.{url}` -- per-page hash, content_preview, last_checked, last_changed
- `sources.{source}` -- last_commit, commits_since_last, last_checked

## Documentation index

### Domain reports (`docs/analysis/`)

| Report | Topic |
|--------|-------|
| `plugin_system_architecture.md` | Plugin anatomy, schema, components, auto-discovery, audit |
| `marketplace_distribution_patterns.md` | Marketplace schema, source types, monorepo, enterprise distribution |
| `mcp_protocol_and_servers.md` | MCP protocol, primitives, transports, SDKs, registry |
| `mcp_apps_and_ui_development.md` | MCP Apps SDK, UI linkage, React hooks, framework templates |
| `hooks_system_patterns.md` | Hook events, types, matchers, security, automation patterns |
| `subagents_and_agent_teams.md` | Custom agents, tool control, teams, delegation patterns |
| `cross_surface_compatibility.md` | Surface matrix, transports, permissions, headless mode |
| `claude_skills_best_practices_guide_full_report.md` | Skills best practices from Anthropic guide |
| `skills_guide_structured.md` | Structured extraction for CDC |
| `skills_guide_analysis.md` | Gap analysis vs repo |
| `self_updating_system_design.md` | CDC architecture decisions |
| `abstraction_analogies.md` | Unifying design principle |
| `duckdb_dimensional_model_strategy.md` | DuckDB star schema strategy |
| `data_centric_agent_state_research.md` | Agent state research |

### Synthesis (`docs/reports/`)

| Report | Topic |
|--------|-------|
| `claude_ecosystem_synthesis.md` | Full ecosystem overview, decision tree, maturity assessment |

### Internals (`docs/internals/`)

| Report | Topic |
|--------|-------|
| `duckdb_schema.md` | Full DuckDB schema documentation |
| `api_reference.md` | Script function signatures and parameters |
| `schema.md` | state.json and config.yaml schemas |
| `troubleshooting.md` | Common issues and recovery |

## Cross-repo references

- **agentskills** (`coderef/agentskills/` -> `~/claude/agentskills`): Agent Skills open standard and `skills-ref` validator.
- **mlx-skills** (`~/claude/mlx-skills`): Semi-automated skill maintenance for MLX-related skills.

## Conventions

Conventions are in `.claude/rules/` and auto-loaded by Claude Code. These are author-side only -- they do not distribute with marketplace plugin installs.

## Dependencies

Managed via `pyproject.toml` with uv:
- `orjson` - fast JSON
- `httpx` - HTTP client for CDC detect/identify layers
- `pyyaml` - config parsing
- `skills-ref` - Agent Skills validator (editable install from `coderef/agentskills/skills-ref`)
- `mcp-ui-server` - MCP UI SDK Python server (editable install from `coderef/mcp-ui/sdks/python/server`)
