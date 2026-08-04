last updated: 2026-08-04

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- At session end, update what's actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Don't bulk-update untouched files.
- `.claude/rules/` already covers language tooling (uv, bun, orjson), TDD, and doc conventions; `path-privacy`'s SessionStart hook covers path rules. Don't restate those here. (The `dimensional-modeling` and `mece-decomposer` SessionStart hooks are disabled in this repo — see invariant 6; `dev-conventions` is enabled but its blocks self-silence here via ground coverage — so `.claude/rules/` is the only copy that loads.)

## Repo invariants

These bite on the first edit if you don't know them.

1. **Plugin content change ⇒ version cascade (three files).** `plugin.json` + root `marketplace.json` + a `CHANGELOG.md` entry; plus `tools/<plugin>/pyproject.toml` and `uv lock` where those exist (the root `pyproject.toml` is a virtual workspace root with no version — never bumped). Without the bump, `marketplace update` never reaches installed users. "Plugin content" is whatever the marketplace `source` actually ships — check it before cascading: `tools/<plugin>/src/` counts when the plugin bundles that tool but not when the tool ships separately (then plugin and CLI version independently), and a skill plugin's `templates/`, `references/`, and `examples/` subdirs count, not just SKILL.md prose. **SKILL.md files are not in the cascade** — `metadata.version` and `metadata.author` are removed classes; do not re-add either. `metadata.last_verified` is written only after an actual human review, never bumped mechanically. Specimens, dates, and rationale: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

1b. **One changelog, at the repo root; a copy earns its place only if it has a consumer other than the check that confirms it is a copy.** The two-question form: **name the copy's consumer, and name what watches the pair — if either answer is "nothing", delete the copy or demote it to data the shipped mechanism cites at dispatch.** Apply it with full force to local copies of components this repo's own plugins ship (agents, skills, procedure prose): an unwatched local variant splits dogfooding from what installs run, so defects in the shipped copy stop being noticed here first. The specimens and the three shapes a legitimate pair can take: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

1c. **A rule earns its tier; re-audit the ones written for older models.** Cost is *emission*, not invocation — a hook firing on every edit and staying silent is nearly free, while `SessionStart` emits unconditionally and re-fires on resume, fork, clear and compact. Order: mechanically detectable violation → `PreToolUse` block; detectable condition → `PostToolUse` notice; neither → one ambient line pointing at a skill. Separately, upstream names a maintenance practice this repo did not have: *"instructions that worked around an older model's limitation may become overhead once a newer model handles the case on its own."* Most of this repo predates the Claude 5 generation, so when touching a rule, ask whether it is still compensating for something. Measurements, the tier test, the built-in introspection commands (do not rebuild them), and the transcript-mining traps: [docs/internals/context-cost.md](docs/internals/context-cost.md).

2. **Path-privacy is enforced via git hooks.** Every path in repo content (code, docs, commit messages, branch names) must resolve under the repo root. Use `<HOME>/.claude/...` or generic names for system paths. Pre-commit + commit-msg hard-block leaks; don't `--no-verify`. **The hooks permit an absolute path that resolves INSIDE the repo** (`/Users/<name>/<this-repo>/x`) — by design, but it still leaks your username, so write those repo-relative too. `skill-maintain test`'s whole-tree audit catches that second class; the hooks do not. Detail: `skills/path-privacy/`.

3. **best_practices.md has two copies that drift.** Edit `.skill-maintainer/best_practices.md` (working copy). The PostToolUse hook mirrors to `skills/skill-maintainer/references/best_practices.md`. Editing only the bundled copy means fresh `skill-maintain init` runs in other repos pull stale rules. More: [docs/internals/gotchas.md](docs/internals/gotchas.md).

4. **Greenfield default for local DBs.** For readwise-reader's DuckDB, prefer `CREATE OR REPLACE VIEW` + re-init over migration bridges. Production-facing schemas (marketplace.json, published plugin contents) are the exception.

5. **Security-guidance plugin's PreToolUse hook is disabled here** via `.claude/settings.json` env `ENABLE_SECURITY_REMINDER=0`. It substring-matches benign tokens in markdown prose and false-fires on docs and session logs. If you reset settings, re-disable. Detail: [docs/internals/gotchas.md](docs/internals/gotchas.md).

6. **Two of this repo's own plugins are disabled here** via `enabledPlugins: false` in `.claude/settings.json`: `dimensional-modeling`, `mece-decomposer`. (`env-forge` is deprecated, not disabled — the `renames` map in `marketplace.json` handles its removal. An `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.) Their SessionStart hooks inject ~3,500 chars of convention text into every session, and in this repo those conventions are already stated twice — in `.claude/rules/general.md` and the user's global `CLAUDE.md`. The hooks stay in the plugins because they are the entire point for a repo with nothing written down; they are just redundant *here*. `path-privacy` and `pyright-autoconfig` remain enabled — the first enforces via PreToolUse, the second acts silently. `dev-conventions` was disabled here too until 2026-08-03: 0.15.x's per-block ground coverage makes its ambient blocks silent in this repo (pinned by `test_this_repo_stays_fully_covered`), so the owner re-enabled it to get the pip/npm/lockfile enforcement hooks back at zero ambient cost. History in [docs/internals/gotchas.md](docs/internals/gotchas.md).

## Where to find what

| Working on... | Look at |
|---|---|
| Plugin authoring (structure, hooks exec form, agents, directives, bash portability) | [docs/internals/plugin-patterns.md](docs/internals/plugin-patterns.md) |
| The version cascade and what is deliberately NOT in it | [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md) |
| Where context cost actually goes; which tier a rule belongs in; built-in introspection not to rebuild | [docs/internals/context-cost.md](docs/internals/context-cost.md) |
| Maintenance commands, freshness windows, upstream drift flow | [docs/internals/maintenance.md](docs/internals/maintenance.md) |
| Repo-specific gotchas (disabled plugins, pipefail trap, best_practices duality) | [docs/internals/gotchas.md](docs/internals/gotchas.md) |
| Postmortem multi-format output (markdown + HTML, pluggable styling) — designed, NOT started | [docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) |
| The audit family, SHIPPED 2026-08-04: claim-audit (diff prose audited by execution, `skills/claim-audit/`), control-audit (census + live-fire over hooks, validators, reminders) and the adversarial-verify primitive it dispatches to (postmortem plugin); the docs are the design records | [docs/internals/claim_audit_design.md](docs/internals/claim_audit_design.md), [docs/internals/control_audit_design.md](docs/internals/control_audit_design.md) |
| Why `agent-state` was retired rather than populated — each candidate population turned out to duplicate a file, and effectiveness needs a controlled A/B, not production correlation | [docs/internals/agent_state_population.md](docs/internals/agent_state_population.md) |
| Why `gemini-bridge` is shaped the way it is — a **frozen design record** of the 2026-08-01 session and the live probing that corrected it. Historical: read the code and SKILL.md for current behaviour. Re-run `apps/gemini-bridge/scripts/probe.py` before exposing any new API parameter | [docs/internals/gemini_bridge_design.md](docs/internals/gemini_bridge_design.md) |
| The contract any second bridge should follow (return a path not a payload; stance as versioned data; files are the store). Scope is capability AND opinion; the boundary is **mutation, not execution** — an external agent harness (Antigravity, Codex) is out of scope and a different plugin. A protocol, NOT a library; no shared code exists yet | [docs/internals/foreign_capability_bridge.md](docs/internals/foreign_capability_bridge.md) |
| Why the delegation feedback layer is a report and not a loop; schema/grain/cost fixes | [docs/internals/model_routing_flywheel.md](docs/internals/model_routing_flywheel.md) |
| Gating expensive/external calls by tier (UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny) | [docs/internals/tiered_authorization.md](docs/internals/tiered_authorization.md) |
| Upstream doc changes identified but not yet absorbed | [docs/internals/upstream_drift_backlog.md](docs/internals/upstream_drift_backlog.md) |
| Why a thing is built this way (architectural worldview) | [VISION.md](VISION.md) |
| The documentation index (what survives, and why) | [docs/README.md](docs/README.md) |
| MCP orientation (start here) | [docs/mcp-ecosystem.md](docs/mcp-ecosystem.md) |
| MCP protocol | [docs/analysis/mcp_protocol_and_servers.md](docs/analysis/mcp_protocol_and_servers.md) (verified current) |
| Current upstream Claude Code docs | `skill-maintain upstream`, then `.skill-maintainer/state/pages/` (gitignored). Nothing upstream is copied into this repo |
| DuckDB schema (readwise-reader) | `apps/readwise-reader/CLAUDE.md` |
| Repo layout, plugins table, install commands | [README.md](README.md) |
| Setup from a fresh clone | [README.md](README.md) "installation" + `uv sync --all-packages` |

## State

- `.skill-maintainer/state/` — per-repo maintenance state (upstream hashes, page snapshots, `changes.jsonl` audit log; gitignored)
- Each `SKILL.md`'s `metadata.last_verified` — the date a human last reviewed that skill against its source. Never bumped mechanically; see invariant 1. Its window is `metadata.review_interval_days` (default 30), tiered 30 / 90 / 365 by how fast the source moves — except skills declaring `metadata.freshness: "cascade"` (source is in-repo code; the version cascade surfaces drift, no calendar window).

## Cross-repo

- `coderef/agentskills/` — symlink to a local clone of the Agent Skills spec + the `skills-ref` library (used here as the SKILL.md frontmatter parser; the validation gate is `skill-maintain validate` against the Claude Code schema, a superset)
- Sibling repos: `star-schema-llm-context` (storage engine / kernel), `ccutils` (client applications). The three together form a database-like component stack — see [VISION.md](VISION.md) for the design.
