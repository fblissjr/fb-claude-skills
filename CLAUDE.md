last updated: 2026-05-04

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- At session end, update what's actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Don't bulk-update untouched files.
- `.claude/rules/` already covers language tooling (uv, bun, orjson), TDD, and doc conventions; `path-privacy`'s SessionStart hook covers path rules. Don't restate those here. (The `dev-conventions`, `dimensional-modeling`, `mece-decomposer`, and `env-forge` SessionStart hooks are disabled in this repo — see invariant 6 — so `.claude/rules/` is the only copy that loads.)

## Repo invariants

These bite on the first edit if you don't know them.

1. **Plugin content change ⇒ version cascade (three files).** `plugin.json` + root `marketplace.json` + a `CHANGELOG.md` entry. Plus `tools/<plugin>/pyproject.toml` and root `pyproject.toml` + `uv lock` only where those exist. **SKILL.md files are not in the cascade** — `metadata.version` was removed from all 39 on 2026-07-21 because it duplicated `plugin.json` and its only reader was the check confirming the duplicate matched. Do not re-add it. `metadata.last_verified` is also out: it asserts a human reviewed the skill, which a version bump does not establish — write it only after an actual review. Detail: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

2. **Path-privacy is enforced via git hooks.** Every path in repo content (code, docs, commit messages, branch names) must resolve under the repo root. Use `<HOME>/.claude/...` or generic names for system paths. Pre-commit + commit-msg hard-block leaks; don't `--no-verify`. Detail: `skills/path-privacy/`.

3. **best_practices.md has two copies that drift.** Edit `.skill-maintainer/best_practices.md` (working copy). The PostToolUse hook mirrors to `skills/skill-maintainer/references/best_practices.md`. Editing only the bundled copy means fresh `skill-maintain init` runs in other repos pull stale rules. More: [docs/internals/gotchas.md](docs/internals/gotchas.md).

4. **Greenfield default for local DBs.** For `<HOME>/.claude/agent_state.duckdb` and readwise-reader's DuckDB, prefer `CREATE OR REPLACE VIEW` + re-init over migration bridges. Production-facing schemas (marketplace.json, published plugin contents) are the exception.

5. **Security-guidance plugin's PreToolUse hook is disabled here** via `.claude/settings.json` env `ENABLE_SECURITY_REMINDER=0`. It substring-matches benign tokens in markdown prose and false-fires on docs and session logs. If you reset settings, re-disable. Detail: [docs/internals/gotchas.md](docs/internals/gotchas.md).

6. **Four of this repo's own plugins are disabled here** via `enabledPlugins: false` in `.claude/settings.json`: `dev-conventions`, `dimensional-modeling`, `mece-decomposer`, `env-forge`. Their SessionStart hooks inject ~3,500 chars of convention text into every session, and in this repo those conventions are already stated twice — in `.claude/rules/general.md` and the user's global `CLAUDE.md`. The hooks stay in the plugins because they are the entire point for a repo with nothing written down; they are just redundant *here*. `path-privacy` and `pyright-autoconfig` remain enabled — the first enforces via PreToolUse, the second acts silently.
