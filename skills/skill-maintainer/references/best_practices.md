last updated: 2026-09-24

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
- `model` — a claim about what the model needs. Rechecked on every model
  release, and settled only by a with-and-without comparison.
- `craft` — learned from building. Rechecked when an audit produces a finding
  that touches it.

Sections also state **what enforces them**. "Nothing" is the common answer and is
stated rather than hidden, because a checklist that reads as uniformly authoritative
hides which half of it anyone is actually checking.

## authoring shape

<!-- class: model | validated_against: Claude 5 generation (Fable 5.1, Opus 5.5, Opus 5, Sonnet 5) | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/model-config | verified_hash: 39520b135e5ca63a | last_verified: 2026-09-24 -->

**Enforced by: nothing mechanical.** The falsifier is a with-and-without
comparison: `claude plugin eval` for a skill that ships in a plugin (see
`behaviour eval` under gates), `skill-creator` for iterating on one skill inside
a conversation.

The shape of an instruction matters as much as its content, and the right shape
changes with the model. The Claude 5 generation is goal-oriented: it works from
constraints on one side and an explicit definition of good — metrics, gates —
on the other, and plans the path itself when the goal is clear.

Two consequences. **Capability absorbs content**: an instruction the current
model no longer needs is not neutral — dated behavioural instructions actively
degrade behaviour (over-triggering, over-planning, rigid responses in gray
areas), while merely irrelevant text is comparatively harmless. **Operating mode
changes shape**: step decomposition that an earlier generation needed is now
scaffolding, and skills written for earlier models are often too prescriptive
for this one. Constraints that encode an observable limit travel; so do gates.

Apply per instruction, not per skill:

- [ ] **Does it carry what the model cannot derive?** Versioned facts, project
      conventions, measured findings, a threshold with evidence behind it. Keep
- [ ] **Does it override a default the model would otherwise follow?** Keep, and
      name the default and the reason. An override without its reason is applied
      literally and too widely: this generation does not generalise an
      instruction from one case to another on its own, and it does not narrow
      one either
- [ ] **Does it restate general competence?** Output templates for output that
      is not format-sensitive, step decompositions of tasks the model plans
      better itself, "be specific", "handle errors", "think step by step".
      Delete
- [ ] Procedure still earns its place when the *order* is load-bearing for a
      reason the model cannot see — "name the deriving command before running
      anything" exists because a command chosen after seeing output drifts
      toward confirming — and when an operation is fragile enough to need an
      exact script. That is a constraint overriding an instinct, not a step
- [ ] Every surviving step carries its reason in one present-tense clause. The
      reason is the behaviour's authority; the incident that motivated it is
      history and belongs in a changelog, not in the body that loads every time
- [ ] Examples earn their place by pinning a judgment boundary (this passes,
      this does not) or a genuinely format-sensitive output shape. Examples of
      judgment the model already has constrain it to the example's region
- [ ] State the negative scope: what this skill is *not* for, and which adjacent
      skill owns that instead
- [ ] Carry a scope caveat where the evidence behind a rule is narrow. A rule
      measured in one setting, or on one model, should say so rather than
      generalise silently
- [ ] **State the target behaviour.** Describe what to do rather than listing
      what not to do. Keep a prohibition only when its failure reproduces on the
      current model; one aimed at a failure the model was not going to make
      names the behaviour and anchors toward it. Where a prohibition does earn
      its place, defining the anti-pattern precisely helps more than a bare
      ban. This governs behaviour steering in a body, not the negative *scope*
      a description carries — see `description precision`
- [ ] **Structure a prompt with XML tags when it has clear sections.** A
      skill or prompt with distinct parts (parameters, scope, procedure,
      gotchas, report shape), or whose steps refer to other parts by name
      ("the test in `<verdicts>`"), puts each part in its own tag. Anthropic's
      prompting guide recommends tags for prompts that mix instructions,
      context, examples and inputs, and Opus 5.5 adds them when asked to adapt
      a prompt for itself. Use descriptive snake_case names, and reuse them
      across skills: `<parameters>`, `<how_to_run>`, `<scope>`, `<procedure>`,
      `<gotchas>`, `<report>`. A short single-purpose skill does not need
      them. Never in a `description` (angle brackets fail validation), and not
      in hook output, where a tag can pass for a harness tag and trip
      prompt-injection defences
- [ ] **One term per concept, used throughout.** Consistency is what lets the
      model parse and follow instructions. *Craft, not documented upstream:*
      prefer a pretrained word to a coined one — a term the model already holds
      (*frontier*, *tracer bullet*, *red*) recruits a region of behaviour in one
      token, while a coined word must be paid for in definition tokens. Coin one
      only when nothing existing fits
- [ ] **Every step ends on a completion criterion, and it has two dimensions.**
      *Clarity*: can the agent tell done from not-done? *Demand*: how much does
      it require — "every modified model accounted for" forces work that "produce
      a change list" does not. Demand is not step-bound; "every rule applied"
      binds a body of flat reference the same way
- [ ] **Done is printed evidence.** State the done-state as something the
      transcript can show: the command and its output, a derived count. `/goal`'s
      evaluator and prompt-based Stop hooks read only what the conversation
      surfaced; they do not run commands or read files
- [ ] **Scope is literal.** An instruction meant for every item says "every";
      the model does not extend it from the first item to the rest
- [ ] **A requirement is stated as one.** "Try to", "if possible" and "ideally"
      attached to a requirement read as permission to under-deliver
- [ ] **Emphasis marks at most one instruction**, one that a with-and-without
      run showed being skipped, and it carries its reason. Emphasis spread over
      many lines marks none of them, and an anxious register produces a
      cautious, hedging model. Routing text in a `description` is exempt: it may
      carry calibrated urgency, tuned against a trigger eval
- [ ] **Depth goes in `effort:` frontmatter; length goes in prose.** Effort does
      not reliably change visible response length, and "think carefully" prose
      does not set depth. Thinking cannot be turned off on the newest models, so
      a "don't think" rule cannot be followed either; lowering effort reduces
      thinking more reliably than prose does. A lookup the answer depends on is
      stated as required, because at low effort the model answers from memory
      more often
- [ ] **An `effort:` value is re-chosen per model, not carried.** Level names do
      not mean the same amount of thinking across models, and defaults differ:
      Claude Code starts Opus 5.5 at `medium` and most other models at `high`.
      Pin a level in frontmatter only where a with-and-without run on the
      current model showed it changes the outcome
- [ ] **Ask for evidence, never for reasoning.** Instructions to echo, transcribe
      or explain internal reasoning as response text can trigger the
      `reasoning_extraction` refusal category. Ask for the command and its output
- [ ] **Verification is a mechanism, not a reminder.** Keep gates that run a
      named command whose output decides. Prose reminders to double-check cause
      over-verification on Opus 5
- [ ] **Name the finish line and the stops.** A skill or agent that runs long
      states what done looks like and when to stop: when nothing can advance
      without the user, or before a destructive or irreversible action. Opus
      5.5 sometimes ends a turn with a report while work is still owed — a
      summary that announces the next step without taking it, an offer to
      continue, a list of decisions none of which blocks the rest, a pause at a
      milestone — and it follows instructions that name those stops. So
      "report after each phase" asks for exactly the stop it gets; ask for
      status notes in the same message as the next action instead. Where a
      human answers every turn, a one-line plan and a short recap may be the
      stops you want; say that instead
- [ ] **Long work keeps its task list in a file** the model ticks off and
      extends, not in the conversation. A file survives compaction, and it is
      what a reader checks instead of the scrollback. The built-in task tools
      are absent in interactive sessions on the Claude 5 generation (see
      `agents and tool access`), so a file is the portable form
- [ ] **Mark what could not be confirmed, and where you looked.** A research or
      audit skill asks for its unconfirmed remainder explicitly; the model
      reports it plainly when asked, and it is the part a reader most needs to
      find
- [ ] **Where a model default is the failure, name the specific patterns.**
      Frontend and design work is the documented case: with no direction the
      model falls back on a few default styles, and "avoid a generic look"
      swaps one default for another. A list of named patterns to leave out
      (a cream background, numbered section labels, pill buttons) works, and is
      extended after looking at what the model chose instead. This is the one
      standing exception to stating the target behaviour positively
- [ ] **Instructions stand.** Claude Code does not re-read a skill file on later
      turns, so write guidance that must hold across a task as standing
      instructions rather than one-time steps. Put the most important content at
      the top: compaction keeps the start of a skill (see `token budget`)
- [ ] **State it once.** Current models retain a once-stated instruction. A hook
      or skill that re-injects reminders on a cadence, or surfaces remaining
      context counts, costs context and adds nothing
- [ ] **Write as if the current rules are the only rules.** No "unlike before",
      no pinned model names, no incident IDs in a shipped body

**Premature completion** is the failure the clarity dimension guards against.
The documented counters: audit each claim against a tool result from this session before
reporting it, prefer a fresh-context verifier to self-critique, and make done a
printed-evidence state (above). *Craft, not documented upstream:* steps still
visible ahead pull attention toward being done, so a fuzzy bound invites ending
the current one early. Sharpen the bound first, because it is local and cheap;
split the sequence only if the bound is irreducibly fuzzy *and* the rush is
observed. Splitting works only across a real context boundary — a hand-off or a
subagent dispatch — because an inline call leaves the later steps in context.

**Where verification runs is decided by authorship, then by isolation, and
last by size.** Anthropic's Opus 5 guidance keeps verification in the main
loop; its Fable 5 guidance finds fresh-context verifiers beat self-critique;
its Opus 5.5 guidance fans work out and keeps acceptance in the lead. They
agree once the question is who produced the subject. *Craft, reasoned from
those sources and not yet measured here:*

- **The judging context produced the subject** — wrote the prose, made the
  change, chose the threshold, earlier in this session: the judgment goes to
  one fresh-context verifier for the whole set. Brief it with the claims and
  where the evidence lives, never with the reasoning that produced them.
  Independence is the benefit, and one extra startup buys it
- **Items interfere with each other** — each mutates files, each needs its
  own scratch worktree: one dispatch per item, run in parallel
- **The set is large and spans independent units:** fan out per unit. Each
  dispatch pays its own startup context (system prompt, tools, CLAUDE.md),
  so per-item fan-out multiplies that fixed cost by the item count; below
  that size, stay in one context
- **Otherwise** the main context verifies, by running the command whose
  output decides
- **In every case the lead checks each report's evidence before accepting
  it.** A subagent's report arrives framed as data; its verdict is a claim
  like any other

A skill that dispatches says which case it is in and why, in its own words:
the gate differs per subject, so each skill states its own rather than
pointing at a shared copy.

**Unattended runs end on a text-only turn.** In `-p`, a routine, or an eval
case, a turn that ends with a progress report ends the run. A skill used there
carries its completion condition in the prompt and names the early stops it
does not want (above). A harness that continues the model automatically treats
a text-only end of turn as a report rather than proof of completion, sends the
open items back as the next message, and gives up after two or three
continuations on the same task so a genuinely stuck run ends and can be read.

**Retrieval has a boundary.** Prefer a skill over the model's innate knowledge
for knowledge that is versioned, project-specific, contested, or newer than the
model. Do not write one for general competence. Ask before writing, not after it
underperforms: what does this supply that the model cannot derive? If the answer
is nothing, it is friction rather than retrieval.

Sources, read 2026-09-21: the platform prompting pages for Opus 5, Fable 5,
Fable 5.1 and general best practices; the `claude-api` skill's
`shared/model-migration.md` and `shared/prompt-audit.md` (`coderef/skills`
@34040c9); the Agent Skills authoring best practices; "The new rules of context
engineering for Claude 5 generation models" (claude.com, 2026-07-24); Claude
Code's `skills`, `best-practices`, `model-config`, `goal` and `context-window`
pages. Read 2026-09-24 for Opus 5.5: the platform's "Prompting Claude Opus 5.5"
and "What's new in Claude Opus 5.5" pages; "Getting the most out of Opus 5.5 in
Claude and Claude Code" (claude.dev, 2026-09-22); the `claude-api` skill's Opus
5.5 migration section and `prompt-audit.md` on the unmerged
`rlm/claude-api-opus-5-5` branch of `anthropics/skills` (@1e24228); Claude
Code's `model-config` and `prompt-caching` pages. The completion-criterion dimensions were adapted from
`mattpocock/skills` (`skills/productivity/writing-for-agents`, MIT).

## part 1 — constraints

### always-loaded context

<!-- class: harness | source: https://code.claude.com/docs/en/memory | verified_hash: b29ff4b8c98da990 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: ecb008122d18c786 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/context-window | verified_hash: 89745e68e4278163 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 8f9d04b404db0517 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/output-styles | verified_hash: f9cc8ce8c625d657 | last_verified: 2026-09-24 -->

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
      `paths` frontmatter — **except a rule that must survive compaction.**
      Path-scoped rules and nested CLAUDE.md files load into message history
      when their trigger file is read, so compaction summarises them away. Drop
      `paths:` or move such a rule to the project-root CLAUDE.md
- [ ] **A rule whose frontmatter does not parse loads unconditionally** — as if
      it had no `paths` — with no error in the session (silent; `claude
      --debug` shows it). `paths` is the only field a rule reads; any other is
      ignored
- [ ] **User and project rules do not override each other.** Where they
      conflict, Claude may follow either. A plugin that installs a rule into a
      repo checks for a user rule covering the same ground
- [ ] Skill descriptions (all listed) each justify their share of the listing
      budget
- [ ] Custom subagent descriptions have their own budget: Claude Code warns at
      startup when their combined descriptions exceed **15,000 tokens**. Keep
      them short and move detail into the agent body, which loads only when the
      agent runs
- [ ] `settings.json`: no ambient hooks on high-frequency events without
      documented justification
- [ ] Auto-memory `MEMORY.md` stays under 200 lines OR 25KB, whichever comes
      first — content past the cap is not loaded at all. Detailed topic files sit
      beside it and load on demand
- [ ] **`AGENTS.md`.** Claude Code reads `AGENTS.md` directly (v2.1.277+), but
      by default only when no `CLAUDE.md` or `CLAUDE.local.md` exists in the
      working directory or above it, and not where the built-in `agents-md`
      plugin is disabled (before v2.1.281, also not on Bedrock or with
      telemetry off). Where a repo keeps both files, the project CLAUDE.md
      imports it with `@AGENTS.md`; the import never causes a double read and
      is the only path that works everywhere. Adding a personal
      `CLAUDE.local.md` to an `AGENTS.md`-only repo silently stops `AGENTS.md`
      loading for you. Prefer the import over `ln -s AGENTS.md CLAUDE.md`: a
      symlink on Windows needs Administrator or Developer Mode, and git checks a
      committed symlink out as a one-line text file unless `core.symlinks` is on
- [ ] Imports recurse to a maximum depth of **four** hops, and relative paths
      resolve against the importing file, not the working directory. An import
      chain deeper than that silently stops resolving
- [ ] A rule file symlinked in from outside the working directory is treated as
      an external import: it does not load until external imports are approved
      for the project, then only if it has no `paths` field, and a symlink alone
      never triggers the approval prompt. Shared rules linked in this way can
      stay silently unloaded
- [ ] A rule earns its tier: mechanically detectable violation belongs in a
      `PreToolUse` block, a detectable condition in a `PostToolUse` notice, and
      only what is neither becomes ambient prose — and ambient is a *pointer*,
      one line, not the content. Cost is *emission*, not invocation: a hook
      that fires and stays silent is nearly free, while an emitter on every
      session is not. Plain stdout enters context on four events:
      `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart` and
      `PostModelSwitch`. The last two fire with no prompt at all —
      `SessionStart` re-fires on resume, fork, clear and compact, and
      `PostModelSwitch` fires when resume restores the model. A `SessionStart`
      hook needed once sets matcher `startup`. The measurement behind the rule
      lives in `docs/internals/context-cost.md`
- [ ] **Two plugin surfaces emit outside the hook events.** A plugin
      `monitor` delivers every stdout line to Claude as a notification for the
      life of the session; start it with `when: "on-skill-invoke:<skill>"`
      rather than the default `always` unless every session needs it. An
      output style with `force-for-plugin: true` overrides the user's chosen
      style and is sent with every request

### hooks

<!-- class: harness | source: https://code.claude.com/docs/en/hooks | verified_hash: e181a8c5bbc57b0c | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/hooks-guide | verified_hash: 4b9d3d1063fd0603 | last_verified: 2026-09-21 -->
<!-- class: harness | source: https://code.claude.com/docs/en/permissions | verified_hash: 08564580476a705f | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/mcp | verified_hash: bc102386c0362a4a | last_verified: 2026-09-24 -->

**Enforced by: nothing.** Every item here is authoring discipline. Several fail
*silently* — marked (silent) — which is why they are constraints rather than
guidance.

- [ ] Hook `timeout` is in **seconds**, not milliseconds. `3000` is fifty
      minutes. Defaults are per type and per event: 600 for `command`, `http`,
      `mcp_tool`; 30 for `prompt`; 60 for `agent`. `UserPromptSubmit`,
      `PreModelSwitch` and `PostModelSwitch` lower the command/http/mcp_tool
      default to 30, and `MessageDisplay` lowers it to 10. The timeout is not
      enforced on a command hook run with `async: true`; it is enforced on one
      run with `asyncRewake`
- [ ] **A timed-out hook renders no decision.** Claude Code cancels a
      `command`, `http` or `mcp_tool` hook at its timeout and discards its
      output. On `PreToolUse` the call then continues through the normal
      permission flow, so a stalled hook is not a gate. On `UserPromptSubmit`
      the prompt proceeds without the hook's `additionalContext`; on
      `MessageDisplay` the original text shows. The one fail-closed command-hook
      event is `PreModelSwitch`: a hook canceled at its timeout blocks the
      switch
- [ ] Agent SDK **callback** hooks are a different surface and fail *closed*: a
      `UserPromptSubmit` callback timeout blocks the prompt, and a `PreToolUse`
      callback timeout blocks the tool call. Do not reason from one surface to
      the other
- [ ] Because a gating command hook fails open at timeout, pick the value so it
      cannot matter: for anything that **gates**, err long. Too-short plus
      fails-open is a silent bypass. Measure the hook, then leave generous
      headroom
- [ ] **JSON on stdout is read on every exit code, not just 0.** For events on
      the standard decision model, a JSON object that passes schema validation
      decides the outcome whatever the exit code; exit 2's block is the one
      outcome JSON cannot override. Exit 0 = no decision reported — for
      `PreToolUse` it does NOT approve the call. Without valid JSON, exit 2
      blocks and any other non-zero exit is a non-blocking error, so never use
      exit 1 to gate. A mistyped hook path exits 127 into the same non-blocking
      bucket and leaves the gate silently disabled (silent)
- [ ] **JSON-shaped stdout that fails to parse is dropped, not shown.** Stdout
      that starts with `{` and ends with `}` is parsed as JSON; on the events
      that add plain stdout as context, a parse failure adds nothing (v2.1.248+).
      A decision field such as `permissionDecision` or `additionalContext`
      placed at the top level instead of inside `hookSpecificOutput` is ignored
      without an error (silent)
- [ ] Per-event exceptions: `WorktreeCreate` fails creation on any non-zero
      exit, and `WorktreeRemove` fails removal on any non-zero exit if the
      directory still exists. `Setup` cannot block, ignores its exit code and
      stderr, and discards its JSON output. `PermissionRequest` does not honour
      exit 2 at all — deny through the `decision` object (silent)
- [ ] Exit 2 does not reach Claude on every event. For `SessionStart`,
      `SubagentStart` and `PostModelSwitch` its stderr renders as a hook-error
      notice to the user and Claude never sees it — a hook trying to inject a
      correction there is talking to the wrong audience. On `UserPromptSubmit`
      the block message shows the stderr to the user and does not add it to
      context. For `SubagentStart` the notice lands in the subagent's transcript
- [ ] `asyncRewake: true` runs the hook in the background and wakes Claude on
      exit 2, surfacing stderr (or stdout when stderr is empty) as a system
      reminder. It is the supported shape for a long-running check that must
      still be able to report a failure. Its `timeout` still applies
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
      commands. A permission deny rule is not a hard boundary either: it covers
      the invocation Claude usually produces, not the same program run another
      way. Sandboxing is the boundary (silent)
- [ ] `if` file patterns are rooted at the working directory: `Edit(src/**)`
      matches only top-level `src`. Use `Edit(**/src/**)` for any depth (silent).
      This is v2.1.214+ behaviour; earlier versions matched at any depth, so a
      pattern written before then quietly narrowed
- [ ] `if` holds **exactly one** permission rule. There is no `&&`, `||`, or list
      syntax — multiple conditions need one handler each (silent)
- [ ] Plugin-bundled MCP tools are named `mcp__plugin_<plugin>_<server>__<tool>`,
      in matchers and in `if` alike. A matcher written against the bare server
      key never fires for them (silent). Key trust decisions on the
      `mcp_server.source` field in the hook input, not on the server name or the
      `mcp__<server>__` prefix
- [ ] `mcp_tool` hooks are skipped on `Setup` every time and on `SessionStart`
      at launch, because the servers are not up yet (silent)
- [ ] `${user_config.*}` is rejected in shell-form plugin hook commands
      (v2.1.207+). Read `$CLAUDE_PLUGIN_OPTION_<KEY>` instead, or set `args` to
      switch to exec form
- [ ] `once: true` is only honoured inside **skill** frontmatter, and removes the
      hook after its first *successful* run; a run that fails, blocks with exit
      2, or times out leaves it in place. Ignored in `settings.json`, plugin
      `hooks.json`, AND agent frontmatter (silent)
- [ ] **Skill-frontmatter hooks outlive the skill.** Once the skill is invoked,
      its hooks keep running for the rest of the session, on later turns too.
      After one invocation they are an ambient cost; use `once: true` or design
      for that
- [ ] `SessionEnd` hooks share a 1.5-second budget, raised to match the highest
      per-hook `timeout` in settings up to 60 seconds. Timeouts set on
      **plugin-provided** hooks do not raise it, so a plugin's `SessionEnd` hook
      gets 1.5 seconds (silent)
- [ ] A gating `Stop` hook checks `stop_hook_active` and stands down when it is
      true, or it blocks on a condition that never resolves. Claude Code
      overrides a `Stop` or `SubagentStop` hook after 8 consecutive blocks
      (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`; `0` disables the cap)
- [ ] **`SubagentStop` also fires for Claude Code's internal agents** — prompt
      suggestions, `/btw` — with `agent_type` set to the session's own agent
      name or `""`. A matcher that is omitted, `""`, `"*"`, or a regex matching
      the empty string runs for those too. Name the agent types a
      `SubagentStop` hook is for (silent)
- [ ] **A `UserPromptSubmit` hook that parses `prompt` allows for pasted
      blocks.** Collapsed pastes arrive expanded, and where Claude Code marks
      pasted text they sit between `<pasted_content id="…">` and
      `</pasted_content id="…">` lines. The same marking is the pattern for
      text a plugin injects that the user did not write — web pages, email, a
      foreign model's output: wrap it with a matching random id and say that
      instructions inside it are not the user's. Opus 5.5 resists instructions
      inside marked text; the tags are plain text and can be imitated, so this
      is one guardrail, not a boundary
- [ ] A hook reading a subagent's result must read the `SubagentHandback` call,
      not `last_assistant_message`: where the subagent hands back (auto mode,
      v2.1.271+), `last_assistant_message` holds its closing text, "not the
      delivered report". A `PreToolUse`/`PostToolUse` hook matched on
      `SubagentHandback` receives the report as `tool_input.message` (silent)
- [ ] Hook output strings (`additionalContext`, `systemMessage`, stdout) are
      capped at 10,000 characters; overflow spills to a file and is replaced with
      a preview plus path. No setting raises it. Cap your own output well below
- [ ] Hook output is minimal — one line of stderr, not paragraphs of context
- [ ] Hook purpose and trigger are documented in the README or inline
- [ ] Model-facing text is factual statements, not imperatives. `additionalContext`
      framed as out-of-band commands can trip prompt-injection defenses and get
      surfaced to the user's terminal instead of read by the model, silently
      converting a model-facing control into a user-facing one

### agents and tool access

<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: ecb008122d18c786 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/tools-reference | verified_hash: 85c992a32373995c | last_verified: 2026-09-21 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 8f9d04b404db0517 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/worktrees | verified_hash: c4647433bd18497b | last_verified: 2026-09-24 -->

**Enforced by: nothing.**

- [ ] `tools` is an allowlist, `disallowedTools` a denylist. With both set the
      denylist applies first; a tool in both is removed. A `disallowedTools`
      entry with a specifier, such as `Bash(git push *)`, removes the **whole**
      tool, not only the matching commands
- [ ] Set `tools` explicitly on read-only agents. Omitting it inherits
      everything, including Write/Edit and all MCP tools
- [ ] **Most subagents run in the background, and background changes the tool
      set.** Where fork mode is on — the default in interactive sessions since
      v2.1.232 — Claude Code runs every subagent Claude spawns in the background
      and Claude cannot ask for the foreground. With fork mode off (`-p`, the
      Agent SDK) Claude chooses, and the `background: true` field forces
      background. There is no `background: false` for agents; the only way to
      force foreground is `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, which applies
      to every subagent
- [ ] **`tools` is not the last word — two filters run after it.** The first
      removes a fixed list from every subagent (see the reference) even when you
      list it. The second applies to background subagents other than forks and
      resumed foreground subagents: apart from `Agent` and `ExitPlanMode`, a
      background subagent keeps every MCP tool but only these built-ins —
      `Read`, `Grep`, `Glob`, `LSP` (v2.1.280+), `Bash`, `PowerShell`, `Edit`, `Write`,
      `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`,
      `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`,
      `SendMessage`, `Artifact`, plus `SubagentHandback`. Everything else is
      removed whether inherited or explicitly listed, **and the removal reports
      no error** unless it empties the list
- [ ] The tool list works the other way too: in auto mode (v2.1.271+) Claude
      Code gives a locally run, non-fork subagent `SubagentHandback` even when it
      is absent from `tools` or listed in `disallowedTools`
- [ ] **The task-tracking tools are absent from interactive sessions on
      current models.** `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList` and
      `TodoWrite` are available by default only on Claude 3.x, Opus 4 through
      4.7, Sonnet 4 through 4.6 and Haiku 4.5, and a session without them does
      not give them to subagents either. Background and cloud sessions provide
      them on every model, and `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` opts a user
      in. So an instruction to track work with them works in some sessions and
      is dead in the rest; a task file works in all of them (see `authoring
      shape`)
- [ ] **A subagent's report reaches the lead as data.** It arrives under a
      header stating that instructions or approval claims inside it carry no
      authority, and a background subagent's report arrives inside a
      notification marked as an automated event. An agent whose output is
      meant to steer the main loop — an advisor, a reviewer — states findings
      and evidence for the lead to act on, not directives
- [ ] **A family alias can resolve to the main model.** `model: opus` on a
      subagent runs on the main conversation's exact model, `[1m]` suffix
      included, when the main model is in that family. Only
      `CLAUDE_CODE_SUBAGENT_MODEL` always resolves an alias to its current
      version. A tiering design that relies on `opus` meaning one specific
      model pins a full model ID
- [ ] Forks skip both filters and receive the main conversation's exact tool
      pool. Agent-team teammates additionally keep `TaskCreate`, `TaskGet`,
      `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, `CronList` — where
      the session has the task tools at all
- [ ] If NO entry in `tools` resolves, the subagent *usually* fails to launch
      with an error naming the unresolved entries. Upstream hedges this word;
      before v2.1.208 such a subagent launched tool-less and returned empty or
      confusing results
- [ ] **`permissionMode` is ignored under auto mode**, which is the default mode
      on Pro, Max and Team plans: when the main conversation is in
      `bypassPermissions`, `acceptEdits` or auto mode, the subagent runs in that
      mode and the field has no effect
- [ ] **A plugin agent whose frontmatter does not parse still loads — with every
      field ignored.** It is named after the file, described as `Agent from
      <plugin> plugin`, and its `tools` allowlist is gone, so a read-only agent
      silently inherits everything. Project and user agents with bad
      frontmatter, or a `name` without a `description`, are skipped with no
      message in the session (silent). `claude plugin validate <agents dir>`
      catches the parse failure; it does not flag a file that parses but has no
      `name`
- [ ] The `skills` field only preloads skills — the full content, not just the
      description — and does not gate access. Subagents can still invoke
      unlisted project, user, and plugin skills through the Skill tool. To block
      that, omit `Skill` from `tools` or add it to `disallowedTools`
- [ ] An agent `name` cannot contain `:`, which is reserved for plugin-scoped
      identifiers. A file whose name contains one is not loaded and the error
      goes to the debug log only (v2.1.218+)
- [ ] `allowed-tools` on a *skill* **grants pre-approval**; it does not restrict.
      Every tool stays callable. `disallowed-tools` is the field that restricts.
      Both are scoped to the invoking turn and clear on the next user message,
      even though skill content stays in context. Workspace trust does not gate
      `allowed-tools`, including in a `-p` run in a never-trusted folder, so
      scope a Bash grant to the exact bundled script path, never a bare `Bash`
- [ ] `isolation: worktree` branches from the DEFAULT branch, not the parent
      session's HEAD, unless `worktree.baseRef` is set to `"head"`. A worktree is
      a fresh checkout: gitignored files are absent unless listed in
      `.worktreeinclude`, and under `worktree.sparsePaths` only the listed
      directories plus root-level files exist. The exception is
      `.claude/skills`, `.claude/agents` and `.claude/commands`: when the
      worktree has no `.claude/skills` at its root, the main checkout's
      project skills load instead (v2.1.277+); a worktree with its own copy
      loads only that
- [ ] Plugin-shipped agents silently ignore `hooks`, `mcpServers`,
      `permissionMode` and `initialPrompt`. Subfolders of a plugin's `agents/`
      load recursively and join into the name with colons:
      `agents/review/security.md` loads as `<plugin>:review:security`

### skill and plugin structure

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 8f9d04b404db0517 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugin-marketplaces | verified_hash: c613ce8f2c87c788 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/prompt-caching | verified_hash: 0cf434f5e388492e | last_verified: 2026-09-24 -->
<!-- class: harness | source: coderef/agentskills | verified_hash: 69ef37e | last_verified: 2026-09-21 -->
<!-- class: craft | note: the no-README and references/ layout rules are house conventions | last_verified: 2026-08-07 -->

**Enforced by:** `skill-maintain validate` (name rules, allowed fields,
description constraints) and the repo-hygiene suite (marketplace listing,
manifest fields). This is the best-covered section in the file.

- [ ] `SKILL.md`, exact case, in a kebab-case folder whose name matches the
      skill `name`
- [ ] YAML frontmatter with `---` delimiters, and the opening `---` on the
      file's **first line**. Anything before it — a blank line, a comment — and
      Claude Code reads the whole file, markers included, as skill content with
      no frontmatter at all (silent)
- [ ] **Frontmatter that does not parse leaves the skill loaded with no fields
      set**: `/name` still works, but there is no `description` to match, so it
      never auto-triggers (silent). A misspelled field name is ignored the same
      way. `claude plugin validate <skills-dir>` finds both
- [ ] `description` under 1024 characters, no angle brackets
- [ ] **A failing `!` command aborts the whole invocation.** Claude never sees
      the skill content. With the default `bash` shell any non-zero exit fails
      (search and comparison commands get exit 1 as a normal result); append
      `|| true` to a command expected to exit non-zero, such as a check script.
      Outside auto mode, a permission check on an injected command that returns
      anything but allow also aborts — including a rule that would normally ask —
      so pre-approve it with `allowed-tools`
- [ ] **A skill's `model` frontmatter is a cache miss.** When it names a model
      other than the session's, that turn is a model switch and the next request
      re-reads the whole conversation with no cache hits. Set `model` only with
      `context: fork`, where it sets the forked subagent's model instead
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
- [ ] **A display field set on the marketplace entry overrides `plugin.json`**
      — `displayName`, `description`, `author`, `homepage`, `repository`,
      `license`, `keywords` — in listings and details, before and after install.
      A field the entry leaves unset falls back to `plugin.json` (readable before
      install only for a relative-path source). `version` runs the other way:
      `plugin.json` wins. Set each display field in one place; two copies drift
      and users see the one nobody edits
- [ ] **A new source type breaks the whole marketplace for older clients.** A
      marketplace containing an `archive` entry fails to load entirely on
      versions before v2.1.120; `command` sources behave the same way. Adopt one
      only when the users you care about are on a version that supports it
- [ ] Marketplace clones never fetch Git LFS content; LFS-tracked files arrive
      as pointer files. Keep what a plugin needs out of LFS
- [ ] **A `userConfig` field with `options` that breaks a rule stops the plugin
      loading.** The field is `type: string`, not `multiple` or `sensitive`,
      and its `default` is one of the options (or it is `required`). Declaring
      `options` at all locks out clients before v2.1.271
- [ ] Plugin Node dependencies install only when the plugin **root** holds both
      a `package.json` and a supported lockfile, and install scripts never run.
      A `package.json` without a lockfile is skipped without a log entry

### MCP servers a plugin bundles

<!-- class: harness | source: coderef/mcp/modelcontextprotocol | verified_hash: 24efd6e7 | last_verified: 2026-09-21 -->
<!-- class: harness | source: https://code.claude.com/docs/en/mcp | verified_hash: bc102386c0362a4a | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/prompt-caching | verified_hash: 0cf434f5e388492e | last_verified: 2026-09-24 -->

**Enforced by: nothing.**

MCP revision `2026-07-28` removes protocol-level sessions and the `initialize`
handshake: every request carries its own protocol version and client
capabilities, and "an open connection, such as a STDIO process, is not a
conversation or session". Claude Code's v2 MCP client speaks it and is the
default in every session since v2.1.274. It asks HTTP servers whether they
support the new revision; stdio servers stay on the legacy handshake unless
`MCP_PROTOCOL_NEGOTIATION` is `auto`. Write servers so they are correct under
both.

- [ ] **No state keyed to a connection, process or session.** Servers "MUST NOT
      rely on prior requests over the same connection to establish context".
      State that spans calls is an explicit handle: a creation tool returns it,
      later calls take it as an argument, the creation tool's description states
      its lifetime, and an expired handle errors by name. Ship a way to list or
      recover live handles — Claude Code clears older tool outputs before it
      summarises, so a handle that exists only in an old result is lost
- [ ] **`tools/list` does not vary per connection or as a side effect of other
      calls**, and returns tools in a deterministic order. It may vary by the
      authorization on the request. Beyond correctness, an unstable list is a
      cache cost for any server loaded into the prompt prefix (below)
- [ ] **Build nothing new on Roots, Sampling, MCP logging, or server-initiated
      requests.** Roots, Sampling and Logging are deprecated (SEP-2577), and on
      the new revision a server may not send requests to the client at all —
      input it needs comes back through a result the client answers. Log to
      stderr; take directories as tool parameters or config. Upstream conflict,
      recorded: Claude Code's MCP page still recommends `roots/list` for a
      server that limits its own filesystem access, and it works today on both
      revisions
- [ ] **A channel server must answer the legacy `initialize`.** The new revision
      cannot carry channel messages, so Claude Code does not register a channel
      server that negotiates it
- [ ] **Long-running work uses progress notifications and the per-server
      `timeout`, not the Tasks extension.** Neither Claude Code nor the Python
      SDK implements Tasks (SEP-2663). Claude Code moves a main-conversation
      call still running after two minutes to a background task on its own
- [ ] **`mcp` for Python 1.x to 2.x is a migration, not a version bump.**
      `FastMCP` becomes `MCPServer`, `get_context()` is replaced by an injected
      `ctx` parameter, and on a 2026-07-28 connection `ctx.elicit()` raises
      `NoBackChannelError`. The 1.x line receives only critical and security
      fixes. Pin an application's SDK exactly
- [ ] **`alwaysLoad` puts a server's tools in the cached prefix.** With the
      default deferred loading, a server connecting or changing its tools only
      appends. Loaded into the prefix, any change to the tools — a reconnect, a
      `list_changed` — invalidates the cache for the whole conversation
- [ ] **A tool description is a contract, not a behaviour channel.** It says
      what the tool does, when to call it and when not to, what each parameter
      means, and what it does not return. Anthropic's MCP directory review
      treats behavioural instructions in a description ("always do X", "call Y
      first") as prompt injection (`mcp-server-dev` plugin,
      `references/tool-design.md`). Put critical detail first: descriptions and
      server instructions are cut at 2,048 characters by default, a limit the
      user, not the server, can change

### unattended and scripted runs

<!-- class: harness | source: https://code.claude.com/docs/en/headless | verified_hash: 0431751667c7fd47 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/hooks | verified_hash: e181a8c5bbc57b0c | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/goal | verified_hash: bb3babb6669f7bf0 | last_verified: 2026-09-21 -->

**Enforced by: nothing.** A plugin's own eval runs are unattended runs, so these
bite at test time as well as in production.

- [ ] **A plugin hook is not a CI enforcement boundary.** `--bare` skips hooks,
      skills, plugins, MCP servers, auto memory and CLAUDE.md, is the
      recommended mode for scripted and SDK calls, and is slated to become the
      default for `-p`. A rule that must hold in scripted runs belongs in a git
      hook or a CI step
- [ ] **A step that needs a human answer states what happens without one.** In
      `-p`, `AskUserQuestion` and `ExitPlanMode` are offered only when the run
      has a permission host to receive the prompt. `claude plugin eval` runs
      never stop to ask: tools that would need a grant are removed and only the
      case's allowlisted read-only tools remain. A routine's fired prompt cannot
      stand in for consent
- [ ] An MCP tool marked `requiresUserInteraction` prompts on every call and is
      denied under `dontAsk` even when an allow rule matches, so scheduled and
      locked-down runs that call it stall or fail
- [ ] `/goal` is a session-scoped prompt-based Stop hook, and its evaluator
      judges only what the conversation surfaced. A skill used under a goal
      prints its evidence (see `authoring shape`)

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
      over its confident region and make it *silent* elsewhere — or hand the
      uncertain region to a real measurement. A warning band over the uncertain
      region is the worst option available: it trains people to skim the
      output, destroying the loud case too. The token-budget gate below is the
      worked instance
- [ ] **Prefer a fixture that cannot collide over one that probably will not.** A
      control right 97% of the time teaches people to re-run it until it agrees
- [ ] **Bracket the control itself**: prove it can go red, pin its silent edges,
      and check that any examples its messages cite still resolve
- [ ] **Live-fire a new gate once.** A mistyped hook path is a non-blocking
      error, so a gate that never fired may never have been installed

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

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/context-window | verified_hash: 89745e68e4278163 | last_verified: 2026-09-24 -->
<!-- class: harness | source: coderef/agentskills | verified_hash: 69ef37e | last_verified: 2026-09-21 -->
<!-- class: craft | note: the 4,000/8,000 token thresholds and the estimator band are house conventions | last_verified: 2026-09-21 -->

**Command:** `skill-maintain test` (the gate) and `skill-maintain quality` (the
report). For a real count, `claude plugin details <plugin>` on the installed
build.

Thresholds apply to SKILL.md only, which is always loaded once the skill
triggers. Reference files are on-demand and tracked separately, so thorough
reference material is not penalised — that is what progressive disclosure is for.

**Exactly one of these numbers is gated: 5,000 tokens per SKILL.md, and two
independent sources converge on it.**

- **Recommendation.** The Agent Skills spec: "Instructions (< 5000 tokens
  recommended): The full `SKILL.md` body is loaded when the skill is
  activated", and its best-practices page, "under 500 lines and 5,000 tokens".
  Anthropic's Agent Skills overview lists level-2 instructions at "Under 5k
  tokens". This figure is tokenizer-agnostic
- **Mechanism.** After auto-compaction Claude Code re-attaches the most recent
  invocation of each skill, "keeping the first 5,000 tokens of each", and all
  re-attached skills share a 25,000-token budget filled from the most recently
  invoked. Past the cut, a skill loses its tail in any session that compacts —
  and the tail is often the reference map and the done-criterion — while
  invoking many skills drops the older ones entirely. This is a hard cut in
  Claude's own tokens, and a fixed number, not a fraction of the window

Upstream (`harness`):

- [ ] SKILL.md under **5,000 tokens** — the gate
- [ ] SKILL.md body under **500 lines**. Upstream's own guidance in both the
      spec and Claude Code's docs; move detailed reference material to separate
      files
- [ ] If a skill must run long, its first 5,000 tokens carry everything that
      has to survive compaction

**The estimate decides only where it is certain** (`craft`). Characters per
token vary with content: measured against `claude plugin details` on
2026-09-21, dense technical skills ran near 2.65 characters per token and plain
prose near 4.3, so the old flat `chars / 4` passed skills that the first-party
count put over the cut. The gate therefore reads SKILL.md characters three ways:

| Characters | Verdict |
|---|---|
| over the limit even at 4.5 per token | red — truncated on re-attach |
| under the limit even at 2.65 per token | green |
| between | unverified: passes, and the report names `claude plugin details` as the measurement |

A passing run states how many skills were certainly under and how many are
unverified, so an unverified skill is visible without training anyone to skim
a warning. Re-derive the two ratios if the tokenizer changes.

House convention (`craft`) — reported, never gated. Do not cite these as
platform limits, and do not fail a board on them:

- [ ] SKILL.md under 4,000 tokens (2% of a 200k window)
- [ ] SKILL.md under 8,000 tokens, the old hard ceiling
- [ ] Heavy material in `references/`, not inline
- [ ] Reference tokens reported but not budget-warned

**Why the gate sits where it does, recorded because the failure was
instructive.** It used to fire at 4,000. That number is an opinion about
attention, and it sat red on two skills that were 0.8% and 2.3% over — for long
enough that the red stopped carrying information — while the skill *listing*,
which is loaded unconditionally every session, went unmeasured. A board that is
permanently red about a house preference trains people to skim it. Demoted
2026-08-13; the boundary is pinned by `test_token_budget_gate.py`, whose
red-side arm exists because a threshold change is exactly the edit that can
silently stop gating anything.

### behaviour eval

<!-- class: harness | source: https://code.claude.com/docs/en/plugin-evals | verified_hash: 890b944094ea57f5 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->

**Command:** `claude plugin eval <plugin-dir>` (v2.1.269+); `claude plugin eval
init` drafts a suite.

The with-and-without comparison that `authoring shape` and `description
precision` rely on. Each case runs in a fresh, isolated `claude -p` session with
only the plugin loaded, by default once more without it, and the difference is
what the plugin contributed. It exits non-zero below `--threshold`, so it gates
CI. For iterating on one skill inside a conversation, `skill-creator` runs a
similar loop in its own format; the two are not interchangeable.

- [ ] Keep the baseline arm on, and pin `--model` per target model, so a model
      rollout is not mistaken for a plugin regression
- [ ] Trigger checks use a `tool_used` grader on `Skill`. It is excluded from the
      score in both arms, so it reports whether the skill fired without
      inflating the difference. A must-not-trigger case sets `arm: both` with
      `min: 0` and `max: 0`
- [ ] The default `--threshold` is 1.0: any case below perfect exits 1
- [ ] A rate-limited run still finishes and is not marked `partial`, so it can
      read as a regression. Re-run before believing a drop
- [ ] The eval session loads none of the user's settings, hooks, CLAUDE.md,
      memory, MCP servers or other plugins. A skill that depends on its repo's
      hooks is measured without them
- [ ] Re-run on every model release and every change of default model
- [ ] Every run, and every model-judged grader, is a real model call on your
      account
- [ ] **A plugin's real MCP servers do not start in an eval.** Each server is
      replaced by a stand-in, and a tool with no mock file at
      `evals/mocks/<server>/<tool>.md` is not available to Claude at all. A
      plugin whose skills call its own server needs mocks, or an explicit
      `--allow-real-servers`, or the case measures a plugin with its tools
      missing
- [ ] The Artifact tool is off in eval runs: a skill that publishes a page is
      graded only on what it produces before that step
- [ ] In CI, pass `--trust-plugin` and `--json`, and pin both models

### description precision

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: craft | note: only the 1,536-char cap is upstream; the rest is authoring judgment | last_verified: 2026-09-21 -->

**Command:** `skill-maintain validate` (quality warnings); `claude plugin eval`
with `tool_used: Skill` graders after every description change (see
`behaviour eval`); `skill-creator`'s description-tuning loop for iteration.

A description is a reverse query: it describes the set of user intents that
should match. Vague descriptions overtrigger; missing trigger phrases
undertrigger.

- [ ] States WHAT it does, with action verbs, in third person — the description
      is injected into the system prompt, and a shifting point of view hurts
      discovery
- [ ] States WHEN to use it, naming the **categories of intent** it serves with
      phrases users actually type. A growing list of near-synonymous phrases,
      one added per missed trigger, generalises worse than the category
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
manage the total at the set level — fewer listed entries — not by shortening the
descriptions that are earning their length.

The negative scope required here is routing metadata read by a selector. It is
not the behavioural prohibition that `authoring shape` tells you to avoid; those
operate on different surfaces and neither licenses the other.

Diagnosing which way it is failing: skills that do not load when they should,
users manually enabling them, and questions about when to use it are
undertriggering — add trigger phrases. Skills loading for irrelevant queries,
users disabling them, and confusion about purpose are overtriggering — add
negative scope. Zero invocations — which `/skill-doctor` flags — is ambiguous
between the two and needs a trigger eval to separate, not a guess.

### versioning and packaging

<!-- class: craft | last_verified: 2026-08-04 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 8f9d04b404db0517 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugin-marketplaces | verified_hash: c613ce8f2c87c788 | last_verified: 2026-09-24 -->

**Command:** `skill-maintain quality` (version alignment); `claude plugin
validate <plugin-dir> --strict` per plugin, plus whatever pre-commit gate the
repo installs.

- [ ] A content change cascades to every copy of the version that can drift —
      the plugin manifest, the marketplace entry, a changelog entry, and any
      `pyproject.toml` or authored `package.json` under the plugin source
- [ ] SKILL.md is deliberately NOT in that cascade
- [ ] Without the bump, a marketplace update never reaches installed users of a
      copied plugin. The exceptions are not pinned by version: a `command`
      source, and a plugin loaded in place from a local-directory marketplace,
      whose edits apply at the next session start or `/reload-plugins`
- [ ] Check what the marketplace `source` actually ships before cascading — a
      tool that ships separately versions independently from the plugin that
      references it
- [ ] One changelog, at the repo root. A second copy earns its place only if it
      has a consumer other than the check confirming it is a copy
- [ ] **Validate each plugin directory, not only the marketplace root.** From a
      marketplace directory, `claude plugin validate` does not open the plugins'
      skill, agent, command or hook files. `--strict` promotes warnings to
      errors; exit 0 passes, 1 fails, 2 means the run itself failed

## part 3 — reference

Look these up. There is nothing here to verify.

### skill frontmatter fields

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: coderef/agentskills | verified_hash: 69ef37e | last_verified: 2026-09-21 -->

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
| `description` | under 1024 chars, no `<` or `>`. If omitted, the first non-empty line of the body |
| `when_to_use` | appended to `description` in the listing; counts toward the 1,536-char cap |
| `metadata` | key-value pairs only |
| `compatibility` | under 500 chars |
| `disable-model-invocation` | removes the skill from the listing entirely and leaves it user-invoked only. Also blocks subagent preloading and scheduled-task auto-run; still runs from `claude -p "/name"` |
| `user-invocable: false` | background knowledge: hidden from the `/` menu, and typing `/name` does not run it |
| `context: fork` | runs the skill in an isolated subagent. Despite the name, not a fork of the current conversation: the subagent does not receive what you have discussed. Backgrounded, it gets the narrower background tool set (set `background: false` to keep the full set), and its edits fall outside the session's checkpoints, so `/rewind` does not undo them |
| `hooks` | registered on invocation and kept for the rest of the session |
| `paths` | scopes auto-activation to matching files |

### agent frontmatter fields

<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: ecb008122d18c786 | last_verified: 2026-09-24 -->

A separate surface from skills. Only `name` and `description` are required.
Multi-word fields are camelCase, and a field that does not match exactly is
ignored without an error.

Full set: `name`, `description`, `tools`, `disallowedTools`, `model`,
`permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`,
`background`, `effort`, `isolation`, `color`, `initialPrompt`, `omitClaudeMd`,
`experimental`. The `--agents` JSON flag accepts `prompt` for the system prompt
plus the same set minus `color` and `experimental`; `experimental` is read only
from agent files.

| Field | Values |
|---|---|
| `model` | `sonnet` \| `opus` \| `haiku` \| `fable` \| a full model ID \| `inherit`. When omitted, resolved in order: the per-invocation `model`, this field, `CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model — so omitted is not `inherit` when that variable is set |
| `effort` | `low` \| `medium` \| `high` \| `xhigh` \| `max`; available levels depend on the model |
| `permissionMode` | `default` \| `acceptEdits` \| `auto` \| `dontAsk` \| `bypassPermissions` \| `plan` \| `manual` (alias for `default`, v2.1.200+). Ignored when the main conversation is in `bypassPermissions`, `acceptEdits` or auto mode |
| `memory` | `user` (across all projects) \| `project` (project-specific, version-controlled) \| `local` (project-specific, not checked in). No default is documented — choose by scope |
| `isolation` | `worktree` only. Branches from the default branch unless `worktree.baseRef` is `"head"`; cleaned up automatically if the subagent makes no changes |
| `background` | `true` keeps the subagent in the background even when Claude asks for the foreground. With fork mode on, every spawned subagent is already background |
| `omitClaudeMd` | `true` launches without the user, project and local CLAUDE.md files; managed policy files still load (v2.1.271+) |
| `experimental` | map; `cacheTtl` of `5m` or `1h` sets the subagent's prompt-cache lifetime (v2.1.248+) |

`name` is the identity — the filename need not match — and is what hooks receive
as `agent_type`. There is no `when-to-use` field; delegation triggers belong in
`description`, as flat prose in third person, with scenarios in the body.

Ignored entirely for plugin-shipped subagents: `hooks`, `mcpServers`,
`permissionMode`.

Removed from every subagent regardless of configuration, even when listed in
`tools`: `Agent` (at the depth limit), `AskUserQuestion`, `EndConversation`,
`EnterPlanMode`, `ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`,
`WaitForMcpServers`, `Workflow`. (`TaskOutput` no longer exists: removed in
v2.1.277; Claude reads a background task's output file with `Read`.) A second, larger filter applies to
background subagents — see the constraint above.

`Agent(agent_type)` allowlist syntax applies only to an agent running as the main
thread via `claude --agent`. Inside a subagent definition, listing `Agent` in
`tools` permits spawning within the depth limit, but any type list in parentheses
is ignored.

**When an agent beats a skill:** delegate to isolate high-volume output (test
runs, doc fetches, log processing) and for parallel independent investigations.
Stay in the main conversation for iterative back-and-forth, shared multi-phase
context, quick targeted edits, and latency-sensitive work.

### hook types and events

<!-- class: harness | source: https://code.claude.com/docs/en/hooks | verified_hash: e181a8c5bbc57b0c | last_verified: 2026-09-24 -->

`type` is one of `command`, `http`, `mcp_tool`, `prompt`, `agent`. Most hooks
in the wild are `command`; `prompt` is LLM-evaluated and can judge what a shell
script cannot pattern-match.

Not every event takes every type. `prompt` hooks run only on
`PermissionDenied`, `PermissionRequest`, `PostToolBatch`, `PostToolUse`,
`PostToolUseFailure`, `PreToolUse`, `Stop`, `SubagentStop`, `TaskCompleted`,
`TaskCreated`, `TeammateIdle`, `UserPromptExpansion` and `UserPromptSubmit`;
`agent` hooks on the same list except `PermissionRequest`, where Claude Code
skips them and the permission flow proceeds unchanged.
`SessionStart` and `Setup` take only `command` and `mcp_tool`.

Tool events (the only ones where `if` works): `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`.

Model events: `PreModelSwitch` runs before a requested model switch and can
block it; `PostModelSwitch` runs after the model changes, including when resume
restores it, and its plain stdout enters context.

### string substitutions

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins-reference | verified_hash: 8f9d04b404db0517 | last_verified: 2026-09-24 -->

| Token | Expands to |
|---|---|
| `$ARGUMENTS` | all arguments passed to the skill |
| `$ARGUMENTS[N]` / `$N` | positional arguments; `arguments` frontmatter names them for `$name` use |
| `${CLAUDE_SESSION_ID}` | session identifier |
| `${CLAUDE_SKILL_DIR}` | directory containing SKILL.md. **For a plugin skill this is the skill's subdirectory, not the plugin root** |
| `${CLAUDE_PROJECT_DIR}` | project root; the same path hooks and MCP servers receive |
| `${CLAUDE_EFFORT}` | `low` \| `medium` \| `high` \| `xhigh` \| `max`. Ultracode is not a distinct level and reports as `xhigh` |
| `${CLAUDE_PLUGIN_ROOT}` | bundled read-only assets. Changes on every update of a copied plugin; stable for a plugin loaded in place from a local-directory marketplace |
| `${CLAUDE_PLUGIN_DATA}` | persistent per-plugin state; survives updates |
| `` !`cmd` `` | preprocessed shell output. Disabled repo-wide by `disableSkillShellExecution: true` for user/project/plugin/add-dir skills |

`${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` — and, in a plugin skill,
`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` — are substituted in two
places: the markdown body **and** Bash rules in `allowed-tools`. Using the same
variable in both is the supported way to run a bundled script with no permission
prompt — `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)` matched
against the exact command the body tells Claude to run. These placeholders are
not environment variables in commands Claude runs through the Bash tool; write
the placeholder in plugin content. Nor are they substituted in a `references/`
file the model reads later: there the placeholder arrives as literal text. A
SKILL.md that routes to a reference states the resolved paths itself, and the
reference refers to them by name.

Inline `` !`cmd` `` is recognised **only** at line start or immediately after
whitespace; `KEY=!`cmd`` is left as literal text and never runs. Substitution
runs once over the original file and output is not re-scanned, so a command
cannot emit a placeholder for a later pass.

### distribution and budgets

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/settings-reference | verified_hash: ce672eb491235dde | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/plugins | verified_hash: 9e26a2871d5f1570 | last_verified: 2026-09-24 -->

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

**The levers differ by who holds them, and a plugin author holds only one.**

- **Author-side, any skill: `disable-model-invocation: true`.** It removes the
  skill from Claude's context entirely — name and description leave the
  listing — and the full skill loads only when a user invokes it. It is also a
  decision about who may invoke the skill, so use it where user-only
  invocation is correct, not as a budget trick for a skill Claude should reach
  for on its own
- **User-side, non-plugin skills: `skillOverrides`** — `"name-only"` lists a
  skill without its description, `"user-invocable-only"` hides it from Claude,
  `"off"` removes it. **Plugin skills are not affected by `skillOverrides`**;
  users manage those through `/plugin`
- **User-side, everything:** trim at the source with the key use case first,
  raise the fraction, disable a plugin, or `disableBundledSkills` (the `/doctor`
  setup checkup stays typable with it on)

**Measure this rather than assume it, and do not build a tool to.** The listing
is the only unconditionally loaded part of a skill, so it is the number that
matters most and the one least likely to be watched — the per-file body budgets
above cap a cost that is conditional on the skill triggering. `/skill-doctor`
reports each skill's context cost and how often it is used, and flags listed
skills that have never been invoked (v2.1.252+; not bundled or enterprise
skills). `/doctor` estimates the listing's total. `claude plugin details <name>`
reports per-plugin always-on versus on-invoke. `docs/internals/context-cost.md`
carries the standing "do not rebuild these" list.

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

So: read the number off the built-ins. Two consequences of the mechanism are
still worth generalising. Overflow is **silent** and drops the least-invoked
first, so the skills you rarely reach for are exactly the ones that disappear.
And the allocation is a *fraction of the window*, so "are we over budget" has a
different answer per model — compute it against the window rather than
asserting a constant character count.

### surface differences

<!-- class: harness | source: https://code.claude.com/docs/en/skills | verified_hash: c50f63c046af3f63 | last_verified: 2026-09-24 -->
<!-- class: harness | source: https://code.claude.com/docs/en/sub-agents | verified_hash: ecb008122d18c786 | last_verified: 2026-09-24 -->

The same skill does not behave identically everywhere.

- **Cowork, cloud sessions and routines do not read the user-scope skills
  directory** (`<HOME>/.claude/skills/`). Cowork and cloud load the skills
  enabled for your claude.ai account, synced at session start; a routine that
  invokes a skill present only there reports it not found. Cloud sessions
  additionally load project skills from the cloned repository's
  `.claude/skills/`. Plugins do not install from a repository's
  `.claude/settings.json` or from your user settings; a plugin reaches cloud
  sessions only by being enabled on the claude.ai account, where it loads as
  `<name>@synced`. The same sync brings account plugins into signed-in
  terminal sessions, and any same-named plugin from another source wins over
  the synced copy.
- **Account skills come back into the terminal changed.** A signed-in terminal
  session syncs the account's skills as `/anthropic-skills:<name>` (a local
  skill of the same short name wins `/<name>`). Outside cloud and Cowork, their
  `!` commands do not run, `@` references are not attached, and
  `${CLAUDE_PROJECT_DIR}` and `${CLAUDE_SESSION_ID}` reach Claude as literal
  text.
- **`context: fork` with `agent: Explore` or `agent: Plan` does not load
  CLAUDE.md.** Those two built-ins skip CLAUDE.md and git status to keep context
  small, so a forked skill using them sees only the SKILL.md content and the
  agent's own system prompt. Every other agent loads it unless its definition
  sets `omitClaudeMd`.
- **Project skills load from `.claude/skills/` in the launch directory and every
  parent up to the repository root**, so starting in a subdirectory still picks
  up root skills. They also load from *nested* `.claude/skills/` below the
  working directory when Claude reads or edits a file there — the monorepo case.
- **`--add-dir` and `/add-dir` load the added directory's `.claude/skills/`,
  `.claude/commands/` and `.claude/agents/`; the `permissions.additionalDirectories`
  setting grants file access only and loads none of them.** Directories the
  Agent SDK adds through its `additionalDirectories` option load like `--add-dir`.
  CLAUDE.md from added directories is still not loaded unless
  `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.
- **Precedence on a name clash:** enterprise over personal over project, and a
  skill at any of those levels overrides a bundled skill of the same name — but
  not its aliases: a project `code-review` skill replaces `/code-review`, and
  the bundled alias `/review` never runs it. Plugin skills are namespaced
  `plugin-name:skill-name` and cannot collide. Where a skill and a legacy
  `.claude/commands/` file share a name, the skill wins.
- **Live change detection** picks up edits to watched skill directories without a
  restart — but a *newly created* top-level skills directory that did not exist
  at session start is not watched until you restart.

### MCP in Claude Code

<!-- class: harness | source: https://code.claude.com/docs/en/mcp | verified_hash: bc102386c0362a4a | last_verified: 2026-09-24 -->

- **Client runtimes.** v1 is built on the MCP TypeScript SDK 1.x; v2 on SDK 2.0,
  adding revision 2026-07-28. Pin one with `MCP_SDK_GENERATION`; choose whether
  Claude Code asks servers for the new revision with `MCP_PROTOCOL_NEGOTIATION`
  (`auto` or `legacy`).
- **Tool search** is on by default: only tool names and server instructions load
  at session start. In `auto` threshold mode, tools load upfront while their
  definitions total under 10% of the window and are all deferred once they reach
  it. `alwaysLoad` opts a server out of deferral.
- **Output.** A warning above 10,000 tokens and a 25,000-token default limit
  (`MAX_MCP_OUTPUT_TOKENS`); a larger text result is saved to a file.
  `_meta["anthropic/maxResultSizeChars"]` in a tool's `tools/list` entry raises
  that tool's threshold, up to 500,000 characters.
- **Descriptions** and server instructions are truncated at 2,048 characters
  each by default; `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` (v2.1.280+) sets
  it for the whole session.
- **Input schemas** with a root-level `anyOf`, `oneOf` or `allOf` are flattened,
  with the constraints moved into the description.
- **Plugin servers** register as `plugin:<plugin>:<server>`. In a remote
  server's `url` and `headers`, credential variables read as empty rather than
  expanding, and a plugin-supplied `headersHelper` runs with every
  credential-looking variable removed from its environment.
- **Skills over MCP.** The Skills extension (SEP-2640) is Final in the spec, but
  Claude Code does not implement it and plugin `skills/` already deliver the
  same format. Revisit when Claude Code's MCP documentation lists it.

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

<!-- class: harness | source: coderef/agentskills | verified_hash: 69ef37e | last_verified: 2026-09-21 -->

**The sections deriving from the Agent Skills spec cite the repo, not the
website.** `agentskills.io` is fetched by nothing, so citing it made those
sections permanently unverifiable; `coderef/agentskills` is a clone this project
already tracks, whose HEAD `skill-maintain sources` records, so the provenance
join compares it by SHA exactly as it compares a page by content hash.

The rules are the validator, not this file. Claude Code's skill schema is a
superset of the cross-vendor Agent Skills spec; `skill-maintain validate`
enforces it, and `--strict` flags fields that are not portable to strict
cross-vendor hosts. Read `cc_schema.py` for the authoritative list rather than
maintaining a prose copy that can disagree with it.

## maintaining this file

<!-- class: craft | last_verified: 2026-09-21 -->

- [ ] A `harness` section is rechecked when its source page moves, not when a
      calendar elapses. Correct the section's `last_verified` when you recheck it
      — a file-level date says nothing about which section anyone looked at
- [ ] A `model` section is rechecked on **every** model release — point releases
      included — and on a change of default model. Point releases move
      behaviour: Fable 5.1 writes fewer progress updates, denser prose and more
      whole-file rewrites than Fable 5, and Opus 5 delegates freely where Opus
      4.8 under-delegated. Opus 5.5 defaults to `medium` effort, thinks more
      per turn at a given level than Opus 5, and ends more turns with a
      progress report while work is still owed. Nothing else triggers it, and elapsed time says
      nothing about whether the model changed
- [ ] A `craft` section is rechecked when an audit produces a finding that
      touches it
- [ ] **Re-audit rules written for older models.** Instructions that worked
      around an older model's limitation become overhead once a newer model
      handles the case on its own — and for this generation, dated behavioural
      instructions do active harm. On each maintenance pass, take at least one
      always-loaded rule or skill instruction and ask whether the model still
      needs it, then delete or demote what it does not
- [ ] Freshness does not catch wrongness. A document can be wrong on the day it
      is written, and no staleness check will ever say so. Audit the added prose
      of a change against what the code and the platform actually do. Specimen:
      this file told readers for weeks that `disable-model-invocation` does not
      shrink the skill listing and that `skillOverrides` is the lever — while the
      page it cited said, in both snapshots, that the flag "removes the skill
      from Claude's context entirely" and that "plugin skills are not affected
      by `skillOverrides`". It also named a `background: false` agent field that
      neither snapshot of the page carries. The sections carried verified hashes
      throughout: a hash says the page did not move, not that the section ever
      matched it. The repo's own `advisor` skill (since retired) stated the
      correct behaviour the whole time
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
      undocumented; by 2026-08-07 it was documented for two events, and by
      2026-09-21 for all of them
- [ ] A rule with no source, no measurement, and no incident behind it is an
      opinion. Opinions are allowed here, but they say so
