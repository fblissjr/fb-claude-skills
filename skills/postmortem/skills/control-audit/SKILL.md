---
name: control-audit
argument-hint: "[scope: hooks, validators, reminders, or named controls]"
description: "Census and live-fire audit of a repo's controls: everything check-shaped that fires outside the test suite (git hooks, Claude Code hooks, CLI validators, ambient reminders). Per control, four slots are re-derived from current code — fires-via, guarded-by, retirement-condition, disclosed-uncontrolled-edges — with 'nothing' in a slot as a reportable finding; controls nothing watches get deliberately violated on a scratch branch to confirm they fire. Use when the user says 'audit the controls', 'control audit', 'do our hooks actually fire', 'census the hooks', 'is anything watching this check', 'would the gate actually catch it'. Do NOT use for auditing a test suite (use test-audit) or prose claims (use claim-audit)."
metadata:
  last_verified: "2026-08-04"
  review_interval_days: "365"
---

# Control audit

A control is anything check-shaped that fires outside the test suite: a git
hook, a Claude Code hook, a CLI validator, an ambient reminder. The failure
mode this audit exists for is a control trusted because it exists, not
because anything watches it — and the controls nothing watches are exactly
the ones most likely to be silently broken.

Siblings partition the territory: `claim-audit` audits prose, `test-audit`
audits tests, this audits controls. Tests are excluded here; when a control
is bracketed by test arms, *name* them in its guarded-by slot but do not
audit them — they belong to test-audit. Cross-reference, not double
coverage.

## A run, not an artifact

Standing artifacts drift; this audit persists nothing. Every run re-derives
the census from the code as it is now. Three refusals keep it that way:

- **Report-only.** The caller fixes; the audit never writes guard tests,
  never patches headers, never adds enforcement.
- **No standing meta-checks spawned.** A hook that fires when a new hook
  lands without its header would be a new control this audit then has to
  census. Do not create one.
- **Headers are re-derived, not trusted.** A control's four-section header
  (see a repo's control-authoring checklist, where one exists) is prose and
  can rot: a stated false-positive rate goes stale, a retirement trigger's
  condition quietly becomes true. Check the header's claims against
  reality — the claim-audit move applied to control headers.

## Tier 1 — census (every control, every run)

Enumerate from the sources the repo actually has:

- **Claude Code hooks**: settings files, plugin `hooks/` directories,
  per-plugin registrations — *including hooks disabled by env or config*. A
  control that had to be turned off is a census row, not an omission; its
  retirement-condition slot is the interesting one.
- **Git hooks**: `.git/hooks/` and `core.hooksPath`. These are per-clone
  and usually untracked, so this part of the census is machine-dependent —
  the report must say so rather than imply the fleet shares its result.
- **CLI validators**: the check registry inside whatever validation command
  the repo ships.
- **Reminders and ambient directives**: SessionStart blocks and their
  ground or trigger conditions.

Per control, fill four slots, each with a citation:

| Slot | Question |
|---|---|
| fires-via | what actually triggers it, shown from config or code |
| guarded-by | what watches it (test arms named, not audited) |
| retirement-condition | when it should be deleted rather than tuned |
| disclosed-uncontrolled-edges | what it admits it does not cover |

Mark each slot **derived** (command output or code path shown) or
**transcribed** (taken from the control's own prose). "Nothing" in any slot
is itself the finding. A slot that can only be transcribed is a tier-2
candidate by definition.

## Tier 2 — live-fire

Deliberately violate what the control guards and confirm it fires: a
commit-shaped path leak against a path hook, a key-shaped string against a
secrets gate, a banned command against a package-manager guard. This is a
dispatch to the `adversarial-verify` protocol (shipped in this plugin),
constructor and needle-verifier as separate judgments.

**Required** for every control whose guarded-by slot is empty. Sampled
beyond that as budget allows.

Safety protocol, non-negotiable:

- A separate scratch worktree (or throwaway clone) for anything that
  touches files or history. A scratch *branch* is not isolation: checking
  it out reuses the live working tree the owner is sitting in, and
  isolates only the commit graph.
- Synthetic violations are visibly fake (marker-prefixed key shapes, paths
  under a throwaway name) so a leaked artifact reads as a test, not a leak.
  When the control anchors on a pattern the marker would break, the needle
  rule wins at the matched token: use a pattern-true dummy (a provider's
  documented example credential, where one exists), move the visible
  fakery to everything around it — file content, path, commit message —
  and put the token itself first on the cleanup inventory.
- Never `--no-verify`; never disable one control to test another.
- **A green must prove the needle was threaded** — record the violation
  reaching the control's input, not just the control's verdict. A firing
  that cannot show its needle is vacuous, and goes back for
  reconstruction, not into the tally.
- Cleanup is verified against the run's own inventory, not `git status`
  alone: every artifact the run created — worktree, branch, stash, commit,
  file — is enumerated and confirmed gone. `git status` cannot see branch,
  commit, stash, or reflog residue, and reflog entries cannot be removed
  at all, which is half the reason violations must be visibly fake.

## Report

One row per control: name, tier, the four slots each marked derived or
transcribed, live-fire outcome where run. Suite-level findings go separately
— the empty-slot pattern across the census is usually worth more than any
single row.

On a first census in a repo with a dated control-authoring checklist,
bucket controls that predate the checklist as "predates checklist" rather
than raising each header gap as a fresh alarm; the backlog is expected.

The report ends with its own scope, claim-audit style: controls enumerated,
slots derived vs transcribed, controls live-fired, and the
machine-dependence disclosure for untracked git hooks. A green census that
cannot be told from a run that read nothing is the class this family exists
to catch.

Cadence: on-demand, plus a listed step in a repo's maintenance pass where
one exists. Nothing automatic.
