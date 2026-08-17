---
mode: session
scope: external-skills-adaptation
date: 2026-08-13
summary: A review of two external skill repos found more wrong in this repo's own doctrine than in theirs — four controls were measuring something other than what they claimed, and the session's two worst errors were both reference sweeps run after a delete instead of before.
artifacts:
  - VISION.md
  - CLAUDE.md
  - docs/internals/architecture.md
  - docs/internals/context-cost.md
  - docs/internals/gotchas.md
  - docs/internals/plugin-versioning.md
  - docs/internals/control_audit_design.md
  - skills/skill-maintainer/references/best_practices.md
  - skills/skill-maintainer/skills/finish-session/references/workflow.md
  - skills/skill-maintainer/skills/sync-versions/SKILL.md
  - skills/skill-maintainer/skills/init-maintenance/SKILL.md
  - skills/skill-maintainer/hooks/skill-maintainer-sync-bundled-ref.sh
  - skills/writing/skills/show-me/SKILL.md
  - skills/grilling/skills/grilling/SKILL.md
  - tools/skill-maintainer/src/skill_maintainer/config.py
  - tools/skill-maintainer/src/skill_maintainer/shared.py
  - tools/skill-maintainer/src/skill_maintainer/tests.py
  - tools/skill-maintainer/tests/test_token_budget_gate.py
  - 3fde1ce
  - beb35df
---

<!--
skills/skill-maintainer/hooks/skill-maintainer-sync-bundled-ref.sh does not
resolve against the current tree: it was deleted in 3fde1ce, which is the commit
where it remains examinable. Kept in the list deliberately, because a
by-artifact view should show that something was written about it.
-->


# Postmortem: external skills adaptation

## 1. What went well

**Reading the artifacts rather than the skill description reversed a verdict.**
An external skill was initially rated "adopt, de-duplicated" on the strength of
its `SKILL.md`. Reading the files it actually installs found injection and
forgery defects in the shipped templates, none of them visible from the
description. The verdict became "take the framing, write our own workflow."
Structural version: for a skill whose deliverable is a file it installs
elsewhere, the description is not the artifact under review.

*Redacted 2026-08-17, on publication: the upstream project and the specific
defects are deliberately unnamed here. They were still live when this was
checked, and a repo that credits that project elsewhere should not publish an
uncoordinated disclosure about it. The structural lesson is what transfers, and
it survives the cut intact.*

**Sweeping for inbound references before a delete caught two live citations.**
Removing CLAUDE.md invariants 4, 5 and 6 would have stranded
`docs/internals/plugin-versioning.md` (which cited "repo invariant 6") and
`docs/internals/control_audit_design.md` (which cited "invariant 5"). Both were
repointed at `docs/internals/gotchas.md` by section name in the same change.
This is the same class as the failure in section 2, done the right way round
once the lesson had been paid for.

**The gate change was verified with a control that can go red.**
`tools/skill-maintainer/tests/test_token_budget_gate.py` pins three sides of the
new boundary rather than asserting the new behaviour once. The `/code-review`
pass noted that the red arm's magnitude (5,500 tokens) would also have failed
the old 4,000 gate, so magnitude alone proves nothing — what discriminates is
its assertion on `"re-attach" in result.detail`, a string only the new code
emits. That is a real weakness found in my own test by a second reader.

**Following a skill exposed a bug in that skill.**
`skills/skill-maintainer/skills/sync-versions/SKILL.md` step 3d directed
`tools/<plugin>/pyproject.toml` to the plugin's new version unconditionally.
Applied to this release it would have moved the CLI from 0.32.0 to 0.24.0,
because the plugin and its CLI are on independent version lines. Caught by
noticing the number went backwards, not by any check. Structural version: a
procedure that hardcodes a relationship between two versions breaks silently
wherever that relationship does not hold, and the only detector is a human
reading the number.

**A blocked commit failed closed and cost only a delay.** A pre-commit guard
refused a commit whose file list crossed a boundary that was itself in flux at
that moment. The block named every path and the reason. Structural version: a
guard that fails closed converts a race into a delay; one that fails open
converts the same race into a silent publish.

## 2. What did not go well

**The reference sweep ran after the delete, twice.** Removing
`.skill-maintainer/best_practices.md` and its mirror hook
(`skills/skill-maintainer/hooks/skill-maintainer-sync-bundled-ref.sh`, 85 lines,
deleted in `3fde1ce`) left four places describing the arrangement as current.
The worst was `skills/skill-maintainer/skills/finish-session/references/workflow.md`,
whose step 3 instructed an agent to `cmp` two files, one of which no longer
existed — a runnable instruction, not prose. `dangling-refs:retire` exists in
this repo for exactly this and was not used. Structural version: deletion-induced
breakage is non-local, so the sweep belongs before the delete, not after the
first thing breaks.

**A number I derived by the wrong method reached shipped content.** A hand-rolled
count reported the skill listing at 4,391 tokens across 36 skills and was written
into `skills/skill-maintainer/references/best_practices.md`, which ships to other
repos. `/doctor` measures the listing at ~2,300 tokens across 26 entries; the
count had measured every description *authored* in the repo, including plugins
that are not enabled. Corrected in the same working tree before commit, but it
did exist. The aggravating detail is that `docs/internals/context-cost.md`
already carried a "do not rebuild these" list naming `/doctor` for this exact
measurement. Structural version: authored is not installed, and a hand-rolled
substitute for a built-in lost to it on its first attempt, in the direction that
would have justified unnecessary work.

**A rewrite of `VISION.md` created the duplication it was meant to remove.** The
first pass pulled five rules up out of `best_practices.md` into `VISION.md` — the
retrieval boundary, the with-and-without falsifier, the evidence-class table,
"elapsed time is not evidence", "freshness does not catch wrongness" — then had
to remove them again under the one-claim-one-home rule stated in the same file.
Five of the nine duplications found in the consolidation pass were introduced
during it.

**`/code-review` was run against the wrong repository, after I had documented
that trap.** The session is rooted in a sibling checkout; `/doctor`, `/init`,
`/context` and `/code-review` all resolve against the session's directory rather
than whatever path is being edited. That constraint was written into the plan's
Step 0 for `/doctor` earlier in the same session, then not applied to
`/code-review`. Recovered by resuming the agent with an explicit repo path.

## 3. Deviations from the plan

| Planned | Shipped | Verdict |
|---|---|---|
| Assess `humanlayer/skills` for adaptable skills | Assessed, and the review turned inward: nine duplications and four mis-measuring controls in this repo. Two commits, 48 files, of which most are our own doctrine | Better than planned — the external review was the instrument, not the deliverable |
| "Completely rewrite CLAUDE.md. Start over." | Dense paragraphs reformatted, three conditional invariants relocated, the 20-row pointer table left intact. 11,247 → 9,864 chars | Scoped down honestly — `/doctor` rated the file lean with nothing derivable to cut, refuting the plank of the plan that cited its own criterion |
| Run `/doctor` and `/init` as inputs | `/doctor` only | Scoped down honestly — `/init` generates discoverable content, the class `/doctor` had just removed 54 lines of |
| Adopt the second external skill | Framing and three references adopted; the workflow and iteration script rejected | Changed on evidence, see section 1 and its redaction note |
| Adopt the staging bucket and router on listing-cost grounds | Neither built; both lost their cost case | Refuted — the corrected listing figure plus the finding that `disable-model-invocation` does not remove a listing entry left only an ergonomics argument |
| One commit | Two, after another session bundled the first changeset under its own message and split it back out on request | As designed after correction |

## 4. Escapes (tests)

**The two-copy defect: green-but-blind, and the check caused the problem it
hid.** `skills/skill-maintainer/skills/init-maintenance/SKILL.md` had always
documented that `init` writes no local `best_practices.md` and the bundled copy
is what `/maintain` reads, while `tools/skill-maintainer/src/skill_maintainer/config.py`
returned only the per-repo path with no fallback. The test arm that existed
asserted the two copies were byte-identical — it tested equality, which is
satisfiable by mirroring, which is why the mirror hook had to exist. That arm
lived in `tools/skill-maintainer/src/skill_maintainer/tests.py` and was removed
with the copy it compared. No arm ever asserted the documented resolution order.
Both consumers guard with `.exists()`, so a repo without a local copy printed
"Provenance join skipped" and the join silently never ran.

**Semantic dangles are not covered by any check.** `skill-maintain lint` verifies
that a markdown link's target file exists. Nothing verifies that a citation
naming a *section* still resolves, which is what broke in section 2 — the files
existed, the named sections did not.

**Tests added:** `tools/skill-maintainer/tests/test_token_budget_gate.py`, three
arms, pinning the boundary introduced as `TOKEN_BUDGET_REATTACH` in
`tools/skill-maintainer/src/skill_maintainer/shared.py`. Recorded claim: if
deleted, a threshold edit could silently stop gating anything, and the red arm
is the one that proves the gate is not decoration. Verified red-then-green by
construction rather than assertion.

## 5. Forward items

1. **Wire a check for semantic dangles, or record that we accept them.** A
   citation of the form "`FILE.md` \"section name\"" where that heading no longer
   exists in that file. Checkable: add the arm and it either finds the class or
   returns zero on a tree we know had two instances today. If zero, the check is
   wrong, not the tree.
2. **Confirm the two skills that were red under the old gate stay green and
   report the soft threshold.** `gemini-multimodal` (4,033) and `path-privacy`
   (4,091) should now pass with "over house soft 4,000, not gated" in the detail.
   Refuted if either fails, or if the detail string is absent — that would mean
   the observation was lost rather than demoted.
3. **Decide whether `beb35df` ships.** It is the only unpushed commit; the three
   before it reached `origin/main` during the session. Done when pushed or
   deliberately held with the reason recorded.
4. **Re-run `/code-review high` from a session rooted in this repo.** The pass
   that ran was low effort with prose skimmed, so the doctrine changes in
   `VISION.md`, `best_practices.md` and `docs/internals/architecture.md` have not
   been read for internal contradiction. Wrong-premise if a high pass returns
   nothing on those files, which would mean low effort was sufficient.
5. **Check whether the new descriptions overtrigger.**
   `skills/writing/skills/show-me/SKILL.md` and
   `skills/grilling/skills/grilling/SKILL.md` add ~423 tokens of listing on a set
   already marginally over its allocation, and both carry heavy negative scope to
   avoid colliding with `dataviz`, `artifact-diagramming` and code review.
   Checkable against invocation counts: if either fires on requests outside its
   stated scope, the negative scope is not doing its job and the entry is not
   earning its length.
