---
name: doc-conventions
description: >-
  House documentation conventions that are not derivable from the repo: last-updated
  dates, where unshared notes and session logs live, how dependency changes get
  recorded, and the rule against decorative counts in prose. Use when creating or
  updating documentation, READMEs, design docs, or session logs. Invoke with
  /dev-conventions:doc-conventions. Triggers on "write docs", "update README",
  "document this", "add a design doc", "session log", "numbers in prose".
---

# Documentation conventions

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

A number that survives is one of three kinds, and each has a home the machine
can re-derive. A copy in prose is a cache with no invalidation, so prose names
what was compared, which way it came out, and where the value lives:

- **Derivable now** (a file size, a row count, the current default): give the
  command or the constant's path, never the value.
- **Measured once** (a speedup, a wall time): point at the dated record that
  carries the conditions (hardware, commit, inputs, cache state). A results
  file, a changelog entry, a session log or a postmortem is that home; prose
  is not.
- **Normative** (a limit you are setting, an exit code): allowed, cited by the
  one constant that holds it, with a word for whether it was measured,
  inherited or reasoned. It cannot drift, because the world moves toward it.

Identifiers (a version, a date, a resolution, an index) are names, not
measurements. Pointers must resolve, in whatever form the project checks
(`path::symbol`, `path:line`, a relative link): a pointer to nothing is worse
than a number.

An existing number with no findable origin gets no invented pointer. Delete it
if the reader's next action does not depend on it; otherwise mark it
unsupported in place, with the date, so it reads as withdrawn rather than never
checked. Re-measuring to refresh it is not the fix.

Binding is not a lesser fix for a decorative number. It makes the claim
permanently true and permanently useless, and still charges every reader a
reconciliation against what they can see. Delete first; bind only what passed
the test. To audit prose already written rather than prose being written:
`/claim-audit:claim-audit`.

## Where unshared writing goes

`./internal/` for documentation not meant to be shared — design notes, debugging
logs, scratch work — gitignored. Session logs at `./internal/log/log_YYYY-MM-DD.md`.

A repo that already has somewhere for unshared notes keeps its own
arrangement; use this layout only where there is none.

## Dependency changes

When a session adds, removes, or bumps package versions, record it in the
session log, and nowhere else outside the manifest and lock files.

```markdown
## Dependency changes

| Action | Package | Old | New | Type |
|--------|---------|-----|-----|------|
| added | httpx | -- | 0.27.2 | direct |
| bumped | orjson | 3.10.0 | 3.10.5 | direct |
| removed | requests | 2.31.0 | -- | direct |
```

Read the changes off `git diff` against the manifest and lock files. Two
plausible defaults this overrides:

- The record is the session-log table only. A `deps.md`, `dependencies.json` or
  other separate manifest would be a second source of truth beside
  `pyproject.toml` / `package.json` and the lock files.
- The table lists what changed, never full `uv tree` or `bun pm ls` output.
  Summarise a long transitive tail by count.
