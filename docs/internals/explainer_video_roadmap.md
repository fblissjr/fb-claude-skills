last updated: 2026-07-21

# explainer-video roadmap

Design for the queued work on the `explainer-video` plugin (currently 0.1.2).
Written after building two worked examples and finding that the skill's central
usability claim is false.

Ordering is deliberate and argued in [Why beats first](#why-beats-first): the
beats refactor blocks three of the other four items, so doing anything else
first means doing it twice.

| # | Item | Status | Blocked by |
|---|---|---|---|
| 1 | [Named beats as the timing source](#1-named-beats-as-the-timing-source) | **DONE** (0.2.0) | — |
| 2 | [Beat-aware contact sheet](#2-beat-aware-contact-sheet) | designed | 1 |
| 3 | [Narration-driven timing](#3-narration-driven-timing-audio) | designed | 1 |
| 4 | [Magic-number lint](#4-magic-number-lint) | designed, advisory only | 1 |
| 5 | [Parallel frame capture](#5-parallel-frame-capture) | designed | — |
| 6 | [Repo-wide version alignment check](#6-repo-wide-version-alignment-check) | designed | — (not this plugin) |
| 7 | [Spike the hostile beat first](#7-spike-the-hostile-beat-first-methodmd-addition) | **DONE** (0.2.0, in method.md) | — |

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
// u(t,'load')          -> 0..1 smoothstep across the whole beat
// u(t,'load',0,.6)     -> 0..1 across the first 60% of it
// u(t,'load',.5,1)     -> 0..1 across the back half
function u(t, name, a = 0, b = 1) {
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
| `ss(t, 2.4, 4.4)` | `u(t, 'scan')` |
| `ss(t, 5.0, 6.9)` | `u(t, 'load', 0, .56)` |
| `bump(t, 6.6, 7.6)` | `pulse(t, 'load', .53, .82)` |
| `ss(t, 4.15, 4.6)` | `u(t, 'scan', .73, .92)` |

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

The iteration loop is the real bottleneck — the longer example took four rounds of
render-look-edit. Right now that means picking timestamps by hand and opening
PNGs one at a time.

```bash
bun run shoot.js <scene>.html sheet          # one tiled PNG, every beat's midpoint
```

Renders the midpoint of each beat, tiles them into a single image, captions each
cell with the beat name and its `t0-t1`. One look tells you which beat fails.
Implementation is a montage of existing sample frames — `ffmpeg tile` filter with
`drawtext`, no new capability.

Deliberately the midpoint, not the start: beat boundaries are transitions and
show half-finished state.

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

## 4. Magic-number lint

Advisory, and honestly heuristic. After the refactor, warn when `animate()`
contains a numeric literal as the 2nd or 3rd argument to `ss`/`bump`:

```
warn: skill-retrieval.html:142 — ss(t, 5.0, 6.9) uses literal timings.
      Use u(t,'<beat>',a,b) so retiming a beat moves this with it.
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

---

## 7. Spike the hostile beat first (method.md addition)

From a freudagent build in progress, and worth generalizing into `method.md`
during the refactor pass rather than losing it here.

That film is 30s and six beats, and beat 5 is a violently wobbling wheel driving
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
