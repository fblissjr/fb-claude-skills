# postmortem

*Last updated: 2026-08-03*

Evidence-grounded retrospectives. One skill runs a postmortem of finished work
— a session, a feature, or a span of sessions mined from git history, session
logs, and changelogs. The other audits an existing test suite for meaning and
drift: whether each green test still verifies what its authors believed.

Both skills share one discipline: findings are claims, claims need citations,
and empty sections are valid output. The postmortem format (what went well /
what did not / deviations table / escapes / forward items, annotate-don't-
rewrite) was distilled from a real run postmortem in this repo that caught its
own process errors; the test-audit method (claim / oracle / envelope, spot
mutation, "a green suite proves what its conditions can express") generalizes
the same run's verification lessons.

## Installation

```bash
/plugin install postmortem@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `postmortem` | "postmortem", "retrospective", "what went well", "what would you do differently" | Verdicted retrospective of finished work; session mode (the conversation) or span mode (git history, session logs, changelogs, plan docs). Output is always a durable file. |
| `postmortem-index` | "browse postmortems", "postmortem index", "what have we written about X" | Generated HTML index over a repo's postmortems: chronological, plus a by-artifact view. Reads frontmatter only. Superseded entries are marked, not hidden; artifact paths that no longer resolve in the tree are marked "not in the tree today", not dropped. |
| `test-audit` | "audit the tests", "are these tests testing the right thing", "test drift", "do we trust this suite" | Per-test claim recovery, oracle verification by spot mutation, envelope mapping, and keep/rewrite/delete verdicts. Per-architecture question packs in `references/architectures.md`. |

## Invocation

```
/postmortem:postmortem                # this session
/postmortem:postmortem <feature|range|plan doc|"last N sessions">
/postmortem:postmortem span auth-migration --out=docs/postmortems
/postmortem:postmortem --html         # markdown plus a readable HTML file
/postmortem:postmortem-index          # browsable index over all of them
/postmortem:test-audit                # audit the current repo's suite
```

Or trigger naturally: "run a postmortem on the auth migration", "which of our
tests are dead weight".

## Design notes

- Every finding must cite a concrete artifact (a file, commit, measurement,
  failed command). Generic advice is banned; "Nothing." is a valid section.
- Postmortems are append-corrected: later evidence gets a dated annotation
  under the original finding, never a silent rewrite.
- The escapes section (bugs vs. the tests that should have caught them) is the
  bridge between the two skills: repeated green-but-blind escapes in
  postmortems are the trigger for a full test-audit.
- Test deletions are recommended with evidence, never applied unasked.
- A postmortem is a standalone file, never a section appended to a plan doc.
  The directory is resolved per repo rather than hardcoded — `--out=<dir>`, a
  root-level `.postmortem.json`, inference from where the repo already keeps
  prose about itself, else a proposal — and the run reports which rung it landed
  on. Named `YYYY-MM-DD_<mode>_<slug>.md`, date first so lexical sort is
  chronological. Frontmatter carries an `artifacts` list that must match the
  body's citations exactly, which is what makes "has anything been written about
  this file" a one-line grep and why there is deliberately no index file. Full
  procedure: `skills/postmortem/references/filing.md`.

## Configuration

Optional, root-level, tracked. Only ever states exceptions:

```json
{ "dir": "docs/postmortems" }
```

Without it, the location is inferred or proposed. Most repos never need it.

## HTML output

Markdown is the postmortem and is always written. `--html` adds a second file
beside it with the same stem — a transform of the markdown just written, not a
second analysis, so the two cannot disagree.

The HTML is self-contained: embedded CSS, light and dark, no external requests
of any kind and no JavaScript. It reads offline and survives being sent to
someone who will never clone the repo. There is no `--style` flag and no styler
integration; one built-in stylesheet is the whole design.

Empty sections render visibly rather than collapsed, citations are never trimmed,
and annotations render distinctly from the findings they correct.

Rendering a postmortem from an earlier run is not a designed capability — the
report format is a house style, not a parse contract. Run a new postmortem
instead.

`test-audit` is markdown only.

## The index

`postmortem-index` generates a browsable page over every postmortem in the
resolved directory: chronological with each one's `summary` and artifacts, plus
a by-artifact view answering "has anything been written about this file".

It is a **view, not a record.** The directory is the index; this page is rebuilt
from the files each time and deleting it loses nothing. That is why there is no
checked-in listing — a committed one becomes a copy that drifts. If the
postmortem directory is tracked, the skill offers to gitignore the generated
file, since a generated artifact that cannot be committed cannot be mistaken for
truth.

Reads frontmatter only, never prose. Superseded postmortems are dimmed and
labelled rather than hidden, and files predating the frontmatter convention
still appear with what the filename yields plus a "partially indexed" badge —
an index that quietly omits is worse than no index.

This page carries a small inline filter script, unlike the postmortem document,
which has none. A record that needs JavaScript to be readable is less durable
than the markdown it came from; an index is a tool that gets rebuilt. Nothing
starts hidden, so with scripting off the page loses filtering and keeps
everything else.

Why it is shaped this way, and which of the original design's recommendations
were rejected on contact with the implementation:
[docs/internals/postmortem_output_formats.md](../../docs/internals/postmortem_output_formats.md).
