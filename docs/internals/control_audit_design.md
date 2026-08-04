last updated: 2026-08-04

# control-audit: design note (not started)

The census-and-fire instrument for controls: everything check-shaped that
fires outside the test suite — git hooks, Claude Code hooks, CLI validators,
reminders. Per control, four slots are re-derived from the current code:
**fires-via** (what actually triggers it), **guarded-by** (what watches it),
**retirement-condition** (when it should be deleted rather than tuned),
**disclosed-uncontrolled-edges** (what it admits it does not cover).
"Nothing" in any slot is itself the reportable finding. Decisions settled
with the owner 2026-08-04; build not started.

Sibling instruments, deliberate boundaries: `claim-audit` audits prose,
`postmortem:test-audit` audits tests, this audits controls. They partition;
none merges with another.

## A run, not an artifact — the regress refusal

The owner's design question: does auditing controls mean writing tests of
tests, with each layer drifting as the code moves? No, and the reason is
structural. Drift happens to *standing artifacts* — things that persist
between runs and encode the understanding of the day they were written.
This audit persists nothing. Every run re-derives the census from the code
as it is now, the way claim-audit re-derives every count. Three refusals
keep it that way:

- **Report-only.** The caller fixes; the audit never writes guard tests,
  never patches headers, never adds enforcement.
- **No standing meta-checks spawned.** The tempting v2 feature — a hook
  that fires when a new hook lands without its four-section header — is a
  new control that this audit would then have to census. Deferred until the
  audit itself has a track record (decision 4 below).
- **Headers are re-derived, not trusted.** The four-section header
  (`best_practices` "control authoring") is prose and can rot: a stated
  false-positive rate goes stale, a retirement trigger's condition quietly
  becomes true. Each run checks the header's claims against reality —
  the claim-audit move applied to control headers.

The pytest arms that bracket hooks sit on the boundary between this and
test-audit. Rule: when this audit examines a hook, it *names* the bracket
arms in the guarded-by slot but does not audit them — they are tests, and
test-audit owns them. Cross-reference, not double coverage.

## Census is targeting; live-fire is the instrument

The yield ordering measured twice in the sibling repo (recorded in
[claim_audit_design.md](claim_audit_design.md)): reading yields ~0;
constructing adversarial inputs found the only true code defects in both
samples. The owner's field experience agrees: the best tests are
adversarial. So the two tiers are not "cheap mode and thorough mode" — the
census is the map that tells the adversarial pass where to aim.

**Tier 1 — census (every control, every run).** Enumerate; fill the four
slots by reading, with a citation per slot; classify each slot as derived
(command output or code path shown) or transcribed (taken from the header's
own prose). A slot that can only be transcribed is a tier-2 candidate by
definition.

**Tier 2 — live-fire (always for unwatched controls; sampled otherwise).**
Deliberately violate what the control guards and confirm it fires:
commit-shaped path leak against the path-privacy hook, key-shaped string
against the secrets gate, a pip command against the package-manager guard.
Required for every control whose guarded-by slot is empty — the controls
nothing watches are exactly the ones most likely to be silently broken.
Sampled beyond that as budget allows.

Safety protocol, non-negotiable:

- Scratch branch or worktree; never the working tree the owner is using.
- Synthetic violations are visibly fake (marker-prefixed key shapes, paths
  under a throwaway name) so a leaked artifact reads as a test, not a leak.
- Never `--no-verify`, never disable a control to test another.
- **A green result must prove the needle was threaded.** The fence-mutation
  incident (2026-08-03 log): a mutation run passed because bash quoting
  turned the needle into a literal that matched nothing — the "mutation"
  was a no-op and the green was vacuous. Every live-fire records the
  violation reaching the control's input, not just the control's verdict.
- Cleanup verified by `git status` before the run reports.

## What the census must enumerate (and disclose)

Sources, in this repo's shapes but stated generally:

- Claude Code hooks: `.claude/settings.json`, plugin `hooks/` dirs, and
  per-plugin hook registrations — including hooks *disabled* by env or
  config. A control that had to be turned off (`ENABLE_SECURITY_REMINDER=0`,
  invariant 5) is a census row, not an omission; its retirement-condition
  slot is the interesting one.
- Git hooks: `.git/hooks/` and `core.hooksPath`. These are **per-clone and
  untracked** (this repo's pre-commit is exactly that), so the census is
  machine-dependent here and must say so in its scope statement rather than
  imply the fleet shares its result.
- CLI validators: the check registry inside `skill-maintain test` and any
  equivalent the target repo ships.
- Reminders and ambient directives: SessionStart blocks, with their ground
  or trigger conditions as the fires-via slot.

## Report

One row per control: name, tier, the four slots each marked derived or
transcribed, live-fire outcome where run. Suite-level findings separate
(the census's most valuable output is usually the empty-slot pattern, not
any single row). The report ends with its own scope, same discipline as
claim-audit: controls enumerated, slots derived vs transcribed, controls
live-fired, and the machine-dependence disclosure for untracked hooks. A
green census that cannot be told from a run that read nothing is the class
the family exists to catch.

## Decisions taken (owner, 2026-08-04)

1. **Scope**: controls = check-shaped things firing outside the test
   suite; tests excluded; bracket arms cross-referenced, not audited.
2. **Live-fire is in v1**, mandatory for empty guarded-by slots, sampled
   beyond. The owner's push: adversarial is the instrument, not the
   escalation.
3. **Packaging**: joins the `postmortem` plugin beside `test-audit`; the
   plugin description widens from "retrospectives" to the audit family.
4. **Cadence**: on-demand plus a listed step in
   `skill-maintainer:maintain`; nothing automatic in v1. The
   header-missing notice is deferred, and if it ever lands it is a new
   control this audit censuses like any other.

## Evidence base this repo already holds

- The fence-scanner mutation no-op (green mutation as red flag) — the
  founding specimen for "a green must prove the needle was threaded".
- The NUL-byte fence forgery — found by adversarial construction, not by
  reading, after 4,000 differential-fuzz bodies found nothing.
- The security-guidance hook disabled by env var — the "control that had
  to be turned off" census class.
- The `best_practices` control-authoring checklist — the measuring stick
  for headers; shipped 2026-08-03, so every control older than that is
  expected to fail the header check on first census. First-run output will
  be dominated by that backlog; the report should bucket it as "predates
  checklist" rather than raising each as a fresh alarm.

## What would revise this note

- Live-fire proves unsafe or too messy in practice — it demotes to an
  escalation and the census carries a "transcribed-only" warning instead.
- The first census finds the four-slot model wrong-grained (controls that
  are pipelines, slots that only make sense per-stage) — regrain before
  building more.
- test-audit and this converge on shared machinery worth extracting — fold
  them into one audit skill with two subjects rather than maintaining
  parallel procedures.
