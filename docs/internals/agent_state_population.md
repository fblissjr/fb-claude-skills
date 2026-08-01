last updated: 2026-08-01

# Populating agent-state, or retiring it

Status: **designed, NOT started.** Nothing here is implemented. The decision this
document is meant to force is whether `tools/agent-state` gets producers or gets
deleted, because its current state — a well-formed schema that nothing writes to
— is the worst of the three options.

## Current state, measured

Against the live database on 2026-08-01:

```
fact_run             13     last write 2026-03-12
fact_watermark       19
fact_run_message      6
dim_run_source        2
dim_skill_version     0
fact_delegation       table does not exist
schema version        2     (README documents 3)
```

Five months since the last write. The one table this repo has actively discussed
using — `fact_delegation` — has never been created.

## Why it is not workable today

Three distinct problems, none of which is "the code is broken."

**1. The live database is a schema version behind, because nothing has opened
it.** `agent_state.sql` does contain `CREATE TABLE IF NOT EXISTS fact_delegation`
and inserts version 3, and `AgentStateDB.__init__` runs the whole schema file on
every connect. So the schema is self-healing: the first process to open the
database gets `fact_delegation` and `v_delegation_stats`. That it is still at v2
is not a migration bug — it is direct evidence that no process has opened the
database since v3 shipped.

**2. `SCHEMA_VERSION = 2` in `database.py` is dead and has drifted.** It is
defined once and read nowhere — `grep -rn SCHEMA_VERSION src tests` returns
exactly one line, its own definition. Meanwhile the SQL inserts 3 and the README
documents 3. Three sources of truth for one number, two values, and the one in
Python has no consumer. This is precisely the pattern CLAUDE.md invariant 1b
names: *a copy earns its place only if it has a consumer other than the check
that confirms it is a copy.* It should be deleted, not corrected.

**3. There are no producers.** This is the real problem, and the other two are
symptoms of it. Every table has a schema, an API, tests, and a CLI. None has
anything that calls it during normal work. `fact_delegation` in particular was
designed to be written by the `model-routing` feedback layer, which is opt-in,
requires this CLI on PATH, and asks the agent to self-report the outcome of its
own delegation — a signal shape that should not be built even if it were wired
up.

## What changed underneath it

Two things happened after agent-state was written that reshape what it is for.

**ccutils now exists and is observational.** It reconstructs Claude Code sessions
from the JSONL transcripts the harness already writes: 2,271 sessions, 947 agent
delegations, per-message model and token attribution. Anything that happens
*inside a Claude Code session* is better recovered there, because it requires no
cooperation from the thing being measured and backfills retroactively.

**That makes `fact_delegation` redundant before it ever ran.** Delegation
outcomes should come from `fact_agent_delegations` in ccutils, not from an agent
grading its own homework. See `internal/plans/2026-08-01_agent_delegation_capture_gap.md`
in the ccutils repo for what that requires.

What survives is the half ccutils structurally cannot see.

## The division of labor

The useful framing is not "which tool is better" but **observational versus
instrumented**.

| | ccutils | agent-state |
|---|---|---|
| Source | Transcripts already on disk | Explicit calls from your own code |
| Timing | Batch, on demand, retroactive | At run time, as it happens |
| Sees | What Claude Code did in a session | What your tooling did, anywhere |
| Backfillable | Yes | No — unrecorded runs are gone |

Three things live on the instrumented side and cannot move:

- **Watermarks.** Incremental-processing bookmarks for your own pipelines. No
  transcript contains them.
- **Runs of things that are not Claude Code sessions.** A cron job, a
  `skill-maintain` pass, an ETL invocation. Nothing writes a transcript for those.
- **Skill content versions.** What a skill's text *was* at a point in time,
  keyed by content hash. A transcript records that a skill was invoked, never
  what it said.

## The insight: each side holds half the flywheel join

`v_flywheel` is defined as producer run → skill version → consumer run. It has
zero rows, and the reason is that agent-state can only ever populate two of those
three.

- **Producer run and skill version**: agent-state's natural territory. A
  maintenance pass changes a skill; that pass is a run, and the resulting text is
  a version.
- **Consumer run** — a session that actually *loaded* that version — is a Claude
  Code session, which is ccutils territory. The transcript even carries an
  `invoked_skills` attachment type (see `context-cost.md`), so skill invocation is
  already recoverable there.

So the flywheel question freudagent poses — *did this version of this guidance
move outcomes?* — needs both halves, and the join key is the **skill content
hash**, which both sides can compute independently from the same file without
coordinating. That is a clean seam, and it is the strongest argument for keeping
agent-state rather than folding everything into ccutils.

## Population plan

The producers mostly already compute the data. They just do not record it.

**1. `dim_skill_version` from `skill-maintain`.** The quality and validate passes
already compute exactly these columns: content hash, token count, spec validity,
skill path. Writing a row per skill per pass is a few lines at the end of an
existing code path, and it is append-only keyed by hash, so unchanged skills
cost nothing. This is the highest-value producer, because without version history
nothing downstream can ask whether a change helped.

**2. `fact_run` + `fact_run_message` from `skill-maintain` and any repo CLI.**
The `RunContext` API exists for this. Every maintenance pass becomes one run with
a parent/child tree.

**3. `fact_watermark` from `.skill-maintainer/state/`.** This one is close to
free and mildly embarrassing: that directory already keeps per-repo upstream doc
hashes and a `changes.jsonl` audit log — a bespoke watermark table and run log in
a parallel format. `migration.py::migrate_from_jsonl` was written to import
exactly that file and has never been run. Either adopt the schema or delete the
importer; maintaining both formats is the actual cost.

**4. `fact_delegation`: do not populate.** Drop the table and
`v_delegation_stats`. Delegation outcomes come from ccutils, observed rather than
self-reported. Retiring it also removes the `model-routing` feedback layer's only
reason to exist.

**5. The cross-repo join, last.** Once 1 is real and ccutils resolves skill
invocations to content hashes, `v_flywheel` can be redefined across both stores.
Not before — a view that joins an empty dimension is what produced the current
situation.

## Freshness and the batch/real-time seam

agent-state is written synchronously by producers; ccutils is batch and
on-demand. Joining them means one side is always fresher than the other.

The content hash makes this safe. It is stable, computed from file bytes, and
does not depend on when either side ran. A session that loaded skill version
`abc123` can be joined to that version whenever ccutils gets around to ingesting
it, including months later. Nothing needs to be correlated by timestamp, which is
the failure mode this kind of join usually has.

The one ordering constraint: a version must be recorded *before or when* it is
used, not after. If `skill-maintain` writes `dim_skill_version` at the moment it
changes a skill, that holds by construction.

## The decision this forces

Three options, and the status quo is not one of them.

**Populate it** (the plan above). Cost: real work in `skill-maintain`, plus
keeping a second store alive. Benefit: version history and watermarks that
ccutils cannot provide, and a flywheel that can actually answer whether a
guidance change helped.

**Retire it.** Delete `tools/agent-state`, the `agent-state-mcp` plugin, and the
`model-routing` feedback layer, with a `renames` entry per the plugin-removal
rule. Cost: lose watermarking and version history, and the flywheel question
becomes unanswerable. Benefit: one less empty thing implying measurement that is
not happening.

**Keep it as-is.** An empty database, a README documenting a table that does not
exist, and an MCP server offering to query all of it. This is the option that
looks like instrumentation while measuring nothing, which is the exact failure
this repo's own `feedback_signal_honesty` principle exists to prevent.

Recommendation: populate `dim_skill_version` first, since it is nearly free, it
is the piece ccutils cannot replace, and it is the one that unblocks the flywheel.
If that has not happened within a reasonable window, retire the package rather
than leaving it — the empty-but-documented state is actively misleading.

## Cross-references

- `tools/agent-state/README.md` — schema detail, and the status note pointing here
- ccutils `internal/plans/2026-08-01_agent_delegation_capture_gap.md` — why
  `fact_delegation` is superseded, and what ccutils needs to fix first
- `skills/model-routing/skills/model-routing/references/feedback-addon.md` — the
  self-reported layer that would be retired
- `docs/internals/context-cost.md` — `invoked_skills` and the other transcript
  attachment types that make the consumer half of the join recoverable
- freudagent `docs/data-flywheel.md` — the design this is a component of;
  specifically that instructions are inert without a definition of what good means
