last updated: 2026-08-07

# best_practices.md: what it is for, and how it should be maintained

Design record, filed 2026-08-07 when the owner asked whether the repo still
treats `best_practices.md` as its north star and how drift in it gets caught.
Every number below was derived that session; the commands are named so they can
be re-run.

**Status, same day.** Steps 0-2 of the build list are SHIPPED; the analysis in
sections 1-3 stands as the record of why.

- Step 0 — `VISION.md` gained `### the model is a variable`, principle 5 its
  boundary, principle 6 the model-release trigger.
- Step 1 — the file was rebuilt as constraints / gates / reference with
  `## authoring shape` replacing `### instructions quality`; the two unmeasured
  signals sections and the prose spec-compliance list are gone.
- Step 2 — **the hash join is built** (`skill_maintainer/provenance.py`,
  CLI 0.29.0). Sections carry `verified_hash`; `skill-maintain upstream` prints
  the join after every fetch; `skill-maintain test` carries two arms,
  `best_practices provenance` and `upstream hash state fresh`, both
  mutation-proven. The calendar arm on the file's first line is retired.
- Also done out of order: the three false claims (section 2d) are corrected.

Steps 0-2 shipped, plus the review fixes and reconcile that followed. Section
6's ordering below is the original; treat it as history. **The current queue is
the handoff at the end of this document.**

## Handoff — state at 2026-08-07, end of session

Written for whoever picks this up next. Everything below was derived at the
time; re-derive before trusting any number, because most of today's findings
were exactly this kind of number having gone quietly wrong.

**Where things stand.** `main` is pushed and clean. `skill-maintain test` reads
**269 passed, 0 failed** — green for the first time in the session, and the
first time the board has had no standing red. `skill-maintain upstream` reports
**23 harness annotations, 0 moved, 19 current, 4 unbound, 0 untracked source, 0
unattributed**.

**Do this first, and do not skip it: re-run `skill-maintain upstream` and
`skill-maintain sources`.** Every conclusion in this document rests on hashes
fetched on 2026-08-07. The `upstream fetch fresh` arm will tell you how old they
are; it dates a real fetch now rather than any file a second writer touches.

### Queue, highest value first

1. **Release notes as a tracked source** (step 3). Still the best single
   addition, and it likely *reduces* the maintenance pass rather than adding to
   it: six of the drift backlog's items are version-gated (`v2.1.207+`,
   `v2.1.214+`), and release notes state what changed instead of requiring a
   +807-line diff to be read. Verify the canonical URL before wiring it.
2. **Give the drift backlog a disposition field.** It sits at 40 unabsorbed and
   cannot distinguish "not yet considered" from "considered and rejected", so it
   can only grow. Three states — absorbed / rejected-with-reason / deferred-with-
   trigger. Cheap, and it unblocks actually working the list.
3. **Mechanise the hooks section** (step 5). Sixteen hook constraints and seven
   agent ones are enforced by nothing, and they are the class that has already
   produced real bugs here (the 1000x timeout, exit-0-approves). Several are
   statically checkable against this repo's own `hooks.json` files.
4. **Reconcile the source lists** (step 6, half done). `upstream_urls` is clean
   at eleven. But there are **18 repos under `coderef/` and 10 in
   `tracked_repos`** — eight clones are kept current by the update script and
   silently ignored by `skill-maintain sources`. Decide each: track it or stop
   cloning it.
5. **The four unbound annotations.** Three cite `coderef/agentskills`, one the
   `plugins` page. They go green only when someone reads the source and stamps a
   `verified_hash`. Do not stamp without reading — that mistake was made and
   caught within this session.
6. **The model-facts A/B** via `skill-creator`'s harness. Highest value, least
   scoped, and the only item needing a method this repo has not built. It is
   what would settle whether `## authoring shape` is right.

### Decisions waiting on the owner

- **MCP 2026-07-28 migration** — see `mcp_spec_2026_07_28.md`. The prior
  question is whether `readwise-reader` should move at all; it is a single-user
  local STDIO server and most of what the stateless redesign buys, it does not
  need. `skill-dashboard`'s `^1.24.0` waits on the same call.
- **The postmortem branch** (`claude/generalized-postmortem-skill-bbqnks`) is
  rebased, verified, and a clean fast-forward — 7 commits, unmerged.

### `.claude/` staleness, audited 2026-08-07

The directory had never been audited as a unit. Two defects fixed in this
session, two findings left for judgment:

- **Fixed:** `rules/skills.md` taught `uv run python
  skill-maintainer/scripts/check_freshness.py`, a path that has not existed
  since the CLI absorbed that check. A rule teaching a command that fails is
  worse than a rule with no example.
- **Fixed:** `rules/plugins.md`'s heading said "three files" while its own body
  correctly listed the lockfiles too. The heading is what gets skimmed.
- **Open — an unwatched pair.** `.claude/agents/fast-executor.md` and
  `task-coder.md` are byte-identical to the templates `model-routing` ships in
  `references/agents/`. That is the legitimate shape (template ships, repo
  installs it), *not* the `control-builder` case retired in 1.11.1 — but
  **nothing watches the pair**, so if the template moves, this repo's installed
  copy goes stale in silence. Invariant 1b's second question has no answer here.
  Either add an arm comparing them, or state in the skill that installed copies
  are snapshots and are expected to drift.
- **Open — priors that rot.** `.claude/agents/doc-claim-auditor.md`'s entire
  evidence base is specimens from `style-3d.md` and `film-language.md`, files
  belonging to `mitate`, which now lives in its own repo. The specimens are
  history and read fine as prose, but a local agent whose every example comes
  from a codebase no longer present is one the next maintainer cannot verify
  against anything. Grow local specimens or say the evidence is inherited.

### Things that will bite

- **`skill-maintain sources` and `upstream` write the same state file.** That is
  what made the old freshness arm lie. `state/last_fetch` has exactly one writer
  by design; keep it that way.
- **A stash predating this session** (`stash@{0}: WIP on main: 36100c3
  path-privacy 0.7.0`). The stash stack is shared across worktrees — a stash
  nobody remembers is the kind of thing that gets popped onto the wrong branch.
- **The session log for 2026-08-07 is gitignored**, so it does not travel. Its
  findings that matter are duplicated here on purpose.

The short version: the file has three different kinds of knowledge inside it,
each with a different clock and a different falsifier, and one calendar date on
line 1 governing all of them. That is a category error, not a staleness bug, and
no amount of checking the date more often fixes it.

## 1. What it actually is today

### It is not the north star, and has not been for some time

`VISION.md` is what the repo points at — CLAUDE.md line 3, "Read VISION.md
first." `best_practices.md` appears in CLAUDE.md exactly once, as invariant 3,
which is a gotcha about its two copies rather than a pointer to its content.
`VISION.md` does not mention it. `docs/README.md` mentions it only inside the
gotchas row.

Worse, the durable framing in `best_practices.md` is a second copy of
`VISION.md`. Both state that the context window is attention rather than memory;
both state that descriptions are reverse queries; both frame the problem as
precision and recall over loaded context. `VISION.md` says it better and is the
copy the repo cites. Under invariant 1b, the `best_practices.md` prose intros
are a copy whose consumer is nobody.

What is left after removing the duplicated framing is a 128-item checklist.

### What holds it up mechanically

Three things, and two of them measure something other than correctness:

| Mechanism | Location | What it establishes |
|---|---|---|
| `last updated:` within 30 days | `tests.py:1150` | Someone edited the file recently |
| The two copies are byte-identical | `tests.py:1175` | A copy is a copy |
| Phase 7 of `/skill-maintainer:maintain` | `skills/skill-maintainer/skills/maintain/SKILL.md:145` | A human or model read it and proposed edits |

`validate.py::check_best_practices()` does not read the file. It hardcodes four
rules — line count, word count, description quality, angle brackets. Nothing in
the codebase parses the 128 checkboxes.

### Enforcement coverage by section

Derived with `awk '/^#{2,3} /{sec=$0} /^- \[ \]/{count[sec]++}'` over the file,
cross-referenced against the arm names in `tests.py` and `cc_schema.py`:

| Section | Items | Mechanised |
|---|---:|---|
| hooks | 19 | none |
| agent authoring (three subsections) | 15 | none |
| control authoring | 7 | none |
| instructions quality | 8 | none |
| string substitutions | 5 | none |
| distribution | 7 | none |
| invocation control | 6 | none |
| frontmatter fields | 11 | most, via `cc_schema.validate_cc` |
| spec compliance | 8 | all, same place |
| token budget / description precision | 13 | most |
| maintenance | 9 | partly (`freshness`, version alignment) |

The single hooks-adjacent arm (`tests.py:1082`) checks `settings.json` for
high-frequency events without a matcher. That is the "always-loaded context"
item, not any of the 19 hooks items. Exec form, timeout-in-seconds, `if` on
non-tool events, exit-1-used-to-gate, `once: true` placement, the 10,000-char
output cap: all statically detectable across this repo's own `hooks.json` files,
none checked. Those are also the rules that already cost real bugs — see
`b14d333 fix two hook timeouts wrong by 1000x`.

## 2. Four failures, with specimens

### 2a. The provenance layer has no consumer and is demonstrably wrong

Fourteen `<!-- source: URL | last_verified: DATE -->` comments sit in the file.
Twelve are stamped `2026-04-19`. Nothing reads them.

`changes.jsonl` records two upstream events hitting those exact pages since that
date. The 2026-07-21 event alone: `docs/en/hooks` +807/-312 lines and +69,529
chars, `docs/en/skills` +217/-47 and +24,617 chars.

The stamps are wrong in both directions, which is the part that matters.
`git log -S` shows commit `b431907` ("reconcile best_practices.md with
upstream", 2026-07-21) rewrote the hooks section — it added the exit-code
semantics rule — and left that section's annotation reading `2026-04-19`. Only
the sub-agents section, newly written that day, got a current stamp. So a
section that *was* reconciled looks 110 days stale, and nothing distinguishes it
from one that genuinely is. Meanwhile the file-level date reads `2026-08-03` and
the test arm is green.

A green that cannot be told apart from a run that checked nothing is the exact
failure the file's own control-authoring section warns about.

### 2b. Detection outruns absorption, and the overflow has become a parallel document

`docs/internals/upstream_drift_backlog.md` holds **44 unabsorbed bullets** under
"Not yet absorbed", identified 2026-07-26 and still unabsorbed twelve days later.
Six of them are version-gated facts (`v2.1.207+`, `v2.1.214+`, `v2.1.218`).

This is not a detection problem. Detection works: hashes, deltas, per-page
snapshots. The bottleneck is that absorption is a human reading a +807-line diff
and hand-picking, and the backlog is where the overflow accumulates. It is now a
third best-practices-shaped document with no consumer other than being read.

Critically, the backlog cannot distinguish **not yet considered** from
**considered and rejected**. Everything that is not absorbed looks identical, so
the list only grows. There is an "Already applied (do not redo)" section, which
is the right instinct, but no "considered and rejected, with reason" section —
so any future pass re-litigates the same items from scratch.

### 2c. Three source lists, no two of which agree

| List | Where | Count | Status |
|---|---|---:|---|
| `upstream_urls` | `.skill-maintainer/config.json` | 12 pages | live, `upstream_check` last logged 2026-07-21 |
| `tracked_repos` | same file | 10 repos | `source_pull` last logged **2026-05-04**, 95 days ago |
| `update_repo` calls | `update-coderef.sh` | 12 repos | gitignored, untracked, unlogged; the one actually keeping clones fresh |

`update-coderef.sh` pulls `mcp/mcp-ui` and `mcp/typescript-sdk`, which are not
in `tracked_repos`. `tracked_repos` includes `mcp/experimental-ext-skills`,
which the script does not pull. `coderef/claude-plugins-community` exists on
disk and is in neither.

The instrumented arm has stalled while the uninstrumented one runs. Same shape
as the untracked pre-commit hook already recorded in the tooling-traps notes:
the mechanism that actually does the work is the one the repo cannot see.

And the 2026-07-26 three-agent read that produced the backlog covered
`debug-your-config`, `best-practices`, and `large-codebases` — none of which are
in `upstream_urls` — plus a Claude 5 context-engineering post that is not
tracked in any form. So the tracked set is known-incomplete, and the gap is
being filled ad hoc without being recorded as a source.

### 2d. Two shipped claims about the file are false

- `skills/skill-maintainer/README.md:73` calls it "machine-parseable checklist
  used by the quality checks." Nothing parses it.
- `init-maintenance`'s skill description says `init` "creates `.skill-maintainer/`
  with config, state tracking, and the best-practices checklist."
  `init_config()` (`config.py:109`) writes `config.json` and the state
  directory. It does not write the checklist.

That second one also means CLAUDE.md invariant 3's stated justification for the
bundled copy — "fresh `skill-maintain init` runs in other repos pull stale
rules" — is wrong. The pair is still legitimate: the real consumer is Phase 7
reading `references/best_practices.md` in an installed repo that has no local
copy. Only the reason given is wrong, and a wrong reason is what lets the pair
survive a future 1b audit it should have to re-earn.

## 3. Walking back: the three-body problem

The stated intent is a north star for building effective skills that
progressively disclose, grounded in the evolving interaction of **harness,
model, and skills**. That phrase is the diagnosis. Three bodies, three clocks,
three falsifiers — and one file treating them identically.

### Harness facts — what the runtime does

*"Hook `timeout` is in seconds." "Exit 0 does not approve a PreToolUse call."*

- Falsifiable by fetching a page or running the harness.
- Moves on Anthropic's release cadence — measured at ~11 days for
  `docs/en/skills` (`tools/skill-maintainer/queries/upstream_churn.sql`).
- Wrongness is silent until it is extremely loud.
- Right trigger: source movement, which is already observed.
- **Current state: well covered.** ~90% of the file.

### Model facts — what this model generation needs from a skill

*"Critical instructions at the top, not buried." "Bullet points preferred over
prose."*

- **Not falsifiable by reading any doc.** These are claims about model
  behaviour, and no page states them as guarantees.
- Moves on model releases, not doc edits. A doc-hash trigger cannot see this
  clock at all.
- Wrongness is silent forever. An instruction that a newer model no longer needs
  does not fail — it just costs tokens on every activation, invisibly.
- Right trigger: a model release.
- Right falsifier: an A/B with the rule and without it.
- **Current state: essentially zero.** Invariant 1c states the practice, and the
  drift backlog concedes the gap in as many words: "stating a practice is not
  the same as triggering it, and this one still has no recurring prompt."

This is the largest hole, and it is the one the original intent named
explicitly.

#### The Opus 5 datum, filed 2026-08-07

The owner's observation, and the first concrete instance this body has had: the
Claude 5 generation is a genuine deviation from prior families. It is goal-
oriented, working from **constraints on one side and a definition of good —
metrics, gates — on the other**. And it carries knowledge earlier models did
not, which makes some skills unnecessary at best and frictional at worst.

That is a larger claim than "some rules went stale." It says the **shape** of a
skill may be wrong, not just its content. And this repo already contains the
before-and-after, unlabelled:

| | `knowledge-retrieval` (2026-04-02) | `claim-audit` (2026-08-04) |
|---|---|---|
| Body | Output templates — literal formats for presenting a synthesis | A scope caveat, a taxonomy of what counts, a procedure, an oracle |
| Steps | 20 numbered | 0 numbered headings; steps exist but each carries why |
| Justification | none stated | "measured above 85% false positives when tried"; "exit-status masking has bitten repeatedly" |
| What is load-bearing | the 5-line highlight priority hierarchy (domain knowledge the model cannot derive) | nearly all of it |
| Failure if deleted | presentation varies; outcome unchanged | the audit stops being falsifiable |

The audit family written in August is already in the constraints-and-gates
shape. Nobody named the shift; it happened by instinct, and the older skills
were never revisited against it.

**The section that encodes the old shape is still in force.**
`### instructions quality` reads, in full: *"Steps include expected commands
with actual arguments"*, *"Bullet points and numbered lists preferred over
prose"*, *"Critical instructions at the top, not buried"*, *"Examples provided
showing expected input/output"*. Those are accommodations for a model that
needed scaffolding to stay on task. Eight items, mechanised by nothing, shaping
every skill written since — and they push authors toward exactly the shape that
now causes friction.

##### The test that replaces "is it procedural?"

Not "does it have steps." Procedure still earns its place when the *order* is
load-bearing for a reason the model cannot see. `claim-audit`'s "name the
deriving command before running anything" is a real step: it exists because a
command chosen after seeing output drifts toward confirming. That is a
constraint overriding an instinct, not scaffolding.

The test is per-instruction:

1. **Does it carry information the model cannot derive?** Repo-specific facts,
   measured findings, domain conventions, a threshold with evidence behind it.
   Keep.
2. **Does it override a default the model would otherwise follow?** State the
   default it overrides and why. Keep, and say the why — an unjustified override
   is indistinguishable from noise and gets reasoned around.
3. **Does it restate general competence?** Output formats, step decompositions
   of tasks the model plans better itself, "be specific," "handle errors."
   Delete. This is the friction class: it does not just waste tokens, it
   competes with a better plan the model already had.

##### Trigger, finally

Invariant 1c has had no trigger since it was written. This is it: **a model
family release fires a redundancy-and-friction pass.** Not a calendar — an
event, which is what the 2026-08-04 dates doctrine says to prefer wherever the
event is observable. A major model release is about as observable as events get.

The honest falsifier remains the with/without A/B (`skill-creator`'s harness).
The triage above is a cheaper first cut that narrows what is worth measuring; it
is not a substitute for measuring, and should not be recorded as one.

### Craft facts — what this repo learned by building

*The seven control-authoring rules. The bracket-the-hook pattern.*

- Falsifiable only by the experience that produced them, or by re-running the
  audit that found them.
- Moves when an audit produces a finding, on no calendar at all.
- Right trigger: an audit finding.
- **Current state: the instruments exist and produce findings; nothing routes a
  finding into the file.** The control-authoring section arrived through a
  human noticing and hand-writing it, once, on 2026-08-03.

### The category error, stated plainly

One `last updated` date. One 30-day window. One absorb-by-hand pass. Applied to
knowledge that refreshes on a doc-edit clock, a model-release clock, and an
audit-finding clock respectively — with a fetch-and-grep falsifier, an A/B
falsifier, and a re-run-the-audit falsifier respectively.

The 30-day window is only even coherent for the first body. For the second it is
meaningless, because a model release is not on a monthly cadence and elapsed
time carries no information about it. For the third it is actively misleading,
because a craft rule learned from a real failure does not decay with time — it
decays when the thing it describes changes.

## 4. Source inventory

### Keep

| Source | Why | Change |
|---|---|---|
| `code.claude.com` doc pages (12) | The primary harness source. Hash-observable, already instrumented. | Add the three the 2026-07-26 read used ad hoc: `best-practices`, `debug-your-config`, `large-codebases` |
| `coderef/agentskills` | Load-bearing: the spec plus `skills-ref`, which is a code dependency, not just a reading source | none |
| `agentskills.io` | Cited twice in the file | Currently **not** in `upstream_urls` — its movement is unobservable. Track it or drop the citations |

### Add — these close the model-facts hole

| Source | Why it is the right shape |
|---|---|
| Claude Code release notes / CHANGELOG | The backlog is full of version-gated facts (`v2.1.207+`, `v2.1.214+`, `v2.1.218`). Those came from release notes, and release notes are a *better* trigger than page hashes: append-only, dated, and they state what changed rather than requiring a diff to be read. This is the single highest-value addition and probably reduces Phase 7's reading load rather than adding to it. Verify the canonical URL before wiring it |
| Model release announcements / model cards | The only honest trigger for invariant 1c. A model release is the event that makes "re-audit rules written for older models" actionable; a calendar never will be |
| Anthropic engineering posts on context engineering | Already consumed once, ad hoc, unrecorded. Either track it or stop citing it |
| This repo's own audit instruments | postmortem, control-audit, claim-audit, test-audit, tune. Not a new source — a **plumbing gap**. They already produce findings; nothing routes one into the file |
| `skill-creator`'s with/without eval harness | The missing falsifier for the entire model-facts body, and for the "quality signals" section specifically. Named in the drift backlog as "a concrete method for our unmeasured quality signals section" and not acted on |

### Demote or remove

| Source | Evidence | Recommendation |
|---|---|---|
| The four MCP repos (`modelcontextprotocol`, `python-sdk`, `ext-apps`, `experimental-ext-skills`) | Produced 122/54/203-commit bursts per pull. Zero best_practices rules cite any of them. They serve readwise-reader and skill-dashboard, which is a different consumer | Move out of best-practices sourcing into dependency tracking. They are real sources for real things, just not for this file |
| `claude-cookbooks` | API-usage notebooks. Zero citations | Drop from best-practices sourcing |
| `claude-plugins-official`, `knowledge-work-plugins`, `claude-plugins-community` | Also zero citations across five months — but these are the **highest untapped value** in the list. They are real shipped plugins from Anthropic; they are practice evidence, not doc evidence, and the reason they have produced nothing is that nobody has mined them, not that they are unproductive | Keep, and give them an actual extraction method (the BACKLOG already proposes one: `git log` plus diff on SKILL.md and plugin.json, surfaced as evidence) |

**Zero of the ten tracked repos has ever produced an annotated rule.** Five
months, ten pulls, hundreds of commits. That is the finding: either their
contribution is real and unattributed, or the repo arm of source tracking has
never worked. Either way the current list cannot be defended as-is.

### Remove from the file itself

Thirteen of the 128 checkboxes, plus fifteen plain bullets that are not
checkboxes at all and so were never counted:

- **`## quality signals` (7 bullets, no checkboxes).** States numbers — 90%
  trigger rate, 0 failed API calls per workflow — that have never been measured
  in this repo. Repo doctrine is that unmeasured thresholds do not ship. Measure
  them with skill-creator's harness or delete them.
- **`## iteration signals` (8 bullets, no checkboxes).** Sound advice, but
  `skill-creator` now ships a description-tuning harness that does this work. A
  prose copy without the harness is the weak half of an unwatched pair.
- **`## spec compliance` (8 checkboxes).** Fully implemented in
  `cc_schema.validate_cc` — verified line by line. The code is the rule. Replace
  the section with a pointer at the validator.
- **`### string substitutions` (5 checkboxes).** Pure lookup table. Belongs in a
  reference, not in a checklist that claims each line is a thing to verify.

That the two signals sections use plain bullets while everything else uses
checkboxes is itself the tell: they were never actionable, and the format
recorded that fact fifteen lines at a time without anyone reading it.

## 4b. The division of labour: VISION.md and best_practices.md

Scope note added 2026-08-07: the target audience for `best_practices.md` is
**anyone building skills, plugins, or marketplaces for Claude Code and related
Claude products** — not this repo. It already ships inside the skill-maintainer
plugin, so it is a product, not config. Its home in `.skill-maintainer/` makes
it read as the latter, which is part of why it rotted quietly.

`VISION.md` turns out to be in good shape and already general. Its principles —
attention not memory, precision as the constraint, descriptions as reverse
queries, always-loaded lines justify themselves, trees not workflows, the
harness is the system, verify by construction — apply to anyone building on this
platform. Only the closing "what this means for this repo" section is local.

So the split is not worldview-versus-checklist. It is:

| | `VISION.md` | `best_practices.md` |
|---|---|---|
| Answers | why | what, and how you know |
| Changes on | rarely; a genuine shift in how the platform works | harness releases, model releases, audit findings |
| Audience | this repo, but the content travels | anyone shipping a skill or plugin |
| Failure if wrong | the repo builds the wrong things | everyone downstream builds the wrong things |

### Two changes VISION.md actually needs

**1. A missing principle: the model is a variable.** `### the harness is the
system` frames model and harness as one compound system that co-optimises — and
then treats the model side as fixed. Nothing in the document says that a model
generation change alters what a skill should contain or what shape it should
take. That is the gap the Opus 5 datum exposed, and it belongs at principle
altitude rather than as a checklist line, because it governs how every other
rule ages.

Draft:

> ### the model is a variable
>
> Model and harness co-optimise. The model side of that pair changes on its own
> schedule, and when it does, two things change with it: what a skill needs to
> say, and what shape it needs to take.
>
> **Capability absorbs content.** Knowledge a newer model carries makes the
> skill that supplied it redundant — and worse than redundant, because an
> instruction restating general competence competes with a better plan the model
> already had.
>
> **Operating mode changes shape.** A generation that works from constraints and
> an explicit definition of good does not need the step decomposition an earlier
> one required. Constraints and gates travel across generations. Scaffolding
> does not.
>
> Per instruction: does it carry what the model cannot derive; does it override
> a default (then say which, and why); or does it restate competence (then
> delete it). The trigger is the release, not the calendar.

**2. Principle 5 needs its boundary stated.** *"Controlled retrieval over
training data"* currently ends: *"When you find yourself relying on the model's
innate knowledge repeatedly for the same domain, that's a signal to create a
skill."* Under a model that already handles the domain, that is a recipe for the
friction class. The principle is right for knowledge that is versioned,
repo-specific, contested, or newer than the model. It is wrong applied to
general competence. The inverse test belongs beside it: **what does this supply
that the model cannot derive?** — asked before writing the skill, not after it
underperforms.

Principle 6 (`human feedback closes the loop`) should also name the model
release as one of the events that reopens the loop; today it names only the
maintenance workflow.

Nothing else in `VISION.md` needs changing. It is not the drifting document.

### What best_practices.md becomes

Reshaped, not relocated, and not split into three. The reflexive point is the
whole argument: **a 128-item checklist is the scaffold shape.** The document
telling authors to write constraints and gates is itself written as an
undifferentiated to-do list where a line asserting a hard runtime fact
(`timeout` is in seconds) looks identical to a line asserting taste (bullet
points preferred over prose). Rebuild it in the shape it recommends:

1. **Constraints** — what must not happen, each with its consequence and, where
   one exists, the check that catches it. *"Hook `timeout` is in seconds; 3000
   is fifty minutes."* *"Exit 0 does not approve a `PreToolUse` call."* These
   are the highest-value lines in the file and the ones that have already
   prevented real bugs.
2. **Gates** — how you know a skill or plugin is good, each bound to the command
   that measures it. Token budget, description precision, version alignment live
   here. Anything in this part without a command that produces its number either
   gets the command or gets deleted; that rule alone removes the two signals
   sections.
3. **Harness facts** — the reference layer: frontmatter fields, hook events,
   substitutions. A table, loaded on demand, not checkboxes. Nobody "verifies"
   that `${CLAUDE_SKILL_DIR}` exists; they look it up.

The evidence-class tags (`harness` / `model` / `craft`) ride on top of that
structure for the maintenance mechanism in section 5. The two are orthogonal:
class determines when a line gets re-checked, part determines what a reader does
with it.

Two further consequences of the portability scope:

- **Mark what is Claude Code-specific versus cross-vendor.** The audience spans
  Claude Code, Cowork, cloud sessions, and the Agent SDK, whose surfaces differ
  (user-scope skills are not read in Cowork or cloud sessions; `context: fork`
  behaviour varies by agent type). Today only `validate --strict` touches this
  axis, and the document is silent.
- **The worldview intros go.** They are a second copy of `VISION.md`, said less
  well. Replace each with a one-line pointer. That is the invariant 1b treatment
  the pair has never been given.

## 5. Mechanism redesign

### Do not split the file

The tempting move is three files, one per body. Resist it. Three files is three
`last updated` dates, three sync obligations, and it destroys the one property
worth keeping — that there is a single place to read. Tag sections instead.

### Tag each section with its evidence class and trigger

Extend the existing annotation rather than inventing a new format:

```
<!-- class: harness | source: https://code.claude.com/docs/en/hooks
     | verified_hash: 3f2a91c8e4d07b56 | last_verified: 2026-07-21 -->
```

- `class: harness` — carries `source` plus `verified_hash`, the upstream page
  hash the section was checked against.
- `class: model` — carries the model generation it was validated against and,
  where one exists, a pointer to the A/B that established it.
- `class: craft` — carries the audit or incident that produced it. The existing
  `<!-- source: field-tested in a sibling repo's claims-reminder apparatus,
  2026-08-03 -->` is already exactly this shape and should stay as the model for
  it.

### Replace the calendar arm with a hash join

`upstream_hashes.json` already stores per-page hashes. Sections already declare
their page. Nothing joins them. Add that join to `skill-maintain upstream`:
after fetching, report which `class: harness` sections cite a page whose hash
has moved past their `verified_hash`.

That converts "the file is 4 days old" into "the hooks section was verified
against a `docs/en/hooks` two revisions and +69k chars behind." The hash is the
evidence; the file-level date demotes to a human breadcrumb and stops being a
gate.

This is the same move the repo already made for SKILL.md freshness on
2026-08-04 — *a calendar window is a proxy for source movement, and a lazy one
where movement is observable*. Fourteen SKILL.mds went to
`metadata.freshness: "cascade"` that day. `best_practices.md` is the last
significant holdout, and it is the file where the observation infrastructure
already exists and sits unused.

### Make the green state its scope

Per the file's own control-authoring rule, the report prints derived counts:
sections checked, sources moved, and **sources not tracked**. That third bucket
is not hypothetical — it catches `agentskills.io` today, and it surfaces the
inverse problem too: six tracked pages (`plugins-reference`, `discover-plugins`,
`plugin-marketplaces`, `settings`, `permissions`, `mcp`) are fetched every pass
and cited by no section.

### Give the backlog a disposition field

The backlog's 44 bullets need three states, not one: `absorbed`, `rejected`
with a reason, `deferred` with what would change the answer. Without that, every
pass re-reads the same items and the list can only grow. "Already applied (do
not redo)" proves the instinct is already there; it just needs its negative
counterpart.

### Route audit findings into the file

The instruments already run. What is missing is one line in each audit's output
contract: when a finding generalises past its instance, name the
`best_practices.md` section it belongs in. Phase 7 then has a queue instead of a
blank page. This is cheap and closes the craft-facts loop without new machinery.

### Run claim-audit on the best_practices diff during Phase 7

Freshness catches drift; it cannot catch wrong-on-day-one, which `maintenance.md`
already names as an open gap. Every edit to this file is added prose asserting
upstream behaviour, which is precisely claim-audit's subject. Already built,
costs nothing new.

## 6. What to build, in order

*Ordering revised the same day it was written, after the Opus 5 datum. The first
draft opened with the hash join. That was wrong: the hash join catches harness
drift going forward, while `### instructions quality` is producing wrong-shaped
skills right now, costs nothing but an edit to fix, and changes what gets built
next.*

0. **Add `the model is a variable` to `VISION.md`, and bound principle 5.** No
   code, and it is the altitude the rest inherits from. Doing this after the
   checklist rewrite means rewriting the checklist twice.
1. **Rewrite `### instructions quality` for the constraints-and-gates shape.**
   No code. Eight items that currently push every new skill toward the scaffold
   shape. Until this changes, every other improvement here compounds in the
   wrong direction. Then re-part the file into constraints / gates / facts.
2. **The hash join.** One function in `upstream.py`, reusing state already
   collected. Replaces a calendar arm the repo's own doctrine calls lazy, and
   makes the twelve stale stamps visible instead of invisible. Everything
   downstream of the harness body needs this signal.
2. **Correct the three false claims** — the README line, the `init-maintenance`
   description, and invariant 3's justification. Cheap, and they are actively
   misleading about how the file is wired.
3. **Add release notes as a source.** Highest-value single addition; likely
   *reduces* Phase 7 effort by replacing diff-reading with change-reading.
4. **Delete the unmeasured sections** (quality signals, iteration signals) and
   demote spec compliance to a pointer. Removing 26 items nobody can act on is
   worth more than adding checks.
5. **Mechanise the hooks section.** Nineteen items, statically checkable against
   this repo's own `hooks.json` files, and the class that already produced real
   bugs.
6. **Reconcile the three source lists**, and decide whether `update-coderef.sh`
   becomes tracked or `tracked_repos` becomes the only list.

Model-facts A/B measurement is deliberately last and deliberately unscheduled.
It is the most valuable thing here and also the only item that needs a method
this repo has not built. Do not let it block the six items above.

## 7. How we would know this worked

Stated in advance so the evaluation cannot be chosen after the fact:

- The drift backlog's unabsorbed count goes **down** across two consecutive
  maintenance passes, or every remaining item carries a `rejected` reason. If it
  keeps growing, absorption is still the bottleneck and the hash join only made
  detection louder.
- At least one `class: harness` section is flagged by the hash join, reviewed,
  and either updated or re-stamped — proving the join can fire. Until that
  happens it is an unbracketed control, and this repo does not trust those.
- A tracked repo produces a cited rule, or gets dropped. Five more months of
  zero citations is the retirement condition, not an invitation to wait longer.
- The Opus 5 triage names at least one skill in each of the three classes —
  keep, override-with-stated-why, delete. A pass that finds only keepers has not
  been run adversarially; the friction class is the one it exists to find, and a
  triage that never finds it is measuring the author's attachment rather than
  the skills.

## 8. Retirement condition for this document

This is a design record. When items 1-6 are built, fold the resulting mechanism
into `maintenance.md` and cut this file down to the analysis in sections 1-3,
which is the part worth keeping as history. If nothing here is built within two
maintenance passes, that is evidence the problem was not worth the machinery —
delete the file and record that verdict rather than leaving a stale proposal
standing.
