last updated: 2026-08-17

# fb-claude-skills

> **Read [VISION.md](VISION.md) first.** Skills are retrieval. High precision is the constraint, high recall is the goal, and every instruction spends from two budgets: context and friction.

Plugin marketplace and extension system for Claude Code. Bundles skills, agents, hooks, MCP servers, and MCP Apps into installable plugins. Property-driven maintenance via git hooks, Claude Code hooks, and on-demand CLI tools.

## Working agreements

- At session end, update what is actually relevant: `internal/log/log_YYYY-MM-DD.md`, this file (only if a hub-level rule changed), READMEs of impacted units, `pyproject.toml` of impacted units. Do not bulk-update untouched files.
- `.claude/rules/` already covers language tooling (uv, bun, orjson), TDD, and doc conventions. `path-privacy`'s SessionStart hook covers path rules. Do not restate any of it here.
- **Do not hedge skill bodies for hypothetical installers.** That these are one person's house style is stated once in `README.md` and `VISION.md`. A per-instance qualifier ("this is the owner's preference, not a universal layout") loads on every activation and tells the reader nothing the front door did not. State the rule flatly; put the stance in the plugin README where it costs nothing per activation.

## Repo invariants

These bite on the first edit if you do not know them. Numbering is stable: other
documents cite these by number, so entries are removed rather than renumbered.

**1. Plugin content change ⇒ version cascade.**

- `plugin.json` + root `marketplace.json` + a `CHANGELOG.md` entry.
- Plus `tools/<plugin>/pyproject.toml` where it exists, but only when the CLI ships *with* the plugin. Read the marketplace `source` first: if it excludes `tools/`, plugin and CLI version independently, and setting them equal is often a downgrade.
- The root `pyproject.toml` is a virtual workspace root with no version. Never bumped.
- "Plugin content" is whatever the `source` ships, minus what has no runtime effect for an installer. A plugin's own `CLAUDE.md` ships and is inert, so it is outside the cascade. A `SKILL.md` body, a `references/` file a skill reads, and a hook script are all inside it.
- **`SKILL.md` frontmatter is not in the cascade.** `metadata.version` and `metadata.author` are removed classes; never re-add them. `metadata.last_verified` is written only after an actual human review, never bumped mechanically.
- Without the bump, `marketplace update` never reaches installed users.
- Detail: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

**1b. One changelog, at the repo root; a copy earns its place only if something other than the check confirming it is a copy reads it.**

- Two questions: name the copy's consumer, and name what watches the pair. If either answer is "nothing", delete the copy, or demote it to data the shipped mechanism cites at dispatch.
- Apply it hardest to local copies of what this repo's own plugins ship. An unwatched local variant splits dogfooding from what installs actually run, so defects in the shipped copy stop being noticed here first.
- Detail: [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md).

**1c. A rule earns its tier, and rules written for older models get re-audited.**

- Cost is *emission*, not invocation. A hook firing on every edit and staying silent is nearly free; `SessionStart` emits unconditionally and re-fires on resume, fork, clear, and compact.
- Tier order: mechanically detectable violation → a `PreToolUse` block; detectable condition → a `PostToolUse` notice; neither → one ambient line pointing at a skill.
- When touching a rule, ask whether it is still compensating for a model limitation that no longer exists. Most of this repo predates the Claude 5 generation.
- **Do not rebuild the built-in introspection.** `/doctor` reports skill-listing cost and proposes CLAUDE.md trims; `claude plugin details <name>` reports per-plugin always-on versus on-invoke; `/context` shows what occupies the window. A hand-rolled substitute lost to the built-in on 2026-08-13 and produced a wrong number.
- Detail: [docs/internals/context-cost.md](docs/internals/context-cost.md).

**2. Path privacy is enforced by git hooks.**

- Every path in repo content — code, docs, commit messages, branch names — must resolve under the repo root. Use `<HOME>/.claude/...` or a generic name for system paths.
- Pre-commit and commit-msg hard-block leaks. Never `--no-verify`.
- The hooks permit an absolute path that resolves *inside* the repo. That is by design, but it still leaks a username, so write those repo-relative too. `skill-maintain test`'s whole-tree audit catches that second class; the hooks do not.
- Detail: `skills/path-privacy/`.

**3. `best_practices.md` is shipped plugin content, and there is one copy.**

- Edit `skills/skill-maintainer/references/best_practices.md`. It is what `/maintain` reads here and in every installed repo.
- `init` writes no local copy, and `best_practices_file()` falls back to the bundled one unless a repo has deliberately taken its own. So this repo dogfoods exactly what installs get.
- Editing it cascades a version bump like any plugin content.

## Where to find what

| Working on... | Look at |
|---|---|
| Plugin authoring (structure, hooks exec form, agents, directives, bash portability) | [docs/internals/plugin-patterns.md](docs/internals/plugin-patterns.md) |
| The version cascade and what is deliberately NOT in it | [docs/internals/plugin-versioning.md](docs/internals/plugin-versioning.md) |
| Where context cost actually goes; which tier a rule belongs in; built-in introspection not to rebuild | [docs/internals/context-cost.md](docs/internals/context-cost.md) |
| Maintenance commands, freshness windows, upstream drift flow | [docs/internals/maintenance.md](docs/internals/maintenance.md) |
| Whether to continue, clear, hand off, delegate, or compact at a phase boundary | [docs/internals/phase_boundaries.md](docs/internals/phase_boundaries.md) |
| Repo-specific gotchas: the security-guidance hook disabled here, the retired plugin disables and the `renames` caution, pipefail trap, path-privacy edges | [docs/internals/gotchas.md](docs/internals/gotchas.md) |
| Postmortem multi-format output (markdown + HTML, pluggable styling) — designed, NOT started | [docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) |
| The audit family, SHIPPED 2026-08-04: claim-audit (diff prose audited by execution, `skills/claim-audit/`), control-audit (census + live-fire over hooks, validators, reminders) and the adversarial-verify primitive it dispatches to (postmortem plugin); the docs are the design records, and a companion records what was specified and deliberately **not** built, with the trigger that reopens each and the tripwire governing new proposals | [docs/internals/claim_audit_design.md](docs/internals/claim_audit_design.md), [docs/internals/control_audit_design.md](docs/internals/control_audit_design.md), [docs/internals/audit_family_holds.md](docs/internals/audit_family_holds.md) |
| What this repo concluded from finished work — dated retrospectives, tracked and public since 2026-08-17 (`.postmortem.json` resolves the directory; the page is the frame and evidence standard, never a listing) | [docs/postmortems/README.md](docs/postmortems/README.md) |
| Why `agent-state` was retired rather than populated — each candidate population turned out to duplicate a file, and effectiveness needs a controlled A/B, not production correlation | [docs/internals/agent_state_population.md](docs/internals/agent_state_population.md) |
| Why `gemini-bridge` is shaped the way it is — a **frozen design record** of the 2026-08-01 session and the live probing that corrected it. Historical: read the code and SKILL.md for current behaviour. Re-run `apps/gemini-bridge/scripts/probe.py` before exposing any new API parameter | [docs/internals/gemini_bridge_design.md](docs/internals/gemini_bridge_design.md) |
| The contract any second bridge should follow (return a path not a payload; stance as versioned data; files are the store). Scope is capability AND opinion; the boundary is **mutation, not execution** — an external agent harness (Antigravity, Codex) is out of scope and a different plugin. A protocol, NOT a library; no shared code exists yet | [docs/internals/foreign_capability_bridge.md](docs/internals/foreign_capability_bridge.md) |
| Why the delegation feedback layer is a report and not a loop; schema/grain/cost fixes | [docs/internals/model_routing_flywheel.md](docs/internals/model_routing_flywheel.md) |
| Gating expensive/external calls by tier (UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny) | [docs/internals/tiered_authorization.md](docs/internals/tiered_authorization.md) |
| Upstream doc changes identified but not yet absorbed | [docs/internals/upstream_drift_backlog.md](docs/internals/upstream_drift_backlog.md) |
| Retrieval principles: context vs friction, progressive disclosure, what reopens a practice | [VISION.md](VISION.md) |
| Why a thing is built this way (agent topology, model tiering, harness coupling, state substrate) | [docs/internals/architecture.md](docs/internals/architecture.md) |
| The documentation index (what survives, and why) | [docs/README.md](docs/README.md) |
| Current upstream Claude Code docs | `skill-maintain upstream`, then `.skill-maintainer/state/pages/` (gitignored). Nothing upstream is copied into this repo |
| DuckDB schema and conventions (readwise-reader) | `apps/readwise-reader/CLAUDE.md` |
| Repo layout, plugins table, install commands | [README.md](README.md) |
| Setup from a fresh clone | [README.md](README.md) "installation" + `uv sync --all-packages` |

## State

- `.skill-maintainer/state/` — per-repo maintenance state (upstream hashes, page snapshots, `changes.jsonl` audit log; gitignored).
- Each `SKILL.md`'s `metadata.last_verified` — the date a human last reviewed that skill against its source. Never bumped mechanically; see invariant 1. Its window is `metadata.review_interval_days` (default 30), tiered 30 / 90 / 365 by how fast the source moves. Skills declaring `metadata.freshness: "cascade"` are exempt: their source is in-repo code, so the version cascade surfaces drift and no calendar window applies.

## Cross-repo

- `coderef/agentskills/` — symlink to a local clone of the Agent Skills spec plus the `skills-ref` library, used here as the SKILL.md frontmatter parser. The validation gate is `skill-maintain validate` against the Claude Code schema, a superset.
- Sibling repos: `star-schema-llm-context` (storage engine / kernel), `ccutils` (client applications). The three together form a database-like component stack — see [docs/internals/architecture.md](docs/internals/architecture.md) for the design.
