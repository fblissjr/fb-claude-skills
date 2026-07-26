last updated: 2026-07-26

# Upstream drift backlog

All nine tracked Claude Code doc pages changed between the 2026-05-04 snapshot
and 2026-07-21 — `hooks` alone by +807/-312 lines, `plugins-reference` by
+380/-106. The corrections that made our own guidance *wrong* were applied to
`.skill-maintainer/best_practices.md` on 2026-07-21. This file tracks what was
identified but **not** yet absorbed, so the remainder is visible instead of
quietly lost.

Re-derive with: `skill-maintain upstream`, then diff
`.skill-maintainer/state/pages/*.md` against the previous snapshot.

## Identified 2026-07-26, not yet absorbed

From a three-agent read of `skills`, `sub-agents`, `plugins-reference`, `hooks`,
`hooks-guide`, `debug-your-config`, `best-practices`, `large-codebases`,
`memory`, and the Claude 5 context-engineering post. Everything that changed a
decision was applied at the time; this is the remainder, recorded so it is not
rediscovered expensively.

**Hook capabilities we do not use**

- `PreToolUse` can return `updatedInput`, rewriting a tool's arguments before it
  runs rather than only allowing or denying. Directly relevant to `path-privacy`:
  a leaking path could be *corrected* instead of blocked, turning a failed call
  into a silent fix. Weigh against surprise — silently rewriting what the model
  asked for is its own hazard.
- Hook `type` is not only `command`: `prompt` (LLM-evaluated, Haiku by default),
  `agent` (experimental), and `http` (POSTs to an endpoint) exist. An entire
  category we have never considered; a `prompt` hook could judge things a shell
  script cannot pattern-match.
- Hook output — `additionalContext`, `systemMessage`, plain stdout, exit-2
  stderr — is capped at **10,000 characters**, then spilled to a file and
  replaced with a preview plus path. Our `ruff-diagnostics` caps its own output
  at 12 findings, which keeps it clear of this, but nothing enforces that.
- `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` and an 8-consecutive-block cap on `Stop`.

**Skill frontmatter we do not use**

- `paths`: glob patterns limiting a skill's auto-activation to matching files.
  This is the targeted alternative to a detection-gated SessionStart hook, and
  would have been the right shape for `dimensional-modeling` had we kept a
  trigger at all.
- `context: fork` runs a skill in a forked subagent, defaulting to background
  since v2.1.218 — relevant to anything long-running we currently do inline.
- `disable-model-invocation` also blocks subagent preloading and scheduled-task
  auto-run, not just the `/` menu.

**Plugin mechanics**

- `${CLAUDE_PLUGIN_DATA}` is a persistent per-plugin directory that survives
  updates, unlike `${CLAUDE_PLUGIN_ROOT}` which changes on every update. The
  documented pattern is diffing a bundled manifest against a copy there to
  detect dependency changes across versions.
- Plugins can ship `bin/`, added to the Bash tool's PATH as bare commands.

**Practice, not mechanics**

- Re-audit rules written for older models. Now invariant 1c, but see the note in
  `.skill-maintainer/best_practices.md` — stating a practice is not the same as
  triggering it, and this one still has no recurring prompt beyond that entry.

## Already applied (do not redo)

- `allowed-tools` grants pre-approval, does not restrict; `disallowed-tools` restricts
- `plugin.json` requires only `name` upstream — our five-field rule is a repo convention
- skill-listing budget: 8,000-char fallback gone; `skillListingBudgetFraction` / `skillListingMaxDescChars`
- hook `type` gained `mcp_tool`
- `if` never runs on non-tool events (not "silently ignored"); `FileChanged` is not a tool event; `PostToolUseFailure` is
- exit 0 = no decision reported, not success; PreToolUse still goes through normal permission flow
- `once: true` is NOT honored in agent frontmatter
- frontmatter allow-list gained `disallowed-tools`, `arguments`
- new `## agent authoring` section
- `args` / exec form for hooks — all 10 hook entries across 8 plugins converted (2026-07-21)

## Not yet absorbed

### hooks

- New event `MessageDisplay` (display-only, no matcher, cannot block)
- Per-type timeout defaults: 600s command/http/mcp_tool, 30s prompt, 60s agent; `UserPromptSubmit` lowers to 30s, `MessageDisplay` to 10s
- `SessionStart` gained `reloadSkills`, `initialUserMessage`, `watchPaths`. `reloadSkills` matters for hook-installed skills going live in the same session
- `SessionStart` matcher gained `fork`; `Notification` gained `agent_needs_input`, `agent_completed`; `StopFailure` gained `overloaded`, `model_not_found`
- Tool-name matcher separator: `,` now interchangeable with `|`
- MCP matcher exact-match set now includes hyphens; plugin-bundled MCP tools need the scoped form `mcp__plugin_<plugin>_<server>__<tool>`
- Identical handlers are deduplicated (command+args, or URL)
- Exit 2 with malformed JSON still blocks (v2.1.214+)
- `Stop` hooks force-overridden after 8 consecutive blocks (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`)
- Multi-hook merge: all matching hooks run in parallel to completion; precedence `deny` > `defer` > `ask` > `allow`
- Command hooks have no controlling terminal (macOS/Linux, v2.1.139+)
- `${user_config.*}` is now **rejected** in shell-form hook commands, monitor commands, and MCP `headersHelper`; read `CLAUDE_CODE_PLUGIN_OPTION_<KEY>` or use exec form (documented in best_practices; no repo hook uses `user_config` today)
- `shell` default may be `powershell` on Windows without Git Bash

### skills

- `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_EFFORT}` substitutions
- `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PROJECT_DIR}` are substituted inside `allowed-tools` Bash rules — the supported way to run a bundled script without a prompt
- Inline `` !`cmd` `` only fires at line start or after whitespace; substitution runs once and output is not re-scanned
- Re-invoking an identical skill appends an "already loaded" note rather than a second copy (v2.1.202+)
- `skillOverrides` (`on` / `name-only` / `user-invocable-only` / `off`), `disableBundledSkills`
- `context: fork` with `agent: Explore` or `agent: Plan` does NOT load CLAUDE.md; other agent types do
- Project skills load from `.claude/skills/` in every parent dir up to repo root
- Name clashes stay available under a directory-qualified name (`/apps/web:deploy`)
- Skill dirs may be symlinks (followed, de-duplicated)
- `--add-dir` loads `.claude/skills/`; the `permissions.additionalDirectories` setting does not
- Cowork/cloud sessions do not read the user-scope skills directory
- Skill stacking (`/a /b 123`): first skill plus up to five more
- `skill-creator` plugin provides a documented with/without-skill eval harness — a concrete method for our unmeasured "quality signals" section

### memory

- CLAUDE.md recursive import depth 5 → **4** hops
- MEMORY.md limit strips frontmatter and block HTML comments before measuring (v2.1.211+)
- Auto memory scope is per-repository, shared across worktrees (was per working tree)
- CLAUDE.md import parsing skips code spans and fenced blocks
- `ln -s AGENTS.md CLAUDE.md` is a documented alternative to `@AGENTS.md`
- Invalid glob bracket expressions now match nothing instead of breaking Read (v2.1.207+)

### plugins / marketplace

- `experimental.themes` / `experimental.monitors` — top-level still works but warns; a future release will require the nested form
- `claude plugin validate --strict` — promotes unknown-field warnings to errors. Good CI gate for this repo
- `claude plugin details <name>` — first-party component inventory + token cost; overlaps skill-maintainer's `measure`
- `claude plugin init`, `@skills-dir` plugins, `--plugin-url`, `.zip` for `--plugin-dir`
- A plugin with a root `SKILL.md` and no `skills/` dir auto-loads as a single-skill plugin
- `skills` path field **adds to** the default scan; `commands`/`agents`/`outputStyles` still **replace**
- Symlinks within the same marketplace are dereferenced and copied — a supported way to share files, but only for marketplace installs. Relevant to invariant 3 (the `best_practices.md` mirror)
- Orphaned cache versions pruned after 14 days, not 7

## Missing: a consistency check

`review_interval_days` and `check_version_alignment` both detect drift over
time. Nothing detects a document that was wrong on the day it was written.

Concrete instance was in a plugin since retired from this repo; the general point stands.

Where a doc in this repo states a numeric threshold governing an artifact, the
two should be compared. See "Designing a new check" in
[maintenance.md](maintenance.md) for why the check must be silent outside its
confident region rather than warning.

## Convention worth reconsidering

**`last_verified` should probably leave the version cascade.** Invariant 1 bumps
`metadata.version` and `metadata.last_verified` together. But a version bump
means "these bytes changed" while `last_verified` means "someone checked this is
still correct", and those are different claims. Converting eight plugins to
exec-form hooks on 2026-07-21 would have marked 17 skills freshly verified on no
evidence, dropping staleness failures 11 -> 5 without anyone reading a line. The
dates were restored by hand. Either drop `last_verified` from the cascade, or
split it into `last_changed` (mechanical) and `last_verified` (a human claim).

## Repo gaps worth deciding on

- `displayName` — unused across all 19 plugins. `name` is the stable install key; `displayName` is the only way to relabel the `/plugin` picker without breaking installs
- ~~`renames` — absent from `marketplace.json`.~~ **Resolved 2026-07-21**: added as `"renames": {"env-forge": null}` when env-forge was deprecated. Append-only history
- `defaultEnabled: false` — candidates are the SessionStart-hook plugins that inject context every session (`dev-conventions`, `dimensional-modeling`, `mece-decomposer`, `pyright-autoconfig`). Would make ambient cost opt-in
- Marketplace top-level `description` — we only set `metadata.description`; the validator warns on the top-level field
