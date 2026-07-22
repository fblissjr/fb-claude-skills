last updated: 2026-07-21

# explainer-video roadmap

Roadmap for the `explainer-video` plugin (currently **0.6.0**). Originally
written at 0.1.2 after finding the skill's central usability claim false; the
beats refactor that fixed it, and most of the review tooling designed here, have
since shipped. The design write-ups below are kept as history even where DONE —
several shipped *differently* than designed, and the deltas are the useful part.

The larger arc — style generalization, cinematic 3D, film language, style
bibles — lives in
[explainer_video_generalization_plan.md](explainer_video_generalization_plan.md);
this file remains the per-item ledger. Note the plan's Phase 1 triggers the
flip condition the "Not doing: a 2D backend" entry below set for itself.

| # | Item | Status | Blocked by |
|---|---|---|---|
| 1 | [Named beats as the timing source](#1-named-beats-as-the-timing-source) | **DONE** (0.2.0) | — |
| 2 | [Beat-aware contact sheet](#2-beat-aware-contact-sheet) | **DONE** (0.6.0, as `build.js sheet`) | 1 |
| 3 | [Narration-driven timing](#3-narration-driven-timing-audio) | designed, unbuilt | 1 |
| 4 | [Caption lint](#4-caption-floor-lint-replaces-the-magic-number-lint) | **DONE** (0.6.0, advisory) | 1 |
| 5 | [Parallel frame capture](#5-parallel-frame-capture) | **DONE** (0.8.0), with a negative speed result | — |
| 6 | [Repo-wide version alignment check](#6-repo-wide-version-alignment-check) | open | — (not this plugin) |
| 7 | [Spike the hostile beat first](#7-spike-the-hostile-beat-first-methodmd-addition) | **DONE** (0.2.0, in method.md) | — |
| 8 | [The three-axis review model](#8-the-three-axis-review-model-06) | **DONE** (0.6.0) | 1 |
| 9 | [Inline delivery: AVIF vs WebP](#9-inline-delivery-avif-vs-webp-06) | **DONE** (0.6.0), one test open | — |
| 10 | [A committed flagship example](#10-a-committed-flagship-example) | open | — |

The 0.6.0 items (8, 9) and how 2 and 4 actually shipped are summarized next; the
older design write-ups follow unchanged from item 1 down.

---

## Shipped in 0.6.0 (the review-tooling session)

A large pass that gave the skill instruments for two failure axes it was blind
to, and — as importantly — recorded honestly where an instrument could **not** be
built. Detail lives in `references/method.md` (reorganized around the three axes)
and the root `CHANGELOG.md` 0.50.0 entry.

- **Contact sheet (item 2) shipped as `build.js sheet`, not `shoot.js sheet`,**
  and captions each cell via a stdout legend rather than `ffmpeg drawtext` —
  libfreetype is not guaranteed present in every ffmpeg build, and a hard
  dependency on it would fail the command. Samples `frac` into each beat (default
  0.6; `sheet <scene> 480 0.95` puts every beat at its end, which is what catches
  an effect that parks at the end of its ramp). Ships with a `.squint.jpg`
  thumbnail strip — the silhouette check the docs had asserted for months with no
  instrument.
- **`build.js strip`** — consecutive frames tiled, the only pixel-level look at
  the continuity axis for a reviewer that cannot play the film. Bracketed both
  ways: a whole-body jump is visible between cells, a 0.35 rad limb rotation is
  not. Catches world/object-level breaks, not limb-level ones.
- **`build.js motion`** — per-beat motion profile + dead-air report. It
  **deliberately does not** detect pops or stalls: that was built, measured
  against a known-bad scene, and cut when whole-frame statistics put the defect at
  1.00x its local baseline and the stall detector fired on a known-good film. A
  negative result, documented in the code and method.md rather than shipped as a
  check that lies.
- **Caption lint (item 4) shipped advisory, not as a hard-fail floor** — see the
  item 4 note below.
- **Exposure lint** — both tails (washed-out *and* crushed), because the wash rule
  turned out palette-conditional; a dark scene refuted the "every render is
  overexposed" law. Advisory.
- **`window.BEATS`** added to the scene contract, so tooling labels frames and
  checks caption timing without re-parsing source. A `manifest` shoot mode emits
  the beat table as JSON without rendering (used by `motion`).
- **`build.js video`** now warns and prints the re-encode command past the 10MB
  attachment ceiling.

---

## 1. Named beats as the timing source

> **Shipped in 0.2.0.** Built as designed, with one addition the design missed:
> a seconds-from-beat-start form (`rampS`/`pulseS`/`secAt`) alongside the
> fractional one. Fractions are right for anything that should stretch when a
> beat is retimed, but a 0.25s flash and a 0.06s world cut are *physical*
> durations — stretching them uncovers the cut. Also added `capEnd`, for a
> caption that must end before its beat does. Items 2, 3 and 4 are now unblocked.

### The problem

`SKILL.md` says: *"Retiming a beat later is a one-line edit."* That is false. Beat
timing currently lives in three unrelated places:

1. `CONFIG.captions` — `{a: 2.4, b: 4.6, s: "..."}`
2. numeric literals scattered through `animate()` — `ss(t, 5.0, 6.9)`, `bump(t, 6.6, 7.6)`
3. the camera rail — `KEYS[].t`

Retiming means hunting magic numbers across the file and hoping you found them
all. Nothing catches a miss: the scene still renders, just wrong.

This is structural, not a discipline problem. The strongest evidence is that
`examples/skill-retrieval.html` was written *in the same session as the critique
describing this flaw*, and has the flaw — `ss(t,2.4,4.4)`, `ss(t,5.0,6.9)`,
`bump(t,6.6,7.6)` each restate a caption window as a literal. The template makes
magic numbers the path of least resistance, so warnings in `SKILL.md` will not
fix it. Only changing the path will.

### The design

One `BEATS` array is the sole timing source. Everything else derives.

```js
const BEATS = [
  {name: 'title', dur: 2.2},
  {name: 'scan',  dur: 2.4, cap: "1 · every description is an index entry — all are candidates"},
  {name: 'load',  dur: 3.4, cap: "2 · only the match is loaded into the context window"},
];
```

Durations **accumulate**; starts are derived. That is what makes the one-line-edit
claim true — lengthening `scan` shifts `load` automatically instead of silently
overlapping it. `CONFIG.duration` becomes the sum, so it can never disagree with
the beats.

Resolution happens once at load:

```js
let _acc = 0;
const BEAT = {};
for (const b of BEATS) { BEAT[b.name] = {...b, t0: _acc, t1: _acc + b.dur}; _acc += b.dur; }
const DURATION_S = _acc;
```

### The addressing primitive

Almost nothing spans a whole beat — things happen in the first third, or the last
20%. So the core helper takes a fractional sub-range:

```js
// ramp(t,'load')       -> 0..1 smoothstep across the whole beat
// ramp(t,'load',0,.6)  -> 0..1 across the first 60% of it
// ramp(t,'load',.5,1)  -> 0..1 across the back half
function ramp(t, name, a = 0, b = 1) {
  const B = BEAT[name];
  return ss(t, B.t0 + a * B.dur, B.t0 + b * B.dur);
}
function pulse(t, name, a = 0, b = 1) {      // rise-and-fall, same addressing
  const B = BEAT[name];
  return bump(t, B.t0 + a * B.dur, B.t0 + b * B.dur);
}
const during = (t, name) => t >= BEAT[name].t0 && t < BEAT[name].t1;
```

Migration is then mechanical and readable:

| before | after |
|---|---|
| `ss(t, 2.4, 4.4)` | `ramp(t, 'scan')` |
| `ss(t, 5.0, 6.9)` | `ramp(t, 'load', 0, .56)` |
| `bump(t, 6.6, 7.6)` | `pulse(t, 'load', .53, .82)` |
| `ss(t, 4.15, 4.6)` | `ramp(t, 'scan', .73, .92)` |

The fractions read worse than the literals in isolation, which is worth naming
honestly. The gain is that they are *relative* — retiming `scan` moves them all
correctly, and a reader can see that an effect belongs to `scan` without holding
the beat table in their head.

### Captions and camera derive

Captions stop being a parallel list. `setOverlay` walks `BEATS`, showing `cap`
where present, insetting the fade from the beat edges:

```js
const CAP_FADE = .35;   // fade in/out inset, seconds
```

The camera rail addresses beats too, so a keyframe cannot drift away from the
beat it was framing:

```js
const KEYS = [
  {beat: 'title', at: 0,  p: [0,0,19.5], l: [0,0,0]},
  {beat: 'load',  at: 1,  p: [0,0,19.5], l: [0,0,0]},
];
// resolved to absolute t once, at load
```

`at` is the fractional position within the named beat, same convention as `u`.

### Migration

Three files, in order: `templates/scene.template.html`, then
`examples/skill-retrieval.html` (small, 2 beats — do it second as the proving
run), then the longer worked example (20s, 5 beats, two worlds — the real
test).

`smoke.js` is the safety net and it is already sufficient: it byte-compares
`seekTo(t)` before and after seeking away. A migration that shifts any timing
changes rendered output, so **shoot the same sample timestamps before and after
and diff the PNGs**. Identical output means the refactor was behavior-preserving.
That check should be part of the migration, not an afterthought.

### Cost

Roughly: template ~40 lines changed, `skill-retrieval` ~15, the longer example
~60, plus `SKILL.md` steps 1-2 and a `method.md` section. Half a session.

---

## Why beats first

Not just "the cost only goes up." Three of the remaining items are *blocked* on
it, and doing them first means building them against a shape already decided to
be wrong:

- **Contact sheet** needs to know where beats are to sample and label them.
  Without `BEATS` it takes a hand-passed timestamp list, which is the magic-number
  problem again in a new place.
- **Narration-driven timing** has to *write beat durations back* from measured
  speech lengths. There is nothing to write back to until durations are data.
- **The lint** exists to enforce the helpers, which do not exist yet.

Only parallel capture is genuinely independent.

---

## 2. Beat-aware contact sheet

> **Shipped in 0.6.0**, with two deltas from the design below:
> - It is `build.js sheet`, not `shoot.js sheet` — the tiling/legend belongs with
>   the other ffmpeg pipeline steps.
> - Cells are **not** captioned with `ffmpeg drawtext`. libfreetype is not
>   guaranteed present in every ffmpeg build, so a drawtext dependency would fail
>   the command on some installs; the legend (beat name + `t`) prints to stdout
>   instead, and the reviewer reads it beside the image.
>
> It also samples `frac` into each beat (default 0.6), not a fixed midpoint —
> `sheet <scene> 480 0.95` puts every beat at its *end*, which is what surfaces an
> effect that parks at the end of its ramp. And it ships a `.squint.jpg`
> thumbnail strip for the silhouette check.

The iteration loop is the real bottleneck — the longer example took four rounds of
render-look-edit. Right now that means picking timestamps by hand and opening
PNGs one at a time.

```bash
bun run build.js sheet <scene>.html          # tiled PNG, every beat + a squint strip
```

Renders a point in each beat, tiles them into a single image. One look tells you
which beat fails — and, tiled, which failures are *systematic* (the same framing
error across every beat is one bad camera formula, invisible one frame at a time).

---

## 3. Narration-driven timing (audio)

`references/audio.md` currently fits narration into pre-decided beat windows and
validates that each clip fits. That is backwards from how explainers are actually
made: you write the script, and the speech duration dictates the beat length.

With named beats, both directions work and narration-drives-timing becomes the
default:

```yaml
audio:
  mode: narration-drives-timing        # default; or `fixed` to keep beat durations
  narration:
    - {beat: scan, text: "Every skill's description is an index entry."}
    - {beat: load, text: "Only the match is loaded into the context window."}
```

Pipeline: TTS each line → `ffprobe` its duration → set `BEATS[i].dur = max(clip +
padding, min_beat)` → re-render. Under `mode: fixed` the current behavior is kept
and a clip that overruns its window is an error.

This is the item that most needs beats to be data rather than literals — there is
no way to write a measured duration back into `ss(t, 5.0, 6.9)`.

Still deliberately unbuilt until a real narration request lands: voice, language,
and licensing are the user's decisions, and guessing them is how you get an
unwanted dependency.

---

## 4. Caption floor lint (replaces the magic-number lint)

> **Shipped in 0.6.0 — but advisory, not the hard-fail floor designed here.**
> Every lint in `smoke.js` (caption speed, caption overflow, exposure) prints a
> `warn` line and never touches the exit code, on the same reasoning the design
> below reaches for: a gate on a judgment call gets bypassed. So rather than
> hard-fail at ~35 CPS and stay silent below, it warns at **30** (inside the
> unresolved 27-comfortable / 37-unreadable gap, biased to the confirmed-good
> end) and is otherwise quiet. The "a proxy can reject, cannot approve" principle
> still holds — a passing scene is unjudged — it is just enforced by not failing
> rather than by a one-sided threshold.

**Revised twice, and the second revision is the one to build.**

The original design was a magic-number detector — heuristic, false-positive
prone, and largely obsoleted when the beats refactor removed the literals
structurally. It was replaced by a caption reading-speed lint, which was then
invalidated in practice: the threshold (17-21 CPS) came from arithmetic, and one
viewer watching three seconds of video read a 27 CPS caption comfortably.

The usable rule that survives is about proxies generally, not captions:

> **A proxy can reject. It cannot approve.**

The characters-per-second metric was not useless — it correctly flagged a caption
at 37 CPS that was genuinely unreadable. It was wrong at 27, where it had no
authority. The error was granting its entire range decision power when it only
has a confident region and an uncertain one. A passing score in the uncertain
region means nothing and must not read as approval.

So the lint that earns its place is a **floor**, not a pacing tool:

- Hard-fail somewhere around 35+ CPS of effective window — the egregious case,
  where you do not need to watch it to know it is broken.
- **Silent everywhere below.** No warning band, no "tight" verdict. A caption
  that passes has not been judged, and the output must not imply it has.
- Report the effective window (`1.5s effective, 3.3s needed`), never just
  "too long" — the cause is often a `capEnd` trim or fade the author forgot,
  not word count.

The ~35 CPS figure is **bracketed by observation on both sides** — 37 watched and
found unreadable, 27 watched and found comfortable — which is the evidence the
original 17-21 threshold never had. But it is one viewer and two data points.
Tighten the bracket as more scenes get watched; do not treat 35 as settled.

Near-zero false positives by construction, which is what makes it safe to gate.
Built in 0.6.0 (advisory — see the banner above), after the JS stabilized.

## 4b. Magic-number lint (dropped)

Advisory, and honestly heuristic. After the refactor, warn when `animate()`
contains a numeric literal as the 2nd or 3rd argument to `ss`/`bump`:

```
warn: skill-retrieval.html:142 — ss(t, 5.0, 6.9) uses literal timings.
      Use ramp(t,'<beat>',a,b) so retiming a beat moves this with it.
```

Scoped to the `animate()` body by brace matching, because literals elsewhere are
legitimate — `setOverlay`'s `ss(t, .2, .8)` title fade is a fade inset, not a
beat. Suppressible with a trailing `// literal-ok` for the genuine exceptions.

**Warning, never a failure.** A brace-matching heuristic will have false
positives, and a gate that cries wolf gets bypassed — which is exactly the
staleness-metric lesson from 0.32.0. If it proves reliable over a few scenes,
revisit promoting it.

---

## 5. Parallel frame capture

> **Shipped in 0.8.0** (Phase 1 of the generalization plan pulled it forward —
> back-to-back execution makes iteration cost the inner loop). Built as
> designed: `--workers N` or `SHOOT_WORKERS=N`, contiguous chunks, N pages in
> one browser. Correctness verified: 4-worker output is **byte-identical** to
> 1-worker output on the template scene, 48/48 frames.
>
> **The speed prediction below was refuted where it was made.** "The ~1 fps
> software-GL case is where this would matter" — measured on a 4-core
> software-GL container: 25.1s single vs 26.1s with 4 workers, ~1.0x.
> SwiftShader already multithreads a single page's rasterization across the
> cores, so extra pages only contend. The remaining win case is a many-core box
> or hardware GL, where one page cannot saturate the machine — plausible,
> unmeasured. Recorded per the build-the-control rule: the mechanism is
> correct, the benefit is environment-conditional and so far undemonstrated.

Falls straight out of determinism: frames are independent, so N headless pages can
each shoot a contiguous 1/N of the range with zero correctness risk. Contiguous
chunks rather than a stride, so a failed worker leaves an obvious gap.

```bash
bun run shoot.js <scene>.html full 30 --workers 4
```

**Low priority.** Measured 5.3 fps on local hardware GL — a 20s/30fps film is
about two minutes. The ~1 fps software-GL case is where this would matter, and
that is CI/cloud, not the common path. Nothing is lost by waiting: determinism
means this can be added at any time without touching scene code.

---

## 6. Repo-wide version alignment check

Not this plugin, but surfaced by it and still open.

`path-privacy` sat at 0.1.1 in `marketplace.json` while its `plugin.json` had
reached 0.1.6 — five releases where installs resolved a stale version. It was
found by accident, when an unrelated edit touched the plugin and the pre-commit
hook fired.

`skill-maintain test` should assert `marketplace.json` version == `plugin.json`
version for **every** plugin on every run, not only for the one being touched.
Cheap, and it closes a hole that persisted across five releases.

Related but not the same: CLAUDE.md invariant 1 was clarified in this repo (a
skill plugin's `templates/`/`references/`/`examples/` edits trigger the cascade,
not just SKILL.md) — that documents *when* to bump; this item is the automated
check that the bump actually landed everywhere. Still open.

---

## 8. The three-axis review model (0.6)

The skill's whole method was "render frames and look at them," which only covers
failures visible *within* a single frame. `method.md` is now reorganized around
three independent axes, because the reorganization is what made the gaps visible:

- **Composition** — fails inside one frame (framing, occlusion, exposure, hidden
  internals). Instrument: look at stills / the contact sheet. Well covered.
- **Continuity** — fails *between* frames (pops, stalls, sliding feet). No metric
  works (see the `motion` negative result above); reviewed by watching the loop,
  `build.js strip`, and three named source-level shapes. This axis had **zero**
  coverage before 0.6.
- **Semantics** — every frame is right and the film still explains nothing.
  Test: cover the caption, ask what the beat is about. A beat that only works with
  its caption is a slideshow with a 3D background.

The load-bearing lesson, worth keeping: a real scene got four thorough rounds of
look-and-edit that converged composition cleanly, and two continuity defects rode
through untouched to a confident all-clear. Rounds of *looking* converge the axis
stills can show and do nothing for the other two.

---

## 9. Inline delivery: the format comparison (0.6)

Four ways to deliver a scene, and — by explicit decision — **no forced default**.
Each wins on a different axis; the choice is the user's, per context. The job of
the tooling and docs is to surface the tradeoff, not to pick.

| Delivery | Size | Plays inline in a README? | Playback | Audio | Notes |
|---|---|---|---|---|---|
| **HTML+JS scene** | n/a (hosted) | No (github.com strips `<script>`) | Interactive, exact | — | The source of truth and the richest form; runs on Pages or a published Artifact. `build.js bundle` makes it a single offline file. |
| **MP4** | small | No — served as `text/plain`; needs an issue/PR attachment URL for a player | Hardware-decoded, smooth everywhere | Yes (attachment player) | The only path with audio. |
| **AVIF** | smallest (measured 7-54x under WebP) | One real-world observation, not independently confirmed | Software-decoded AV1 sequence — heavier; low-end smoothness unconfirmed | Silent | Lifts the held-camera constraint. |
| **WebP** | largest (ruinous on a moving camera) | Yes, verified | Light, smooth | Silent | Inline rendering is the best-verified case. |

These are **peers**, not a ranking. Keep the measured facts (sizes, the AVIF
decode cost, the content-type mechanism, browser support) as decision inputs in
`method.md`; do not phrase any one as "the default." The single open empirical
question is whether animated AVIF stays smooth on genuinely low-end hardware —
until that is watched and recorded, none of the three raster formats is presented
as safer than the others, just *different*.

Forward: a first-class **deploy-the-HTML-scene** path (package the bundled scene
and publish it to Pages / as an Artifact) is worth treating as a real delivery
option rather than a footnote — it is the only form that keeps the interactivity
and the determinism, and it sidesteps the raster tradeoff entirely. Possible
`build.js deploy` helper; not built.

---

## 10. A committed flagship example

The repo ships exactly one example: `examples/skill-retrieval.html` — 11s,
held-camera, diagrammatic (now in html/webp/avif). There is **no committed
character/"Playful"-style example**; SKILL.md admits as much. The flagship
walkthrough that exercises a figure, world cuts, and a moving camera was built in
a sibling project and is not committed here.

Worth a committed hero example that shows the character/moving-camera path end to
end — it is the case the diagrammatic sample cannot demonstrate, and the one most
likely to be copied from. Open; deliberately not auto-created.

---

## 7. Spike the hostile beat first (method.md addition)

From a walkthrough built in a sibling project, generalized into `method.md`
rather than lost here.

That film is 30s and six beats, and one beat is a violently wobbling wheel driving
a second geared one — every pixel changing every frame, which is precisely the
case that defeats inter-frame compression. It is simultaneously the most
important beat and the most compression-hostile one.

The move: **build and encode the single hardest beat first**, before the other
five exist. Seven seconds of work answers both open questions at once — does the
motion read without a caption, and does it encode small enough to sit inline.
Fail the first and the premise is wrong. Fail only the second and the delivery
plan changes, not the film.

Generalized rule for `method.md`: identify the beat that is both load-bearing and
compression-hostile, and spike it before committing to the full beats table. This
is the same "iterate by looking, not by hoping" discipline applied to the encode
step, which currently has no equivalent early check — the skill tells you to look
at frames but says nothing about testing the delivery target early.

Note this rule also mostly disappears if the scene holds the camera, since the
whole problem is per-frame change. It matters for the moving-camera case.

## Not doing

- **GIF output.** GitHub renders it, but it lost to WebP on every axis measured
  (12.08 MB vs 15.56 MB on a hostile scene; WebP wins outright on a friendly one)
  and it has no audio and visible banding. WebP plus the poster path covers it.
- **Baking audio into the scene file.** Keeps the artifact self-contained and
  small; muxing stays a separable post-step that never re-renders frames.
- **A 2D backend.** The contract already permits one — `smoke.js` was fixed in
  0.1.2 to stop asserting `window.THREE`, so any scene exposing the four globals
  gets frame-exact MP4s. Worth building only when a real 2D sequence is wanted;
  the point is that nothing now blocks it.
