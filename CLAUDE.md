last updated: 2026-08-01

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- At session end, update what's actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Don't bulk-update untouched files.
- `.claude/rules/` already covers language tooling (uv, bun, orjson), TDD, and doc conventions; `path-privacy`'s SessionStart hook covers path rules. Don't restate those here. (The `dev-conventions`, `dimensional-modeling` and `mece-decomposer` SessionStart hooks are disabled in this repo — see invariant 6 — so `.claude/rules/` is the only copy that loads.)

## Repo invariants

These bite on the first edit if you don't know them.

1. **Plugin content change ⇒ version cascade (three files).** `plugin.json` + root `marketplace.json` + a `CHANGELOG.md` entry. **Editing `tools/<plugin>/src/` counts as plugin content and triggers the cascade *when the plugin bundles that tool*** — without the bump, `marketplace update` never reaches installed users. It does **not** apply when the tool ships separately: `skill-maintainer`'s marketplace source is `./skills/skill-maintainer`, which carries no code from `tools/skill-maintainer`, so a CLI change reaches nobody through a plugin bump and the two version independently (plugin 0.17.0 / CLI 0.19.0 as of 2026-08-01, correctly). Check what the marketplace `source` actually contains before cascading. The same holds for a skill plugin's shipped subdirs: editing `skills/<plugin>/**/templates/`, `.../references/`, or `.../examples/` is a plugin-content change and triggers the cascade, not just SKILL.md prose edits (this session's explainer-video 0.5.1→0.6.0 was mostly template + reference work). Skill plugins here carry no pyproject/uv.lock, so their cascade is exactly the three: plugin.json + marketplace.json + CHANGELOG. Plus `tools/<plugin>/pyproject.toml` and `uv lock` where those exist; the root `pyproject.toml` is a virtual workspace root with no version, so it is never bumped. **SKILL.md files are not in the cascade** — `metadata.version` was removed from every SKILL.md on 2026-07-21 because it duplicated `plugin.json` and its only reader was the check confirming the duplicate matched. Do not re-add it. `metadata.author` went the same way on 2026-07-24 (all 30 remaining instances swept): the whole SKILL.md, frontmatter included, loads into context on activation, so attribution lives in `plugin.json` and the plugin README, never in the skill file. Do not re-add that either. `metadata.last_verified` is also out: it asserts a human reviewed the skill, which a version bump does not establish — write it only after an actual review. Detail: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

1b. **One changelog, at the repo root.** No unit gets its own `CHANGELOG.md` — `apps/readwise-reader` was the only first-party exception and it drifted five versions behind its own `pyproject.toml` before anyone noticed (removed 2026-07-26). The general rule this came from, and the one to apply to the next duplicated field: **a copy earns its place only if it has a consumer other than the check that confirms it is a copy.** `plugin.json` and `marketplace.json` versions each have a real consumer and are machine-checked against one another; SKILL.md's `metadata.version` and per-unit changelog headings had none, and both are gone.

1c. **A rule earns its tier; re-audit the ones written for older models.** Cost is *emission*, not invocation — a hook firing on every edit and staying silent is nearly free, while `SessionStart` emits unconditionally and re-fires on resume, fork, clear and compact. Order: mechanically detectable violation → `PreToolUse` block; detectable condition → `PostToolUse` notice; neither → one ambient line pointing at a skill. Separately, upstream names a maintenance practice this repo did not have: *"instructions that worked around an older model's limitation may become overhead once a newer model handles the case on its own."* Most of this repo predates the Claude 5 generation, so when touching a rule, ask whether it is still compensating for something. Measurements, the tier test, the built-in introspection commands (do not rebuild them), and the transcript-mining traps: [docs/internals/context-cost.md](docs/internals/context-cost.md).

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
| Where context cost actually goes; which tier a rule belongs in; built-in introspection not to rebuild | [docs/internals/context-cost.md](docs/internals/context-cost.md) |
| Maintenance commands, freshness windows, upstream drift flow | [docs/internals/maintenance.md](docs/internals/maintenance.md) |
| Repo-specific gotchas (disabled plugins, pipefail trap, best_practices duality) | [docs/internals/gotchas.md](docs/internals/gotchas.md) |
| Postmortem multi-format output (markdown + HTML, pluggable styling) — designed, NOT started | [docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) |
| Why `agent-state` is empty, what would populate it, and the populate-or-retire decision — designed, NOT started | [docs/internals/agent_state_population.md](docs/internals/agent_state_population.md) |
| Gemini multimodal bridge — API facts established by live probing (every static source was wrong about something), recipes-as-data, why storage is irreversible. Shipped as `apps/gemini-bridge`; re-run `internal/scratch/gemini_probe.py` before exposing any new API parameter | [docs/internals/gemini_bridge_design.md](docs/internals/gemini_bridge_design.md) |
| The contract any second foreign-capability bridge should follow (return a path not a payload; stance as versioned data; files are the store) — a protocol, NOT a library; no shared code exists yet | [docs/internals/foreign_capability_bridge.md](docs/internals/foreign_capability_bridge.md) |
| Why the delegation feedback layer is a report and not a loop; schema/grain/cost fixes | [docs/internals/model_routing_flywheel.md](docs/internals/model_routing_flywheel.md) |
| Gating expensive/external calls by tier (UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny) | [docs/internals/tiered_authorization.md](docs/internals/tiered_authorization.md) |
| Upstream doc changes identified but not yet absorbed | [docs/internals/upstream_drift_backlog.md](docs/internals/upstream_drift_backlog.md) |
| Why a thing is built this way (architectural worldview) | [VISION.md](VISION.md) |
| The documentation index (what survives, and why) | [docs/README.md](docs/README.md) |
| MCP orientation (start here) | [docs/mcp-ecosystem.md](docs/mcp-ecosystem.md) |
| MCP protocol | [docs/analysis/mcp_protocol_and_servers.md](docs/analysis/mcp_protocol_and_servers.md) (verified current) |
| Current upstream Claude Code docs | `skill-maintain upstream`, then `.skill-maintainer/state/pages/` (gitignored). Nothing upstream is copied into this repo |
| DuckDB schema (agent-state, readwise-reader) | `tools/agent-state/README.md`, `apps/readwise-reader/CLAUDE.md` |
| Repo layout, plugins table, install commands | [README.md](README.md) |
| Setup from a fresh clone | [README.md](README.md) "installation" + `uv sync --all-packages` |

## State

- `.skill-maintainer/state/` — per-repo maintenance state (upstream hashes, page snapshots, `changes.jsonl` audit log; gitignored)
- `<HOME>/.claude/agent_state.duckdb` — global DuckDB for run audit and state tracking (schema in `tools/agent-state/`)
- Each `SKILL.md`'s `metadata.last_verified` — the date a human last reviewed that skill against its source. Never bumped mechanically; see invariant 1. Its window is `metadata.review_interval_days` (default 30), tiered 30 / 90 / 365 by how fast the source moves.

## Cross-repo

- `coderef/agentskills/` — symlink to a local clone of the Agent Skills spec + the `skills-ref` library (used here as the SKILL.md frontmatter parser; the validation gate is `skill-maintain validate` against the Claude Code schema, a superset)
- Sibling repos: `star-schema-llm-context` (storage engine / kernel), `ccutils` (client applications). The three together form a database-like component stack — see [VISION.md](VISION.md) for the design.
