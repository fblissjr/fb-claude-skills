last updated: 2026-08-07

# best practices: building skills and plugins for Claude

For anyone shipping a skill, plugin, or marketplace that runs in Claude Code and
related Claude products. Not specific to any one skill, plugin, or repo.

The *why* behind all of this — attention as the scarce resource, context traded
against friction, precision as the constraint, descriptions as reverse queries,
progressive disclosure as the mechanism — is not repeated here. It lives in
`VISION.md` alongside this file in the source repo, and it changes on a different
clock than anything below. The architecture that retrieval model serves — agent
topology, model tiering, harness coupling, state substrate — is a third clock
again, in `docs/internals/architecture.md`.

One rule governs all three: **one claim, one home, chosen by what reopens it.**
`VISION.md` holds principles, this file holds rules and gates, and
`docs/internals/` holds the measurements the rules cite. Where a sentence would
appear in two of them, the lower tier keeps it and the higher tier points.

## how to read this

Three parts, because three different things are being asked of you:

| Part | What it is | What you do with it |
|---|---|---|
| **Constraints** | What must not happen, and what breaks when it does | Check your work against it. Violations are defects |
| **Gates** | How you know the thing is good | Run the named command. A gate with no command is not a gate |
| **Reference** | How the platform behaves | Look it up. Do not "verify" it |

Constraints and gates carry checkboxes because they are verifiable. Reference
does not, because there is nothing to verify — a field either exists or it does
not, and you look. A line that cannot be put in one of the three parts does not
belong in this file.

Each section carries an evidence class, which determines when it gets rechecked:

- `harness` — a fact about the runtime. Rechecked when the source page moves.
- `model` — a claim about what the model needs. Rechecked on a model family
  release, and settled only by a with-and-without comparison.
- `craft` — learned from building. Rechecked when an audit produces a finding
  that touches it.

Sections also state **what enforces them**. "Nothing" is the common answer and is
stated rather than hidden, because a checklist that reads as uniformly authoritative
hides which half of it anyone is actually checking.

## authoring shape

<!-- class: model | validated_against: Claude 5 generation | last_verified: 2026-08-07 -->

**Enforced by: nothing mechanical.** The falsifier is a with-and-without
comparison; `skill-creator` ships the harness.

The shape of an instruction matters as much as its content, and the right shape
changed with the Claude 5 generation. That generation is goal-oriented, working
from constraints on one side and an explicit definition of good — metrics,
gates — on the other. It also carries knowledge earlier models did not.

Two consequences. **Capability absorbs content**: an instruction restating what
the model already does well is not merely wasted tokens, it competes with a
better plan the model had. **Operating mode changes shape**: step decomposition
that an earlier generation needed is now scaffolding, and scaffolding does not
travel across generations. Constraints and gates do.

Apply per instruction, not per skill:

- [ ] **Does it carry what the model cannot derive?** Versioned facts, project
      conventions, measured findings, a threshold with evidence behind it. Keep
- [ ] **Does it override a default the model would otherwise follow?** Keep, and
      name the default and the reason. An unjustified override is
      indistinguishable from noise and gets reasoned around rather than followed
- [ ] **Does it restate general competence?** Output templates, step
      decompositions of tasks the model plans better itself, "be specific",
      "handle errors". Delete
- [ ] Procedure still earns its place when the *order* is load-bearing for a
      reason the model cannot see — "name the deriving command before running
      anything" exists because a command chosen after seeing output drifts
      toward confirming. That is a constraint overriding an instinct, not a step
- [ ] Every step that survives states why it exists. A step whose omission
      changes nothing is decoration
- [ ] Examples earn their place by pinning a judgment boundary (this passes,
      this does not), not by showing output format
- [ ] State the negative scope: what this skill is *not* for, and which adjacent
      skill owns that instead
- [ ] Carry a scope caveat where the evidence behind a rule is narrow. A rule
      measured in one setting should say so rather than generalise silently
- [ ] **Prompt the positive, not the prohibition.** Steering by ban drags the
      forbidden behaviour into context and makes it *more* available; the
      negation is a weak modifier over a strongly activated concept, so the ban
      half-reads as an instruction to do the thing. State the target behaviour so
      the banned one is never named. A prohibition earns its place only as a hard
      guardrail that cannot be phrased positively, and even then it is paired
      with the positive target. This governs behaviour steering in a body, not
      the negative *scope* a description carries — see `description precision`
- [ ] **Prefer a pretrained word to a coined one.** A compact term the model
      already holds — *frontier*, *tracer bullet*, *red* — anchors a whole region
      of behaviour in one token by recruiting priors, and repeating the token
      accumulates a distributed definition. A coined word recruits nothing, so
      you pay in definition tokens what an existing word gives free. Coin one
      only when nothing existing fits
- [ ] **Every step ends on a completion criterion, and it has two dimensions.**
      *Clarity*: can the agent tell done from not-done? *Demand*: how much does
      it require — "every modified model accounted for" forces work that "produce
      a change list" does not. Demand is not step-bound; "every rule applied"
      binds a body of flat reference the same way, which is how an all-reference
      document still carries an exhaustiveness bar

**Premature completion** is what the clarity dimension guards against. Steps
still visible ahead pull attention toward being done, so a fuzzy bound invites
ending the current one early. Fix in order: sharpen the bound first, because it
is local and cheap; split the sequence only if the bound is irreducibly fuzzy
*and* the rush is actually observed. Splitting works only across a real context
boundary — a hand-off or a subagent dispatch — because an inline call leaves the
later steps in context and clears nothing.

The negation, leading-word, and completion-criterion items above were adapted
from `mattpocock/skills` (`skills/productivity/writing-for-agents`, MIT).

**Retrieval has a boundary.** Prefer a skill over the model's innate knowledge
for knowledge that is versioned, project-specific, contested, or newer than the
model. Do not write one for general competence. Ask before writing, not after it
underperforms: what does this supply that the model cannot derive? If the answer
is nothing, it is friction rather than retrieval.

## part 1 — constraints

### always-loaded context

<!-- class: harness | source: https://code.claude.com/docs/en/memory | verified_hash: 5892867364cbe366 | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->

**Enforced by:** the ambient-hook arm in `skill-maintain test` (matcher-less
high-frequency hooks) and the token-budget gate below. The rest is unchecked.

Everything in this list loads on every session. Each line is a fixed cost paid
whether or not it is used.

- [ ] Target **under 200 lines per CLAUDE.md file** — upstream's own number, on
      the grounds that longer files consume more context *and reduce adherence*.
      Size is not only a cost problem; a bloated instruction file is followed
      less well
- [ ] CLAUDE.md holds operational instructions only, never reference material.
      Where it is growing, path-scoped rules beat imports: an imported file still
      loads in full at launch, so splitting for tidiness moves the text without
      moving the cost
- [ ] `.claude/rules/`: unconditional rules stay minimal; scope the rest with
      `paths` frontmatter
- [ ] Skill descriptions (all installed) each justify their share of the listing
      budget
- [ ] `settings.json`: no ambient hooks on high-frequency events without
      documented justification
- [ ] Auto-memory `MEMORY.md` stays under 200 lines OR 25KB, whichever comes
      first — content past the cap is not loaded at all. Detailed topic files sit
      beside it and load on demand
- [ ] Where a repo has an `AGENTS.md`, the project CLAUDE.md `@AGENTS.md` imports
      it rather than duplicating it. Claude Code does not read `AGENTS.md`
      directly. `ln -s AGENTS.md CLAUDE.md` is the documented alternative, but the
      import is the portable one — a symlink on Windows needs Administrator or
      Developer Mode
- [ ] Imports recurse to a maximum depth of **four** hops, and relative paths
      resolve against the importing file, not the working directory. An import
      chain deeper than that silently stops resolving
- [ ] A rule earns its tier: mechanically detectable violation belongs in a
      `PreToolUse` block, a detectable condition in a `PostToolUse` notice, and
      only what is neither becomes ambient prose — and ambient is a *pointer*,
      one line, not the content. Cost is *emission*, not invocation: a hook
      that fires and stays silent is nearly free, while `SessionStart` emits
      unconditionally and re-fires on resume, fork, clear and compact. This is
      the rule; the measurement behind it (5,109 silent `PreToolUse` firings at
      zero bytes against 54 `SessionStart` firings at 53% of all hook output,
      and the per-project variance that makes a plugin unjudgeable in the
      abstract) lives in `docs/internals/context-cost.md`

### hooks

<!-- class: harness | source: https://code.claude.com/docs/en/hooks | verified_hash: 167d43c0d553ffd7 | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/hooks-guide | verified_hash: 482854ea8980890f | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/permissions | verified_hash: 89c6b6956bbea598 | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/mcp | verified_hash: 79ed1603ffb8c963 | last_verified: 2026-08-07 -->

**Enforced by: nothing.** Every item here is authoring discipline. Several fail
*silently* — marked (silent) — which is why they are constraints rather than
guidance.

- [ ] Hook `timeout` is in **seconds**, not milliseconds. `3000` is fifty
      minutes. Defaults are per type and per event, not one number: 600 for
      `command`, `http`, `mcp_tool`; 30 for `prompt`; 60 for `agent`.
      `UserPromptSubmit` lowers the command/http/mcp_tool default to 30 and
      `MessageDisplay` lowers it to 10. `SessionEnd` hooks share a 1.5-second
      budget, raised to match a longer per-hook `timeout` up to 60 seconds
- [ ] **Timeout behaviour is documented per event, and it is not uniform.** For
      a *command* hook it is stated for exactly two events, and both fail open:
      on `UserPromptSubmit` the hook is canceled and its output, including any
      `additionalContext`, is discarded while the prompt proceeds without it
      (a transcript notice names the hook and the timeout); on `MessageDisplay`
      the original text is displayed. On every other event, what a command hook
      does at timeout is still unstated
- [ ] Agent SDK **callback** hooks are a different surface and fail *closed*: a
      `UserPromptSubmit` callback timeout blocks the prompt, and a `PreToolUse`
      callback timeout blocks the tool call. Do not reason from one surface to
      the other
- [ ] Because a gating command hook fails open where it is documented and is
      unspecified everywhere else, pick the value so it cannot matter: for
      anything that **gates**, err long. Too-short plus fails-open is a silent
      bypass — the prompt continues, minus the context your hook was supposed to
      supply. Every other combination is a visible stall or a loud block.
      Measure the hook, then leave generous headroom
- [ ] Exit code semantics: exit 0 = **no decision reported** (JSON output
      processed). For `PreToolUse` this does NOT approve the call — the normal
      permission flow still applies. Exit 2 = blocking error (stderr shown to
      user). Any other non-zero = non-blocking error. Never use exit 1 to gate
- [ ] Per-event exceptions: `WorktreeCreate` fails creation on ANY non-zero exit;
      `Setup` cannot block at all — any non-zero including 2 surfaces stderr as a
      `<hook name> hook error` notice and execution continues
- [ ] Exit 2 does not reach Claude on every event. For `SessionStart`, `Setup`,
      and `SubagentStart` the stderr renders as a hook-error notice to the user
      and Claude never sees it — so a hook trying to inject a correction on those
      events via exit 2 is talking to the wrong audience. For `SubagentStart` the
      notice lands in the subagent's transcript, not the parent's
- [ ] `asyncRewake: true` runs the hook in the background and wakes Claude on
      exit 2, surfacing stderr (or stdout when stderr is empty) as a system
      reminder. Implies `async`. This is the supported shape for a long-running
      check that must still be able to report a failure
- [ ] A hook runs **exec form** when `args` is set and **shell form** when it is
      omitted. Set `args` whenever the command references a path placeholder like
      `${CLAUDE_PLUGIN_ROOT}`: exec form passes each element as one argument with
      no quoting and no shell, so spaces and `$`, apostrophes and backticks pass
      through verbatim on every platform
- [ ] Shell form passes the string to a shell that varies by platform — `sh -c`
      on macOS and Linux, Git Bash on Windows, PowerShell when Git Bash is not
      installed. Set the `shell` field to choose explicitly rather than inheriting
      that. Keep shell form only where pipes, `&&`, redirects, or globs are
      genuinely needed
- [ ] Exec form for a bundled script names the interpreter:
      `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]` — NOT the
      script path as `command`. On Windows exec form requires `command` to resolve
      to a real executable, so a `.sh` file is not spawnable and neither are the
      `.cmd`/`.bat` shims under `node_modules/.bin`. Naming the interpreter
      (`bash`, or `node` plus the script path) works everywhere
- [ ] `if` applies only to tool events: `PreToolUse`, `PostToolUse`,
      `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`. `FileChanged`
      is NOT one of them. On any other event a hook with `if` set **never runs** —
      it is not ignored, the hook is skipped entirely (silent)
- [ ] `if` Bash matching is best-effort and **fails open** on unparseable
      commands. Use the permission system, not a hook, for hard allow/deny (silent)
- [ ] `if` file patterns are rooted at the working directory: `Edit(src/**)`
      matches only top-level `src`. Use `Edit(**/src/**)` for any depth (silent).
      This is v2.1.214+ behaviour; earlier versions matched at any depth, so a
      pattern written before then quietly narrowed
- [ ] `if` holds **exactly one** permission rule. There is no `&&`, `||`, or list
      syntax — multiple conditions need one handler each (silent)
- [ ] Plugin-bundled MCP tools need the scoped matcher form
      `mcp__plugin_<plugin>_<server>__<tool>`. A matcher written against the bare
      server key never fires for them (silent). The scoped-name construction is
      documented on the MCP page, not the hooks page
- [ ] `${user_config.*}` is rejected in shell-form plugin hook commands
      (v2.1.207+). Read `$CLAUDE_PLUGIN_OPTION_<KEY>` instead, or set `args` to
      switch to exec form
- [ ] `once: true` is only honoured inside **skill** frontmatter (auto-removes
      after first run). Ignored in `settings.json`, plugin `hooks.json`, AND agent
      frontmatter (silent)
- [ ] Hook output strings (`additionalContext`, `systemMessage`, stdout) are
      capped at 10,000 characters; overflow spills to a file and is replaced with
      a preview plus path. Cap your own output well below this
- [ ] Hook output is minimal — one line of stderr, not paragraphs of context
- [ ] Hook purpose and trigger are documented in the README or inline
- [ ] Model-facing text is factual statements, not imperatives. `additionalContext`
      framed as out-of-band commands can trip prompt-injection defenses and get
      surfaced to the user's terminal instead of read by the model, silently
      converting a model-facing control into a user-facing one

### agents and tool access

<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: 5b1893f5d9b84725 | last_verified: 2026-08-07 -->

**Enforced by: nothing.**

- [ ] `tools` is an allowlist, `disallowedTools` a denylist. With both set the
      denylist applies first; a tool in both is removed
- [ ] Set `tools` explicitly on read-only agents. Omitting it inherits
      everything, including Write/Edit and all MCP tools
- [ ] **`tools` is not the last word — two filters run after it.** The first
      removes a fixed list from every subagent (below) even when you list it.
      The second applies to *background* subagents, which since v2.1.198 is the
      **default**: apart from `Agent` and `ExitPlanMode`, a background subagent
      keeps every MCP tool but only these built-ins — `Read`, `Grep`, `Glob`,
      `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`,
      `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`, `EnterWorktree`,
      `ExitWorktree`, `Monitor`, `TaskStop`, `SendMessage`, `Artifact`.
      Everything else is removed whether inherited or explicitly listed, **and
      the removal reports no error** unless it empties the list. The same
      definition therefore resolves to different tools in foreground and
      background. Set `background: false` where a tool outside that set is
      load-bearing
- [ ] Forks skip both filters and receive the main conversation's exact tool
      pool. Agent-team teammates additionally keep `TaskCreate`, `TaskGet`,
      `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, `CronList`
- [ ] If NO entry in `tools` resolves, the subagent *usually* fails to launch
      with an error naming the unresolved entries. Upstream hedges this word;
      before v2.1.208 such a subagent launched tool-less and returned empty or
      confusing results
- [ ] The `skills` field only preloads skills — the full content, not just the
      description — and does not gate access. Subagents can still invoke
      unlisted project, user, and plugin skills through the Skill tool. To block
      that, omit `Skill` from `tools` or add it to `disallowedTools`
- [ ] An agent `name` cannot contain `:`, which is reserved for plugin-scoped
      identifiers. A file whose name contains one is not loaded and the error
      goes to the debug log only (v2.1.218+; earlier versions accepted it)
- [ ] `allowed-tools` on a *skill* **grants pre-approval**; it does not restrict.
      Every tool stays callable. `disallowed-tools` is the field that restricts.
      Both are scoped to the invoking turn and clear on the next user message,
      even though skill content stays in context. Both accept space- or
      comma-separated strings, or YAML lists
- [ ] `isolation: worktree` branches from the DEFAULT branch, not the parent
      session's HEAD
- [ ] Plugin-shipped agents silently ignore `hooks`, `mcpServers`, and
      `permissionMode`

### skill and plugin structure

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->
<!-- class: harness | source: coderef/agentskills | last_verified: 2026-04-19 -->
<!-- class: craft | note: the no-README and references/ layout rules are house conventions | last_verified: 2026-08-07 -->

**Enforced by:** `skill-maintain validate` (name rules, allowed fields,
description constraints) and the repo-hygiene suite (marketplace listing,
manifest fields). This is the best-covered section in the file.

- [ ] `SKILL.md`, exact case, in a kebab-case folder whose name matches the
      skill `name`
- [ ] YAML frontmatter with `---` delimiters
- [ ] `description` under 1024 characters, no angle brackets. **The 1024 figure
      comes from the Agent Skills spec, which this repo does not fetch** — it
      cannot be refreshed by the upstream check and is the oldest unverifiable
      number in the file
- [ ] Supporting files are a feature, not a smell: templates, example outputs,
      scripts, and reference docs all belong beside SKILL.md. Reference them
      from the body so the model knows what they hold and when to load them
- [ ] *House convention:* no `README.md` inside a skill folder — docs go in
      SKILL.md or `references/`. Upstream permits it; this keeps one entry point
- [ ] No `metadata.author` and no `metadata.version` in SKILL.md. The whole file
      loads into context on activation, so a name or version there is standing
      cost with no runtime use. Attribution belongs in `plugin.json` and the
      README; the version belongs in `plugin.json` alone, or N sub-skills need N
      edits per bump and the only consumer is the check confirming the copies agree
- [ ] No unexpected frontmatter fields (see the reference table)
- [ ] Plugin listed in the marketplace manifest, with a README carrying install
      instructions
- [ ] Know which manifest fields are actually required before enforcing them.
      Upstream requires only `name`, and the manifest itself is optional. A house
      rule demanding `version`, `description`, `author`, and `repository` is a
      convention worth having — but call it yours, not the platform's

### controls: hooks, checks, and reminders

<!-- class: craft | source: field-tested in a sibling repo's claims-reminder apparatus | last_verified: 2026-08-03 -->

**Enforced by:** `/postmortem:control-audit`, which censuses controls and
live-fires the ones nothing watches.

Applies to anything check-shaped a plugin ships. The failure mode these guard
against is a control trusted because it exists rather than because anything
watches it.

- [ ] **The header carries four sections**: WHY NOT the obvious alternative (the
      tool you rejected, with the disqualifying fact); the measured
      false-positive rate with its sample ("fires on 15 of 25 commits,
      undeduped"); WHAT IT DOES NOT DO, said plainly; and a RETIREMENT TRIGGER
      named at install — the observable condition under which the control gets
      deleted rather than tuned. A control that cannot say when it should die
      outlives its usefulness by default
- [ ] **A subordination rule where classes are involved**: any class the control
      covers that later becomes mechanically checkable gets a real check, and the
      control drops that class. Reminders are the bottom tier, not a destination
- [ ] **Reminder-tier output is deduplicated and measured.** An undeduplicated
      reminder firing on most actions is wallpaper — people learn to scroll past
      it, which trains dismissal of the whole channel. Measure the fire rate on
      real history before shipping
- [ ] **A green states its scope.** A check whose success output cannot be
      distinguished from a run that checked nothing is the recurring silent
      killer (zero files scanned, report `ok`). Print the derived count of what
      was covered
- [ ] **A proxy can reject; it cannot approve.** Give a heuristic authority only
      over its confident region and make it *silent* elsewhere. A warning band
      over the uncertain region is the worst option available: it trains people
      to skim the output, destroying the loud case too
- [ ] **Prefer a fixture that cannot collide over one that probably will not.** A
      control right 97% of the time teaches people to re-run it until it agrees
- [ ] **Bracket the control itself**: prove it can go red, pin its silent edges,
      and check that any examples its messages cite still resolve

### one claim in several places

<!-- class: craft | source: five same-day instances across heylookitsanllm and this repo, 2026-08-29 | last_verified: 2026-08-29 -->

A claim that exists once is maintained. The same claim in four places is
maintained in one of them and stale in three, and the copies fail differently
from the original: nothing is red, so nothing is looked at.

- [ ] **Per-path tests cannot see cross-path divergence.** Where two code paths
      must agree, tests that assert each path's behaviour are individually
      correct and collectively blind: the bug lives between them and every test
      passes. Specimen: a `stop_reason` passthrough existed in two modules,
      one was fixed, and 1,700 tests stayed green while the routes disagreed.
      Assert that the paths *agree* — that every write goes through the shared
      mapper — not that each produces the right answer
- [ ] **"Hand-copied constant" does not reach a copied shape.** The usual
      framing catches duplicated values. It does not catch a duplicated
      *description* of a structure, especially in a documentary model or a
      docstring that no assertion reads, so those drift in the same commit
      that fixes the other copy
- [ ] **Sweep the generated artifact, not the source.** Every widest-reach copy
      of a claim ends up in something rendered — a generated schema, a
      published listing, a manifest. One pass over that artifact for strings
      you know are false catches route descriptions, headers, examples and
      endpoint maps at once, where sweeping the source catches whichever file
      you thought to open. This is a procedure; "remember to also check X" is
      a habit, and habits are not controls. Specimen: sweeping the source had
      already missed two instances that one pass over the generated schema
      found
- [ ] **The string you just replaced is the sweep input, and a clean sweep
      proves only that those strings are absent.** Taking the list from the
      fix gives the control a defined moment and a defined input, instead of
      asking the reader to somehow know what is false. It never proves the
      artifact is correct — a sweep is only as good as its list
- [ ] **Report what was EXAMINED, not only what matched.** "0 hits" cannot be
      distinguished from a sweep that never ran. Through a pipe the two are
      identical in every shell — a failed glob and a clean run both exit 0,
      because the pipeline reports `head`'s status — so the common `| head`
      shape masks the failure in the direction that reads as success. Bare,
      it depends on the shell and is not safe to rely on: zsh exits 1 for
      both, while bash distinguishes them (2 for the failed glob, 1 for
      clean). Your `grep` may also skip files silently — a shim over `ugrep
      -I` passes over anything containing a NUL byte with no output and no
      message, where GNU and BSD grep say "Binary file X matches". Check
      which yours does rather than assuming. "Scanned 66 route descriptions,
      0 hits" is a result; "0 hits" is not
- [ ] **The copy with the widest reach is the one the editing loop never looks
      at.** A skill `description` is loaded into every session's listing and
      sits above the prose being edited, so it is simultaneously the
      most-read instance of a claim and the least-reread. Specimen: a "closed
      list" claim survived three fixes to the body it described because all
      three were edits to the body

## part 2 — gates

A gate names the command that produces its number. Anything here without one is
not a gate — it is an opinion, and it either gets a command or gets deleted.

### token budget

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->
<!-- class: craft | note: the 4,000/8,000 token thresholds are a house convention, not upstream | last_verified: 2026-08-07 -->

**Command:** `skill-maintain measure`

Thresholds apply to SKILL.md only, which is always loaded once the skill
triggers. Reference files are on-demand and tracked separately, so thorough
reference material is not penalised — that is what progressive disclosure is for.

**Exactly one of these numbers is gated, and it is the one with a documented
consequence.**

Upstream (`harness`) — the gate:

- [ ] SKILL.md under **5,000 tokens**. Only the first 5,000 tokens of each
      re-attached skill survive auto-compaction, and all re-attached skills
      share a combined 25,000-token budget filled from the most recently
      invoked. Above this, a skill is silently truncated in any session that
      compacts, and invoking many skills drops the older ones entirely. This is
      what `skill-maintain test` fails on
- [ ] SKILL.md body under **500 lines**. Upstream's own guidance; move detailed
      reference material to separate files

House convention (`craft`) — reported, never gated. Do not cite these as
platform limits, and do not fail a board on them:

- [ ] SKILL.md under 4,000 tokens (2% of a 200k window). Estimation: chars / 4
- [ ] SKILL.md under 8,000 tokens, the old hard ceiling
- [ ] Heavy material in `references/`, not inline
- [ ] Reference tokens reported but not budget-warned
- [ ] Treat the estimate as a budget heuristic, not a measurement — real
      tokenization varies by content type

**Why the split, recorded because the failure was instructive.** The gate used to
fire at 4,000. That number is an opinion about attention, and it sat red on two
skills that were 0.8% and 2.3% over — for long enough that the red stopped
carrying information — while the skill *listing*, which is loaded
unconditionally every session rather than only when a skill triggers, went
unmeasured. A board that is permanently red about a house preference trains
people to skim it, which costs more than the preference is worth. Demoted
2026-08-13; the boundary is pinned by `test_token_budget_gate.py`, whose
red-side arm exists because a threshold change is exactly the edit that can
silently stop gating anything.

### description precision

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->
<!-- class: craft | note: only the 1,536-char cap is upstream; the rest is authoring judgment | last_verified: 2026-08-07 -->

**Command:** `skill-maintain validate` (quality warnings), and `skill-creator`'s
description-tuning harness for trigger accuracy.

A description is a reverse query: it describes the set of user intents that
should match. Vague descriptions overtrigger; missing trigger phrases
undertrigger.

- [ ] States WHAT it does, with action verbs
- [ ] States WHEN to use it, with trigger phrases users actually type
- [ ] States negative scope where an adjacent skill could match instead
- [ ] Specific enough not to match unrelated queries
- [ ] No duplicate or near-duplicate descriptions across installed skills —
      ambiguous routing is a precision failure with no error message
- [ ] Front-loads the core use case: `description` plus `when_to_use` is
      truncated at 1,536 characters in the listing

**This section pulls against `distribution and budgets`, and the tension is
real.** Negative scope and trigger phrases are what stop a description
overtriggering, and they are also the expensive part of it — the longest
descriptions in a well-tuned set are long for exactly the reason this section
requires. The listing is the always-loaded cost, so precision here is paid there.
Neither rule yields to the other: write the description the routing needs, then
manage the total at the set level (fewer listed entries, or `skillOverrides`),
not by shortening the descriptions that are earning their length.

The negative scope required here is routing metadata read by a selector. It is
not the behavioural prohibition that `authoring shape` tells you to avoid; those
operate on different surfaces and neither licenses the other.

Diagnosing which way it is failing: skills that do not load when they should,
users manually enabling them, and questions about when to use it are
undertriggering — add trigger phrases. Skills loading for irrelevant queries,
users disabling them, and confusion about purpose are overtriggering — add
negative scope. Zero invocations is ambiguous between the two and needs the
tuning harness to separate, not a guess.

### versioning and packaging

<!-- class: craft | last_verified: 2026-08-04 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 192ea4a63e04adbe | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugin-marketplaces | verified_hash: 6cb7e9b227d93560 | last_verified: 2026-08-07 -->

**Command:** `skill-maintain quality` (version alignment), plus whatever
pre-commit gate the repo installs.

- [ ] A content change cascades to every copy of the version that can drift —
      the plugin manifest, the marketplace entry, a changelog entry, and any
      `pyproject.toml` or authored `package.json` under the plugin source
- [ ] SKILL.md is deliberately NOT in that cascade
- [ ] Without the bump, a marketplace update never reaches installed users
- [ ] Check what the marketplace `source` actually ships before cascading — a
      tool that ships separately versions independently from the plugin that
      references it
- [ ] One changelog, at the repo root. A second copy earns its place only if it
      has a consumer other than the check confirming it is a copy

## part 3 — reference

Look these up. There is nothing here to verify.

### skill frontmatter fields

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->
<!-- class: harness | source: coderef/agentskills | last_verified: 2026-04-19 -->

Agent Skills spec (portable): `name`, `description`, `license`, `allowed-tools`,
`metadata`, `compatibility`.

Claude Code extensions (not portable — `skill-maintain validate --strict` flags
these): `paths`, `model`, `effort`, `hooks`, `agent`, `background`,
`argument-hint`, `shell`, `context`, `disable-model-invocation`,
`user-invocable`, `when_to_use`, `disallowed-tools`, `arguments`.

Narrower still: claude.ai skill uploads, the Skills API, and `package_skill.py`
accept only `name`, `description`, `license`, `compatibility`, `metadata`, and
`allowed-tools` — so `argument-hint` alone is enough to be rejected there. A
personal skill enabled for Cowork or cloud sessions is uploaded to claude.ai and
subject to those rules.

| Field | Notes |
|---|---|
| `name` | kebab-case, max 64 chars, NFKC-normalized, no consecutive hyphens, cannot start or end with one, must match the directory. Cannot contain "claude" or "anthropic" |
| `description` | under 1024 chars, no `<` or `>` |
| `when_to_use` | appended to `description` in the listing; counts toward the 1,536-char cap |
| `metadata` | key-value pairs only |
| `compatibility` | under 500 chars |
| `disable-model-invocation` | for side-effect workflows (deploy, commit). Also blocks subagent preloading and scheduled-task auto-run |
| `user-invocable: false` | background knowledge skills |
| `context: fork` | isolated execution in a subagent |
| `paths` | scopes auto-activation to matching files |

### agent frontmatter fields

<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: 5b1893f5d9b84725 | last_verified: 2026-08-07 -->

A separate surface from skills. Only `name` and `description` are required.

Full set: `name`, `description`, `tools`, `disallowedTools`, `model`,
`permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`,
`background`, `effort`, `isolation`, `color`, `initialPrompt`. The `--agents`
JSON flag accepts the same set plus `prompt` for the system prompt.

| Field | Values |
|---|---|
| `model` | `sonnet` \| `opus` \| `haiku` \| `fable` \| a full model ID \| `inherit` (default) |
| `effort` | `low` \| `medium` \| `high` \| `xhigh` \| `max`; available levels depend on the model |
| `permissionMode` | `default` \| `acceptEdits` \| `auto` \| `dontAsk` \| `bypassPermissions` \| `plan` \| `manual` (alias for `default`, v2.1.200+) |
| `memory` | `user` (across all projects) \| `project` (project-specific, version-controlled) \| `local` (project-specific, not checked in). No default is documented — choose by scope |
| `isolation` | `worktree` only. Branches from the DEFAULT branch, not the parent session's `HEAD`; cleaned up automatically if the subagent makes no changes |
| `background` | `true` forces background. Unset lets Claude choose, and since v2.1.198 it chooses background by default — which changes the tool set |

`name` is the identity — the filename need not match — and is what hooks receive
as `agent_type`. There is no `when-to-use` field; delegation triggers belong in
`description`.

Ignored entirely for plugin-shipped subagents: `hooks`, `mcpServers`,
`permissionMode`.

Removed from every subagent regardless of configuration, even when listed in
`tools`: `Agent` (at the depth limit), `AskUserQuestion`, `EndConversation`,
`EnterPlanMode`, `ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`,
`TaskOutput`, `WaitForMcpServers`, `Workflow`. A second, larger filter applies to
background subagents — see the constraint above, since background is the default.

`Agent(agent_type)` allowlist syntax applies only to an agent running as the main
thread via `claude --agent`. Inside a subagent definition, listing `Agent` in
`tools` permits spawning within the depth limit, but any type list in parentheses
is ignored.

**When an agent beats a skill:** delegate to isolate high-volume output (test
runs, doc fetches, log processing) and for parallel independent investigations.
Stay in the main conversation for iterative back-and-forth, shared multi-phase
context, quick targeted edits, and latency-sensitive work.

### hook types and events

<!-- class: harness | source: https://code.claude.com/docs/en/hooks | verified_hash: 167d43c0d553ffd7 | last_verified: 2026-08-07 -->

`type` is one of `command`, `http`, `mcp_tool`, `prompt`, `agent`. Most hooks
in the wild are `command`; `prompt` is LLM-evaluated and can judge what a shell
script cannot pattern-match.

Tool events (the only ones where `if` works): `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`.

### string substitutions

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->

| Token | Expands to |
|---|---|
| `$ARGUMENTS` | all arguments passed to the skill |
| `$ARGUMENTS[N]` / `$N` | positional arguments; `arguments` frontmatter names them for `$name` use |
| `${CLAUDE_SESSION_ID}` | session identifier |
| `${CLAUDE_SKILL_DIR}` | directory containing SKILL.md. **For a plugin skill this is the skill's subdirectory, not the plugin root** |
| `${CLAUDE_PROJECT_DIR}` | project root; the same path hooks and MCP servers receive |
| `${CLAUDE_EFFORT}` | `low` \| `medium` \| `high` \| `xhigh` \| `max`. Ultracode is not a distinct level and reports as `xhigh` |
| `${CLAUDE_PLUGIN_ROOT}` | bundled read-only assets; changes on every plugin update |
| `${CLAUDE_PLUGIN_DATA}` | persistent per-plugin state; survives updates |
| `` !`cmd` `` | preprocessed shell output. Disabled repo-wide by `disableSkillShellExecution: true` for user/project/plugin/add-dir skills |

`${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` are substituted in two places:
the markdown body **and** Bash rules in `allowed-tools`. Using the same variable
in both is the supported way to run a bundled script with no permission prompt —
`allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)` matched against the
exact command the body tells Claude to run.

Inline `` !`cmd` `` is recognised **only** at line start or immediately after
whitespace; `KEY=!`cmd`` is left as literal text and never runs. Substitution
runs once over the original file and output is not re-scanned, so a command
cannot emit a placeholder for a later pass.

### distribution and budgets

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/settings | verified_hash: 9518c46c0f08d743 | last_verified: 2026-08-07 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins | last_verified: 2026-07-21 -->

| Scope | Location |
|---|---|
| Personal | `<HOME>/.claude/skills/<name>/SKILL.md` |
| Project | `.claude/skills/<name>/SKILL.md` |
| Plugin | `<plugin>/skills/<name>/SKILL.md` (prefer `skills/` over legacy `commands/`) |

Skill descriptions get 1% of the model's context window. Override with
`skillListingBudgetFraction` (e.g. `0.02`) or `SLASH_COMMAND_TOOL_CHAR_BUDGET`
(fixed char count). **On overflow, descriptions are dropped starting with the
LEAST-invoked skills.** The 1,536-char per-entry cap is configurable via
`skillListingMaxDescChars`.

Three levers when the budget is tight, in increasing order of how much you give
up: trim `description` and `when_to_use` at the source with the key use case
first; set low-priority entries to `"name-only"` in `skillOverrides` so they
list without a description; or raise the fraction. `skillOverrides` also takes
`off` and `user-invocable-only`, and `disableBundledSkills` removes the shipped
set entirely.

**`disable-model-invocation` is not one of those levers, and it is worth saying
so because the mistake is natural.** Upstream: *"The listing always contains
every skill name"*, and the field's own row says it *"prevent[s] Claude from
automatically loading this skill"* plus blocking subagent preloading and
scheduled-task auto-run. It governs **who may invoke**, not what the listing
carries. A user-invoked skill still occupies a listing entry. If you want an
entry to stop costing its description, the mechanism is `skillOverrides`
`"name-only"`; if you want it gone entirely, uninstall it. Any argument of the
form "make it user-invoked and it becomes free" is false, and an authoring model
built on that premise will not save what it claims.

**Measure this rather than assume it, and do not build a tool to.** The listing
is the only unconditionally loaded part of a skill, so it is the number that
matters most and the one least likely to be watched — the per-file body budgets
above cap a cost that is conditional on the skill triggering. `/doctor` already
reports skill-listing cost and `claude plugin details <name>` reports per-plugin
always-on versus on-invoke; `docs/internals/context-cost.md` carries the standing
"do not rebuild these" list.

Worked example, and a caution about how to measure it. `/doctor` reported this
repo's listing on 2026-08-13 at **26 entries, ~2,300 tokens**, against the ~2,000
a 1% allocation gives at a 200k window: marginally over, and comfortable at a
larger window.

A hand-rolled count taken the same day said 4,391 tokens across 36 skills, and it
was measuring the wrong set. Globbing `SKILL.md` across a repo counts every
description *authored* there. The listing carries only the skills actually
**enabled** in the session, plus the bundled ones — for this repo, 8 skills from
four enabled plugins, ~1,358 tokens, with the rest of the 26 coming from
elsewhere. Authored is not installed, and a repo that ships more plugins than it
enables will overstate its own listing badly by counting files.

So: read the number off `/doctor`. Two consequences of the mechanism are still
worth generalising. Overflow is **silent** and drops the least-invoked first, so
the skills you rarely reach for are exactly the ones that disappear. And the
allocation is a *fraction of the window*, so "are we over budget" has a different
answer per model — compute it against the window rather than asserting a constant
character count.

### surface differences

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: 07e165cddf652d35 | last_verified: 2026-08-07 -->

The same skill does not behave identically everywhere.

- **Cowork and cloud sessions do not read the user-scope skills directory**
  (`<HOME>/.claude/skills/`). Both load the skills enabled for your claude.ai
  account, synced at session start. Cloud sessions additionally load project
  skills from the cloned repository's `.claude/skills/`, and plugins declared in
  the repository's `.claude/settings.json` install at session start — plugins
  enabled only in your user settings do not transfer.
- **`context: fork` with `agent: Explore` or `agent: Plan` does not load
  CLAUDE.md.** Those two built-ins skip CLAUDE.md and git status to keep context
  small, so a forked skill using them sees only the SKILL.md content and the
  agent's own system prompt. Other agent types do load it.
- **Project skills load from `.claude/skills/` in the launch directory and every
  parent up to the repository root**, so starting in a subdirectory still picks
  up root skills. They also load from *nested* `.claude/skills/` below the
  working directory when Claude reads or edits a file there — the monorepo case.
- **`--add-dir` and `/add-dir` load `.claude/skills/` from the added directory;
  the `permissions.additionalDirectories` setting does not.** Skills are the
  documented exception to add-dir granting file access rather than configuration
  discovery. CLAUDE.md from those directories is still not loaded unless
  `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.
- **Precedence on a name clash:** enterprise over personal over project, and a
  skill at any of those levels overrides a bundled skill of the same name. Plugin
  skills are namespaced `plugin-name:skill-name` and cannot collide. Where a
  skill and a legacy `.claude/commands/` file share a name, the skill wins.
- **Live change detection** picks up edits to watched skill directories without a
  restart — but a *newly created* top-level skills directory that did not exist
  at session start is not watched until you restart.

### composable directive pattern

<!-- class: craft | last_verified: 2026-08-17 -->

**Reach for this only after the cheaper answer fails.** The cheaper answer is to
write the convention into the repo's own always-loaded files, where it also
reaches collaborators who never installed the plugin. Measured 2026-08-17 in the
repo that authored this pattern: three of its four shipped directives were
permanently silent there, because a repo that cares enough to install a
conventions plugin has usually already written the conventions down — and the
whole ground-coverage apparatus below exists to detect that and get out of the
way. A mechanism whose success condition is silence is a bootstrap, not a
feature. That repo retired its own implementation the same day; the pattern is
documented here because it is still the right shape *if* you have behavioural
content a repo genuinely cannot state for itself, which is rarer than it looks.

Pair it with a measurement before you trust it: grep your transcripts for the
hook's own output, and separate real emissions from the transcript merely
quoting the source. A control that has never fired is not the same as a control
that works.

For plugins with behavioural content that should persist across sessions:

- `hooks/` holding `hooks.json` (event to command) and `session-start.sh`.
- Directives in `hooks/directives/*.md`, each with `# trigger: <signal>` on line
  one. A directive a repo can supersede also declares `# ground: <ERE>` — the
  pattern of a repo-local rule covering the same ground, which silences the block
  there. A directive without a ground line broadcasts unconditionally, which is
  usually not what you want for convention prose.
- Detection orders cheap checks (file or directory stat) before expensive ones
  (grep).
- Adding a convention means dropping a `.md` file in `directives/`, never editing
  shell.

### spec compliance

<!-- class: harness | source: coderef/agentskills | last_verified: 2026-04-19 -->

**The three sections deriving from the Agent Skills spec cite the repo, not the
website.** `agentskills.io` is fetched by nothing, so citing it made those
sections permanently unverifiable; `coderef/agentskills` is a clone this project
already tracks, whose HEAD `skill-maintain sources` records, so the provenance
join can compare them by SHA exactly as it compares a page by content hash.
They currently report **unbound** — correct source, never yet checked against a
specific commit — which is the honest state and the one that goes green only
when someone actually reads the spec.

The rules are the validator, not this file. Claude Code's skill schema is a
superset of the cross-vendor Agent Skills spec; `skill-maintain validate`
enforces it, and `--strict` flags fields that are not portable to strict
cross-vendor hosts. Read `cc_schema.py` for the authoritative list rather than
maintaining a prose copy that can disagree with it.

## maintaining this file

<!-- class: craft | last_verified: 2026-08-07 -->

- [ ] A `harness` section is rechecked when its source page moves, not when a
      calendar elapses. Correct the section's `last_verified` when you recheck it
      — a file-level date says nothing about which section anyone looked at
- [ ] A `model` section is rechecked on a model family release. Nothing else
      triggers it, and elapsed time says nothing about whether the model changed
- [ ] A `craft` section is rechecked when an audit produces a finding that
      touches it
- [ ] **Re-audit rules written for older models.** Instructions that worked
      around an older model's limitation become overhead once a newer model
      handles the case on its own. On each maintenance pass, take at least one
      always-loaded rule or skill instruction and ask whether the model still
      needs it, then delete or demote what it does not
- [ ] Freshness does not catch wrongness. A document can be wrong on the day it
      is written, and no staleness check will ever say so. Audit the added prose
      of a change against what the code and the platform actually do
- [ ] **A summarising fetch can never source a claim that the docs do NOT say
      something.** Absence is exactly what summarisation discards, so its silence
      is not evidence. Grep the raw page. And quote sentences rather than line
      numbers — snapshots renumber
- [ ] **Absence claims decay fastest, and nothing flags them.** "The docs do not
      say X" is falsified by upstream adding one sentence, while a claim about
      what the docs *do* say usually survives an edit. No diff-watcher reports
      "a thing you called undocumented now exists". Where a gap must be recorded,
      write what IS documented and where, then name the gap as the remainder —
      that form fails loudly on recheck instead of silently. Specimen: this
      file asserted for months that command-hook timeout behaviour was
      undocumented; by 2026-08-07 it was documented for two events
- [ ] A rule with no source, no measurement, and no incident behind it is an
      opinion. Opinions are allowed here, but they say so
