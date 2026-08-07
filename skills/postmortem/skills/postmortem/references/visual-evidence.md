# Visual evidence

last updated: 2026-08-07

Read this when `--visuals` was passed. It covers figures, charts, and the media
directory. Any mode may use it; experience mode uses it most.

`--visuals` implies `--html`. A figure set whose only rendering is relative
image links in a markdown file is half a deliverable — the point of showing
something is to hand someone one file they can open, and that is the HTML.
Both files are still written, and the markdown is still the addressable
artifact.

## The rule

The grounding rule runs in both directions here.

> **No finding, no figure.** Every figure is attached to a finding. A figure
> with no finding is decoration — the visual form of the generic advice this
> skill bans — and it gets cut.

> **When the claim is about something visible, prose is a lossy citation.** If
> a finding says the output was wrong, the layout broke, the frame was off, or
> the numbers moved, show it. Describing a picture is the same failure as
> paraphrasing an error message.

Between them these bound the figure set from both sides, and they bound its
size as a side effect: there is no such thing as a figure this postmortem does
not need.

## What earns a figure

- **Produced output that is wrong** — and, wherever it exists, the intended
  output beside it. A wrong-versus-right pair does more work than either alone
  and is the highest-value figure in the file.
- **Something temporal** — an animation, a run, a multi-step flow. A **labelled
  still sequence**, not a video: state what changed between consecutive stills.
  Stills embed, diff, print, and survive; video does none of those. Inline a
  video only when the motion itself is the finding and the file is genuinely
  small; otherwise keep it in the media directory, inline a still, and name the
  file in the caption.
- **A measured series** — a chart. See below.
- **A structure that is actually a graph** — a pipeline, a dependency, a state
  machine. Hand-authored inline SVG. Do not reach for a diagram library:
  the HTML has no JavaScript, so anything that renders client-side renders
  nothing.

## Captions carry the claim

"Screenshot of the editor" is a filename, not a caption. The caption says
**what to look at and why it matters**: "the axis labels overlap below 640px,
which is the default width in the example config".

Also state **how the figure was produced** — the command, the tool, the
version, the moment. A developer who cannot reproduce a figure has to take it
on faith, and one who can reproduce it can start work immediately.

## Charts

### No chart without its numbers

A chart whose values cannot be recovered is an unfalsifiable claim in picture
form. So the numbers live in the markdown as a small table, and **the chart is
a rendering of that table**, not a separate artifact.

This is the same split the whole skill runs on: the markdown is the record, the
HTML is a transform of it. A reader of the markdown gets the table — which is
the better form for a model anyway — and a reader of the HTML gets the table
rendered. Neither can contradict the other, because there is only one set of
numbers. Charts therefore produce **no files** in the media directory.

### Chart only what was counted

Charting an estimate launders an inference into a measurement, and a chart is
believed far more readily than the sentence it came from. If a series is
inferred rather than observed, label it as inference in the table caption
(ground rule 5) or leave it out. Never mix counted and estimated series in one
chart without marking which is which.

### A chart needs a comparison

A bare number is not a finding, and a bar chart of one series usually is a bare
number wearing a costume. Chart against something: a prior run, another path
through the same system, the stated expectation, or the same measure before and
after a change. If there is nothing to compare against, say the number in a
sentence.

### Under about five points, write the sentence

"Three retries on the first task, one on the second, none after" is faster to
read than any chart of it, and it takes no space.

### What is actually countable in a session

The measures below come from the session record rather than from memory, which
is what makes them chartable at all:

- tool or command invocations, by kind
- retries per operation, and attempts before first success
- failed commands grouped by error class — a taxonomy bar chart is often the
  single most useful figure in an experience postmortem
- turns between first attempt and working result, per task
- files created and later deleted; lines written and later reverted
- wall-clock or turn count between commits
- documentation or reference lookups, by subject — repeated lookups of the same
  page are a discoverability signal
- wrong turns, and how many turns each survived

Plus whatever the subject itself emits: build times, compile errors by
category, test durations, bundle sizes, token counts.

### Rendering

Hand-authored inline SVG in the HTML. No chart library, no JavaScript, no
external font. Draw with the page's CSS custom properties (`var(--fg)`,
`var(--muted)`, `var(--rule)`, `var(--accent)`) so the chart follows the
document into dark mode instead of turning into a white rectangle. Label axes
and units directly; a legend that costs a lookup is worse than labels on the
marks.

`references/html-render.md` has the figure and chart markup.

## Captured media: the directory

Charts produce no files. Screenshots, frames, and recordings do, and they go in
a sidecar directory with the same stem as the postmortem:

```
<resolved-dir>/2026-08-07_experience_mitate.md
<resolved-dir>/2026-08-07_experience_mitate.html
<resolved-dir>/2026-08-07_experience_mitate/
    fig-01-overlapping-axis-labels.png
    fig-02-intended-layout.png
```

Same stem so filing resolves once, as with the HTML. Files are numbered in the
order they are first cited, with a slug describing the content.

The markdown references them relatively — `![...](./2026-08-07_experience_mitate/fig-01-overlapping-axis-labels.png)`
— and the HTML **inlines them as `data:` URIs**. That is not a loosening of the
self-containment constraint in `references/html-render.md` but the reason it
exists: the HTML has to survive being sent to someone who will never clone the
repo, and a relative image link breaks that as thoroughly as a CDN link does.

**The media directory is why `--visuals` is a flag rather than a judgment
call.** Filing never silently creates a directory in a layout the repo did not
choose, and a sidecar full of PNGs is exactly that. The flag is the consent.
Report the directory path alongside the two file paths.

## Redact at capture time

**Path-privacy's hooks read text. They cannot see inside a PNG.** A screenshot
that catches a terminal title bar, an editor sidebar, a window title, or a
browser URL carries absolute paths and usernames past every check this repo
has — and an experience postmortem is written specifically to be sent
elsewhere.

So redaction is part of capturing, not a review step afterwards:

- Capture the region the finding is about, not the desktop.
- Check the edges of every figure before writing it: title bars, tabs,
  sidebars, breadcrumbs, status lines, notification toasts.
- Mask tokens, keys, customer names, and internal hostnames in the image
  itself. A caption saying "ignore the path in the corner" is not redaction.

Cropping tightly satisfies this and makes the figure better, which is why it is
the first thing to do rather than the last.

## Size

Cropping is also the first size lever, and unlike the others it costs nothing:
a figure cropped to its claim is smaller *and* clearer.

- Downscale to at most ~1600px on the long edge. Beyond that is detail no
  reader uses.
- PNG for text, UI, and diagrams — crisp edges, and JPEG artefacts around small
  type make screenshots of error messages hard to read. JPEG or WebP for
  photographic or video-frame content.
- Keep the rendered HTML under roughly 5 MB. Past that it stops being a file
  people open casually, which defeats the point of producing it.

If a set will not fit: crop harder, then downscale further, then — as a last
resort — keep the full-resolution original in the media directory and inline a
reduced version, saying so in the caption. Never drop a cited figure to save
space; the finding it belongs to would lose its citation.
