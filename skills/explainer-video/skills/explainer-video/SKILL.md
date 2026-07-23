---
name: explainer-video
description: >
  Create animated explainer sequences — 3D, diagrammatic, or cross-section — as
  a self-contained HTML page, an MP4, or an animated WebP/AVIF that plays inline
  in a README. Use when asked to "make a video / animation / walkthrough /
  explainer / animated sequence / motion graphic" of any subject in any field:
  a process, mechanism, system, architecture, organism, market, supply chain,
  building, policy, or document (e.g. "turn docs/data-flywheel.md into a
  30-second video", "animate how a heat pump works", "show how our approval
  process flows"). Two backends — three.js 3D and Canvas2D flat vector — with
  the look set by style packs and bibles. Domain-agnostic: only the geometry and
  caption register change by field, never the pipeline. Deterministic — the film
  is a pure function of time t, so one scene file drives the HTML loop and the
  frame-exact render alike. Do NOT use for editing existing video files, screen
  recordings, or slide decks. Audio narration is designed but not wired
  (references/audio.md).
metadata:
  author: Fred Bliss
  last_verified: 2026-07-21
  review_interval_days: 90
---

# explainer-video

One idea powers everything here: **the entire film is a pure function of `t`**.
No simulation state, no `Math.random()` at runtime, no wall-clock dependence.
Any frame can be rendered independently and identically — which is why a single
scene file serves as both the interactive HTML artifact (a `requestAnimationFrame`
loop mapping wall time onto `seekTo(t)`) and the source for a frame-exact MP4
(headless Chromium stepping `seekTo(t)` frame by frame into ffmpeg).

Parity has two halves, and `t` is only the first. **`t` fixes what happens;
`FRAME` fixes what is on screen.** The render is whatever `FRAME.px` says; the
HTML artifact is whatever shape the reader's window is — so both templates
compose against the declared design frame and *contain* it. A window that is
not the design shape reveals more world on the long axis; it never crops the
composition. Everything measures against `FRAME` and nothing else: the canvas,
the shot ladder, the DOM overlays, and the lints. See "Framing rules" in
`references/method.md`.

## Workflow

### 1. Write the spec first (data before code)

Before touching the template, write the spec as a comment block or scratch file.
Everything downstream is derived from it:

```yaml
topic:      what the sequence explains, one sentence
source:     doc/file it's based on, if any (read it FIRST — facts before film)
audience:   who watches, and what they should understand at the end
duration_s: 15-40 typical; ~3-4s per beat is the pacing that reads well
aspect:     16:9 default — the DESIGN FRAME, declared once in the scene as
            `const FRAME = {aspect: 16/9, px: [1920,1080]}`. This is the single
            source: shoot.js sizes its viewport from FRAME.px, smoke.js measures
            overlay fit against FRAME.aspect, and both templates compose against
            it. Vertical (9:16) and square (1:1) are first-class — set
            `{aspect: 9/16, px: [1080,1920]}` and the whole pipeline follows;
            no flags, no other edit. A window that is not the design shape
            reveals world on the long axis, it never crops the composition.
domain:     what field this is from — it decides the geometry vocabulary, not
            the pipeline (a pump, a protein, a portfolio, a permit process)
style:      palette (3-5 colors), tone (playful | neutral | technical),
            figures if any (procedural, built from primitives)
subtitles:  on | off  — if on, one caption per beat. Budget by TIME, not
            characters: a character count cannot reference beat duration, and
            the same line is comfortable over 4s and impossible over 1.5s.
            Aim under ~27 chars per second of *effective* window (beat duration
            minus capFade, minus any capEnd trim); the lint warns at 30.
            Observed, not derived — 27/sec read fine to one viewer, 37/sec did
            not, and nothing narrows the gap between
beats:      ordered list of {name, dur, caption, what happens on screen}
            — durations, not absolute times: they accumulate
outputs:    html | mp4 | loop | avif | poster (see "Delivery" — decide this HERE, not
            at encode time: it constrains the camera, which constrains the beats)
```

Decide delivery now — it constrains the beats, not just the encode step. Four
peer options, not a ranked list (full comparison in "Delivery"): **HTML** is the
interactive source itself — no encode step, no held-camera constraint (though
it alone renders at the reader's window shape, so check a narrow window before
shipping one — see "Framing rules" in `references/method.md`), but it does
not run on github.com (script tags are stripped) and needs Pages or a published
Artifact. **MP4** is the only format with audio and the only one that gives a
true player, but that requires an issue/PR attachment — it does not render
inline in a README. **WebP** decodes cheaply on any hardware and its inline
rendering is the best-verified case, but its cost is driven by how much of the
frame changes per frame, so it wants a held camera (`CONFIG.sway = 0`, no
swooping keyframes) — a beats-level constraint, not an encode flag. **AVIF** is
far smaller (a moving-camera 12s scene is 0.28 MB vs 15 MB for WebP) and lifts
the held-camera constraint, but an animated AVIF is an AV1 image sequence
decoded in software, so it costs decode CPU and was observed to stutter on weak
machines — a real cost to weigh, and whether it holds on genuinely low-end
hardware is still open. Choose by context: held-camera diagram → WebP or AVIF
either; moving-camera walkthrough shipped inline → AVIF, accepting the
playback-cost question; audio or a guaranteed player → MP4 via attachment; the
scene itself, interactive → HTML via Pages or an Artifact.

Get the beats table agreed with the user (or settled yourself) before building.
Retiming a beat later really is a one-line edit — the `BEATS` array is the only
place timing exists, and captions, camera keyframes and `DURATION` all derive
from it. Re-planning a scene is not.

Beats are **named and contiguous**, and their durations accumulate, so
lengthening one shifts every later beat instead of silently overlapping it.

Three things to settle here, because they are expensive to fix after building:

- **Every beat needs geometry, not just a caption.** A beat whose content is an
  *assertion* ("signal quality is what makes it compound") has no natural
  geometry, and the path of least resistance is to caption it over B-roll. That
  is the specific hazard of building a film from a document: a doc's argument
  does not decompose into visible process the way its mechanism does. Invent
  geometry for the claim or cut the beat.
- **Vary the durations.** Six beats at an identical length with identical framing
  reads as a slideshow however good each shot is.
- **Transit eats the content window.** If a beat spends its first 40% moving the
  camera or the subject into place, a 3.4s beat gives the mechanism under 2s —
  below the pacing floor. Budget the content window, not the beat.

### 2. Scaffold from the template

Two scene templates implement the identical window contract; every tool works
unchanged on both. Pick by the look the spec calls for:

- `scene.template.html` — three.js 3D: rendered depth, lighting, camera in
  space. Needs the vendor step below.
- `scene2d.template.html` — Canvas2D: flat vector illustration, paper-and-ink
  diagrams, motion graphics. Born self-contained — **skip the `bun add three`
  and `vendor` lines entirely** (only `playwright-core` is needed, for the
  recorder). Carries a `STYLE` block split out of `CONFIG`, so the look swaps
  without touching timing or camera.

```bash
# ${CLAUDE_SKILL_DIR} is substituted when this skill loads. If it comes through
# literally (it is NOT a shell variable), use the skill's own directory path.
cp "${CLAUDE_SKILL_DIR}"/templates/{scene.template.html,shoot.js,build.js,smoke.js} .
mv scene.template.html <name>.html
bun add three@0.185.1 playwright-core@1.61.1
bun run build.js vendor            # EMBEDS three into the scene; leaves no .js
```

Either scene is runnable as-is (placeholder scene, 12s) and already contains
the full contract:

- `BEATS` — the single source of timing truth; nothing else holds a timestamp
- `CONFIG` — title, style tokens, seed: everything that is *not* timing
- deterministic kit — seeded PRNG (`R[]` pool), `ss()` smoothstep, `bump()`,
  `lerp()`, plus the easing personalities (`backOut`, `elasticOut`, stop-motion
  `quant`, seeded `noise1`) — identical in every template, part of the future
  shared kernel; **never** call `Math.random()`/`Date.now()` in scene code
- beat addressing — `ramp(t,'beat',a,b)` and `pulse(t,'beat',a,b)` take
  **fractions of the beat**, so an effect keeps its place when you retime.
  `rampS`/`pulseS`/`secAt` take **seconds from the beat start**, for durations
  that must *not* stretch: a 0.25s flash, a 0.06s world cut. Write
  `ramp(t,'lift',0,.6)`, never `ss(t, 9.2, 11.4)`
- cinematography — `SHOTS[]` in cinematographer vocabulary (subject, size,
  angle, lens, cut, focus), solved to the camera per frame; match cuts are a
  checked constraint, racks are two shots differing only in focus. See
  `references/film-language.md`. (3D template; the 2D template keeps its
  simpler `{x,y,zoom}` rail. World-cut flashes still work under any cut.)
- caption + title overlay as DOM (crisp text in screenshots), styled from CONFIG
- driver — `window.seekTo(t)`, `window.DURATION`, `window.stopPlayback()`,
  `window.sceneReady`: the recorder contract; do not rename these. Plus
  `window.BEATS`, which exposes the beats table so tooling can label frames by
  beat and check caption timing without re-parsing the source, and
  `window.FRAME`, the declared design frame — `shoot.js` sizes its viewport from
  `FRAME.px`, so changing it is the only edit needed to ship vertical or square

Replace the placeholder in the two marked sections: `buildWorlds()` (geometry)
and `animate(t)` (per-beat motion, every property a function of `t`).

### 3. Review on three axes (looking is the method)

```bash
bun run build.js sheet <name>.html            # one frame per beat -> .sheet.jpg + .squint.jpg
bun run build.js sheet <name>.html 480 0.95   # every beat at its END — catches effects that park
bun run build.js aspect <name>.html 8.5       # one moment at four window shapes -> .aspect.jpg
bun run shoot.js <name>.html sample 0,3,7,11  # arbitrary timestamps, one PNG each
```

Run the **0.95 end-of-beat sheet as a standing pass, not an option.** The default
0.6 sample cannot show an effect that never finishes or a beat whose target
arrives late — two shipped defects were caught only there: a payload dot that
travelled to a box which did not draw until the following beat, and a connector
routed through the interior of the box it was entering.

`build.js aspect` is the framing counterpart. `smoke.js` can *reject* a scene
whose design frame changes with the window; it cannot *approve* one, and the
render is always the design shape so it can never show you this. Look at the
tiled sheet: every cell must be the same composition.

**Read the generated images with the Read tool — it renders them visually.** A
filename is not a review, and every check below depends on having actually seen
the frames. Composition problems are invisible in code and obvious in pixels.

But stills only cover one of the three ways a film fails:

| Axis | Fails | Instrument |
|---|---|---|
| **Composition** | within a frame — framing, occlusion, exposure, detail hidden inside geometry | `build.js sheet`, then Read the sheet |
| **Continuity** | between frames — pops, stalls, sliding feet, camera velocity breaks | watch the loop; check the three shapes in source. `build.js motion` profiles energy per beat but does **not** detect these |
| **Semantics** | every frame is fine and the film still explains nothing | cover the caption: can you still tell what the beat is about? |

Start with the contact sheet rather than individual samples. One frame per beat
side by side is what reveals a *systematic* error — six shots each framed the
same way wrong look like six small problems viewed one at a time, and like one
bad camera formula when tiled. Generated keyframes (`STAGES.map(...)`) are the
usual source: verify one before you generate the rest. The `.squint.jpg` strip
is the silhouette check — a subject that does not read as a distinct shape at
90px will not read at full size either.

`shoot.js` prints any scene error to stderr — a renamed three API fails quietly
otherwise, and you do not want to discover it after 600 frames.

Budget 3-4 rounds of look-and-edit for composition — that's the axis rounds
converge. Continuity and semantics don't get better from repeating this loop;
they need their own passes, watching the film and covering the caption.
`references/method.md` organizes the recurring failure modes by axis, with the
fix for each — read it before the first render, it saves two rounds. For a
three.js scene, `references/style-3d.md` carries the renderer-specific half
(lighting, camera lenses, the asset cookbook).

### 4. Smoke-test the contract

```bash
bun run smoke.js                              # all scenes, source + bundled
bun run build.js motion <name>.html           # per-beat motion profile + dead air
```

`smoke.js` checks each scene loads with no console errors, exposes the full
contract, renders something, and — the one that matters — that `seekTo(t)` is
deterministic: same `t` twice, byte-identical pixels. A scene that carries state
across frames looks fine in the MP4 (rendered 0→N once) and wrong in the HTML
loop's second pass. Run it before you shoot 600 frames. It also emits advisory
warnings for caption reading speed, captions too wide for the viewport, and
exposure at **both** tails — washed out and crushed are equally common, and
which one you get depends on your palette.

`build.js motion` reports how much each beat moves, and where nothing moves at
all. A beat far below its neighbours is either a deliberate hold or an action
that never fired; a run of near-identical bars is a slideshow.

It deliberately does **not** claim to find pops or stalls. That was tried and
measured against a scene with a known discontinuity: whole-frame statistics put
it at 1.00x its own local baseline — invisible, because the camera and six
mechanisms were already moving — while a stall detector fired at *every* beat
boundary on both a bad scene and a good one, because films are supposed to
settle between beats. A check reporting "0 pops" on a scene that has one is
worse than no check.

`build.js strip <name>.html <t0> <t1>` tiles **consecutive** frames from one
narrow window, which is the only pixel-level look at continuity available to a
reviewer who cannot play the film. Bracketed both ways on a moving-camera scene:
a 1.2-unit whole-body jump is obvious between adjacent cells, a 0.35 rad limb
rotation is invisible. It catches world- and object-level breaks, not limb-level
ones, and does better on a held camera.

So continuity is reviewed by **watching the loop**, by `strip` at a suspect
moment, and by checking three shapes in source, all of which have shipped bugs:

- `ss()` has zero derivative at both ends, so *summing* per-beat ramps brings
  continuous motion to a dead stop at every boundary. Span one ramp across the
  beats instead.
- Any term inside an `if(during(...))` guard that is nonzero at the beat edge
  steps to zero in one frame. Use `ramp`/`pulse`, which return to zero on their
  own, or cover the step with a flash.
- An effect that finishes its ramp **parks** there. Gate it off at the end of
  its beat rather than trusting it to leave.

### 5. Build outputs

```bash
bun run build.js all <name>.html              # bundle -> frames -> mp4
bun run shoot.js <name>.html range 300 360    # re-shoot 2s after an edit, then re-encode
```

`bundle` inlines `three.global.js` into the HTML, so the artifact is a single
file that runs offline and the render never touches the network. Requires
ffmpeg on PATH; `shoot.js` finds Chromium via `CHROMIUM_PATH`, playwright's
cache, or system Chrome (macOS/Linux), in that order — `bunx playwright install
chromium` if none.

### 6. Deliver

```bash
bun run build.js loop   <name>.html 12 720   # <name>.webp — plays inline in a README
bun run build.js avif   <name>.html 12 720   # <name>.avif — same shape as loop, different size/decode tradeoff
bun run build.js poster <name>.html 7.2      # <name>.jpg + the markdown to paste
```

Four peer delivery options — HTML, MP4, WebP, AVIF — not a ranked list. Which
one(s) to ship is a per-project call; choose by what the context needs.

HTML: the scene file itself is a single self-contained artifact that runs
offline (three is embedded at vendor time; `build.js bundle` just asserts it) — the interactive, deterministic source itself, not a
rendering of it. It autoplays and loops. It does **not** run on github.com
(script tags are stripped); serve it via GitHub Pages or publish it as an
Artifact, both of which run it fine. A `build.js deploy` helper to automate
that publish step is a plausible future addition — not built yet.

MP4: encode at the fps you shot (30 default), `crf 17`, `yuv420p`. It is the
only delivery format with audio. A repo-relative mp4 will **not** render as a
player in a README — GitHub serves it from `raw` with a content type no
browser will treat as media, and `<video>` is stripped from GFM on top of
that. To get a real player, drag the file into an issue or PR composer and use
the `github.com/user-attachments/assets/...` URL it returns. The mechanism,
verified by fetching both, is in `references/delivery.md`.

**Do not track the loop under Git LFS.** `raw` returns the LFS pointer file, not
the image, and the README shows a broken image. Most repos with demo videos hit
exactly this.

Inline motion: GitHub renders animated **WebP** and **AVIF**, so `build.js loop`
or `build.js avif` is the output that embeds. They are peer options with
different costs — WebP's is on disk, AVIF's is at playback:

| Scene | Inline artifact | Why |
|---|---|---|
| Held camera (diagram, architecture, data flow) | `loop` (WebP) or `avif` | Either decodes cheaply on a held camera. WebP's inline rendering is the best-verified case; measured on a held-camera diagram: **0.27 MB** for 15.8s at 720px/12fps, against **4.58 MB** for the same pipeline on a moving camera — a 17x swing from camera choice alone. |
| Moving camera you must ship inline | `avif` | A WebP loop here costs megabytes; AVIF stays small. Costs decode CPU at playback (below) — weigh against the audience's hardware. |
| Size or bandwidth matters most | `avif` | ~7-54x smaller than WebP on disk. |
| Authored diagram, motion *is* the explanation | Neither — hand-write an animated SVG | 10-25 KB, inline, no cap. Wrong tool for a rendered 3D scene; right tool for a diagram. |

Measured on the 12s template scene at 960px/24fps, where the default sway moves
every pixel every frame: mp4 0.52 MB, gif 12.08 MB, webp 15.56 MB, **avif 0.28
MB**. On the held-camera example (720px/12fps): **avif 0.029 MB** vs 204 KB WebP.
AVIF wins decisively on size — but an animated AVIF is an AV1 image sequence
decoded in software, so it costs decode CPU at playback and was observed to
stutter (worse in macOS Preview than Chrome). Whether it stays smooth on
genuinely low-end hardware is an open, unconfirmed question — weigh that
against WebP's better-verified inline rendering when choosing. Full tradeoff,
encoder settings, and the inline-rendering evidence chain:
`references/delivery.md`.

Whatever you ship, the scene file stays the single source: never maintain two.

## Style quick-reference

The skill is domain-agnostic: the subject can be a process, a mechanism, an
organism, a market, a supply chain, a codebase, a building, a policy. Only two
things change with domain — the geometry you compose from primitives, and the
register of the captions. The contract, the beats and the pipeline do not.

- **Playful** (a figure carrying the story — onboarding, explainers for
  non-specialists, anything with a mascot or a person to follow): saturated
  pastels, soft shadows, big shapes, a character "presenting". Build the figure
  procedurally from primitives — recipes in `references/style-3d.md`. For the
  cinematic register (cel shading + outlines, analytic IK, rack-focus DoF,
  bloom through the post chain), see `examples/toybot-walk.html` and the
  "cinematic kit" section of `references/style-3d.md`.
- **Technical/diagrammatic** (architecture, data flow, supply chains, org
  processes, circuits, transit): flat planes, labeled boxes, a pulse traveling
  edges; camera glides between stations rather than cutting between worlds. Same
  contract, just calmer keyframes and an orthographic-feeling long lens (fov
  20-25). See `examples/one-scene-every-format.html`.
- **Cross-section** (geology, buildings, machinery, soil, anything with hidden
  internals): a frontal cutaway slab. The one rule is that "inside" is invisible
  — internals must sit proud of the front face. See `references/style-3d.md`.
- Subtitles off: beats still exist — they discipline pacing even uncaptioned.
- **Style packs** (`references/styles/`): swappable `STYLE` blocks plus the
  register rules that make a look coherent — easing temperament, camera
  energy, fill/line vocabulary. Current packs: `paper-cutout` (the 2D
  default, documented as a choice), `blueprint`, `neon-dark`. Swapping the
  block is the whole mechanism; verified to produce a categorically
  different film from the same beats. Worked 2D example in the paper-cutout
  pack: `examples/one-scene-every-format.html`. For the 3D register the pack
  idea grows into **style bibles** (`references/styles/bibles.md`): one
  object constraining palette, lights, post, lens, cut pace, and camera
  energy — `examples/toybot-walk.html` ships the committed control pair
  (`toybox` / `midnight`, one line apart).

## Environment

Pinned: `three@0.185.1`, `playwright-core@1.61.1`, ffmpeg on PATH, bun.

**GL backend defaults to hardware.** `ANGLE_BACKEND=swiftshader` forces software
if you need cross-machine byte-identity; note frames are NOT byte-identical
across backends (PSNR 57-58 dB, antialiased edges and speculars only). Hardware
is ~2.6x faster end to end on a post-chain scene and 55x on the GL draw — and
software silently rendered a Sky/PMREM scene 100% black. Review passes capture
JPEG (~6x faster than PNG over the same readback); masters stay PNG.

Two constraints that dictate the setup — do not "simplify" them away:

- **three is vendored locally and EMBEDDED in the scene. Never CDN-loaded, never
  a sibling `.js`.** Three constraints force this and none of them have relaxed:
  a CDN means the render touches the network and the artifact stops working
  offline; three dropped its UMD build after 0.160, so a CDN copy can no longer
  be loaded from a classic `<script>` at all; and module imports are CORS-blocked
  over `file://`, which is exactly how these artifacts are opened. So
  `build.js vendor` builds three as an **IIFE** (a plain ESM bundle leaks its
  top-level identifiers into global scope and collides with scene variables —
  a minified `MW` shadowed one and broke an example) and splices it straight
  into the HTML, deleting the intermediate file.

  **One scene = one file.** There is no `.bundled.html` and no `three.global.js`
  to ship alongside. This is enforced, not merely advised: `ensureVendor` runs
  before every command that opens a scene, so a scene cannot reach the renderer
  — or a reviewer, or a commit — still pointing at a library that is not inside
  it, and `smoke.js` fails any scene that is not self-contained. The rule exists
  because the previous arrangement made bundling a manual last step, and a
  committed 3D example duly shipped as un-bundled source with a dangling
  reference: it rendered nothing when opened. Cost is ~0.73 MB per 3D scene,
  paid once, and worth it — the file is the artifact.
- **The scene stays a classic `<script>`, never `type="module"`.** Chrome
  CORS-blocks ES module imports over `file://`, and opening the HTML straight
  from disk is the whole point of the artifact.

## Files

- `templates/scene.template.html` — the 3D scaffold (three.js)
- `templates/scene2d.template.html` — the 2D scaffold (Canvas2D, self-contained,
  `STYLE` split from `CONFIG`)
- `templates/shoot.js` / `templates/build.js` — recorder + pipeline, incl. `sheet`
  and `motion` review passes (copy beside the scene)
- `templates/smoke.js` — contract + determinism check, plus caption and exposure
  lints (run before a full shoot)
- `references/instruments.md` — what every check can and cannot see, with its
  measured bracket (read before trusting a green result)
- `references/method.md` — the universal method: failure axes, beats and
  controls discipline, continuity/semantics review, determinism rules
  (L3: read when building, any backend)
- `references/styles/` — style packs: swappable `STYLE` blocks + register
  rules (read the chosen pack at art-direction time)
- `references/film-language.md` — the shot vocabulary: sizes, cuts, match
  constraint, focus, camera energy (read when planning shots)
- `references/style-3d.md` — the three.js half: lighting, camera rail,
  procedural-asset cookbook, r185 notes (L3: read when building a 3D scene)
- `references/delivery.md` — GitHub delivery forensics: format tradeoffs,
  encoder settings, the content-type evidence chain (read at ship time)
- `references/audio.md` — narration/music extension design (not yet wired)
