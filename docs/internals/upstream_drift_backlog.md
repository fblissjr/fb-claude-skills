last updated: 2026-09-24

# Upstream drift backlog

Upstream changes identified but **not** yet absorbed into
`skills/skill-maintainer/references/best_practices.md`, kept so the remainder is
visible instead of quietly lost. Anything that made the guidance *wrong* is
applied when found; this file holds what was seen and deliberately left.

Re-derive with: `skill-maintain upstream`, then diff
`.skill-maintainer/state/pages/*.md` against the previous snapshot.

## Pending follow-ups from the 2026-09-21 refresh

- **Two skills over the 5,000-token re-attach cut**, by `claude plugin details`:
  `heylook-provider` (~7.6k; `skill-maintain test` reports it over) and
  `path-privacy` (~5.7k; reported unverified, because its character count sits
  inside the estimator's band). For heylook, what a compacted session loses is
  most of "Operational shape", the "References" map and "Done means". The fix
  is to move the last two to the top and "Operational shape" into
  `references/`. Each is its own plugin with its own version bump.
- **Marketplace descriptions after push.** Entries no longer carry a
  `description`; once the marketplace updates, confirm with `claude plugin
  details <name>` that the text shown is `plugin.json`'s.

## Seen on 2026-09-21, deliberately not absorbed

- **Channels** (`channels`, `channels-reference`): the silent failures a channel
  author hits — hyphenated meta keys dropped, unregistered sessions dropping
  events with no error, the pre-v2.1.234 `false`-as-declared permission
  capability, sender gating on the sender and not the room. Absorb, and track
  both pages, when this repo ships a channel. The one channel fact that bears on
  MCP servers generally (legacy handshake only) is already in the file.
- **Code-intelligence plugins** (`.lsp.json`): the first server registered for an
  extension wins and the others never start; the binary is not bundled; LSP
  starts only in a trusted workspace. Absorb when an LSP plugin ships.
- **Plugin hints, relevance and dependencies**: hints outside the official
  marketplace are dropped; relevance needs an administrator's
  `pluginSuggestionMarketplaces`; dependency ranges and `claude plugin tag`.
  Revisit at this repo's first `dependencies` entry.
- **Large-codebase mechanisms that are repo configuration, not plugin
  authoring**: `claudeMdExcludes`, `worktree.sparsePaths` itself, `Read` deny
  rules. A plugin's `settings.json` supports only `agent` and
  `subagentStatusLine`, so none of them is shippable.

## Identified 2026-07-26, still open

**Hook capabilities we do not use**

- `PreToolUse` can return `updatedInput`, rewriting a tool's arguments before it
  runs rather than only allowing or denying. Directly relevant to `path-privacy`:
  a leaking path could be *corrected* instead of blocked. Weigh against surprise
  — silently rewriting what the model asked for is its own hazard.

**Plugin mechanics**

- Plugins can ship `bin/`, added to the Bash tool's PATH as bare commands (not
  allowed for organization-distributed plugins).

## Not yet absorbed

### hooks

- `SessionStart` gained `reloadSkills`, `initialUserMessage`, `watchPaths`. `reloadSkills` matters for hook-installed skills going live in the same session
- `Notification` gained `agent_needs_input`, `agent_completed`; `StopFailure` gained `overloaded`, `model_not_found`
- Tool-name matcher separator: `,` now interchangeable with `|`
- Identical handlers are deduplicated (command+args, or URL)
- Multi-hook merge: all matching hooks run in parallel to completion; precedence `deny` > `defer` > `ask` > `allow`
- Command hooks have no controlling terminal (macOS/Linux, v2.1.139+)

### skills

- Re-invoking an identical skill appends an "already loaded" note rather than a second copy (v2.1.202+)
- Name clashes stay available under a directory-qualified name (`/apps/web:deploy`)
- Skill dirs may be symlinks (followed, de-duplicated)
- Skill stacking (`/a /b 123`): first skill plus up to five more

### memory

- MEMORY.md limit strips frontmatter and block HTML comments before measuring (v2.1.211+)
- Auto memory scope is per-repository, shared across worktrees (was per working tree)
- CLAUDE.md import parsing skips code spans and fenced blocks
- Invalid glob bracket expressions now match nothing instead of breaking Read (v2.1.207+)

### plugins / marketplace

- `experimental.themes` / `experimental.monitors` — top-level still works but warns; a future release will require the nested form
- `claude plugin init`, `@skills-dir` plugins, `--plugin-url`, `.zip` for `--plugin-dir`
- A plugin with a root `SKILL.md` and no `skills/` dir auto-loads as a single-skill plugin
- `skills` path field **adds to** the default scan; `commands`/`agents`/`outputStyles` still **replace**
- Symlinks within the same marketplace are dereferenced and copied — a supported way to share files, but only for marketplace installs
- Orphaned cache versions pruned after 14 days, not 7

## Already applied (do not redo)

**2026-09-21 refresh** (`skill-maintainer` 0.30.0, `skill-maintain` 0.37.0):

- Hook timeout behaviour for every event, `PreModelSwitch` failing closed, the per-type defaults and the `MessageDisplay` / model-switch lowerings
- JSON output read on every exit code; exit 2 with malformed JSON superseded by the parse-failure rules; `PermissionRequest` ignoring exit 2; `Setup` ignoring exit and stderr
- `Stop` hooks and `stop_hook_active`, overridden after 8 consecutive blocks (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`)
- Hook types per event (`prompt`/`agent` only on 13 events; `SessionStart` and `Setup` take `command` and `mcp_tool`)
- Plugin-bundled MCP scoped names in matchers and `if`; trust keyed on `source`
- The `SessionStart` `fork` matcher, folded into the tier rule
- `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_EFFORT}`, substitution inside `allowed-tools` (now including `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}`), and the `!` line-start and single-pass rules
- `skillOverrides` with its plugin-skill exception; `disable-model-invocation` as a listing lever
- `paths`, `context: fork` (and that it is not a conversation fork), `disable-model-invocation` blocking subagent preloading and scheduled auto-run
- `${CLAUDE_PLUGIN_DATA}` as persistent state
- The `skill-creator` harness, now beside `claude plugin eval` as the `behaviour eval` gate
- Import depth four hops; `ln -s AGENTS.md CLAUDE.md` and direct `AGENTS.md` reading
- `claude plugin validate --strict` (now per plugin directory in the pre-commit template) and `claude plugin details`
- Re-auditing rules written for older models, now in `maintaining this file` with the every-release trigger

**Earlier**

- `allowed-tools` grants pre-approval, does not restrict; `disallowed-tools` restricts
- `plugin.json` requires only `name` upstream — our five-field rule is a repo convention
- skill-listing budget: 8,000-char fallback gone; `skillListingBudgetFraction` / `skillListingMaxDescChars`
- hook `type` gained `mcp_tool`
- `if` never runs on non-tool events (not "silently ignored"); `FileChanged` is not a tool event; `PostToolUseFailure` is
- exit 0 = no decision reported, not success; PreToolUse still goes through normal permission flow
- `once: true` is NOT honored in agent frontmatter
- frontmatter allow-list gained `disallowed-tools`, `arguments`
- `args` / exec form for hooks — all hook entries converted (2026-07-21)
- Four surface differences, absorbed 2026-08-07
- `renames` added to `marketplace.json` (2026-07-21, env-forge deprecation). Append-only history

## Missing: a consistency check

A calendar window and `check_version_alignment` both detect drift over
time. Nothing detects a document that was wrong on the day it was written.
The 2026-09-21 refresh found three such rules in `best_practices.md`, each
contradicted by the page it cited in both snapshots.

Where a doc in this repo states a numeric threshold governing an artifact, the
two should be compared. See "Designing a new check" in
[maintenance.md](maintenance.md) for why the check must be silent outside its
confident region rather than warning.

## Convention worth reconsidering

**~~`last_verified` should probably leave the version cascade.~~ CLOSED
2026-08-29 — it left the repo.** The item proposed either dropping
`last_verified` from the cascade or splitting it into `last_changed`
(mechanical) and `last_verified` (a human claim). Neither was taken: the owner
directed removal of the calendar review rule altogether, so the field, its
interval, its cascade exemption, and the gate that read them are all gone. The
original argument is preserved because it is the reasoning the removal rests
on — a version bump means "these bytes changed" while a review date means
"someone checked this is still correct", and converting eight plugins to
exec-form hooks on 2026-07-21 would have marked 17 skills freshly verified on
no evidence, dropping staleness failures 11 -> 5 without anyone reading a
line.

## Repo gaps worth deciding on

- `displayName` — unused across all plugins. `name` is the stable install key; `displayName` is the only way to relabel the `/plugin` picker without breaking installs. If adopted, set it in `plugin.json` only: an entry-level value overrides it
- `defaultEnabled: false` — candidates are the SessionStart-hook plugins that inject context every session. Would make ambient cost opt-in. An entry-level value overrides the manifest's, and a user's setting or a dependency requirement overrides both
- Marketplace top-level `description` — we only set `metadata.description`; the validator warns on the top-level field
