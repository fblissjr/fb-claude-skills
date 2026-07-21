# Method: designing a sequence that reads

## Beats are data, not comments

`BEATS` is the only place a timestamp exists. Captions, camera keyframes and
`DURATION` all derive from it, and `animate()` addresses beats by name:

```js
const BEATS = [
  {name:'title', dur:2.4},
  {name:'scan',  dur:2.4, cap:"…"},
  {name:'load',  dur:3.2, cap:"…", capEnd:2.85},   // caption ends early, beat does not
];
ramp(t,'load',0,.56)      // fraction of the beat — stretches when you retime
rampS(t,'load',1.8,2.3)   // seconds from beat start — does NOT stretch
```

**Fractions by default; seconds when the duration is physical.** A rise "across
the first half of a beat" should stretch if the beat grows. A 0.25s flash or a
0.06s world cut should not — stretching a cut window uncovers the cut, which is
the bug below that already cost one re-render. That distinction is the whole
reason both forms exist.

Durations **accumulate**: lengthening `scan` shifts `load` rather than
overlapping it. Retiming is genuinely one edit.

Two things this bought immediately, both structural rather than stylistic:

- Before it existed, a scene written *in the same session that documented the
  problem* still restated caption windows as literals in `animate()`. The
  template made magic numbers the path of least resistance, so no amount of
  warning fixed it.
- Narration-driven audio becomes possible at all: you cannot write a measured
  speech duration back into `ss(t, 5.0, 6.9)`.

### Migrating an existing scene

Shoot the same sample timestamps before and after and compare with
`ffmpeg -lavfi psnr`. Byte-identical frames mean behavior-preserving; >70 dB is
imperceptible rounding. Anything lower, go look at a difference image
(`blend=all_mode=difference`) before assuming it is fine — when this was done on
the shipped scenes the only sub-70 dB frames were caption-fade boundaries,
localized to the caption pill, and a precision-critical world cut came out
byte-identical.

## Dwell: measured, not derived

Two numbers observed by rendering and watching, not reasoned about. Treat them
as starting points and re-measure rather than trusting the arithmetic:

- **A sweep highlight at ±0.55 units wide reads as a flicker.** At ±0.9 the lit
  phases of neighbouring elements overlap and it reads as a wave passing
  through. Width mattered more than beat length: stretching the beat alone just
  spaced the flickers further apart.
- **A beat under ~3s felt rushed even when its caption was comfortably
  legible.** Caption speed and motion speed are separate problems and the
  caption is the weaker signal — a beat can pass a reading-speed check and still
  be too fast to follow.

Overlay fades belong **inside** their beat. The title fade used to be centred on
the beat boundary, which spilled title pixels 0.3s into the next beat and made
retiming non-local. Fade out completes at `t1`; fade in starts after `t0`.

## Motion that reads vs causality that reads

These are different problems and the second is harder. A sweep only has to be
perceived as motion — get the dwell right and it works. But a beat whose job is
"A drives B" fails if the viewer perceives *A moving and B moving*. Co-occurrence
is not causation, and no amount of extra beat length fixes it.

The lever is usually **phase and derivation, not duration**. If B's motion is
visibly locked to A's — same phase, amplified, or offset by a fixed lag — the
coupling is perceptible. If A and B are animated from independent expressions
that merely happen to overlap in time, it reads as two unrelated things moving.
Drive B from A's own expression rather than from `t` separately.

Verify it with a control: deliberately break the phase relationship and watch
again. If the broken version reads the same as the locked one, the locking was
not doing the work and the causality is not landing — go find another cue
(a connecting element, a lag, a colour that propagates).

Untested here; recorded because it is the specific thing to watch a spike for.

## Beats before geometry

A sequence is a list of beats — (time range, caption, one visible change). Write
the beats table first and keep each beat to ONE idea. 3-4 seconds per beat is
the pacing that reads; under 2s the viewer misses it, over 6s it drags. The
title card is a beat. The payoff/outro is a beat. 20 seconds ≈ 5-6 beats.

Structure that consistently works for explainers:
establishing shot → dive into the subject → 3-4 stages of the process →
pull back out → payoff/celebration. The "dive" and "pull out" are world cuts.

## Worlds and cuts

Model distinct settings (a workshop and a machine's interior; a datacenter and a
database's insides) as separate Groups offset far apart (y -60). Toggle
`.visible` per frame in `animate(t)`; jump the camera between them instantly.

**The one rule about cuts: hide them under a flash, completely.** A camera
interpolating between worlds shows empty void. Make the camera jump span ≤0.06s
between two adjacent keyframes, centered on a `CONFIG.flashes` midpoint. If the
exit keyframe is seconds before the world switch, add a holding keyframe just
before the cut — this exact bug shipped once and cost a re-render.

## The camera rail

- Keyframes in `KEYS[]`, smoothstep between consecutive pairs. Ease-in-out per
  segment is what makes it feel filmed rather than programmed.
- A gentle sin() sway (amplitude ~0.06) keeps held shots alive.
- Frame for the beat: the thing changing should occupy the middle third. When a
  new object enters (a part rising, a pulse arriving), aim where it WILL be.
- Long lens (fov 20-25) + frontal angles for diagram worlds; normal lens
  (fov 40-45) + three-quarter angles for character worlds.

## Procedural assets (no files, no downloads)

Everything is composed from primitives — spheres, boxes, cylinders, planes, tori.
No model files, no textures, no downloads. That constraint is what keeps a scene a
single self-contained HTML file, and it is far less limiting than it sounds.

### The general move

Recipes below are organized by **shape problem**, not by subject, because the same
geometry serves wildly different domains. Before reaching for one, derive your own:

1. **Decompose to primitives.** Almost anything reads as spheres, boxes and
   cylinders in a Group hierarchy. Detail is not what makes it legible.
2. **Silhouette first.** If it does not read as a black shape at thumbnail size,
   more detail will not save it. Check by squinting at a sample frame.
3. **Signature feature, oversized ~30%.** Whatever identifies the subject — a
   beak, a hat, a chimney, a rotor, a spike in a chart — push it past comfortable.
   The first render is always too timid.
4. **Costume beats anatomy.** A hard hat makes a figure a builder; a torus brim
   and a cap make one a surgeon. Role reads instantly from accessories and never
   from accurate proportions.
5. **Signal over realism.** Emissive brightness, scale pulses and colour shifts
   carry meaning. A photoreal object that does not change is worse than a crude
   one that does.

### Recipes that have actually been built

- **Figure** (creature, mascot, person, robot — anything that presents or
  reacts): body = sphere scaled ~(0.9, 1.1, 1.15); head sphere on a short neck
  sphere; limbs = spheres or cylinders in pivot Groups at the shoulder/hip so
  they rotate for gestures; feet = flattened boxes. A protruding feature (beak,
  snout, visor) = cone scaled flat in one axis and rotated forward.
- **Expressive face**: head sphere; eyes = white spheres scaled z≈0.5 sitting
  PROUD of the face (bug-eyed reads at distance), pinpoint pupils, glint dots;
  brows floated slightly off the head; blush = flat circles rotated to the
  cheeks; open mouth = dark sphere in a Group (doubles as a portal for dive-ins;
  scale to 0 and swap in a half-torus smile for a finale).
- **Cutaway / cross-section** (geology strata, building floors, soil horizons,
  battery internals, an engine block, a seabed): a flat slab box + bands for
  layers, viewed frontally. CRITICAL: anything "inside" the slab is invisible —
  cavities, thin layers and particles must sit PROUD of the front face by 0.1-0.3
  units, like a museum diorama. A thin dark torus rim where a cavity meets the
  surface sells the carved look.
- **Network or flow** (data pipelines, supply chains, transit maps, circuits,
  approval workflows, nutrient cycles): stations = labeled boxes on a ground
  plane; the payload = a bright emissive sphere whose position is a piecewise
  function of t along the edge path; arrival = `pulse()` scale bump on the
  station. Captions carry the semantics; the geometry carries the motion.

### Not yet built, but the shape is obvious

Sketches, not battle-tested — treat them as starting points and add what you
learn back here.

- **Field of instances** (populations, portfolios, fleets, A/B cohorts): one
  instanced primitive per item on a grid, driven by a seeded `R[]` offset so the
  arrangement is deterministic. Colour or height encodes the variable; the beat
  is a wave passing through the field.
- **Mechanism** (gears, levers, pumps, linkages): cylinders and boxes in nested
  Groups where each rotation is a closed form of `t`. Meshing is faked — two
  gears at a fixed ratio never actually collide, so drive both from one ramp.

Text ON surfaces (posters, station labels): draw to an offscreen canvas2d, use
as `CanvasTexture` with `tex.colorSpace = THREE.SRGBColorSpace`. Overlay text
stays in the DOM.

## three r185 API notes (the renames that fail silently)

Pinned at 0.185.1. Several r149-era names were removed outright, and because
`THREE.<removed>` evaluates to `undefined` rather than throwing, the scene keeps
rendering with wrong colors and no error. If output looks subtly off, check
these first:

| removed | use instead |
|---|---|
| `renderer.outputEncoding = THREE.sRGBEncoding` | `renderer.outputColorSpace = THREE.SRGBColorSpace` (also the default) |
| `texture.encoding = THREE.sRGBEncoding` | `texture.colorSpace = THREE.SRGBColorSpace` |
| `THREE.PCFSoftShadowMap` | `THREE.PCFShadowMap` (PCFSoft deprecated; silently downgrades and warns) |
| `renderer.useLegacyLights` | gone — physical lighting is the only mode now |

The directional/hemisphere rig in the template was re-checked under r185 and
still exposes correctly at `exposure: 1.0`; the wash guidance above is unchanged.

## Lighting and color — the wash problem

ACES + hemisphere + directional + point lights WILL wash pale materials to
white. Every first render comes out overexposed. In order of effectiveness:

1. Lower exposure (1.0, not 1.1+) and hemisphere intensity (~0.6).
2. Pick material colors 2 shades darker and more saturated than the target —
   ACES lifts them. A "dark maroon" mouth (0x5e1f28) rendered salmon; 0x24090d
   read as intended. Same for yellows and creams: 0xffd54d not 0xfffbe8.
3. Big pale surfaces (plaster, walls) need speckle/detail dots or they read as
   blank paper at every distance.
4. Transparent glows (MeshBasic + opacity): opacity 0.5+ and saturated colors,
   else they vanish against light backgrounds.

## Spike the hostile beat first

Identify the beat that is both load-bearing and compression-hostile — the one
carrying the explanation *and* changing every pixel every frame (a wobbling
mechanism, a whip pan, a particle burst) — and build that beat alone before
committing to the full table.

A few seconds of work answers two questions at once: does the motion read
without a caption, and does it encode small enough for the delivery target. Fail
the first and the premise is wrong. Fail only the second and the delivery plan
changes, not the film. Discovering either after building six beats is expensive.

This is "iterate by looking" applied to the encode step, which otherwise has no
early check. It mostly stops mattering if the camera is held, since per-frame
change is the entire problem.

## The iteration loop (this is the actual method)

1. `bun run shoot.js scene.html sample <t of each beat>`
2. LOOK at every image. Checklist: Is the beat's subject in the middle third?
   Is anything floating/disconnected? Is detail hidden inside solid geometry?
   Washed out? Does the caption contradict what's on screen?
3. Fix coordinates/colors in source; re-render ONLY the affected samples.
4. Budget 3-4 rounds. Then `bun run build.js all`, and spot-check the encoded mp4 at
   2-3 timestamps INCLUDING mid-transition frames (`ffmpeg -ss <t> -frames:v 1`)
   — transition bugs hide between sampled beats.

## Determinism rules (breaking these breaks video/HTML parity)

- All randomness from the seeded pool `R[]`, indexed, never re-drawn.
- No `Date.now()`, no `performance.now()` outside the preview driver, no state
  accumulated across frames — `seekTo(8)` after `seekTo(2)` must equal
  `seekTo(8)` cold.
- `renderer.setPixelRatio(1)` and `preserveDrawingBuffer: true` — screenshots
  need both.
- Physics is faked with closed forms: a drop is `y0 - k*(t-t0)²`, a wobble is
  `sin(t*ω) * ramp`, a screw-in is position + rotation both driven by the same
  ss() ramp.

### Where you will be tempted to break this

The rule above is easy to keep until the subject *is* a physical process. Any
scene depicting **momentum, decay, accumulation, charge, wear, growth, or
trails** pulls toward simulation, because the natural way to write "a flywheel
coasting down" is to carry velocity from the previous frame. That is state
across frames, and it breaks two things at once: `seekTo` stops being pure, and
the beat stops being independent of the beats before it.

Author the closed form instead. A coast-down is `ω0 * exp(-k*(t-t0))` evaluated
from `t`, never integrated. Accumulation is `count * ramp(t,...)`, not `count++`.
A trail is N samples of the same position function at `t - i*dt`, not a buffer of
past positions.

This is where the physical metaphor pulls against the architecture, and it is
worth knowing *before* writing the beat rather than after `smoke.js` fails the
determinism check. Physical-metaphor scenes are exactly the ones most likely to
reach for a simulator — and exactly the ones where a viewer would notice the
HTML loop and the MP4 disagreeing on the second pass.

## Performance envelope

Depends entirely on whether you have a real GPU, so know which case you're in
before you budget time:

| Environment | 1080p capture | 20s @ 30fps |
|---|---|---|
| Cloud container, SwiftShader software GL | ~1 fps | ~10 min |
| Local machine, hardware GL | ~5 fps (measured: 288 frames in 54s) | ~2 min |

The software-GL number is the one that shapes the design — keep polycounts modest
(spheres at 24×16, one 2048 shadow map, no postprocessing). But do not let it
scare you off a local render that finishes while you read this. Sample frames are
cheap in both cases.

Capture is embarrassingly parallel, and that falls straight out of determinism:
frames are independent, so N headless pages can each shoot 1/N of the range with
zero correctness risk. Not implemented yet — the obvious fix if long pieces start
hurting.

## Delivering inline on GitHub

GitHub renders animated WebP and GIF inline; it does **not** render a
repo-relative mp4 as a player, and it strips `<script>`, so the HTML artifact is
inert on github.com (Pages or a published Artifact both run it fine).

WebP's cost is driven by how much of the frame changes per frame, which makes the
camera decision a file-size decision:

| Scene | 12s template, 960px/24fps | 8s held-camera diagram, 720px/12fps |
|---|---|---|
| mp4 | 0.52 MB | 0.23 MB |
| gif | 12.08 MB | — |
| **webp** | **15.56 MB** | **0.17 MB** |

Same encoder, same pipeline, 90x apart. The template's default sway
(`CONFIG.sway = 0.06`) moves every pixel every frame and defeats inter-frame
compression entirely; the held-camera scene's WebP comes in smaller than its own
mp4. So: hold the camera and `build.js loop` is nearly free, or let the camera
move and ship `build.js poster` — a still linking to the mp4 — instead. Do not
shrink a moving-camera loop until it squeezes under the 10MB cap; you get a
degraded artifact that also shows different content than the video.

`loop` needs `img2webp` (`brew install webp`). Homebrew's ffmpeg ships without
libwebp, so `-c:v libwebp` fails with "Encoder not found".

### Why WebP embeds and mp4 does not

It is a content-type allowlist, not a markdown-syntax problem. Verified by
fetching both from the URL a repo-relative reference resolves to:

| committed file | `raw` Content-Type | result |
|---|---|---|
| `.webp` | `image/webp` | renders inline; `ANIM`/`ANMF` chunks arrive intact |
| `.mp4` | `text/plain; charset=utf-8` + `nosniff` | inert — no browser will treat it as media |

`<video>` being stripped from GFM is a second, independent block on the mp4 path.
Both have to be true for the workaround (an issue/PR attachment URL) to be the
only route to a player.

Two traps that follow:

- **Never track the loop under Git LFS.** `raw` returns the pointer file rather
  than the image and the README shows a broken image. This catches most repos
  that ship demo media.
- **Animated GIF, WebP and APNG are all silent.** There is no format that gives
  inline motion *with audio* in a README. Audio requires the attachment player,
  which means the narration path and the inline path are different artifacts.

APNG is unverified — the issue-composer upload rejects `.apng`, and whether a
committed `.png` carrying APNG frames animates is undocumented. Do not rely on it
without testing.
