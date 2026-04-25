# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. VISION.md covers the architectural worldview and the retrieval system that implements it. High precision is the constraint, high recall is the goal.

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
    dev-conventions/         # Plugin: development conventions (SessionStart hook for tooling, TDD, version pinning, session logging, dep-audit + on-demand skills)
    skill-maintainer/        # Plugin: maintenance tools (quality, freshness, upstream, best practices)
    json-query/              # Plugin: JSON query tool selection (jg vs jq)
    scan-for-secrets/        # Plugin: pre-share scanner (simonw/scan-for-secrets literal pass + ripgrep regex pass)
    path-privacy/            # Plugin: enforces repo-relative paths via SessionStart directive + pre-commit / commit-msg git hooks
  apps/                      # MCP server applications
    readwise-reader/         # MCP server: Readwise Reader library (OAuth, DuckDB, FTS)
    agent-state-mcp/         # MCP server: read-only tools over ~/.claude/agent_state.duckdb (thin layer on tools/agent-state)
    mece-decomposer/         # Plugin: MECE decomposition + MCP App tree visualizer
    env-forge/               # Plugin: database-backed MCP tool environment generator
    skill-dashboard/         # Project-scoped: ext-apps MCP App quality dashboard (TypeScript)
    heylook-monitor/         # Project-scoped: MCP App dashboard for local LLM server
  tools/                     # CLI packages and scripts
    dep-audit-scan.sh        # Standalone: scan macOS for projects with dependency vulnerabilities
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
    analysis/                # 15 domain reports (skills, plugins, MCP, hooks, agents, memory, etc.)
    reports/                 # Synthesis reports
    claude-docs/             # Captured Claude Code official docs (20 files)
  coderef/
    agentskills/             # Symlink -> ~/claude/agentskills (Agent Skills spec + skills-ref)
    ext-apps/                # MCP Apps SDK reference
    mcp/                     # MCP protocol spec, SDKs, inspector, registry, servers
    mcp-ui/                  # MCP UI SDK reference
  internal/log/              # Session logs (log_YYYY-MM-DD.md)
  research/                  # Benchmark suites and research artifacts (schema-processing)
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
/plugin install skill-maintainer@fb-claude-skills
/plugin install readwise-reader@fb-claude-skills
/plugin install agent-state-mcp@fb-claude-skills
/plugin install json-query@fb-claude-skills
/plugin install scan-for-secrets@fb-claude-skills
/plugin install path-privacy@fb-claude-skills
```

After installing, skills are available as namespaced slash commands (e.g., `/mcp-apps:create-mcp-app`, `/mece-decomposer:decompose`).

To remove: `claude plugin uninstall <name>@fb-claude-skills`

### Project-scoped modules

heylook-monitor and skill-dashboard run from within this repo only. skill-dashboard is listed in marketplace.json as a reference but is not intended for external installation.

skill-maintainer has two interfaces: a plugin (`skills/skill-maintainer/`) for interactive use in Claude Code, and a Python CLI package (`tools/skill-maintainer/`) for CI/headless use. Install the plugin for the best experience. The CLI is available from other repos via: `uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer`.

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
  hooks/                   # optional: SessionStart/PreToolUse hooks
    hooks.json             # hook registration (event -> command)
    session-start.sh       # detection logic + directive assembly
    directives/            # composable directive files (# trigger: <signal>)
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

Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal. Every always-loaded line (CLAUDE.md, rules, skill descriptions) must justify its presence. See `VISION.md` for the full design principles and architectural worldview.

### Hooks as directives

Hooks inject behavioral directives (what to do). Skills provide reference material (how to do it in detail). If something must always be active when a project matches certain markers, it belongs in a hook directive, not just a skill. Skills are on-demand only -- they load when triggered by keywords or explicit invocation.

**Composable directive pattern**: Each plugin with behavioral content should have a `hooks/` directory containing a `session-start.sh` that detects project markers and assembles directives from `hooks/directives/*.md` files. Each directive file declares `# trigger: <signal>` on line 1. Adding a new convention = dropping a file, no shell editing. Signals are plugin-specific (e.g., `python`, `duckdb`, `tui`, `envforge`).

Plugins using this pattern: dev-conventions, tui-design, dimensional-modeling, mece-decomposer, env-forge.

### Plugin versioning

Any change to plugin content (hooks, scripts, directives, references) requires a version bump or `marketplace update` won't refresh the cache. Always use `/skill-maintainer:sync-versions <plugin> <version>` for version bumps -- it updates the core sources atomically (plugin.json, marketplace.json, primary SKILL.md, pyproject.toml, CHANGELOG.md). For plugins with multiple sub-skills (e.g. skill-maintainer has 4 sub-skills), every sub-skill SKILL.md also has its own `metadata.version` + `metadata.last_verified` that must be bumped -- the sync-versions playbook only touches the primary SKILL.md, so additional sub-skills need manual edits. Manual bumps miss sources.

### Canonical best_practices.md

Two copies exist: `.skill-maintainer/best_practices.md` (this repo's working copy, read by `skill-maintain`) and `skills/skill-maintainer/references/best_practices.md` (seed for `skill-maintain init` in new repos). When updating rules, edit the working copy and `cp` it to the bundled reference -- otherwise new inits pull stale rules. A `sync-best-practices` subcommand or symlink would close this loop but hasn't been implemented.

### Security hook gotcha

The `security-guidance` plugin ships a PreToolUse hook (`security_reminder_hook.py`) that substring-matches several English tokens that appear in doc prose (code-evaluation builtins with parens, serialization lib names, DOM sink method names, OS exec function names). No path or context awareness. Fires on MLX docs and session logs routinely.

Disabled for this repo via `.claude/settings.json` -> `env.ENABLE_SECURITY_REMINDER=0`. Upstream fix: path-aware exemption for .md files. Trade-off: this repo gives up all of the plugin's checks, but since content here is mostly markdown and Python without those patterns in source code, and the repo's own pre-commit + TDD workflow provide other safety nets, the trade is worth it. If you need the checks back, flip the env var.

### Pre-commit hook

`.git/hooks/pre-commit` validates staged SKILL.md files (via agentskills), checks version alignment across all sources, and warns when plugin content changes are staged without a version bump. Not tracked by git -- must be re-applied on fresh clones.

### Catalog as exemplar

When generating new artifacts, first search existing catalogs for structurally similar examples. Use the closest match as a few-shot reference -- adapt patterns, don't copy verbatim. See the env-forge `forge` skill's step 2.

### Schema evolution: greenfield default

For local DBs in this repo (`~/.claude/agent_state.duckdb`, readwise-reader's DuckDB, future ones), the preferred evolution pattern is `CREATE OR REPLACE VIEW` + schema re-init on next connection. Don't write migration bridges or backward-compat shims unless explicitly asked. "OK to drop data, greenfield is fine" is the working default for non-production state. Production-facing schemas (marketplace, published plugins) are the exception.

### Bash portability for plugin scripts

Plugin scripts use `#!/usr/bin/env bash` and may run on macOS system bash (3.2). Avoid bash 4+ features: `mapfile`/`readarray`, `declare -A` (associative arrays), and `[[ =~ ]]` when a `case` will do. For per-line file reads use `while IFS= read -r line; do arr[$i]="$line"; i=$((i+1)); done < "$f"` with indexed arrays. The pre-commit hook (`jq`-based) and `regex-scan.sh`/`find-external-paths.sh` all stick to this subset.

## How to keep things fresh

| Concern | Mechanism | Trigger |
|---------|-----------|---------|
| Spec compliance | Pre-commit git hook | Automatic on commit |
| Unbumped content changes | Pre-commit git hook (warning) | Automatic on commit |
| Bundled best_practices.md drift | skill-maintainer PostToolUse hook (`sync-bundled-ref.sh`) | Automatic on Edit/Write of working copy |
| Forgotten session log | skill-maintainer Stop hook (`maybe-draft-session-log.sh`) | Automatic on session stop when substantive work + no log |
| End-of-session wrap-up | `/skill-maintainer:finish-session` (orchestrates drafter -> sync -> version bumps -> quality) | On demand |
| Red/green tests | `skill-maintain test` | On demand |
| Full maintenance pass | `/skill-maintainer:maintain` (pulls sources, checks upstream, runs quality report, proposes best_practices.md updates) | On demand |
| Quality/budget/freshness | `/skill-maintainer:quality` or `skill-maintain quality` | On demand |
| Upstream change detection | `skill-maintain upstream` | On demand |
| Local source pulls | `skill-maintain sources` | On demand |
| Version alignment | `/skill-maintainer:sync-versions <plugin> <ver>` | On demand |
| Bundled reference manual sync | `/skill-maintainer:sync-bundled-ref` (fallback when hook didn't fire) | On demand |
| Change history | `skill-maintain log` | On demand |
| Dependency security | `/dev-conventions:dep-audit` (per-project) or `./tools/dep-audit-scan.sh` (cross-project) | On demand |
| Enable agent-state MCP server | `/agent-state-mcp:enable` (promotes `.mcp.json` `_available_servers` -> `mcpServers`) | On demand |

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
- `.skill-maintainer/state/pages/<slug>.md` -- per-page content snapshots so `skill-maintain upstream` can compute line/char deltas on subsequent runs (auto-generated, v0.4.0+)
- `.skill-maintainer/state/changes.jsonl` -- append-only audit log of quality reports and upstream checks
- `metadata.last_verified` in each SKILL.md frontmatter -- date the skill was last reviewed
- `~/.claude/agent_state.duckdb` -- global DuckDB for run audit and state tracking (schema v2, see `tools/agent-state/README.md` for full schema docs)

## Documentation index

See [docs/README.md](docs/README.md) for the full documentation index (15 domain reports, synthesis, internals, captured docs).

## Cross-repo references

- **agentskills** (`coderef/agentskills/` -> `~/claude/agentskills`): Agent Skills open standard and `skills-ref` validator.

## Conventions

Conventions are in `.claude/rules/` and auto-loaded by Claude Code. These are author-side only -- they do not distribute with marketplace plugin installs. Note: shell hooks use `jq` for JSON parsing (not python3/orjson) since they run outside the project venv.

## Dependencies

JavaScript/TypeScript projects use `bun` instead of `npm` or `yarn`.

Python managed as a **uv workspace**. The root `pyproject.toml` coordinates workspace member packages, each declaring its own deps:

| Member | Path | Key dependencies |
|--------|------|-----------------|
| `skill-maintainer` | `tools/skill-maintainer` | orjson, httpx, skills-ref (PyPI); CLI: `skill-maintain` |
| `agent-state` | `tools/agent-state` | orjson, duckdb; CLI: `agent-state` |
| `agent-state-mcp` | `apps/agent-state-mcp` | mcp, duckdb, orjson, agent-state (workspace); CLI: `agent-state-mcp` (stdio MCP server) |
| `env-forge` | `apps/env-forge` | orjson, huggingface-hub |
| `skill-dashboard` | `apps/skill-dashboard/mcp-app` | TypeScript ext-apps MCP App (gray-matter, react, zod); no Python deps |
| `mece-decomposer` | `apps/mece-decomposer` | orjson |
| `readwise-reader` | `apps/readwise-reader` | mcp, httpx, duckdb, pydantic, authlib, skill-maintainer (workspace); opt-in, requires Python 3.13+ |

Setup: `uv sync --all-packages` installs all member deps into a shared venv. Existing `uv run` commands work unchanged. readwise-reader is excluded from the default workspace (requires Python 3.13+); opt in by removing it from the `exclude` list in `pyproject.toml`.
