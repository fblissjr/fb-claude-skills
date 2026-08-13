# design principles

Skills are retrieval. This document holds the principles that govern what gets
loaded, when, and at what cost. It is deliberately short and deliberately
stable.

What it is not: the practice. Field rules, harness constraints, thresholds, and
the frontmatter reference live in `skill-maintainer`'s `best_practices.md`,
which moves on a faster clock and is rechecked against sources. When the two
disagree, the sourced document wins and this one gets corrected.

The architecture worldview this retrieval model serves, agent topology, model
tiering, harness coupling, state substrate, moved to
[docs/internals/architecture.md](docs/internals/architecture.md).

## context and friction

Every instruction spends from two budgets, and the second is the one people
forget.

**Context** is attention. An LLM's window is not memory; everything in it
competes. Irrelevant context does not merely waste tokens, it degrades accuracy
and dilutes the signal. This is precision and recall applied to context:

- **Precision**: what fraction of the window is relevant to the task at hand?
  Low precision means skill overtriggering, bloated bodies, ambient hooks
  injecting noise. The consequence is behavioral, the model acts on information
  it should not have.
- **Recall**: does the model have what it needs? Low recall means falling back
  to training data, which is stale, unversioned, and unauditable.

High precision is the constraint. High recall is the goal. The failure modes are
asymmetric: low precision causes active harm, low recall causes passive
degradation. Low precision is worse, because a polluted window cannot be
un-polluted mid-session.

**Friction** is what an instruction costs beyond its tokens. An instruction that
restates what the model already does well does not sit there inertly, it
competes with a better plan the model already had. Overriding competence is the
real price, and it is charged on every activation.

Friction also lands on the human. A skill nobody can remember exists is not free
just because it loads nothing: someone has to be the index. That cost is worth
paying where human judgement belongs in the loop, and worth removing where it
does not, but it is never zero and it is not interchangeable with the context
budget. Moving material out of context often just moves the cost onto a person.

Neither budget is minimised on its own; they are traded. Spending context to
remove friction is often right, and so is the reverse. Which way a given
instruction goes is a rule rather than a principle, and the rule lives in
`best_practices.md`, which carries the per-instruction test and the boundary it
draws around retrieval.

## progressive disclosure

The mechanism that keeps precision high without sacrificing recall: stage the
loading, and gate each stage on increasing specificity. Index, then snippet,
then full page.

| Level | What | When | Control |
|-------|------|------|---------|
| **L1** | CLAUDE.md (global + project), `MEMORY.md`, unconditional `.claude/rules/`, all installed skill descriptions, `settings.json` | Always | Edit, uninstall, or scope it |
| **L1**\* | Path-scoped `.claude/rules/` | When matching files are in context | `paths` frontmatter |
| **L2** | SKILL.md body | Intent matches the description | Description quality |
| **L3** | `references/*`, `scripts/*` | The active skill links to them | Explicit link in SKILL.md |

*\* Conditional rules use the same static-load mechanism, gated by path globs.*

The asymmetry between the levels is the whole point. **L1 is unconditional cost,
paid every session whether or not it is used.** L2 and L3 are earned: a large
reference file that loads only when its skill is active is cheap, while one
extra always-loaded line is expensive forever. Optimize for relevant context at
the right time, not for minimal context and not for maximal context.

This is also why sharding an always-loaded file for tidiness accomplishes
nothing. An import still loads in full. Moving text is not moving cost; gating
it is.

## descriptions are reverse queries

A skill description is not documentation. It describes the set of user intents
that should match, so the techniques that make a search query effective are the
ones that make a description effective: specific terms, explicit scope, negative
conditions.

A vague description is a broad query and matches too much. This is the highest-
leverage text in a skill, because it is the only part that is always loaded and
the only part that decides whether the rest is ever seen.

## practices evolve; sources decide

The principles above are stable. Almost nothing downstream of them is, and a
practice document that does not say what would change its mind is an opinion
with formatting.

**The model is a variable.** Capability absorbs content: knowledge a newer model
carries makes the skill that supplied it redundant, and worse than redundant.
Operating mode changes shape: a generation working from constraints and an
explicit definition of good does not need the step decomposition an earlier one
required. Constraints and gates travel across generations. Scaffolding does not.

**The harness is a variable too**, and a faster-moving one. Field rules about
hooks, frontmatter, tool filters, and budgets are claims about a system someone
else ships and changes without asking.

So a practice carries the event that reopens it rather than a calendar, and it
carries what would settle it. `best_practices.md` is where that is implemented:
each section declares the evidence class naming its reopening event, states what
enforces it, and cites the source it was last checked against. Those are the
rules. This is why they exist.

Retrieval quality cannot be fully automated. Whether a skill fired at the right
moment, whether the loaded context helped, whether the answer was right: these
need a human, and the maintenance loop exists to keep one in place.

## what this means here

- **Skill authoring**: descriptions are reverse queries; bodies stage their
  material; every always-loaded line justifies itself.
- **Instruction pruning**: on a model family release, take the always-loaded
  rules and ask what the model still needs told. Delete or demote the rest.
- **Rules and hooks**: unconditional is always-on cost. Path-scoped rules and
  matcher-gated hooks are precision-gated retrieval. Ambient injection needs a
  documented reason.
- **Distribution**: the marketplace listing is the catalog, and install or
  uninstall is the user controlling their own always-loaded index.
- **Maintenance**: practices are rechecked on their triggering event, and the
  recheck reads the source rather than trusting the summary.
