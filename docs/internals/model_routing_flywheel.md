last updated: 2026-08-01

# model-routing as a data flywheel

> Design notes, not a verdict on shipped work. `model-routing` and
> `fact_delegation` do what they were built to do. This document argues they
> were built as a **logging and reporting** system, and describes what would
> have to change for the loop to actually compound.

## What exists today

**The rule** (`skills/model-routing/.../references/model-delegation.md`) states
delegation criteria as task properties: well-specified, mechanical or
pattern-bound, verifiable. Judgment work stays in the orchestrator. It is a
static markdown file installed into a target project.

**The optional feedback layer** — *removed in `model-routing` 0.5.0; described
here in the past tense because the diagnosis below is what motivated removing
it. See the closing section for what superseded it.* It appended an
instruction: after verifying a delegated result, run

```
agent-state delegation record --task ... --model ... --outcome <accepted|revised|redone|escalated> \
  --verification <tests|diff_review|schema_validation|spot_check|none> --domain ... --orchestrator-model ...
```

and "skip silently" if the CLI is absent.

**The store** is `fact_delegation` in `<HOME>/.claude/agent_state.duckdb`.
Grain: one row per delegated subagent task, recorded when the orchestrator
verifies the result. Columns: task_summary, task_domain, model_name,
orchestrator_model, outcome, verification, timestamps, metadata JSON.

**The aggregate** is `v_delegation_stats` — acceptance rate grouped by
(model_name, task_domain), with the comment "the signal for tuning down-tier
delegation criteria from data rather than intuition."

That is a well-built star-schema fact table. The problem is not the modelling.

## Diagnosis: the loop is open

A flywheel needs four links: capture → aggregate → **change behavior** →
generate new signal. Test each.

**Capture — partial and biased.** Recording is voluntary, unenforced, and
performed from memory at the end of a task. "Never block work on recording"
means the miss rate is high, and it is not randomly high: memorable delegations
get recorded, routine ones evaporate. Worse, the orchestrator delegates the
work, verifies the work, and grades the work. Self-reported outcomes from the
party whose decision is being evaluated.

**Aggregate — thin.** `v_delegation_stats` has no sample-size gate, so one
delegation at 0% reads like ten at 0%. No time decay, though "haiku" in May and
"haiku" in August are different models behind the same string.

**Change behavior — this link does not exist.** Nothing reads
`v_delegation_stats`. The rule is a hand-written file. The feedback addon's own
closing line is "Review with `agent-state delegation stats`" — a human opens a
table and may or may not rewrite a markdown file by hand. There is no mechanical
path from evidence to policy.

**New signal — never reached**, because behavior never changed.

So the honest description is: a manual logging habit feeding a report that
nobody is obligated to read, terminating in a hand-edit. Every individual piece
is fine. It is just not a loop.

## The deepest flaw: the schema speaks a different language than the rule

This is the one I would fix first, because everything else is downstream of it.

The rule routes on three properties: **well-specified**, **mechanical**,
**verifiable**. The fact table records **domain** ('coding', 'data', 'docs') and
**outcome**.

None of the rule's criteria are columns. So the data can never answer the
question the rule actually asks. You can learn "haiku has a 0.6 acceptance rate
on coding tasks" — which is not actionable, because the rule never said "route
coding tasks to haiku." It said "route *well-specified, mechanical, verifiable*
tasks down-tier." Whether that criterion is any good is exactly what the table
cannot tell you.

`task_domain` is a proxy someone reached for because it was easy to fill in. It
measures the wrong thing precisely.

## Second flaw: the grain excludes the counterfactual

Grain is "one row per delegated task." There is no row for *considered and kept
in the main loop*.

The consequence is directional and permanent: **the data can only ever show that
delegation was too aggressive, never that it was too conservative.** Every task
the rule declined to delegate is invisible. A rule that delegates nothing scores
a perfect acceptance rate.

A system that can only ratchet toward caution is not learning the boundary. It
is walking away from it.

The dimensional-modeling skill in this repo preaches grain-first design, and
this is a grain bug: the fact being modelled is not "a delegation," it is **"a
routing decision."** Delegating and not-delegating are two values of one
decision, and both belong in the table.

## Third flaw: acceptance rate is not a decision variable

Nothing about cost is recorded. No tokens, no dollars, no wall-clock — for the
subagent *or* for the orchestrator's verification pass.

Acceptance rate alone cannot answer "was this worth it." 70% acceptance at
one-tenth the cost is a clear win. 95% acceptance where verification burned more
orchestrator tokens than doing the work directly would have is a **loss** — and
the current schema cannot distinguish those two cases, or even represent the
second one.

That failure mode is not hypothetical. Verifying an unfamiliar diff is often
more expensive than writing the diff. A delegation system blind to verification
cost will happily recommend delegations that lose money at a 100% acceptance
rate.

## Principles for a redesign

**Derived beats declared.** Every field the orchestrator must self-report is a
field that gets skipped, guessed, or flattered. Rank instrumentation by whether
the system can observe it rather than ask for it. A Task tool call happened; a
file was edited after a subagent returned; a session ended with no record
written — all observable. "Was this task well-specified?" is not.

**The grain is the decision, not the action.** Include non-delegations. Without
the counterfactual there is no boundary to find.

**Cost is the dependent variable, quality is the constraint.** Record tokens and
wall-clock on both sides of the delegation, including verification. Then the
question becomes "did this save anything at acceptable quality," which is
answerable.

**Machine-gather, human-decide.** Evidence collection should be automatic;
policy change should not be. An auto-tuning rule that widens delegation because
acceptance looks high is a system optimizing a number it also controls — the
exact failure this repo already refuses elsewhere. Generate the *proposal*, make
a human accept it.

**Don't over-instrument.** Each added required field lowers the capture rate of
every other field. Prefer four reliable columns to twelve aspirational ones.

## Concrete changes, ranked

**1. Record the rule's own vocabulary at delegation time.**
Three fields, asserted when the delegation is made rather than remembered
afterwards: `well_specified`, `mechanical`, `verifiable_by`. Now acceptance can
be cross-tabulated against the criteria the rule is written in. That is the
difference between "haiku is 0.6 on coding" and "verifiable-by-tests predicts
acceptance; verifiable-by-spot-check does not, at any tier" — the second is a
rule edit.

**2. Widen the grain to routing decisions.**
Add `not_delegated` as an outcome with a reason. One extra row per decision,
and the conservative failure mode becomes visible for the first time.

**3. Add cost columns on both sides.**
`subagent_tokens`, `orchestrator_verify_tokens`, `wall_clock_ms`. Derive from
the harness where possible rather than asking. Then compute realized savings
per (criteria-profile, tier) instead of a bare acceptance rate.

**4. Fix capture rate with a Stop hook, not a reminder.**
A session that made Task calls and wrote no delegation records is a
*mechanically detectable condition* — tier 2 by invariant 1c. One line at
session end naming the count. This costs nothing when there is nothing to say,
which is the property that makes a hook defensible here where a SessionStart
directive would not be.

**5. Gate on sample size and decay by age.**
No recommendation under n≈10. Weight the last 60 days higher. Model identity
should include a captured version or date, because tier names are reused across
genuinely different models.

**6. Close the loop with a generated, human-accepted policy appendix.**
The criteria section of the rule stays hand-written — those are principles. Add
a generated block below it:

```
agent-state delegation policy --emit    # proposes an appendix from the data
```

stating, for this repo at this sample size, which criteria profiles have earned
down-tier routing and which have not, with counts. A human reviews and accepts
the diff. That is the missing link — evidence reaching policy through a gate
rather than through somebody's memory of a table they looked at once.

**7. Allow deliberate exploration.**
An `--explore` flag marking an intentional out-of-policy delegation, logged
separately so it does not pollute policy stats. Without an explicit exploration
path, a policy tuned only on in-policy data can never discover that its boundary
is drawn too tight. Small change, and it is the only mechanism that lets the
rule loosen.

## What not to do

- **Do not auto-rewrite the rule.** See "machine-gather, human-decide."
- **Do not make recording blocking.** The current "skip silently" instinct is
  right; the fix for low capture is observation and a cheap nudge, not
  enforcement.
- **Do not keep `task_domain` as the primary cut.** It is the wrong axis. Keep
  it as a secondary label if useful, but stop treating it as the signal.
- **Do not add a dashboard before fixing the schema.** A prettier view of the
  wrong columns is a more persuasive wrong answer.

## Why this generalizes to the other routing plugins

`fact_delegation` already has an `escalated` outcome and an
`orchestrator_model` column. With the vocabulary and grain fixes above, one fact
table serves all three routing decisions in this repo:

| Plugin | Direction | Binding constraint |
|---|---|---|
| `model-routing` | down-tier, within Claude | cost |
| `advisor` | up-tier, within Claude | capability, bounded by spend |
| `gemini-bridge` (designed, not started) | cross-vendor | capability the default lacks |

All three are "should this work happen somewhere other than here," and all three
currently answer it from intuition or from a single memorable incident. Recording
them into one table with a shared vocabulary means the answer to "when is a
different model worth it" gets learned once instead of three times.

For `gemini-bridge` specifically this is the reason not to write a Gemini clause
into `model-routing` now: after a month of logged calls — recipe, model, tokens,
cost, accepted or not — the routing rule can be written from the log. See
[gemini_bridge_design.md](gemini_bridge_design.md).

## The one-line version

The current system measures *what happened to delegations that occurred*, graded
by the party that made them, in a vocabulary the routing rule does not use, with
no cost data and no path back into the rule. Fix the vocabulary, widen the grain
to include decisions not taken, add cost on both sides, and put a human-accepted
generated appendix at the end of the loop. Then it compounds.

---

# Addendum, 2026-08-01: what changed after this was written

Everything above stands. This section records facts that arrived later the same
day, one of which changes the order of work and one of which changes the
question being asked.

## The rule is gone, and that is the experiment

The rule was removed from all eight repos carrying it, and `model-routing` 0.4.0
paused installation (`disable-model-invocation: true`, so it cannot reinstall on
Claude's judgment).

That was done to stop paying for an unmeasured belief. The side effect is more
valuable than the intent: **there is now a before/after.**

| | Period | Delegations |
|---|---|---|
| Baseline | 2026-03-06 → 2026-08-01, rule installed | 947 |
| Treatment | 2026-08-01 onward, rule absent | accumulating |

If the rate, tier mix, and shape of delegation do not measurably change, the
rule was inert. No labelling, no instrumentation, no new schema — just the same
observational query over two windows.

This is a different question from the one this document asks. Everything above
assumes the rule is worth repairing and asks how. This asks whether it does
anything at all, and it is much cheaper to answer. It should run first, because
a null result makes the rest moot. It also directly tests invariant 1c's
suspicion that some rules here compensate for older-model limitations that no
longer exist.

## The capture diagnosis is now wrong, in a good way

"Capture — partial and biased" was accurate for `fact_delegation`. It is not
accurate for what is available.

`fact_delegation` was never populated — the table does not exist in the live
database, which has had no writes since 2026-03-12 (see
[agent_state_population.md](agent_state_population.md)). Meanwhile `ccutils`
holds **947 delegations** derived from transcripts: observational, complete, and
retroactive over five months. No self-reporting, no miss rate, no cooperation
from the party being evaluated.

The principle "derived beats declared" was already stated here. What is new is
that the derived half is already sitting in a warehouse.

It is not usable yet. Measured against `archive.duckdb`:

```
fact_agent_delegations -- 947 rows
  async_launched    724    0 tokens   0 duration   0 agent_session_key
  completed         192  192 tokens 192 duration   0 agent_session_key
  (null)             31
```

Subagents run in the background by default now, so the parent's tool result is a
launch acknowledgment. 76% of delegations carry no metrics, and two columns hold
values that read as valid and are not — `completion_timestamp` is the
acknowledgment time, and `seconds_to_completion` derived from it measures
acknowledgment latency. All of it is recoverable from files already on disk.
Fixes are specified in the ccutils repo at
`internal/plans/2026-08-01_agent_delegation_capture_gap.md`.

## Re-ranking the seven changes by observable vs. assertable

With transcripts as the source, most of the ranked list above no longer needs a
recording habit:

| Change | Status |
|---|---|
| 3. Cost on both sides | **Observable.** Subagent tokens and duration from its own JSONL; orchestrator verification cost from `fact_token_usage`. |
| 4. Fix capture rate with a Stop hook | **Moot.** Transcripts already capture 100% of `Task`/`Agent` calls. The hook existed to patch a voluntary-recording gap that does not apply. |
| 5. Model identity as captured version | **Already done.** `dim_model` holds exact ids (`claude-opus-5`, `claude-fable-5`, …), not tier names. |
| 1. Criteria vocabulary | **Assertable only.** No transcript records why the orchestrator judged a task well-specified. |
| 7. Exploration flag | **Assertable only.** |
| 2. The counterfactual | **Partially observable.** "Considered and declined" leaves no trace, but main-loop stretches of mechanical tool calls are a detectable proxy — inference, needing its own control. |
| 6. Generated policy appendix | Unchanged, and still last. |

So **only changes 1 and 7 require anything to be declared.** That is a much
smaller instrumentation surface than this document assumed, and it sharpens a
tension already latent here: "derived beats declared" is listed as a principle,
while the top-ranked change asks the orchestrator to declare three fields. Given
that nearly everything else is now free, the honest question is whether those
three fields are worth the capture-rate cost the principles section itself warns
about — *"each added required field lowers the capture rate of every other
field."*

Worth considering that the observable-only cut (tier × agent type × cost ×
duration × outcome) may answer the practical question adequately. If it does,
nothing needs instrumenting, and the delegation half of the agent-state
populate-or-retire decision resolves by becoming unnecessary.

## Correction to the proposed gate

An earlier version of the plan was to hand-label ~50 delegations from the 192
`completed` rows, since those are the ones with real metrics. **That sample is
biased and the bias points the wrong way.**

The completed rows are the *synchronous* delegations — systematically the
shorter, lighter ones. The 724 async rows are the long-running expensive ones.
Short mechanical tasks are exactly where down-tier routing works best, so a
sample drawn only from them would very likely return "delegation works fine,"
and that finding would be an artifact of the sampling frame.

Split the gate into two questions with different data requirements:

- **"Is the outcome label decidable from the record?"** A methodology question,
  unaffected by which rows are sampled. Answerable today on the sync rows. If a
  reader cannot reliably tell *accepted* from *quietly redone*, nothing
  downstream works.
- **"Does acceptance vary by tier?"** Needs the full population. Blocked on the
  ccutils capture fix.

## Revised order

1. **ccutils capture fix** — `agent_session_key`, then re-derive async rollups.
   Retroactive, so it repairs the five-month baseline rather than starting a new
   collection window. Plus `get_model_family`, which files `claude-fable-5` —
   third-most-used model, second-largest output producer — as `unknown`, so
   every tier-grouped cut is currently wrong.
2. **Decidability check** — ~30 minutes of reading. Parallel with 1.
3. **The before/after comparison.** Cheapest real answer available.
4. **Decide whether anything needs asserting** — changes 1 and 7 only, and only
   if the observable cut proves insufficient.
5. **Rewrite the rule**, if justified. Two gaps identified separately and still
   open: no delegation *floor* (a three-line rename satisfies all three criteria
   but costs more to specify than to do), and no *escalation policy* (the rule
   says "always check what comes back" and stops).
6. **Unpause.**

## Expiry on the pause

A pause without a decision date becomes indefinite limbo, which is the same
failure as the empty-but-documented state described in
[agent_state_population.md](agent_state_population.md), arriving by a different
road. So the condition is written down rather than left to memory.

**Deprecate `model-routing` if either holds:**

- the before/after comparison shows no measurable difference in delegation
  behavior, or
- **2027-02-01** arrives with the ccutils capture work not done.

Removal follows the standard procedure in `.claude/rules/plugins.md`: delete the
directory, drop the `marketplace.json` entry, add `"renames": {"model-routing": null}`
so existing installs get a removal notice rather than `plugin-not-found`, sweep
the README (plugins table, install list, invocation list), and write a CHANGELOG
entry. Same path `env-forge` took.

The feedback layer was already removed in 0.5.0 — it depended on a table that
never existed and asked the agent to grade its own work. That part needed no
waiting.

## The outcome this should be allowed to have

The rule may not come back, and that is a legitimate result rather than a
failure. In its current state `model-routing` costs nothing: nothing installed,
no always-loaded text, no false measurement, removal still working. The plugin
keeps shipping, so it is one command away if evidence ever justifies it.

The failure mode to avoid is unpausing on intuition, which is how it became
fuzzy the first time.
