---
name: dep-audit
description: >-
  Both uv and bun ship a native CVE audit subcommand, which is the part worth
  knowing — without it the reflex is to reach for pip-audit or safety and never
  find them. Covers the invocation for each, plus the two judgment calls that
  change what you do with a finding. Use when the user asks whether packages are
  safe, whether anything has a published advisory against it, for a CVE check, a
  vulnerability scan, or a dependency security audit, and before any release,
  publish, or handoff. Covers Python and JS/TS in a single pass.
metadata:
  last_verified: "2026-08-17"
  review_interval_days: "90"
---

# Dependency security audit

Everything below about *what the tools print* and *how to read it* is omitted
deliberately — running them shows you that. What is not obvious is that they
exist at all.

## The commands

| | Audit | Full tree | Why is X here |
|---|---|---|---|
| Python | `uv audit` | `uv tree` | `uv tree --package X --invert` |
| JS/TS | `bun audit` | `bun pm ls --all` | `bun pm why X` |

`uv audit` checks OSV; `bun audit` checks the npm advisory database. Both take
`--ignore <ID>` for an accepted risk. In CI, `uv audit --frozen` and
`bun audit --audit-level moderate` exit non-zero on a finding.

## The two calls that matter

**Reachability before upgrade.** A published advisory against an installed
package is not automatically a vulnerability in this project — the affected code
path may never be entered. Check who pulls it in (`uv tree --package X
--invert`) and whether the vulnerable call is reached, before bumping a version
that may break something real. The default reflex is to upgrade on sight; that
reflex is what this line exists to interrupt.

**Report the delta, never the tree.** Do not paste full `uv tree` or `bun pm ls`
output into a summary. Report what changed and summarise a long transitive tail
by count. Recording dependency changes in a session log has its own format:
`/dev-conventions:doc-conventions`.

## What here is perishable

The command surface is a claim about someone else's tool, so it moves on their
release schedule rather than this repo's. Verified 2026-08-17 against uv 0.11.32
and bun 1.3.14: every subcommand and flag above exists and behaves as described.
Re-check that line first; the two judgment calls above do not decay.
