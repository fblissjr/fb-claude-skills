last updated: 2026-08-13

# architecture

The worldview the retrieval model in [VISION.md](../../VISION.md) serves: how
work is decomposed across agents, where behavior belongs, and what shape agent
output takes. Split out of `VISION.md` on 2026-08-13 so that document could stay
a short statement of retrieval principles; the sections below are unchanged in
substance and keep their original names, because other documents cite them by
name.

The companion claim, that the model itself is a variable and practices must name
the event that reopens them, stayed in `VISION.md` under "practices evolve;
sources decide". It is referenced from here rather than repeated.

## trees, not workflows

Linear A-B-C workflows compound context at every handoff. By step six, the model treats everything as one big input -- the condition where things go wrong silently. Earlier steps bleed into later ones, contradictions accumulate, and the model has no mechanism to forget what it shouldn't have seen.

The right topology is a tree. The orchestrator decomposes the problem to its lowest useful granularity, spins up focused subagents, they execute and return results to the orchestrator (not to each other), then disappear. Each subagent sees only its slice. The orchestrator synthesizes. This maps directly to the five invariant operations of selection under constraint: decompose, route, prune, synthesize, verify.

```
                      ORCHESTRATOR
                (decompose, route, verify)
                          |
        +-----------------+-----------------+
        |                 |                 |
        v                 v                 v
  +-----------+     +-----------+     +-----------+
  | subagent A|     | subagent B|     | subagent C|
  | (scoped   |     | (scoped   |     | (scoped   |
  |  context) |     |  context) |     |  context) |
  +-----------+     +-----------+     +-----------+
        |                 |                 |
        +-----------------+-----------------+
                          |
                          v
                      ORCHESTRATOR
                       (synthesize)

  Subagents execute and return; they never talk to each other.
```

Parallelism heuristic: divide work the way you would for humans. If you can't explain a clean division of labor to a team, you can't explain it to agents either.

## route to the cheapest capable model

Routing has two axes: what context a subagent sees, and which model executes it. The tree topology above covers the first. The second is model tiering: a well-decomposed leaf task -- mechanical edits, data transformation, well-specified coding -- is precisely the thing that doesn't need the frontier model. Decomposition quality and model tiering are complements: the better the orchestrator scopes a subtask, the lower the tier that can execute it.

Cost is a constraint alongside attention, with the same asymmetric failure modes: over-tiering wastes money silently; under-tiering produces wrong work that must be detected and redone. So the split follows judgment density. Design decisions, ambiguity resolution, user interaction, and verification of delegated results stay in the orchestrator on the strongest model. Execution of scoped, verifiable work routes down-tier, and the orchestrator checks what comes back.

Tier names change with the model lineup; the principle doesn't. State delegation rules in terms of task properties (well-specified, mechanical, verifiable) with current tiers as examples, not as a fixed task-to-model table.

## the harness is the system

Model and harness (Claude Code, Codex, Gemini CLI) are a single compound AI system that jointly optimizes. The moat is the harness and everything you don't see -- tool orchestration, context management, permission models, caching, retry logic, output formatting.

External wrappers can't optimize at the level the AI lab can. They break when the harness changes. They can't participate in the co-optimization loop between model and tooling.

Build inside the harness. Guide it with data and structure -- skills, rules, metadata, retrieval indexes. New behavior is new data, not new code.

Corollary: don't be model-agnostic for most use cases. The harness optimizes for specific model capabilities. Model-agnostic design sacrifices the tight coupling that makes the system work.

The model half of that compound system moves on its own schedule. That is the subject of "practices evolve; sources decide" in [VISION.md](../../VISION.md).

## context isolation over context accumulation

Each subagent gets only the precise context it needs. Precise beats bloated.

This is the memory hierarchy from early computing applied to attention. Fewer things in context means fewer contradictions, less prompt injection surface, less behavioral corruption.

Context isolation motivates the L1/L2/L3 loading hierarchy in `VISION.md`.

## use it, then prepare it

You don't prepare it first and use it second. You use it, and the using prepares it.

LLMs consume semantically rich data -- PDFs, images, unstructured docs -- more efficiently than ETL pipelines can parse them. Don't perpetually "get ready." A subagent extracts structured data from the raw layout. Another writes tests and validates. A human reviews and corrects. The data is ready when it has been used, tested, and refined -- not when a pipeline declares it clean.

The real investment is not bigger context windows but better indexing, richer metadata, and search that returns the right thing instead of everything.

## structured outputs as state

Store agent outputs as structured data. The invariant is the **shape**, not the substrate: append-only facts, explicit grain, versionable, queryable. Relational access is what makes that shape pay off -- queryable, debuggable, intuitive to data people, and LLMs are good at SQL.

Knowledge graphs are seductive but brittle. Updates are impossible without breaking existing edges. Granularity changes invalidate the schema. What looks like flexibility is actually fragility at scale.

**Substrate follows from consumers.** Ask what reads the artifact besides a query:

- **Nothing else reads it** -- a database is the store. `readwise-reader` mirrors a remote SaaS with FTS indexes and staged reconciliation: no local file could be authoritative, because the truth is on someone else's server.

  This case is rarer than it looks, and the cautionary tale is worth more than the rule. `agent-state` was cited here as the second example and did not survive its own test: watermarks duplicated `upstream_hashes.json` plus `changes.jsonl`, skill-version rows duplicated what git already stores, and the delegation table was one the same repo had already decided not to populate. What remained was run lineage with no producer. The package was retired on 2026-08-02. **Run the test on your own units before citing them as exemplars** -- a principle illustrated by something that fails it ships with a counterexample built in.
- **Something else reads it** -- files are the store, and relational is a *lens* over them. A prompt that must stay re-runnable, a response another agent opens deliberately with Read, a manifest that is the only local record of remote state: none of those survive being flattened into a row. Query them in place instead. DuckDB reads JSON and JSONL directly, in memory by default, so relational access costs no ingestion step and creates no second copy.

The second case is not a grudging exception to the first. It is the more common one, and this repo already lives by it. `postmortem-index` rebuilds its index from the directory every time it is asked and refuses to commit a listing, because "a listing that gets committed and trusted becomes a copy that drifts out of agreement with the directory." `gemini-bridge` writes run directories that are the handoff contract between models, plus an append-only `ledger.jsonl` queried in place.

The failure this rule prevents is a copy with no reader. A copy earns its place only if it has a consumer other than the check that confirms it is a copy -- the same test CLAUDE.md invariant 1b applies to versions and changelogs.

## verify by construction

A green result is evidence only if the thing it certifies could have gone
red. Measured twice in a sibling repo and confirmed here: *reading* an
artifact to review it yields approximately nothing, while *constructing*
the input that would refute it finds the real defects. Census, reading,
and reports are targeting; construction is the instrument.

The audit family (claim-audit, test-audit, control-audit, and the
adversarial-verify primitive they dispatch to) shares one structural
commitment: **audits are runs, not artifacts.** They re-derive everything
from current state on every run, persist nothing that can drift, never
rewrite what they audit, and end by stating their own scope -- lines read,
claims derived, mutations run over arms in frame -- because a green report
indistinguishable from a run that read nothing is the exact class they
exist to catch. Two corollaries with teeth: a test born green (a pin) gets
one mutation at birth to prove it can fail, and any pre-registered
decision rule that consumes a rate or count must state its exposure basis,
because an underpowered zero decides nothing.

## feedback loops compound

Each iteration of the compound system generates signal -- what gets created, what gets discarded, what succeeds, what fails. That signal feeds the next cycle. Coding agents are getting better because this loop exists.

In this repo: pipeline creates skill, agent uses skill, human reviews, pipeline refines skill. The maintenance system (`/maintain`, quality checks, upstream detection) implements this loop explicitly.

Build the feedback mechanism where users already spend their days. Adoption of new systems is hard. Signal that requires switching tools gets ignored.

## what this means for this repo

- **Agent topology**: orchestration uses tree decomposition, not linear handoff chains. Subagents get scoped context and return results to the orchestrator (trees, not workflows).
- **Model tiering**: well-specified, verifiable work delegates to lower-tier models in subagents; judgment-heavy work stays in the orchestrator. Opt-in per project via the model-routing plugin (route to the cheapest capable model).
- **Harness-native design**: all behavior is expressed as data inside the harness -- skills, rules, metadata, hooks. No external wrappers (the harness is the system).
- **State management**: agent outputs carry a relational *shape* -- append-only facts with explicit grain. The substrate follows from what else reads them: a database when nothing does (`readwise-reader`; the retired `agent-state` is the section's cautionary tale, not an example), files with query layered on when something does (`postmortem`, `gemini-bridge`) (structured outputs as state).
- **Verification**: greens must prove they can fail. Audits are runs, not artifacts -- re-derived per run, report-only, self-scoping; adversarial construction is the instrument and everything else is targeting (verify by construction).
- **Compound feedback**: each maintenance cycle generates signal that refines the data driving the next cycle. The loop compounds (feedback loops compound).
