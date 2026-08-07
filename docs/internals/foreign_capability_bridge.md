last updated: 2026-08-02

# The foreign-capability bridge

> Status: **a contract, not a library.** One bridge exists (`apps/gemini-bridge`,
> shipped). This document states the discipline a second one should follow, so
> that the second is cheap and so that the differences between them are
> informative rather than accidental. **No shared code exists and none should be
> written yet** — see "Extraction" at the end for the trigger and the scope.
>
> The title says *capability* and the category below says *consultation*. That is
> deliberate, not drift: the first draft of this document scoped it to work
> Claude cannot do at all, and a design conversation the same day showed that was
> too narrow — a second opinion is work Claude *can* do, and belongs here too.
> The filename is load-bearing (two indexes link it) so it stays; the category
> widened. Foreign capability is now one of two kinds inside it.

## The category

The durable abstraction is not "a bridge to other models." It is a **foreign
consultation**: anything that

1. costs real money or real time, and
2. returns output of unbounded size, and
3. **does not mutate your working tree.**

Those three properties, not the vendor, generate every constraint below.

The third is the boundary of this document, and it is the one that took a second
pass to find. The first version of this section said "any consultation that
Claude cannot perform itself," which was too narrow in one direction and too
broad in another. Two useful things sit inside the boundary:

| Kind | What it is | Example |
|---|---|---|
| **Foreign capability** | Claude cannot do it at all | comparing two renders; watching a video; a corpus that will not fit |
| **Foreign opinion** | Claude *can* do it — the value is that a different model fails differently | a second read on a design; an outside review of a session |

Both are in scope, and the invariants below apply to both. Non-models qualify
too: a solver, a fuzzer, a long-running analysis, an embedding pass.

What sits **outside** is a third kind:

> **Foreign agent** — an external harness (Antigravity, Codex, any agentic CLI)
> that runs its own tool loop against your filesystem. That is not a
> consultation; it is a competing agent with hands on the same working tree.
> Different plugin, different design, and the invariants here do not carry over.
> Its central problem is isolation — a worktree, a sandbox, and a merge story —
> none of which a consultation needs. Do not extend this contract to cover it.

The framing matters because it determines what gets built. "A bridge to other
models" invites an abstraction layer over vendors. "A foreign consultation"
invites a protocol, which is what this is.

## The cut is mutation, not execution

The obvious place to draw the line is "does it run code," and that is wrong. A
second opinion frequently *cannot be given* without execution: opinions about
design are readable, opinions about behaviour are not. This repo's own strongest
evidence for that is `gemini_bridge_design.md` — every static source about the
Gemini API was wrong about something material, and only live calls settled it. An
advisor reasoning from a description would have been confidently wrong the same
way the documentation was.

So the line is **mutation**:

- **Non-mutating execution is in scope** — running the test suite, profiling,
  probing an API, grepping the tree. Nothing changes, so there is no merge story
  and no isolation requirement.
- **Mutating execution is out** — writing files, installing, committing. That is
  the foreign-agent case above.

### Claude executes; the foreign model advises

When a consultation needs evidence, the foreign model says what it needs and
**Claude runs it** — under the permission prompts, tool logging, and approval
flow that already exist. The foreign model never touches the machine.

This is the opposite of the function-calling path in
[gemini_bridge_design.md](gemini_bridge_design.md)'s open question 4, which
inverts control: the foreign model drives a loop executing code outside Claude
Code's permission system. Same capability, opposite direction of control, and
the direction is the whole safety argument. That document already identified the
right function shape without connecting it to advising — *"the high-value
functions are ones that let it ask for more data about what it is already looking
at, not ones that act."* Read-more, not act. That generalises past frames and
images to test output and profiles.

### Two stateless calls, not one stateful conversation

The obvious implementation of an evidence loop is a stateful follow-up. Avoid it:
statefulness requires `store: true`, and stored interactions cannot be deleted.

Instead:

1. **Stateless call 1** — "here is the situation; what evidence would change your
   answer?" Returns a list.
2. You run what you are willing to run.
3. **Stateless call 2** — a fresh, better-informed request carrying that evidence.

Storage stays off, and you keep a veto between the two. The second call is not a
continuation; it is a better question.

### What this adds to the threat model

A consultation that can request evidence introduces a party that can **ask** for
things. Until now the risk was the caller accidentally including something
sensitive; now there is a counterparty that can say "show me your config."

The existing guards still hold, because a content scan is content-based and does
not care who prompted the text. But this is a new reason they matter, and it is
the argument for
[tiered_authorization.md](tiered_authorization.md): an evidence-gathering
consult over a session digest is a different risk class from comparing two
images, and it is much closer to `advisor`'s threat model — which is locked to
user invocation precisely so a model cannot self-authorise its own second
opinions.

## The shape: a bridge is a subagent with a file boundary

VISION.md's tree topology says a subagent receives scoped context, executes,
returns to the orchestrator, and disappears. A bridge call is structurally
identical: scoped context in (a stance, a question, attachments), execution
elsewhere, a return, and nothing of the intermediate work persists in the
caller. Gemini's thought tokens — 195 of them for "17 × 23" at `thinking: high` —
never touch Claude's window.

The bridge is **stricter than a subagent in one way, and it is the important
one**: a subagent returns text directly into the orchestrator's context, while a
bridge returns *a path*, and the caller decides how much to read.

That difference is measurable. A survey agent run during this design session
returned roughly 1,500 words into the orchestrator's context, all of which
persisted for the rest of the session; two sections were acted on. Had it written
a report file and returned a path, the cost would have been one line plus two
deliberate reads.

**The bridge discipline is better than the harness's own default.** Invariant 1
below is worth applying to ordinary subagent delegation, not only to external
vendors.

## The seven invariants

### 1. Return a path, not a payload

The answer lands on disk. Standard output carries a status line, a location, and
counts — nothing that would be expensive to have been wrong about.

Rationale: you cannot un-pollute a context window mid-session (VISION.md,
"precision is the constraint"). Tool output persists for the remainder of a
session, so a 40 KB response printed to stdout is thousands of tokens that cannot
be reclaimed, spent before anyone decided the content was worth having.

Corollary: the caller must be able to read *part* of the answer. A single opaque
blob on disk satisfies the letter and not the point.

### 2. The stance is versioned data, not composed prose

The analytical framing — what the consulted party is being asked to be — lives
in a tracked file. The caller supplies only the specific question.

Rationale: a stance composed fresh each session makes the answer depend on how
the question happened to be phrased that day, which makes two runs incomparable
and a regression invisible. A file is diffable, reviewable, and can carry a
determinism knob alongside it. "New behavior is new data, not new code"
(VISION.md, "the harness is the system").

Consequence: there must be a default stance for the unstructured case. Otherwise
the ad-hoc majority of calls has no path at all, which is the state
`gemini-bridge` shipped in until 0.5.0 — `--recipe` was required and exactly one
recipe existed.

### 3. Tiered scope with evidence-gated promotion

Stances live at three tiers: **bundled** (ships with the plugin), **user** (yours
across projects, ships nowhere), **project** (travels with one repo). Resolution
is most-specific-first.

Promotion between tiers requires evidence, not enthusiasm:

| Promotion | Test |
|---|---|
| ad hoc → project | asked twice in this project |
| project → user | a second project wants it; if you edit it to fit, it was not ready |
| user → bundled | read it as a stranger; if it names your work, it stays user |

Rationale: "You don't prepare it first and use it second. You use it, and the
using prepares it" (VISION.md, "use it, then prepare it").

Without the middle tier, project-shaped stances get published to everyone because
bundled is the only place to put them. `perceptual-diff` says "the same 3D scene,
produced by the same pipeline" — one project's need, shipped to all, because the
user tier did not exist when it was written.

### 4. Progressive disclosure applies to the bridge's own documentation

The always-loaded skill body holds only what is true of every stance. Anything
true of one stance lives with that stance.

Rationale: stance files are read by the tool at call time and never enter the
context window, so fifty of them are free. What is not free is stance-specific
knowledge in the skill body, which is paid on every activation. This fails
quietly: `gemini-bridge`'s SKILL.md carried two `perceptual-diff`-specific
sections while only one recipe existed, which would have become six sections at
six recipes.

Mechanical trap: if the stance file's body becomes the system instruction, notes
appended there are transmitted and billed. The caller-facing notes need a
delimiter.

### 5. Files are the store; relational is the lens

Artifacts stay files. Facts are append-only and queried in place.

Rationale and the deciding test are in VISION.md, "structured outputs as state":
ask what reads the artifact besides a query. A prompt that must stay re-runnable,
a response another agent opens deliberately, a manifest that is the only local
record of remote state — none of those survive being flattened into a row.

Precedent, and it predates any bridge: `postmortem-index` rebuilds its index from
the directory every time and refuses to commit a listing, because "a listing that
gets committed and trusted becomes a copy that drifts out of agreement with the
directory" (`skills/postmortem/skills/postmortem-index/SKILL.md`). The same
plugin refuses to store a supersedes chain for the same reason
(`skills/postmortem/references/filing.md`). That is CLAUDE.md
invariant 1b derived independently, for a unit with no connection to this one.

### 6. Facts at call time, outcomes as a later keyed append

Record what the call reported: what ran, whether it succeeded, what it consumed.
Never record a judgment of quality at call time.

Rationale: at call time nobody knows. Worse, the party that would grade it is the
party being evaluated — the caller composes the request, reads the answer, and
would score its own decision. That is the flaw diagnosed in
[model_routing_flywheel.md](model_routing_flywheel.md): self-reported outcomes
from the party whose decision is under evaluation.

The outcome, when it comes, is a separate record keyed to the run. Its vocabulary
should describe **evidential value**, not work-product quality — a verdict is
evidence, not a deliverable, so `accepted / revised / redone` does not transfer.
Something closer to `acted_on / confirmed / contradicted / unusable`.

The single most valuable row is `contradicted`, and it is knowable only later.
That is the argument for the keyed-append shape: it works precisely because
querying is decoupled from storage (invariant 5), so a late record joins rather
than migrates.

### 7. Guard at the narrowest chokepoint that covers every caller

Refusals, budget limits, and content checks live in the tool, not in a hook.

Rationale: the tool is the one place that covers interactive use, scripted use,
subagent use, and a human at a shell identically. A hook covers one harness and
fails the tier test in CLAUDE.md invariant 1c. Guards must also refuse rather than
warn when the action is irreversible — for `gemini-bridge`, `interactions.delete`
returns HTTP 501, so anything sent is permanent for the retention window and a
warning the caller can ignore is not a control.

Corollary learned the hard way: a guard that implies protection it does not
provide is worse than no guard. State what it does not cover, in the place
someone would look for reassurance.

## The boundary: capability routing is not cost routing

Three routing decisions exist in this repo and they are not the same question:

| Plugin | Direction | Binding constraint |
|---|---|---|
| `model-routing` | down-tier, within Claude | **cost** — several options work, pick the cheapest |
| `advisor` | up-tier, within Claude | **capability**, bounded by spend |
| `gemini-bridge` | cross-vendor | **capability** — the default option does not work at all |

Do not merge them. "Is this mechanical enough for a cheaper model" and "can the
default do this at all" have different evidence and different failure modes.
Folding them together makes both criteria fuzzier, and the argument is developed
at length in [gemini_bridge_design.md](gemini_bridge_design.md).

## Anti-goals

**Not a model-agnostic abstraction layer.** VISION.md rejects model-agnostic
design directly: the harness optimizes for specific model capabilities, and
abstraction sacrifices the coupling that makes it work. It would also fail on its
own terms here — `gemini-bridge`'s recipes are good *because* they are coupled to
Gemini specifics (per-item media resolution semantics, `transcription_config`,
the asymmetry between storing and deleting). An abstraction over "any vision
model" erases exactly the detail that makes a stance worth versioning.

**Not a framework at N=1.** Every invariant above was derived from one
implementation with a lifetime call count in the single digits. A second instance
is what separates the essential from the incidental.

**Not a shared vendor layer, ever.** Authentication, media handling, and API
semantics stay per-bridge even after extraction. Those are the parts that differ,
and pretending otherwise is the model-agnostic trap wearing a smaller hat.

## Extraction

**Trigger:** a second bridge exists and has been used for real work.

**Method:** the second bridge follows this contract or documents why not. The
divergences are the data — an invariant that survives two unrelated capabilities
is real; one that bends was incidental to vision.

**Scope, when it happens:** small. The run-directory contract, the append-only
fact log, and a schema-agnostic stance parser. Roughly `runs.py`, `ledger.py`, and
`recipes.py` from `apps/gemini-bridge`, with the vendor coupling left behind.

Do not extract before the trigger. The repo has a worked example of the cost:
`model-routing`'s delegation feedback layer was built ahead of its evidence and
removed in 0.5.0.

## See also

- [gemini_bridge_design.md](gemini_bridge_design.md) — the one implementation, and
  the API facts that only live probing established
- [model_routing_flywheel.md](model_routing_flywheel.md) — why self-graded
  outcomes do not close a loop
- [tiered_authorization.md](tiered_authorization.md) — gating expensive calls by
  tier, designed and deliberately not built
- [../../VISION.md](../../VISION.md) — the context economy the invariants serve
