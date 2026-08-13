# Context cost: where it actually goes, and how to decide a rule's tier

last updated: 2026-07-26

Written after measuring this repo's own plugins across four projects. The
headline is counter-intuitive enough to be worth stating first:

**Cost is emission, not invocation.** A hook that fires on every edit and stays
silent is nearly free. A hook that fires once per session and always speaks is
expensive. Optimise the second, not the first.

## The measurement

Across 27 transcripts in this repo:

| Hook event | Fired | Spoke | Rate | Bytes emitted | Latency |
|---|---:|---:|---:|---:|---:|
| `PreToolUse` | 5,109 | 0 | 0.0% | 0 | 294s |
| `PostToolUse` | 5,994 | 1,122 | 18.7% | 69,564 | 280s |
| `Stop` | 450 | 0 | 0.0% | 0 | 26s |
| `SessionStart` | 54 | 54 | 100% | 77,582 | 14s |

`SessionStart` fired 111x less often than `PreToolUse` and emitted 53% of all
hook bytes. The hook that fired 5,109 times cost zero tokens.

The real per-edit cost is **latency, not context**: ~58ms per `PreToolUse`
firing. That is the budget to watch for edit-time hooks.

Upstream confirms the finding independently — the hooks reference singles out
the exact event the numbers flagged: *"SessionStart runs on every session, so
keep these hooks fast... For static context that doesn't require a script, use
CLAUDE.md instead."*

And it is worse than the table shows. `SessionStart` re-fires on `startup`,
`resume`, `fork`, `clear`, **and `compact`** — so a long session pays it
repeatedly, not once.

### Per-project variance is the whole story

The same plugin behaves completely differently per repo. `hookify` emitted
**0 bytes across 3,693–10,399 firings** in three projects, and **2,055,910
bytes across 17,172 firings** in a fourth — because that project had a rule
configured that injected a long suppression essay on every edit to four hot
files. It was the single largest context consumer in that repo, by ~20x.

A plugin cannot be judged good or bad in the abstract. It has to be measured
where it runs.

## What the measurement decided

The tier test these numbers produced is a **rule**, and it lives in
`best_practices.md` under `always-loaded context`, together with the
emission-not-invocation finding. This file keeps the evidence; that file states
what to do about it.

Two facts that belong with the evidence rather than the rule:

- `PreToolUse` `deny` blocks even in `bypassPermissions` mode, which is what
  makes tier 1 worth reaching for.
- A hook's `if` field is an optimisation, not the enforcement boundary. Upstream:
  the filter *"fails open, running your hook regardless of pattern, when the Bash
  command can't be parsed"*, and *"use the permission system rather than a hook to
  enforce a hard allow or deny."* Enforcement logic belongs **inside** the hook
  script, parsing `tool_input` robustly; `if` only decides whether to spawn.

### DRY across tiers

The tiers carry *different things*, not copies of one thing: canonical prose in
exactly one place (the skill, pull-based); hook messages as terse actionable
statements, never a copy of the explanation; ambient as a pointer, not content.

Worked example from this repo: the ruff `select`/`extend-select` rule. Full
reasoning in `python-tooling/SKILL.md`; one sentence in the `ruff-diagnostics`
hook, fired only on projects that actually set `select`; nothing at all in the
`dev-conventions` SessionStart directive.

## Do not rebuild these

Claude Code ships introspection that covers most of what a home-grown audit
would compute. Check these before building anything:

| Need | Built-in |
|---|---|
| Per-plugin token cost, always-on vs on-invoke | `claude plugin details <name>` |
| What is occupying the context window, by category | `/context` |
| Config problems, skill-listing cost, CLAUDE.md trim proposal | `/doctor` |
| Which hooks are registered | `/hooks` |
| Which hooks actually fired, with exit codes and output | `claude --debug hooks` |
| Isolate whether a plugin/hook/skill causes a problem | `claude --safe-mode` |
| Verify which instruction files loaded and why | `InstructionsLoaded` hook |
| Does a skill trigger when it should | `skill-creator` plugin's eval harness |

What is genuinely *not* covered, and is the only thing worth building: observed
behaviour over time — emission rates per plugin, per-project variance, and skill
invocation counts. That data lives in the session transcripts under
`<HOME>/.claude/projects/*/*.jsonl`.

## Mining transcripts: four traps

All four produced plausible-looking wrong numbers before being caught.

1. **`{}` is not speech.** No-op JSON responses are the common hook return.
   Counting any non-empty stdout as an emission makes every silent hook look
   like a 100% emitter.
2. **Do not double-count channels.** `hook_success.stdout` and
   `hook_additional_context` are separate records for what can be one emission.
   Summing both yields emission rates above 100%.
3. **`session-start.sh` cannot be attributed by command string.** Seven plugins
   share that filename, and `${CLAUDE_PLUGIN_ROOT}` is stored unexpanded.
   Content fingerprinting works but over-attributes; resolve against the
   installed plugin registry instead.
4. **Date-filter everything.** Transcripts span months and mix in
   since-disabled plugins and since-fixed behaviour.

Useful attachment types: `hook_success` (`hookName`, `command`, `stdout`,
`exitCode`, `durationMs`), `hook_additional_context`, `diagnostics`,
`invoked_skills`, `skill_listing`.

## Skill listing is a real budget

The mechanics — the allocation, the overflow behaviour, the per-entry cap, and
the levers for staying inside it — are stated in `best_practices.md` under
`distribution and budgets`. The measurements are here.

**Measured 2026-08-13, by `/doctor`:** 26 listed entries, ~2,300 tokens. A 1%
allocation gives ~2,000 at a 200k window and ~10,000 at 1M, so the set is
marginally over at standard context and comfortable above it. The single largest
entry is a bundled skill at ~400 tokens, which is not removable.

**And a correction worth keeping, because the wrong method looked convincing.**
A hand-rolled count the same day reported 4,391 tokens across 36 skills and was
measuring a different quantity: every description *authored* in this repo,
including plugins under `apps/` that are not enabled. The listing carries only
enabled plus bundled skills. This repo contributes 8 of the 26 entries, ~1,358
tokens, via four enabled plugins.

Two lessons. Authored is not installed, and any repo shipping more plugins than
it enables will overstate its own listing by counting files. And the "do not
rebuild these" table below is not only about wasted effort: the built-in was
right and the rebuild was wrong, on the first attempt, in the direction that
would have justified unnecessary work.

**Measured invocation rates** here are ~0.2–0.4 per session. Low, but not zero —
an earlier claim of "near-zero recall" came from a single unrepresentative repo
and was wrong.
