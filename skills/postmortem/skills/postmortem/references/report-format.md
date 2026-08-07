# Report format

last updated: 2026-08-07

The shape of a finding, and the shape of the file. These hold under **every**
lens — a lens chooses the sections, never these.

The section-by-section content lives in the lens, in the plugin-level `lenses/`
directory: `project.md` is the default, `experience.md` the other built-in, and
`README.md` there describes the format and where repo-local lenses are found.
Read the chosen lens alongside this file.

## A finding

A few sentences: the claim, the citation, and — only when it generalizes — the
structural lesson in one plain sentence.

- **No citation, no finding.** A finding names a concrete artifact: a file, a
  commit, a failed command, a measurement, a decision visible in the record.
  Generic advice is banned in every section of every lens.
- **Empty sections are valid output.** Write "Nothing." and move on. The
  expected honest output for a small clean task is mostly "Nothing.", and
  inventing an item to fill a frame is the failure this rule prevents.
- **Distinguish measurement from inference.** Label anything not directly
  observed.
- **Group repeats.** Three instances of one shape are one finding with three
  citations, not three findings. The pattern is the finding.

## The file

A postmortem's value depends on being durable and annotatable, so chat-only
output is not a postmortem. **Every run writes a file.**

The file opens with the frontmatter block, then the lens's sections in the
lens's order.

Where it goes, what it is called, what the frontmatter must carry, and what to
do when a postmortem for the same scope already exists: the plugin-level
`references/filing.md`. Resolve the location from that ladder; never assume one.

## Annotation

A postmortem is append-corrected. When later evidence contradicts a finding, add
a dated annotation under it stating what changed — never silently edit the
original. A postmortem that slips its own conclusions quietly is worse than
none.

Annotating also re-renders any derived rendering beside the file; see
`references/html-render.md` and the filing reference.

## Figures and charts

Only under `--visuals`. A figure attaches to a finding inside one of the lens's
sections; there is no figures section, because a figure that has to be gathered
into one has no finding to sit under. A chart's numbers live in a table in this
document and the chart is a rendering of that table, so the markdown is never
lossy. Full discipline: `references/visual-evidence.md`.

## Routing the findings

Every lens ends by sorting what should outlive the document. Where those
findings go depends on who the lens is written for — a `project` postmortem
routes into this repo, an `experience` one routes to somebody else's backlog —
so the routing table itself lives in the lens.

Route only what earned it. Most findings correctly stay in the postmortem.
