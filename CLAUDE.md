last updated: 2026-05-04

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- TDD red/green for behavioral changes.
- At session end, update what's actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Don't bulk-update untouched files.
- `.claude/rules/` plus the SessionStart hooks from `dev-conventions`, `path-privacy`, `dimensional-modeling`, `mece-decomposer`, and `env-forge` already inject language tooling (uv, bun, orjson), TDD, doc conventions, path-privacy, MECE, and dimensional modeling rules. Don't restate those here.

## Repo invariants

These bite on the first edit if you don't know them.

1. **Plugin content change ⇒ full version cascade.** `plugin.json` + root `marketplace.json` + plugin `pyproject.toml` + every sub-skill's `metadata.version` + `metadata.last_verified` + root `pyproject.toml` + new `CHANGELOG.md` entry + `uv lock`. `/skill-maintainer:sync-versions` covers four of those; the rest is manual. Pre-commit hard-blocks if any sub-skill's `metadata.version` drifts from `plugin.json`. Detail and worked example: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

2. **Path-privacy is enforced via git hooks.** Every path in repo content (code, docs, commit messages, branch names) must resolve under the repo root. Use `<HOME>/.claude/...` or generic names for system paths. Pre-commit + commit-msg hard-block leaks; don't `--no-verify`. Detail: `skills/path-privacy/`.

3. **best_practices.md has two copies that drift.** Edit `.skill-maintainer/best_practices.md` (working copy). The PostToolUse hook mirrors to `skills/skill-maintainer/references/best_practices.md`. Editing only the bundled copy means fresh `skill-maintain init` runs in other repos pull stale rules. More: [docs/internals/gotchas.md](docs/internals/gotchas.md).

4. **Greenfield default for local DBs.** For `<HOME>/.claude/agent_state.duckdb` and readwise-reader's DuckDB, prefer `CREATE OR REPLACE VIEW` + re-init over migration bridges. Production-facing schemas (marketplace.json, published plugin contents) are the exception.

5. **Security-guidance plugin's PreToolUse hook is disabled here** via `.claude/settings.json` env `ENABLE_SECURITY_REMINDER=0`. It substring-matches benign tokens in markdown prose and false-fires on docs and session logs. If you reset settings, re-disable. Detail: [docs/internals/gotchas.md](docs/internals/gotchas.md).

## Where to find what

| Working on... | Look at |
|---|---|
| Plugin authoring (structure, hooks, agents, directives, bash portability) | [docs/internals/plugin-patterns.md](docs/internals/plugin-patterns.md) |
| Maintenance commands and freshness flow | [docs/internals/maintenance.md](docs/internals/maintenance.md) |
| Repo-specific gotchas (security hook, pre-commit re-install, best_practices duality) | [docs/internals/gotchas.md](docs/internals/gotchas.md) |
| Why a thing is built this way (architectural worldview) | [VISION.md](VISION.md) |
| Captured Claude Code official docs (domain reports + ecosystem field guide) | [docs/README.md](docs/README.md) |
| MCP protocol / apps / cross-surface | [docs/analysis/mcp_protocol_and_servers.md](docs/analysis/mcp_protocol_and_servers.md), [docs/analysis/mcp_apps_and_ui_development.md](docs/analysis/mcp_apps_and_ui_development.md), [docs/analysis/cross_surface_compatibility.md](docs/analysis/cross_surface_compatibility.md) |
| DuckDB schema (agent-state, readwise-reader) | `tools/agent-state/README.md`, `apps/readwise-reader/CLAUDE.md` |
| Repo layout, plugins table, install commands | [README.md](README.md) |
| Setup from a fresh clone | [README.md](README.md) "installation" + `uv sync --all-packages` |

## State

- `.skill-maintainer/state/` — per-repo maintenance state (upstream hashes, page snapshots, `changes.jsonl` audit log; gitignored)
- `<HOME>/.claude/agent_state.duckdb` — global DuckDB for run audit and state tracking (schema in `tools/agent-state/`)
- Each `SKILL.md`'s `metadata.last_verified` — date the skill was last reviewed (skill-maintainer's `freshness` check uses this)

## Cross-repo

- `coderef/agentskills/` — symlink to a local clone of the Agent Skills spec + `skills-ref` validator
- Sibling repos: `star-schema-llm-context` (storage engine / kernel), `ccutils` (client applications). The three together form a database-like component stack — see [VISION.md](VISION.md) for the design.
