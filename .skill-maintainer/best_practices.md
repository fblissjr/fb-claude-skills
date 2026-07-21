last updated: 2026-07-21

# best practices checklist

Machine-parseable best practices extracted from the Anthropic skills guide (PDF), official Claude Code docs, Agent Skills spec, and this repo's design principles (see `VISION.md`). Used by skill-maintainer scripts and the test suite to validate skills and detect drift.

## context hygiene

These checks enforce the retrieval principles in `VISION.md`. The context window is attention, not memory. Every loaded item competes for the model's focus.

### token budget

<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->

Budget thresholds apply to SKILL.md only (always-loaded when skill triggers). Reference files (`references/`, other `.md`) are on-demand and tracked separately -- they do not count against the budget. This prevents penalizing skills for having thorough reference material, which is exactly what progressive disclosure encourages.

- [ ] SKILL.md under 4,000 tokens (2% of 200k context window). Estimation: chars / 4
- [ ] SKILL.md under 8,000 tokens (hard ceiling -- above this degrades attention on other context)
- [ ] SKILL.md body under 500 lines
- [ ] Heavy reference material in `references/` directory, not inline in SKILL.md
- [ ] Reference tokens tracked and reported but do not trigger budget warnings
- [ ] Token estimation is approximate (chars / 4). Real tokenization varies by content type. Treat as a budget heuristic, not exact measurement
- [ ] On auto-compaction, only the first 5,000 tokens of each re-attached skill are kept; all re-attached skills share a combined 25,000-token budget. SKILL.md over ~5,000 tokens gets truncated when it survives compaction

### description precision

<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->

Descriptions are reverse queries. They determine when a skill loads. Vague descriptions cause overtriggering (low precision). Missing trigger phrases cause undertriggering (low recall).

- [ ] Description includes WHAT the skill does (action verbs: handles, generates, validates, designs)
- [ ] Description includes WHEN to use it (trigger phrases: "use when user says...", "when the user wants to...")
- [ ] Combined `description` + `when_to_use` truncated at 1,536 characters in the skill listing. Front-load the core use case so it survives truncation
- [ ] Description is specific enough to avoid matching unrelated queries
- [ ] Description includes negative scope if needed ("do NOT use for...")
- [ ] No duplicate or near-duplicate descriptions across skills (causes ambiguous routing)

### always-loaded context

<!-- source: https://code.claude.com/docs/en/memory | last_verified: 2026-04-19 -->
<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->

Everything in this list loads on every session. Each line is a fixed cost.

- [ ] CLAUDE.md: only operational instructions, no reference material
- [ ] `.claude/rules/`: unconditional rules are minimal; use `paths` frontmatter to scope rules that don't apply everywhere
- [ ] Skill descriptions (all installed): each must justify its presence in the 1% budget
- [ ] `settings.json`: no ambient hooks that fire on high-frequency events without documented justification
- [ ] Auto-memory `MEMORY.md`: under 200 lines OR 25KB, whichever comes first -- content past the cap is not loaded at session start. No session-specific or stale entries. Detailed topic files sit beside `MEMORY.md` and load on demand
- [ ] If the repo has an `AGENTS.md`, the project `CLAUDE.md` should `@AGENTS.md` import it rather than duplicating content. Claude Code does not read `AGENTS.md` directly
- [ ] `disableSkillShellExecution: true` in settings disables `` !`cmd` `` preprocessing in user/project/plugin/add-dir skills. Bundled/managed skills unaffected. Use when distributing skills where shell preprocessing is not safe

### hooks

<!-- source: https://code.claude.com/docs/en/hooks | last_verified: 2026-04-19 -->
<!-- source: https://code.claude.com/docs/en/hooks-guide | last_verified: 2026-04-19 -->

- [ ] No hooks that fire on every tool call, file read, or other high-frequency event without documented justification
- [ ] Hook `type` is one of: `command`, `http`, `mcp_tool`, `prompt`, `agent`
- [ ] Hook `timeout` is in **seconds**, not milliseconds. `3000` is fifty minutes. The upstream default is 600 for `command`, `http`, `mcp_tool`
- [ ] What a **command** hook does when it times out is NOT documented. The only two timeout behaviours stated on the hooks page are the HTTP-hook one (fails open, but that section says it "differs from command hooks" and uses status codes "instead of exit codes") and the Agent SDK callback one (a `PreToolUse` timeout "blocks the tool call"). They disagree, and neither is a command hook. Quote sentences, not line numbers -- the snapshots are gitignored and renumber
- [ ] A summarising fetch can never source a claim that the docs DON'T say something. Absence is exactly what summarisation discards, so its silence is not evidence. Grep the raw snapshot instead
- [ ] Because the failure mode is unknown, pick the value so it cannot matter: for anything that **gates**, err long. Too-short + fails-open is a silent bypass; every other combination is a visible stall or a loud block. Measure the hook, then leave generous headroom
- [ ] Hook `if` field used for argument-level filtering when possible (avoids unnecessary process spawning). `if` applies only to tool events: PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionDenied. `FileChanged` is NOT one of them. On any other event a hook with `if` set **never runs** -- it is not ignored, the hook is skipped entirely
- [ ] `if` Bash matching is best-effort and **fails open** on unparseable commands. Use the permission system, not a hook, for hard allow/deny
- [ ] `if` file patterns are rooted at the working directory: `Edit(src/**)` matches only top-level `src`. Use `Edit(**/src/**)` for any depth
- [ ] Hook purpose and trigger documented in README or inline comments
- [ ] Hook output is minimal (one-line stderr, not paragraphs of context)
- [ ] Exit code semantics: exit 0 = **no decision reported** (JSON output processed). For PreToolUse this does NOT approve the call -- the normal permission flow still applies. Exit 2 = blocking error (stderr shown to user). Any other non-zero = non-blocking error. Do not use exit 1 to gate -- use exit 2
- [ ] Per-event exceptions to the above: `WorktreeCreate` fails creation on ANY non-zero exit; `Setup` surfaces stderr as a hook error on any non-zero exit including 2
- [ ] Hook output strings (`additionalContext`, `systemMessage`, stdout) are capped at 10,000 characters; overflow is spilled to a file and replaced with a preview plus path
- [ ] Use **exec form** (set `args`) whenever a hook command references a path placeholder like `${CLAUDE_PLUGIN_ROOT}`. Shell form passes the whole string to `sh -c`, so a plugin root containing a space breaks the hook silently. Exec form passes each element as one argument with no shell involved
- [ ] Exec form for a bundled shell script is `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]` -- NOT the script path as `command`. On Windows a `.sh` file is not a spawnable executable; naming the interpreter works on every platform (the docs make the same point with `node`)
- [ ] Keep shell form when you actually need shell features (pipes, `&&`, redirects, globs)
- [ ] `${user_config.*}` is rejected in shell-form plugin hook commands (v2.1.207+). Read `$CLAUDE_PLUGIN_OPTION_<KEY>` instead, or set `args` to switch to exec form
- [ ] `once: true` in hook blocks is only honored inside **skill** frontmatter (auto-removes after first run). Ignored in `settings.json`, plugin `hooks.json`, AND agent frontmatter

### composable directive pattern

For plugins with behavioral content that should persist across sessions:

- [ ] `hooks/` directory with `hooks.json` (event -> command) and `session-start.sh`
- [ ] Directives in `hooks/directives/*.md`, each with `# trigger: <signal>` on line 1
- [ ] Detection logic orders cheap checks (file/dir stat) before expensive checks (grep)
- [ ] Adding a new convention = dropping a `.md` file in `directives/`, no shell editing
- [ ] Behavioral content in hook directives; detailed reference in on-demand skills

## skill structure

<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->
<!-- source: https://agentskills.io | last_verified: 2026-04-19 -->

Source: Anthropic skills guide (PDF, Jan 2026)

### file layout

- [ ] SKILL.md file exists (exact case: `SKILL.md`)
- [ ] Folder named in kebab-case
- [ ] YAML frontmatter has `---` delimiters
- [ ] No README.md inside skill folder (docs go in SKILL.md or references/)
- [ ] Detailed docs moved to `references/` and linked from SKILL.md body

### frontmatter fields

- [ ] `name` field: kebab-case, no spaces, no capitals, matches folder name
- [ ] `name` field: max 64 characters
- [ ] `name` field: does not contain "claude" or "anthropic" (reserved)
- [ ] `description` field: under 1024 characters
- [ ] `description` field: no XML angle brackets (< >)
- [ ] `license` field: present if open source (MIT, Apache-2.0)
- [ ] `compatibility` field: under 500 characters, lists env requirements
- [ ] `metadata` field: key-value pairs only (author, version, mcp-server)
- [ ] No unexpected fields in frontmatter. Allowed by Agent Skills spec: name, description, license, allowed-tools, metadata, compatibility. Claude Code extensions: paths, model, effort, hooks, agent, argument-hint, shell, context, disable-model-invocation, user-invocable, when_to_use, disallowed-tools, arguments
- [ ] `when_to_use` field (optional) is appended to `description` in the skill listing and counts toward the 1,536-character truncation cap

### instructions quality

- [ ] Instructions are specific and actionable (not vague)
- [ ] Steps include expected commands with actual arguments
- [ ] Error handling section included with common issues
- [ ] Examples provided showing expected input/output
- [ ] References to bundled files are clearly linked
- [ ] No ambiguous language ("validate things properly" -> specific checks)
- [ ] Critical instructions at the top, not buried
- [ ] Bullet points and numbered lists preferred over prose

### progressive disclosure

- [ ] First level (frontmatter): just enough for Claude to know when to load
- [ ] Second level (SKILL.md body): full instructions when skill is relevant
- [ ] Third level (linked files): additional detail loaded on demand

## invocation control

<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->

Source: Claude Code official docs

- [ ] `disable-model-invocation: true` for side-effect workflows (deploy, commit)
- [ ] `user-invocable: false` for background knowledge skills
- [ ] `context: fork` for isolated execution (subagent)
- [ ] `allowed-tools` **grants pre-approval**; it does not restrict. Every tool stays callable. The grant is scoped to the invoking turn and clears on the next user message, even though skill content stays in context
- [ ] `disallowed-tools` is the field that restricts -- it removes tools from the pool while the skill is active, and also clears on the next message
- [ ] Both accept space- or comma-separated strings, or YAML lists

### string substitutions

- [ ] `$ARGUMENTS` for all arguments passed to skill
- [ ] `$ARGUMENTS[N]` or `$N` for positional arguments
- [ ] `${CLAUDE_SESSION_ID}` for session tracking
- [ ] `${CLAUDE_SKILL_DIR}` for the directory containing SKILL.md
- [ ] Dynamic context via `!`command`` syntax (preprocessed)

### distribution

<!-- source: https://code.claude.com/docs/en/skills | last_verified: 2026-04-19 -->
<!-- source: https://code.claude.com/docs/en/plugins | last_verified: 2026-04-19 -->

- [ ] Personal skills: `~/.claude/skills/<name>/SKILL.md`
- [ ] Project skills: `.claude/skills/<name>/SKILL.md`
- [ ] Plugin skills: `<plugin>/skills/<name>/SKILL.md` (prefer `skills/` over legacy `commands/`)
- [ ] Skill descriptions budget: 1% of the model's context window. Override via `skillListingBudgetFraction` (e.g. `0.02`) or `SLASH_COMMAND_TOOL_CHAR_BUDGET` (fixed char count). On overflow, descriptions are dropped starting with the LEAST-invoked skills
- [ ] The 1,536-char per-entry description cap is configurable via `skillListingMaxDescChars`
- [ ] Use `paths` frontmatter to scope skill auto-activation to relevant file types
- [ ] Use `${CLAUDE_PLUGIN_DATA}` for persistent plugin state (survives updates); `${CLAUDE_PLUGIN_ROOT}` for bundled read-only assets

## agent authoring

<!-- source: https://code.claude.com/docs/en/sub-agents | last_verified: 2026-07-21 -->

Subagents are a separate surface from skills, with their own frontmatter. Only
`name` and `description` are required.

### frontmatter

- [ ] Full field set: `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`
- [ ] `model`: `sonnet` | `opus` | `haiku` | `fable` | a full model ID | `inherit` (default)
- [ ] `effort`: `low` | `medium` | `high` | `xhigh` | `max`
- [ ] `memory`: `user` | `project` | `local` (`project` is the documented default choice)
- [ ] `isolation`: `worktree` only -- and it branches from the DEFAULT branch, not the parent session's HEAD
- [ ] `name` is the identity (the filename need not match) and is what hooks receive as `agent_type`
- [ ] There is no `when-to-use` field. Delegation triggers belong in `description`
- [ ] Plugin-shipped agents silently ignore `hooks`, `mcpServers`, and `permissionMode`

### tool restriction

- [ ] `tools` is an allowlist, `disallowedTools` a denylist. If both are set, the denylist applies first; a tool in both is removed
- [ ] Set `tools` explicitly on read-only agents. Omitting it inherits everything, including Write/Edit and all MCP tools
- [ ] If NO entry in `tools` resolves, the subagent refuses to launch rather than starting tool-less
- [ ] The `skills` field only preloads skills; it does not gate access. To block skill invocation, omit `Skill` from `tools` or add it to `disallowedTools`
- [ ] Never available to subagents regardless: `AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`, `WaitForMcpServers`

### when an agent beats a skill

- [ ] Delegate to isolate high-volume output (test runs, doc fetches, log processing) and for parallel independent investigations
- [ ] Stay in the main conversation for iterative back-and-forth, shared multi-phase context, quick targeted edits, and latency-sensitive work

## spec compliance

<!-- source: https://agentskills.io | last_verified: 2026-04-19 -->

Source: Agent Skills spec (agentskills.io). Enforced by `agentskills validate`.

- [ ] name: required, non-empty string
- [ ] name: lowercase only (Unicode letters + hyphens allowed)
- [ ] name: no consecutive hyphens (--)
- [ ] name: cannot start/end with hyphen
- [ ] name: directory name must match skill name exactly
- [ ] name: NFKC Unicode normalization applied
- [ ] description: required, non-empty string
- [ ] Only allowed fields in frontmatter: name, description, license, allowed-tools, metadata, compatibility

## maintenance

- [ ] `metadata.last_verified` present in every SKILL.md frontmatter
- [ ] `last_verified` is within the skill's own `metadata.review_interval_days` (default 30). Tier by how fast the source moves, not uniformly -- a single global window makes the board permanently red, and a permanently-red board is an ignored board
- [ ] `last_verified` is written ONLY after a human reviewed the skill against its source. It is not part of a version cascade: a version bump says "bytes changed", not "someone checked this"
- [ ] Do NOT store a version in SKILL.md frontmatter when the skill ships in a plugin. `plugin.json` is the single source; duplicating it into N sub-skills forces N edits per bump and the only consumer is the check verifying the copies agree
- [ ] Plugin listed in root `marketplace.json` (if installable)
- [ ] Plugin has a README.md with installation instructions
- [ ] Plugin `plugin.json` has name, version, description, author, repository. NOTE: upstream requires only `name` (and the manifest itself is optional) -- the other four are a convention of THIS repo, enforced by our own test suite, not a Claude Code requirement
- [ ] `best_practices.md` has a `last updated` date within 30 days

## quality signals

Source: Anthropic skills guide (PDF)

### quantitative

- Skill triggers on 90% of relevant queries
- Completes workflow in X tool calls (compare with/without skill)
- 0 failed API calls per workflow

### qualitative

- Users don't need to prompt Claude about next steps
- Workflows complete without user correction
- Consistent results across sessions
- New user can accomplish task on first try with minimal guidance

## iteration signals

### undertriggering (low recall)

- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Fix: add more detail and keywords to description

### overtriggering (low precision)

- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Fix: add negative triggers, be more specific, clarify scope
