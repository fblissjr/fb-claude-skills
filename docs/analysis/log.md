last updated: 2026-05-04

# analysis log

Append-only narrative log of ingests, updates, and audits across `docs/analysis/`. Complements `.skill-maintainer/state/changes.jsonl` (operational, machine-readable) by capturing the *why* behind significant updates and the human decisions made when reviewing upstream deltas.

## Conventions

Each entry is an `H2` header with a date prefix and a verb classifier:

```
## [YYYY-MM-DD] ingest | <new report or page>
## [YYYY-MM-DD] update | <existing report> — <reason>
## [YYYY-MM-DD] audit  | <scope> — <finding>
```

Verbs:

- **ingest** — first-time addition of a new report, captured doc, or analysis page
- **update** — substantive edit to an existing report (driven by upstream change, internal correction, or new understanding)
- **audit** — a review pass that produced findings (linting, cross-reference check, manual sweep)

Body text: 1–4 sentences explaining what changed and why. Reference upstream commits, PRs, or `changes.jsonl` lines when relevant. Don't restate the diff — the git log has it.

## Entries
