---
name: doc-conventions
description: >-
  House documentation conventions that are not derivable from the repo: last-updated
  dates, where unshared notes and session logs live, how dependency changes get
  recorded, and the rule against decorative counts in prose. Use when creating or
  updating documentation, READMEs, design docs, or session logs. Invoke with
  /dev-conventions:doc-conventions. Triggers on "write docs", "update README",
  "document this", "add a design doc", "session log", "numbers in prose".
metadata:
  last_verified: "2026-08-17"
  review_interval_days: "365"
---

# Documentation conventions

Only what a repo cannot tell you by being read. Lowercase filenames, subfolders
by topic, and "explain the why, not just the what" are omitted deliberately —
they are already the default behaviour, and restating them costs context to
change nothing.

## Dates

A last-updated date at the top of every document you create or modify, as
`last updated: YYYY-MM-DD`. Dated records that carry their date in the filename
or in their own content are exempt — changelogs, session logs, postmortems.

## Numbers in prose

Before writing a number into prose, substitute a different plausible value. **If
the reader's next action is unchanged, the number is decorative — delete it.**
"Sixteen constraints are enforced by nothing" and "seventeen constraints are
enforced by nothing" prompt the same next step, so the count is liability
carrying no information.

A number that survives is one of two things:

- **Normative** — a limit you are setting ("keep the body under 500 lines").
  Cannot drift, because the world moves toward it rather than away.
- **Descriptive** — then it needs an observation point (a date, a commit, an
  attribution, past tense), and it belongs only in a dated record.

Binding is not a lesser fix for a decorative number. It makes the claim
permanently true and permanently useless, and still charges every reader a
reconciliation against what they can see. Delete first; bind only what passed
the test. To audit prose already written rather than prose being written:
`/claim-audit:claim-audit`.

## Where unshared writing goes

`./internal/` for documentation not meant to be shared — design notes, debugging
logs, scratch work — gitignored. Session logs at `./internal/log/log_YYYY-MM-DD.md`.

This is the owner's layout, not a universal one. A repo that already has
somewhere for unshared notes keeps its own arrangement; adopt this only where
there is none.

## Dependency changes

When a session adds, removes, or bumps package versions, record it in the
session log. That is the only place dependency changes are written outside the
source-of-truth files.

```markdown
## Dependency changes

| Action | Package | Old | New | Type |
|--------|---------|-----|-----|------|
| added | httpx | -- | 0.27.2 | direct |
| bumped | orjson | 3.10.0 | 3.10.5 | direct |
| removed | requests | 2.31.0 | -- | direct |
```

Read the changes off `git diff` against the manifest and lock files. What not to
do, because each is a plausible default worth overriding:

- Do **not** create a `deps.md`, `dependencies.json`, or any separate manifest.
  The source of truth is always `pyproject.toml` / `package.json` and the lock
  files.
- Do **not** dump full `uv tree` or `bun pm ls` output — report only what
  changed. Summarise a long transitive tail by count rather than listing it.
