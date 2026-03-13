# fb-claude-skills

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Includes property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Guidelines

- Use a TDD red/green style approach to development
- When you finish a session or iteration of work, update the following, at minimum:
  - `internal/log`
  - `./CLAUDE.md` (if needed)
  - `./README.md` (if needed)
  - The `README.md` and related docs for each impacted app, skill, or tool (example: `apps/mece-decomposer/README.md`)
  - If relevant, the `pyproject.toml` for each impacted app or tool (example: `tools/agent-state/pyproject.toml`)

## Repo structure

```
fb-claude-skills/
  .mcp.json                  # Root MCP server config (empty; add servers on demand)
  .claude-plugin/
    marketplace.json         # Root marketplace catalog (lists all installable plugins)
  skills/                    # Pure markdown skill bundles
    mcp-apps/                # Plugin: MCP Apps creation and migration
    plugin-toolkit/          # Plugin: plugin analysis and management
    cogapp-markdown/         # Plugin: auto-generate markdown sections
    tui-design/              # Plugin: terminal UI design principles
    dimensional-modeling/    # Plugin: Kimball star schema patterns
    dev-conventions/         # Plugin: development conventions (tooling, TDD, documentation)
  apps/                      # MCP server applications
    readwise-reader/         # MCP server: Readwise Reader library (OAuth, DuckDB, FTS)
    mece-decomposer/         # Plugin: MECE decomposition + MCP App tree visualizer
    env-forge/               # Plugin: database-backed MCP tool environment generator
    skill-dashboard/         # Project-scoped: Python MCP App skill dashboard (rawHtml reference impl)
    heylook-monitor/         # Project-scoped: MCP App dashboard for local LLM server
  tools/                     # CLI packages
    skill-maintainer/        # Installable package: maintenance CLI for any skill repo
      src/skill_maintainer/  # Python package (cli, shared, tests, quality, validate, freshness, measure, upstream, sources, log)
      references/            # Best practices
    agent-state/             # Installable package: DuckDB audit/state tracking for runs (schema v2)
      src/agent_state/       # Python package (database, run_context, watermarks, skill_versions, query, migration, cli)
      BACKLOG.md             # Future work items
      tests/                 # Unit tests
  .skill-maintainer/         # Per-repo config and state (gitignored state/)
    config.json              # upstream URLs, tracked repos, llms-full URL
    best_practices.md        # Machine-parseable best practices checklist
    state/                   # upstream_hashes.json, changes.jsonl (auto-generated, gitignored)
  docs/
    analysis/                # 16 domain reports (skills, plugins, MCP, hooks, agents, memory, etc.)
    reports/                 # Synthesis reports
    claude-docs/             # Captured Claude Code official docs (20 files)
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
/plugin install cogapp-markdown@fb-claude-skills
/plugin install tui-design@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
/plugin install mece-decomposer@fb-claude-skills
/plugin install env-forge@fb-claude-skills
/plugin install dev-conventions@fb-claude-skills
/plugin install readwise-reader@fb-claude-skills
```

After installing, skills are available as namespaced slash commands (e.g., `/mcp-apps:create-mcp-app`, `/mece-decomposer:decompose`).

To remove: `claude plugin uninstall <name>@fb-claude-skills`

### Project-scoped modules

heylook-monitor and skill-dashboard run from within this repo only. skill-dashboard is listed in marketplace.json as a reference but is not intended for external installation.

skill-maintainer is an installable Python package. From other repos: `uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer`. Then run `skill-maintain init` to create per-repo config.

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

### Context as retrieval

Skills are retrieval. High precision is the constraint, high recall is the goal. Every always-loaded line (CLAUDE.md, rules, skill descriptions) must justify its presence. See `VISION.md` for the full design principles.

### Catalog as exemplar

When generating new artifacts, first search existing catalogs for structurally similar examples. Use the closest match as a few-shot reference -- adapt patterns, don't copy verbatim. See the env-forge `forge` skill's step 2.

### Cross-member imports

`skill-dashboard` declares `skill-maintainer` as a workspace dependency. Imports: `from skill_maintainer.tests import test_skills, test_plugins, test_repo_hygiene` and `from skill_maintainer.shared import TOKEN_BUDGET_WARN, TOKEN_BUDGET_CRITICAL`. Budget threshold constants live in `skill_maintainer.shared` and are injected into downstream consumers (dashboard HTML) -- never hardcode them.

## How to keep things fresh

| Concern | Mechanism | Trigger |
|---------|-----------|---------|
| Spec compliance | Pre-commit git hook | Automatic on commit |
| Red/green tests | `skill-maintain test` | On demand |
| Full maintenance pass | `/maintain` (pulls sources, checks upstream, runs quality report, proposes best_practices.md updates) | On demand |
| Quality/budget/freshness | `skill-maintain quality` | On demand |
| Upstream change detection | `skill-maintain upstream` | On demand |
| Local source pulls | `skill-maintain sources` | On demand |
| Change history | `skill-maintain log` | On demand |

Other useful commands:

```bash
skill-maintain validate --all                    # validate all skills
skill-maintain measure                           # token budget report
skill-maintain freshness                         # staleness check
skill-maintain init                              # initialize .skill-maintainer/ in a new repo
uv run agentskills validate path/to/SKILL.md     # validate a single skill (low-level)
```

All commands accept `--dir <path>` to target a different repo.

## State

- `.skill-maintainer/state/upstream_hashes.json` -- page content hashes for upstream detection (auto-generated)
- `.skill-maintainer/state/changes.jsonl` -- append-only audit log of quality reports and upstream checks
- `metadata.last_verified` in each SKILL.md frontmatter -- date the skill was last reviewed
- `~/.claude/agent_state.duckdb` -- global DuckDB for run audit and state tracking (schema v2, see `tools/agent-state/README.md` for full schema docs)

## Documentation index

See [docs/README.md](docs/README.md) for the full documentation index (16 domain reports, synthesis, internals, captured docs).

## Cross-repo references

- **agentskills** (`coderef/agentskills/` -> `~/claude/agentskills`): Agent Skills open standard and `skills-ref` validator.

## Conventions

Conventions are in `.claude/rules/` and auto-loaded by Claude Code. These are author-side only -- they do not distribute with marketplace plugin installs.

## Dependencies

JavaScript/TypeScript projects use `bun` instead of `npm` or `yarn`.

Python managed as a **uv workspace**. The root `pyproject.toml` coordinates workspace member packages, each declaring its own deps:

| Member | Path | Key dependencies |
|--------|------|-----------------|
| `skill-maintainer` | `tools/skill-maintainer` | orjson, httpx, skills-ref (PyPI); CLI: `skill-maintain` |
| `agent-state` | `tools/agent-state` | orjson, duckdb; CLI: `agent-state` |
| `env-forge` | `apps/env-forge` | orjson, huggingface-hub |
| `skill-dashboard` | `apps/skill-dashboard` | orjson, mcp, mcp-ui-server (git), skill-maintainer (workspace) |
| `mece-decomposer` | `apps/mece-decomposer` | orjson |
| `readwise-reader` | `apps/readwise-reader` | mcp, httpx, duckdb, pydantic, authlib, skill-maintainer (workspace); opt-in, requires Python 3.13+ |

Setup: `uv sync --all-packages` installs all member deps into a shared venv. Existing `uv run` commands work unchanged. readwise-reader is excluded from the default workspace (requires Python 3.13+); opt in by removing it from the `exclude` list in `pyproject.toml`.
