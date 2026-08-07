# postmortem

*Last updated: 2026-08-07*

The audit family, and the adversarial primitive its audits run on. One skill
runs a postmortem of finished work — a session, a feature, or a span of
sessions mined from git history, session logs, and changelogs. `test-audit`
audits an existing test suite for meaning and drift: whether each green test
still verifies what its authors believed. `control-audit` does the same for
controls — everything check-shaped that fires outside the test suite (git
hooks, Claude Code hooks, CLI validators, reminders) — by census and
live-fire. The `adversarial-verify` skill and `control-builder` agent package
the verification move they all lean on: build the experiment that would
refute a claim, then separately prove the attempt actually reached its
subject.

The skills share one discipline: findings are claims, claims need citations,
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
| `postmortem` | "postmortem", "retrospective", "what went well", "what would you do differently", "what was confusing about using X", "feedback for the devs" | Verdicted retrospective of finished work: session mode (the conversation), span/feature mode (git history, session logs, changelogs, plan docs), or experience mode (feedback to the developers of the system the work was done *with*). Output is always a durable file; `--visuals` adds figures and charts. |
| `postmortem-index` | "browse postmortems", "postmortem index", "what have we written about X" | Generated HTML index over a repo's postmortems: chronological, plus a by-artifact view. Reads frontmatter only. Superseded entries are marked, not hidden; artifact paths that no longer resolve in the tree are marked "not in the tree today", not dropped. |
| `test-audit` | "audit the tests", "are these tests testing the right thing", "test drift", "do we trust this suite" | Per-test claim recovery, oracle verification by spot mutation, envelope mapping, and keep/rewrite/delete verdicts. Files a dated `audit` artifact via the shared filing ladder. Per-architecture question packs in `references/architectures.md`. |
| `adversarial-verify` | "adversarially verify this", "build the control", "try to refute this", "did that green actually test anything" | The single-claim primitive: construct the refutation (dispatched to the `control-builder` agent), then a separate pass verifies the attempt reached the subject before either outcome counts. Verdicts: confirmed / refuted / no separation / vacuous. |
| `control-audit` | "audit the controls", "do our hooks actually fire", "is anything watching this check" | Census of everything check-shaped outside the test suite — four slots per control (fires-via, guarded-by, retirement-condition, disclosed-uncontrolled-edges), each derived or transcribed — plus mandatory live-fire of controls nothing watches, dispatched to `adversarial-verify` under a strict safety protocol. Report-only; a run, not an artifact. |

## Agents

| Agent | Role |
|-------|------|
| `control-builder` | Takes one claim and tries to falsify it by construction: single-variable control, proof the control took effect, both measurements, verdict. Returns three verdicts; `vacuous` is deliberately not its to issue, because it does not grade its own needle. Deliberately inherits the session model — designing a refutation is not down-tier work. Ships mechanism only; installing repos grow their own evidence record. |

## Invocation

```
/postmortem:postmortem                # this session
/postmortem:postmortem <feature|range|plan doc|"last N sessions">
/postmortem:postmortem span auth-migration --out=docs/postmortems
/postmortem:postmortem --html         # markdown plus a readable HTML file
/postmortem:postmortem experience mitate --visuals   # feedback for that tool's devs, with figures
/postmortem:postmortem-index          # browsable index over all of them
/postmortem:postmortem-index --from=docs/postmortems --out=build/
/postmortem:test-audit                # audit the current repo's suite
/postmortem:adversarial-verify <claim>  # refute-by-construction, needle verified
/postmortem:control-audit             # census + live-fire the repo's controls
```

Or trigger naturally: "run a postmortem on the auth migration", "write up what
it was like building with X for their devs", "which of our tests are dead
weight", "prove this check can actually fail", "do our hooks actually fire".

## Experience mode

The first three modes ask *what did we build and what did it teach us*.
Experience mode asks *what was it like to build with this thing*, and its reader
is someone who maintains that thing and has never seen your repository. Six
sections instead of five:

| Section | What it holds |
|---|---|
| What worked | Affordances that paid off — the only signal a developer gets about what **not** to break. |
| What did not | Friction, with a cost attached. Repeats are one finding with several citations, not several findings. |
| Expectation vs. behaviour | Expected / Actual / **What led me to expect it**. The third column names the surface that misled, which is the thing to fix. |
| Escapes: guidance and instrumentation | Per wrong turn, which surface should have prevented it: absent, present-but-not-found, or present-but-misleading. The structural twin of the test-escapes section. |
| Built outside the system | What you had to make yourself, what it substitutes for, and whether it is a workaround (should stop existing) or a legitimate extension. Each row is a capability request shipping with a reference implementation. |
| Forward items | Checkable, ordered by cost. The only section where a wish is allowed, and only if a finding above names the moment it was wanted. |

Its evidence is friction, which is the first thing a successful session
overwrites, so it is reconstructed from the session trace rather than from
memory — "I was confused" is not a finding; the turn where you were confused,
what you did next, and what it cost is. Two rules keep the output usable:
**rank by cost, not annoyance**, and **separate "it is missing" from "I did not
find it"** — the second is still a finding, but a discoverability one with a
completely different fix.

Frontmatter adds `version` (the build of the subject as it was used — feedback
ages against releases) and `task` (what you were building while using it).

Because this file is written to be sent outside the repo, redaction matters more
here than anywhere else — including in pixels, which path-privacy's hooks cannot
read.

## Visuals

`--visuals` adds figures and charts, and implies `--html`. Two rules bound the
figure set from both sides: **no finding, no figure** — decoration is the visual
form of the generic advice the skill bans — and, when a claim is about something
visible, prose is a lossy citation, so show it.

**No chart without its numbers.** The numbers live in a table in the markdown
and the chart is a rendering of that table, exactly as the HTML is a rendering
of the markdown; neither can contradict the other because there is one set of
numbers. Charts therefore write no files, are hand-authored inline SVG (the page
has no JavaScript, so nothing client-side would render), and only ever plot what
was actually counted.

Captured media — screenshots, frames, still sequences — goes in a sidecar
directory with the same stem as the postmortem. The markdown references it
relatively; the HTML inlines it as `data:` URIs, because a relative image link
breaks "send this one file to someone" as thoroughly as a CDN link does. The
media directory is why this is a flag rather than a judgment call: filing never
silently creates a directory the repo did not choose, and the flag is the
consent.

## Shared references

Three concerns are used by more than one skill, so they live at the plugin root
rather than inside whichever skill happened to need them first:

| File | Read by |
|------|---------|
| `references/filing.md` | `postmortem` and `test-audit` (write), `postmortem-index` (locate) |
| `references/verification.md` | `adversarial-verify`, `test-audit`, `control-audit`, and the `control-builder` agent |

There is no import mechanism in a plugin made of prose — a file is shared only
because several skills name its path — so the **path is the only signal** a
future editor gets about who depends on a file. Both were previously owned by
one skill and reached into by others, and both drifted the first time something
was added.

Two things deliberately stay duplicated. The HTML palette is mirrored between
`html-render.md` and `index-page.md` because each template must be embeddable
verbatim to emit one self-contained file; extracting ~12 lines would make every
render an assembly step. That pair is pinned by a test arm rather than merged.
And `postmortem-index` no longer keeps its own copy of the frontmatter field
set — `filing.md`'s table is now the only enumeration of it.

Note: files at the plugin root sit outside per-skill token accounting, so
`skill-maintain`'s `ref_tokens` figure undercounts a skill's real reference
surface. The budget gate is on SKILL.md only, so nothing is bypassed — but the
number is informational, not complete.

## Design notes

- Every finding must cite a concrete artifact (a file, commit, measurement,
  failed command). Generic advice is banned; "Nothing." is a valid section.
- Postmortems are append-corrected: later evidence gets a dated annotation
  under the original finding, never a silent rewrite.
- The escapes section (bugs vs. the tests that should have caught them) is the
  bridge between postmortem and test-audit: repeated green-but-blind escapes in
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
  procedure: `references/filing.md` at the plugin root.
- Renderings are derived and disposable. A run that annotates a markdown file
  re-renders every sibling rendering, and each rendering carries a provenance
  footer naming its source file and render date — an annotated markdown beside
  a stale HTML is a state the skill defines as wrong, so nothing may produce it
  silently.

## Configuration

Optional, root-level, tracked. Only ever states exceptions:

```json
{ "dir": "docs/postmortems" }
```

Without it, the location is inferred or proposed. Most repos never need it.

## HTML output

Markdown is the postmortem and is always written. `--html` adds a second file
beside it with the same stem — a transform of the markdown just written, not a
second analysis, so the two cannot disagree. `--visuals` implies it.

The HTML is self-contained: embedded CSS, light and dark, no external requests
of any kind and no JavaScript. It reads offline and survives being sent to
someone who will never clone the repo. There is no `--style` flag and no styler
integration; one built-in stylesheet is the whole design.

Empty sections render visibly rather than collapsed, citations are never trimmed,
and annotations render distinctly from the findings they correct.

Rendering a postmortem from an earlier run is not a designed capability — the
report format is a house style, not a parse contract. Run a new postmortem
instead.

`test-audit` is markdown only — its reader is the next audit, and a rendering
would be a second format to keep in step for no reader that exists yet.

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
