last updated: 2026-07-22

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- At session end, update what's actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Don't bulk-update untouched files.
- `.claude/rules/` already covers language tooling (uv, bun, orjson), TDD, and doc conventions; `path-privacy`'s SessionStart hook covers path rules. Don't restate those here. (The `dev-conventions`, `dimensional-modeling` and `mece-decomposer` SessionStart hooks are disabled in this repo — see invariant 6 — so `.claude/rules/` is the only copy that loads.)

## Repo invariants

These bite on the first edit if you don't know them.

1. **Plugin content change ⇒ version cascade (three files).** `plugin.json` + root `marketplace.json` + a `CHANGELOG.md` entry. **Editing `tools/<plugin>/src/` counts as plugin content and triggers the cascade** — without the bump, `marketplace update` never reaches installed users. The same holds for a skill plugin's shipped subdirs: editing `skills/<plugin>/**/templates/`, `.../references/`, or `.../examples/` is a plugin-content change and triggers the cascade, not just SKILL.md prose edits (this session's explainer-video 0.5.1→0.6.0 was mostly template + reference work). Skill plugins here carry no pyproject/uv.lock, so their cascade is exactly the three: plugin.json + marketplace.json + CHANGELOG. Plus `tools/<plugin>/pyproject.toml` and root `pyproject.toml` + `uv lock` only where those exist. **SKILL.md files are not in the cascade** — `metadata.version` was removed from every SKILL.md on 2026-07-21 because it duplicated `plugin.json` and its only reader was the check confirming the duplicate matched. Do not re-add it. `metadata.last_verified` is also out: it asserts a human reviewed the skill, which a version bump does not establish — write it only after an actual review. Detail: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

2. **Path-privacy is enforced via git hooks.** Every path in repo content (code, docs, commit messages, branch names) must resolve under the repo root. Use `<HOME>/.claude/...` or generic names for system paths. Pre-commit + commit-msg hard-block leaks; don't `--no-verify`. **The hooks permit an absolute path that resolves INSIDE the repo** (`/Users/<name>/<this-repo>/x`) — by design, but it still leaks your username, so write those repo-relative too. `skill-maintain test`'s whole-tree audit catches that second class; the hooks do not. Detail: `skills/path-privacy/`.

3. **best_practices.md has two copies that drift.** Edit `.skill-maintainer/best_practices.md` (working copy). The PostToolUse hook mirrors to `skills/skill-maintainer/references/best_practices.md`. Editing only the bundled copy means fresh `skill-maintain init` runs in other repos pull stale rules. More: [docs/internals/gotchas.md](docs/internals/gotchas.md).

4. **Greenfield default for local DBs.** For `<HOME>/.claude/agent_state.duckdb` and readwise-reader's DuckDB, prefer `CREATE OR REPLACE VIEW` + re-init over migration bridges. Production-facing schemas (marketplace.json, published plugin contents) are the exception.

5. **Security-guidance plugin's PreToolUse hook is disabled here** via `.claude/settings.json` env `ENABLE_SECURITY_REMINDER=0`. It substring-matches benign tokens in markdown prose and false-fires on docs and session logs. If you reset settings, re-disable. Detail: [docs/internals/gotchas.md](docs/internals/gotchas.md).

6. **Three of this repo's own plugins are disabled here** via `enabledPlugins: false` in `.claude/settings.json`: `dev-conventions`, `dimensional-modeling`, `mece-decomposer`. (`env-forge` is deprecated, not disabled — the `renames` map in `marketplace.json` handles its removal. An `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.) Their SessionStart hooks inject ~3,500 chars of convention text into every session, and in this repo those conventions are already stated twice — in `.claude/rules/general.md` and the user's global `CLAUDE.md`. The hooks stay in the plugins because they are the entire point for a repo with nothing written down; they are just redundant *here*. `path-privacy` and `pyright-autoconfig` remain enabled — the first enforces via PreToolUse, the second acts silently.

## Where to find what

| Working on... | Look at |
|---|---|
| Plugin authoring (structure, hooks exec form, agents, directives, bash portability) | [docs/internals/plugin-patterns.md](docs/internals/plugin-patterns.md) |
| The version cascade and what is deliberately NOT in it | [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md) |
| Maintenance commands, freshness windows, upstream drift flow | [docs/internals/maintenance.md](docs/internals/maintenance.md) |
| Repo-specific gotchas (disabled plugins, `_deprecated`, pipefail trap, best_practices duality) | [docs/internals/gotchas.md](docs/internals/gotchas.md) |
| Upstream doc changes identified but not yet absorbed | [docs/internals/upstream_drift_backlog.md](docs/internals/upstream_drift_backlog.md) |
| The explainer-video generalization plan (phases, gates, execution status) and per-item roadmap | [docs/internals/explainer_video_generalization_plan.md](docs/internals/explainer_video_generalization_plan.md), [docs/internals/explainer_video_roadmap.md](docs/internals/explainer_video_roadmap.md) |
| What the explainer-video test suite covers, and every case's outcome | [docs/internals/explainer_video_test_cases.md](docs/internals/explainer_video_test_cases.md) |
| The explainer-video hardening plan — the run's findings grouped by root cause, structural fixes vs deliberate bandaids | [docs/internals/explainer_video_hardening_plan.md](docs/internals/explainer_video_hardening_plan.md) |
| Why a thing is built this way (architectural worldview) | [VISION.md](VISION.md) |
| The documentation index (what survives, and why) | [docs/README.md](docs/README.md) |
| MCP orientation (start here) | [docs/mcp-ecosystem.md](docs/mcp-ecosystem.md) |
| MCP protocol | [docs/analysis/mcp_protocol_and_servers.md](docs/analysis/mcp_protocol_and_servers.md) (verified current) |
| MCP Apps / UI | `skills/mcp-apps/references/` — the official spec, shipped as a plugin |
| Current upstream Claude Code docs | `skill-maintain upstream`, then `.skill-maintainer/state/pages/` (gitignored). Nothing upstream is copied into this repo |
| DuckDB schema (agent-state, readwise-reader) | `tools/agent-state/README.md`, `apps/readwise-reader/CLAUDE.md` |
| Repo layout, plugins table, install commands | [README.md](README.md) |
| Setup from a fresh clone | [README.md](README.md) "installation" + `uv sync --all-packages` |

## State

- `.skill-maintainer/state/` — per-repo maintenance state (upstream hashes, page snapshots, `changes.jsonl` audit log; gitignored)
- `<HOME>/.claude/agent_state.duckdb` — global DuckDB for run audit and state tracking (schema in `tools/agent-state/`)
- Each `SKILL.md`'s `metadata.last_verified` — the date a human last reviewed that skill against its source. Never bumped mechanically; see invariant 1. Its window is `metadata.review_interval_days` (default 30), tiered 30 / 90 / 365 by how fast the source moves.
- `apps/_deprecated/` — units kept for reference but no longer published. In `SKIP_DIRS`, so nothing there is scanned for skills or plugins.

## Cross-repo

- `coderef/agentskills/` — symlink to a local clone of the Agent Skills spec + `skills-ref` validator
- Sibling repos: `star-schema-llm-context` (storage engine / kernel), `ccutils` (client applications). The three together form a database-like component stack — see [VISION.md](VISION.md) for the design.
