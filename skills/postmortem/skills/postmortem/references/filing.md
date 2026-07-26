# Filing a postmortem

last updated: 2026-07-26

Where the file goes, what it is called, and what its frontmatter must carry so
that someone — more often, some model — can find it months later without
reading everything.

A postmortem filed inside a plan doc is findable only by a reader who already
knows which plan doc to open. That is the failure this exists to prevent.

## Resolving the directory

Never hardcode a location and never silently create a directory in a layout the
repo did not choose. `internal/` is one repo's convention, `docs/notes/` is
another's, and whether postmortems are local scratch or a tracked shared record
is the repo owner's call — it changes the answer completely.

Resolve in this order, stopping at the first hit. **Say which rung you landed
on** in the message that reports the written file.

1. **Explicit on the invocation.** An `--out=<dir>` flag, or the user naming a
   location in the request. Highest precedence, never persisted — a one-off
   override is one-off.

2. **Per-repo config.** A root-level `.postmortem.json` with:

   ```json
   { "dir": "internal/postmortems" }
   ```

   Path is repo-relative. Omitted keys mean "default", so the file only ever
   states exceptions. This is the plugin's own config file, deliberately not a
   shared one — see "Per-repo plugin config" in this repo's
   `docs/internals/plugin-patterns.md` for why.

3. **Inferred from where the repo already keeps prose about itself.** The repo
   has answered "where does writing about this project live"; read its answer
   rather than imposing one. In descending confidence:

   - A session-log directory (`internal/log/`, `notes/sessions/`, anything
     holding dated `log_*.md`-shaped files) → a `postmortems/` sibling under the
     same parent.
   - An existing `postmortems/` or `retros/` directory anywhere → use it as-is.
   - A working-notes or internals tree (`docs/internals/`, `notes/`, `docs/adr/`)
     → a `postmortems/` sibling under the same parent.
   - A bare `docs/` tree with prose in it → `docs/postmortems/`.

   Inference picks the *parent*; the leaf is always `postmortems/`. Match the
   parent's tracked-ness: if the sibling directory is gitignored, the postmortem
   is local scratch, and that is a deliberate answer rather than an oversight.

4. **Propose, then remember.** With no signal, do not guess and do not write.
   Propose a location and say **whether it would be tracked or gitignored** in
   this repo as it stands — rung 3 reads that answer off a sibling directory,
   but at rung 4 there is no sibling and "these are committed and shared" versus
   "these are local scratch" is the actual decision being made. Get agreement,
   then write the agreed path to `.postmortem.json` so the question is asked
   exactly once. If the user declines to create the config, honour that and ask
   again next time — a declined config is not a bug.

Rung 4 is the only rung that blocks. Rungs 1–3 write without asking.

## Naming

```
<resolved-dir>/YYYY-MM-DD_<mode>_<slug>.md
```

- **Date first** so lexical sort is chronological sort. Recency is the most
  common filter, and it is the same reason session logs are `log_YYYY-MM-DD.md`.
  For a span, the date is the **start of the range**, not the day someone got
  round to writing it: `2026-07-01_span_lint-tooling.md`. The write date goes in
  frontmatter.
- **Mode** is one of `session`, `span`, `feature`. `feature` is a span scoped to
  a named feature rather than a date range; when a run could be called either,
  the deciding question is what a reader would search for — a feature name or a
  period of time.
- **Slug** derived from the scope, not the date: `ruff-diagnostics`,
  `pyright-baseline`, `q3-migration`. Lowercase, hyphenated. This is the part a
  grep will match, so prefer the name the artifacts already use over a
  descriptive phrase.

The naming is the portable part and holds in any repo. Only the directory is
negotiable.

## Frontmatter

Every postmortem carries this block. It exists so a model can triage a file
without reading it.

```yaml
---
mode: span
scope: lint-and-type-tooling
date: 2026-07-26
range: 2026-07-01..2026-07-26
artifacts:
  - CHANGELOG.md
  - skills/ruff-diagnostics/
  - docs/internals/context-cost.md
supersedes: 2026-06-14_feature_ruff-trial.md
---
```

| Field | Required | Notes |
|---|---|---|
| `mode` | yes | Matches the filename token. |
| `scope` | yes | Matches the filename slug. |
| `date` | yes | When it was written. For a span this differs from the filename date; that is the point. |
| `range` | span only | Exact git range or date range examined. |
| `artifacts` | yes | Repo-relative paths, commits, or command names. May be empty only if the body has no findings. |
| `supersedes` | no | Bare filename of an earlier postmortem this one revisits. |

**`artifacts` is a projection of the citations, not free metadata.** Every entry
must appear as a citation somewhere in the body, and every artifact cited in the
body must appear in the list. That is what makes "has anything been written
about this file" a one-line grep, and it is checkable: if the two sets disagree,
one of them is wrong. It also keeps the frontmatter honest under the no-citation-
no-finding rule — a findings-bearing postmortem with an empty `artifacts` list
is a contradiction, not a formatting slip.

Paths are repo-relative. An absolute path in a postmortem leaks the machine it
was written on.

`supersedes` is a single value. A long-running scope forms a chain by following
the pointers; a stored chain would be a copy whose only consumer is the check
that it matches the pointers.

## Existing postmortem for the same scope

Annotate, do not duplicate — the append-correction rule in SKILL.md. When new
evidence contradicts a finding in an existing postmortem, add a dated annotation
under that finding in the existing file.

Write a **new** file with `supersedes:` only when the scope was genuinely
revisited as fresh work rather than corrected — a second migration attempt, a
rebuilt feature. The test: if the old document's verdicts still stand and only
one is now wrong, annotate. If its whole framing has been overtaken, supersede.

## Cross-linking

If a plan doc for this scope exists, add a one-line pointer to the postmortem in
it. That direction only. The plan doc is where a reader already knows to look;
the postmortem's `artifacts` list already records everything it examined,
including the plan doc and any session logs, so a second inbound link from each
of those would be a copy that drifts.

Do not add an index file. A `postmortems/README.md` listing every file is a copy
whose only consumer is the check that it matches the directory. The naming
convention is the index: listing the directory sorts by date, and a slug grep
finds a topic.

## Reporting

The written path is part of the output. Report it as a repo-relative path,
alongside which resolution rung produced it, so the user can correct a wrong
inference before a second postmortem lands in the same wrong place.
