---
mode: session
scope: agent-state-retirement
date: 2026-08-02
range: 73a29d3..16fd166
summary: Twice in one session an artifact was shipped without being tested against its own premise — a VISION principle whose exemplar failed it, and a sweep skill whose sweep could not see what the skill exists to find. Review caught the second in under four minutes; nothing caught the first.
artifacts:
  - VISION.md
  - CHANGELOG.md
  - docs/internals/agent_state_population.md
  - docs/internals/foreign_capability_bridge.md
  - docs/internals/gemini_bridge_design.md
  - .claude/rules/skills.md
  - apps/gemini-bridge/src/gemini_bridge/cli.py
  - tools/skill-maintainer/src/skill_maintainer/tests.py
  - tools/skill-maintainer/queries/upstream_churn.sql
  - skills/dangling-refs/skills/retire/SKILL.md
  - 1875e6c
  - a146fcc
  - 3f09163
  - 5cb86a9
  - c712c4a
  - addb5f7
  - 58cf04e
  - 54ada95
  - 23e911b
  - d353935
  - 16fd166
  - 5beaf3a
  - docs/internals/gotchas.md
---

# Session postmortem: the agent-state retirement

Started as "what is the flywheel behind the gemini-bridge recipes." Ended having
retired a package, shipped a plugin, amended VISION.md three times and frozen a
design doc. 16 commits, 12:42 to 15:44.

## 1. What went well

**Stopping before executing a decision the repo had already analyzed.** I
recommended retiring only the MCP and keeping the schema; that was agreed. Then
`docs/internals/agent_state_population.md:176-195` turned out to name exactly
that option as the worst of three — "looks like instrumentation while measuring
nothing." Surfacing it instead of proceeding changed the outcome to a full
retirement (`54ada95`). *Structural: when a document already analyzed the
decision you are about to make, read it before executing, not while cleaning up.*

**The `internal/` check's predicate.** `check_internal_citations`
(`tools/skill-maintainer/src/skill_maintainer/tests.py`) fires on "resolves to an
existing **file**", not "mentions `internal/`". Verified against every current
use before shipping: naming conventions pass, directories pass, Go project-layout
references in the MCP analysis pass. Zero false positives on first run, and it
caught both real violations. *Structural: an existence-predicate has almost no
false positives; the absence-predicate that looks like its twin has almost
nothing else.*

**Measuring a proposed check before building it.** Before writing the whole-tree
reference checker, I tested its catch rate against the five real stale references
from `d353935`: one of five was mechanically detectable. Shipped the procedure
(`skills/dangling-refs/skills/retire/SKILL.md`, `16fd166`) and left the linter
unbuilt. *Structural: measure a proposed check against real historical instances
before writing it, not after.*

> **Annotation, 2026-08-02 (post code-review).** This finding stands as written
> but was over-credited. The measurement was of the **rule**, not the
> **artifact** — and the artifact shipped broken. `git ls-files` is
> cwd-scoped, so the sweep at the heart of the skill searched only the current
> directory. Run from inside the unit being deleted, which is the most natural
> place to run it, sweeping for `gemini-bridge` returned 12 files — every one
> inside `apps/gemini-bridge/` and therefore about to be deleted anyway — while
> missing all 14 external references. Fixed in `5beaf3a`. *Revised structural
> form: measuring a premise is not testing an implementation, and the two feel
> identical from the author's chair.*

**The enforcement layer caught its own author.** Writing the `CHANGELOG.md` entry
*about* replacing tilde-path examples, I wrote a literal tilde path into it. The
`path-privacy` PreToolUse hook blocked the edit before it landed. Direct evidence
that the mechanical gate catches what judgment misses, including the judgment of
the person writing the fix.

## 2. What did not go well

**Two version cascades spent on a package deleted 15 minutes later.** `c712c4a`
(14:54) bumped `agent-state-mcp` to 0.2.3; `addb5f7` (14:57) bumped it to 0.2.4
to fix angle brackets in a skill description; `54ada95` (15:12) deleted the
package. Its populate-or-retire status was already flagged as an open question
earlier in the same session. *Structural: fix defects in a unit only after its
fate is decided — an undecided unit's defects may not need fixing at all.*

**A contract shipped and corrected 49 minutes later.** `a146fcc` (14:02)
published `docs/internals/foreign_capability_bridge.md` defining its category as
"any consultation that Claude cannot perform." `3f09163` (14:51) widened it,
because a second opinion is work Claude *can* do. The correction came from a
design conversation, not from review — nothing would have caught it.
*Structural: a contract written from one instance encodes that instance's
accidents. The second use case is the test, and it is cheaper to seek one before
publishing than to amend after.*

**VISION.md amended three times on one principle.** `1875e6c` (12:42) added
"substrate follows from consumers," citing `agent-state` as an exemplar.
`58cf04e` (15:02) narrowed it after finding the watermark table duplicates
`upstream_hashes.json` plus `changes.jsonl`. `54ada95` (15:12) removed the
example when the package was retired. The exemplar was never run against the
principle before being cited. *Structural — now written into VISION.md itself:
run the test on your own units before citing them as exemplars.*

**Five stale references shipped, found by manual sweep after the fact.**
`54ada95` broke references in `path-privacy`, `skill-maintainer` and
`model-routing`; `d353935` fixed them. A markdown-link check passed cleanly the
whole time, because four of the five were prose naming a concept rather than
links pointing at a path. *Structural: "no broken links" is strictly weaker than
"nothing names a thing that no longer exists."*

> **Appended 2026-08-02 (post code-review): the same failure recurred, in the
> artifact built to prevent it.** `dangling-refs` 0.1.0 shipped at 15:44 with a
> sweep that could not see outside the current directory — a skill whose entire
> thesis is *"deletion-induced breakage is non-local, so no edit-time tool catches
> it"*, shipped with a command that could not catch it either. Four further
> defects in the same four snippets: `xargs` whitespace-splitting silenced by a
> blanket `2>/dev/null`, GNU `xargs` blocking on stdin when nothing matched
> (passing on macOS, hanging on Linux), the unit name interpolated as a regex,
> and a hand-listed extension glob missing 21 tracked files. The README install
> block also omitted both `dangling-refs` and `gemini-bridge`, which is the
> skill's own "indexes must change" bucket, missed on the commit that introduced
> the skill. All fixed in `5beaf3a`; the durable authoring lesson is now in
> `docs/internals/gotchas.md`. *Structural: an artifact that embodies a lesson is
> not thereby exempt from it, and is the most likely place to violate it, because
> the author's attention is on the lesson rather than the artifact.*

**Two subagent reports landed in context in full.** Roughly 1,500 and 1,200
words; I used about a third of the first and nearly all of the second. Both were
dispatched *after* I had written the return-a-path-not-a-payload discipline into
`docs/internals/foreign_capability_bridge.md` as invariant 1. Related: my first
claim about the waste ("a third of each") was wrong in the honest direction and
had to be corrected — the real hit rate was 1 of 2.

## 3. Deviations from the plan

No plan doc existed. The Planned column is the task as stated at the start:
*"What's the process/flywheel behind the gemini bridge recipes?"*

| Planned | Shipped | Verdict |
|---|---|---|
| Answer a design question about recipe promotion | Answered, plus a `general` recipe, two ledger fields, a prune design | **Better than planned** — the question surfaced that no ad-hoc path existed at all (`apps/gemini-bridge/src/gemini_bridge/cli.py` required `-r`) |
| — | `agent-state` and `agent-state-mcp` retired; repo to 1.0.0 | **Unplanned, justified** — grew out of a survey I requested; each candidate population was disproved on evidence |
| — | `dangling-refs` plugin shipped (`16fd166`) | **Unplanned, earned** — written from a failure in the same session that produced it |
| — | `VISION.md` principle amended, then corrected twice | **Necessary but self-inflicted** — see section 2 |
| Survey the query-over-files pattern across the repo | Delivered: 1 inversion, 2 conversions, 7 correctly-a-database | **As planned** — the small honest total is why it was trustworthy |
| Build a whole-tree reference checker | Deliberately not built | **Scoped down honestly** — 1-of-5 measured catch rate |
| Fix the `content-triage` staleness | Deferred to a readwise-reader design session | **Scoped down honestly** — the drift is real and paired with a code fix |

## 4. Escapes (tests)

**Angle brackets in a skill description — green-but-blind at the gate that
mattered.** `.claude/rules/skills.md` records that `skill-creator`'s validator
rejects angle brackets in frontmatter outright while `skill-maintain validate`
only warns. The defect surfaced only because a pre-commit hook printed the
warning during an unrelated commit. Fixed at `addb5f7`, then made moot by
deletion 15 minutes later. The check that should have caught it exists and is
non-blocking by design; nothing changed about that this session.

**Five stale references — no test existed, and still none does.**
`check_path_privacy` passed, link checking passed. `check_internal_citations`
(`23e911b`) does not cover it either: none of the five were `internal/` citations.
Honest status — uncovered, deliberately, with the procedure as the mitigation.

**The `interaction_id` gap — not a test escape.** No test could have caught it; it
was a design gap surfaced by asking how run directories get cleaned up. Now
covered by two tests at `5cb86a9`, each carrying its claim in the docstring —
`test_ledger_records_a_null_id_when_nothing_was_stored` states what breaks if
deleted.

Tests went 198 → 206 across the session (8 added), all in `gemini-bridge`. No
repeated green-but-blind pattern, so no `test-audit` trigger.

## 5. Forward items

1. **Next removal anywhere: invoke `dangling-refs:retire` and record whether the
   four-bucket sort changed the answer versus ad-hoc judgment.** If it produces no
   difference across two consecutive removals, the skill is decorative — cut it.

   > **Annotation, 2026-08-02.** Partly answered early and in the worst way: the
   > skill's commands were exercised against a real unit within the hour and the
   > sweep was wrong. That says nothing yet about whether the four-bucket *sort*
   > earns its place — the judgment half is still untested. The item stands.
   > A new precondition: re-verify the commands from inside a unit, not from the
   > repo root, before trusting a sweep result.
2. **Over the next three broad subagent delegations, return path-plus-summary.**
   Record whether the summary alone sufficed. Sufficient in ≥2 of 3 → write the
   one-line memory; otherwise drop the discipline and stop proposing it.
3. **At 20 ad-hoc `general`-recipe calls, run the promotion pass.** If no prompt
   shape recurred by then, the ladder's first rung ("asked twice in this project")
   is set wrong and needs a higher threshold.
4. **Re-run `tools/skill-maintainer/queries/upstream_churn.sql` at the next
   maintenance pass.** If `docs/en/skills` has moved outside an 8–15 day interval,
   the 30-day tier conclusion needs revisiting.
5. **Keep the whole-tree reference checker unbuilt until a single removal produces
   ≥3 references a path-resolution check would have caught.** Below that threshold
   the procedure is sufficient and the check is unearned.
6. **`docs/internals/gemini_bridge_design.md` is frozen — verify it stays frozen.**
   If any future commit edits its body rather than annotating it, the freeze
   failed and the doc should be split instead.

### Routing

- **Memory:** nothing new. The substrate lesson landed in `VISION.md`, which is a
  better home than memory for a principle this repo enforces.
- **Check/hook:** forward item 5 is the only candidate, and it is deliberately
  gated rather than proposed.
- **Backlog:** items 3 and 4 are already recorded in
  `internal/context_architecture_backlog.md`; 1, 2, 5 and 6 are new here.
