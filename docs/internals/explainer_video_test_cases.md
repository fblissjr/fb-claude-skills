last updated: 2026-07-22

# explainer-video: test cases

A diverse test suite for the `explainer-video` plugin at **0.15.0** — the state
after the back-to-back Phase 0–4 run (two backends, shots-as-data, style
bibles). Companion to
[explainer_video_generalization_plan.md](explainer_video_generalization_plan.md)
(the arc) and [explainer_video_roadmap.md](explainer_video_roadmap.md) (the
per-item ledger). This file is the **exercise sheet**: films to build that span
the capability surface and aim at the plan's own stated opens.

Not plugin content (`docs/internals/`), so no version cascade — see the plan's
cross-cutting rule 5.

## How to read a case

Every case is a **hypothesis**, not just a prompt. That is the repo's
"build the control" discipline (`references/method.md`) applied to testing: a
case earns its place only if it can come back either *worked* or *didn't*, and
the prediction is written down before the render so the result can refute it.
Each line carries: backend + register/style + a delivery target, **what it
probes**, and **the hypothesis** (what should work, and what to watch).

Fill in an `Outcome:` under a case after building it. An outcome that matches
the hypothesis is a confirmation; one that doesn't is the valuable kind — it
goes back to `method.md` or the roadmap ledger as a bracket or a gotcha.

Render cost is real: minutes per contact sheet on software GL, per the plan's
postmortem, and the continuity axis's strongest instrument (watching the loop
at speed) needs a human. Every continuity verdict below carries the
"owner hasn't watched it yet" asterisk until someone does.

---

## Coverage map — cases against the plan's open questions

The highest-value cases are the ones that aim at something the plan admits is
unproven. Mapping is explicit so the suite can't drift into only testing the
happy path:

| Open question (from the plan / postmortem) | Case(s) |
|---|---|
| Every committed film is self-referential; external-subject semantics never stressed ("the real Phase 6") | A3, A5 |
| Watch-the-loop is human-only; outstanding on all three committed films | C3, D1, and every case's continuity verdict |
| AVIF inline smoothness on low-end hardware unconfirmed | B2, C4 |
| The 2D shot-solver is unbuilt (earn-in item) | D2 |
| IBL / procedural Sky / PMREM unverified on hardware GL (blacks out SwiftShader) | C5 |
| Caption bracket thin — 37–50 CPS band unmapped, ledger wants the next point | D3 |
| Convention pre-flight: new-craft vocabulary shipped wrong three times | C1, C2, D6 |
| Determinism pull on physical-process scenes (momentum/decay/trails) | D1, B3 |
| Assertion-shaped beats (film-from-a-document hazard) | A3, A5 |
| Film language must read at explainer scale, floor and ceiling | D4, D5 |
| Cinematography solver exists in two copies with no drift guard | (maintenance, not a film — see note at end) |

---

## Track A — Domain-agnostic explainers

The core claim under test: only the geometry and the caption register change
with domain; the contract, beats, and pipeline do not.

### A1 · How a heat pump works
3D cross-section · technical · WebP.
**Probes:** the one cross-section rule (internals must sit *proud of* the front
face, never hidden inside the slab) + closed-form physics of a refrigeration
cycle (compression, phase change, expansion — all pure functions of `t`).
**Hypothesis:** works; the trap is burying the compressor inside solid geometry
where the squint strip can't see it. A held camera makes WebP the right
inline format.
*Outcome:* —

### A2 · Our approval process
2D diagrammatic · blueprint pack · WebP.
**Probes:** the best-verified happy path — held camera, a pulse traveling
labeled edges between stations. `examples/skill-retrieval.html` is the
reference shape.
**Hypothesis:** the cleanest win in the suite; serves as the baseline the
harder cases are judged against. If this needs more than 2 composition rounds,
something regressed.

**Outcome (2026-07-22): PASS — but it took 3 composition rounds, not the
predicted ≤2, and it produced the run's best instrument finding.**
Film: `internal/video-tests/a2-approval-flow.html` — a request travelling from
filing to recorded decision. 5 beats / 15.8s, blueprint pack, locked camera
(`sway:0`, KEYS pinned to zoom 1). Built by splicing the 2D template so the
KERNEL block stays byte-identical; `smoke.js` kernel-parity check confirms it.
Semantics passes: filed → routed with one branch **visibly not taken** →
checked → recorded. Keeping the untaken `AUTO-OK` branch drawn but faint is
what makes a decision legible; a single drawn path is just a pipe.

**Two defects, both found only by the end-of-beat sheet (`sheet 480 0.95`),
both invisible at the default 0.6 sample:**
1. The payload dot **arrived at empty space** — the connector and dot completed
   during `route`, but the APPROVER box did not draw until the following beat.
   Fixed by drawing the box during route's tail, as the branch is chosen.
2. The ledger connector **descended through the box interior** (vertical
   segment at x=52 inside a box spanning x 46–70) instead of approaching from
   outside. Fixed by moving the descent clear of the left edge.

This is a direct argument for the 0.95 pass as a standing step, not an option:
both defects are *timing/geometry* errors that a mid-beat sample cannot show.

**INSTRUMENT FINDING — `build.js motion`'s dead-air detector is blind to
low-contrast linework, and its threshold is global rather than per-beat.**
The submit beat drew three evidence rules sequentially across 3.84–5.54s and
`motion` still reported `DEAD AIR t=3.92–5.17` — the identical window before
and after the rules were converted from an alpha fade to a sequential
`drawOn`. Control run (same timing, same geometry, **only** stroke weight
×3.7 and colour changed from `faint` to an accent):

| | submit bar | dead-air flags |
|---|---|---|
| faint thin rules | 0.05 | `submit 3.92–5.17` |
| bright thick rules | 0.07 | **submit clean**; three NEW flags in `review` and `record` |

Two conclusions, both bracketed by that control:
- The detector measures **pixel contrast, not activity**. Thin, low-alpha
  linework animates without registering — and the blueprint pack (fine lines,
  faint construction grid) is precisely the register that trips it.
- The threshold is **relative to a global median**, so making one beat busier
  pushes quieter beats below it and *manufactures* dead-air flags elsewhere.
  A dead-air report is therefore not a stable per-beat property; it is a
  statement about one beat relative to the rest of that particular cut.

Same family as the documented pop/stall negative result: whole-frame
statistics see *that* a film moves, not *what* moved. Recorded, threshold
deliberately not touched — the submit beat genuinely animates and the flag is
a false positive for this register.

**Delivery — the held-camera case, and the bracket it completes.** Same
encoder settings, 720px @ 12fps, against D4's moving camera:

| film | camera | WebP | AVIF | AVIF advantage |
|---|---|---|---|---|
| A2 approval flow | **held** | **0.27 MB** | 0.051 MB | 5.3x |
| D4 noise cancelling | **moving** | **4.58 MB** | 0.195 MB | 23.5x |

A 17x swing in WebP cost from camera choice alone, on the same pipeline. This
is a self-generated confirmation of the delivery table's central claim: WebP is
entirely shippable on a held camera and ruinous on a moving one, and AVIF's
advantage grows with how much of the frame changes per frame.

### A3 · A real external document → 30s film
3D or 2D · register per doc · AVIF.
**Probes:** THE semantics stress the plan calls "the real Phase 6" — a film
about a subject the plugin did not write about itself. Deliberately choose a
doc that is *argument*, not just mechanism (`VISION.md` is a strong candidate),
to trigger the assertion-shaped-beat hazard on purpose.
**Hypothesis:** composition converges normally; 2–3 beats come back as
B-roll-with-a-thesis and force the "invent geometry for the claim, or cut the
beat" decision from `method.md` Axis 3. **The single highest-value case — this
exact stress has never been run.**
*Outcome:* —

### A4 · Photosynthesis (inside a chloroplast)
3D playful · AVIF.
**Probes:** geometry vocabulary for an *organism* — a domain far from tech —
and a conversion (light + water + CO₂ → sugar) that is a claim, not a native
motion.
**Hypothesis:** works, but leans hard on inventing geometry for a conversion;
a good check that "playful" register survives a non-character subject.
*Outcome:* —

### A5 · A market flywheel / supply chain
2D paper-cutout · WebP.
**Probes:** inventing visible geometry for a *non-physical economic* claim —
the flywheel hazard (`method.md`: "a beat that asserts has no geometry")
generalized past the plugin's own flywheel film.
**Hypothesis:** the hardest semantics case that isn't a character film; expect
at least one beat to have no honest geometry and need cutting.
*Outcome:* —

---

## Track B — Fun / creative / non-explainer

The register the skill documents least. These test whether the semantics axis
and the "every beat needs geometry, not a caption" discipline even apply when
the goal is delight rather than explanation.

### B1 · Toybot victory dance
3D cinematic cel · **no captions** · AVIF.
**Probes:** reuses the committed IK asset in `examples/toybot-walk.html`
(cheap); with the caption-cover test removed, does the review method still
function? Tests character-as-star and a bible for mood.
**Hypothesis:** fast and fun; quietly tests whether "semantics" means anything
without a caption to cover. Best first case — highest delight per render minute.
*Outcome:* —

### B2 · Generative loop — particle / flow field
3D neon-dark (or 2D) · **no subject** · AVIF.
**Probes:** `InstancedMesh` field + seeded `noise1`, pure vibe with nothing to
explain, and AVIF on a busy every-pixel-moving frame — the compression-hostile
delivery case and the unconfirmed-low-end-smoothness question at once.
**Hypothesis:** AVIF wins decisively on size (the plan's 0.28 MB vs 15 MB WebP
measurement lives here); the open risk is playback smoothness, which needs a
human on real hardware.
*Outcome:* —

### B3 · Rube Goldberg chain reaction
3D · cross-section-ish · MP4/AVIF.
**Probes:** causality-must-read *for fun* — each step drives the next, which is
the phase/derivation rule from `method.md` Axis 3 applied to a delight subject
— plus a compression-hostile spike and several chained closed-form physics
events.
**Hypothesis:** genuinely delightful *and* a real stress test: if step N reads
as "moving near step N+1" rather than "driving it," it fails exactly the way an
explainer's causality beat fails. Spike the busiest link first.
*Outcome:* —

### B4 · Kinetic-typography quote loop
2D neon-dark · WebP.
**Probes:** text *is* the hero — deliberately inverts "geometry not caption."
Tests whether the overlay/caption system can carry a beat when it is supposed
to, and 2D motion-graphics timing.
**Hypothesis:** exposes the limits of the caption layer as a primary subject;
likely wants the text drawn into the canvas, not the DOM overlay.
*Outcome:* —

### B5 · Animated greeting / seasonal card
2D or 3D playful · warm · WebP.
**Probes:** tone as a register (warmth), a short shareable loop for a README or
a message.
**Hypothesis:** trivial mechanically; a real test of whether "warm/playful"
reads as *warmth* and not just saturated color. Good WebP-shareable exemplar.
*Outcome:* —

### B6 · One-joke visual gag
3D or 2D · e.g. "merge conflict as two trains," "the spinner that finally
finishes," "CI red → green."
**Probes:** comedic timing, anticipation, whip/match cut as a *punchline*.
**Hypothesis:** the whole film lives in beat-duration variation and one
well-placed cut — a sharp test of the pacing floor at the short end and of
timing as authorship.
*Outcome:* —

---

## Track C — Cinematic & film-language stress (3D shots-as-data)

Exercises the Phase 3–4 layer: the framing solver, cuts, focus, camera energy,
and bibles. All 3D template (the 2D backend has no solver — see D2).

### C1 · Match-cut short
3D · author two shots that must rhyme, then deliberately break one.
**Probes:** does the match-cut constraint **throw at load** when the entry
framing vocabulary (size/angle/elev/fov/anchor) differs, and hold silently when
it matches? This is the compiler-verified cohesion device.
**Hypothesis:** the headline film-language feature; confirming the throw fires
(the negative control) matters as much as confirming a good match passes.

**Outcome (2026-07-22): PASS in both directions — the constraint genuinely
enforces.** Ridden on D4 rather than given its own film, and it needed **no
rendering at all**: the check runs at load, so both directions cost one page
open each. Two variants of the same scene, differing only in shot 3:

| variant | shot 3 framing vs shot 2 | result |
|---|---|---|
| `c1-matchcut-bad` | `match:true`, angle 4 vs -17, elev 26 vs 12 | **throws** — `match cut into SHOTS[2] breaks framing: size/angle/elev/fov must equal the previous shot` |
| `c1-matchcut-good` | `match:true`, framing vocabulary identical | loads and shoots clean |

Critically, the failure is **loud, not advisory** — verified by exit code, not
by reading the message: `shoot.js` exits **1**, and `smoke.js` exits **1** with
`FAIL` on *both* source and bundled. A broken match cut cannot reach a render.

Worth noting for authors: the constraint compares size/angle/elev/fov/anchor
and deliberately **not** `subject` — so a match cut may change what is on
screen while holding the framing, which is exactly the real editorial device.

### C2 · Rack-focus reveal
3D · two subjects, focus-only shot change joined by `blend`.
**Probes:** BokehPass DoF + rack-as-two-shots (`references/film-language.md`).
**Hypothesis:** works; watch for racking onto a subject that is off-frame at
the moment of the rack — a recorded past bug and a convention-pre-flight case
(racks need both subjects visible).
*Outcome:* —

### C3 · Handheld documentary energy, moving subject
3D · `energy: handheld`.
**Probes:** the watch-the-loop human-only gap directly — does handheld noise
read as *intent* or as *pops*, and can `build.js strip` even resolve the
difference at limb scale (it can't below ~0.35 rad)?
**Hypothesis:** this is where the continuity axis is genuinely blind; the
verdict *requires* a human viewing and should be logged as such.
*Outcome:* —

### C4 · Whip-pan transition
3D · accelerate, cut mid-smear.
**Probes:** the spike-the-hostile-beat rule + AVIF-vs-WebP on a full-frame
smear.
**Hypothesis:** reads well, encodes badly on WebP — a clean, concrete argument
for AVIF on a moving camera. Build and encode this beat alone first.
*Outcome:* —

### C5 · IBL open-sky hero shot
3D · procedural Sky + PMREM · spiked on a *matching* composition (open sky).
**Probes:** the unverified-on-hardware-GL IBL recipe, tested on the
composition its premise needs (per the postmortem: spike art-direction-
conditional features on matching compositions, not on whatever film is
standing).
**Hypothesis:** blacks out on software GL (SwiftShader + PMREM `fromScene`);
**only meaningful on hardware GL.** A scoping flag on the render environment,
not a failure of the scene.
*Outcome:* —

---

## Track D — Deliberate edge / negative probes

The point of these is to break something, feel an unbuilt gap, or extend a thin
bracket — not to ship a pretty film.

### D1 · A scene that *wants* to be a simulation
3D or 2D · flywheel coast-down, particle trails, or accumulating charge.
**Probes:** forces the closed-form-vs-simulation fork (`method.md`,
"Where you will be tempted to break this"). Does `smoke.js`'s determinism
byte-check catch a shared-material mutation or a `count++` slip — the HTML
second-pass desync that renders fine in the MP4?
**Hypothesis:** the sharpest test of the prime directive; a scene actively
pulling toward carried state. Expect to hand-author `ω0·exp(-k·(t-t0))` where
the instinct is to integrate velocity.
*Outcome:* —

### D2 · A 2D film that wants shot vocabulary
2D · a piece begging for CU/MS/rack (a face, a reveal, a push-in).
**Probes:** the known-unbuilt 2D shot-solver (`film-language.md`,
"Deliberately not built yet").
**Hypothesis:** you feel the gap immediately — the `{x,y,zoom}` rail can't
express a size ladder or a rack. The deliverable is an honest earn-in ledger
entry ("a 2D film finally wanted shots"), not a finished film.
*Outcome:* —

### D3 · Caption-density torture test
Either backend · author a beat squarely in the unmapped **37–50 CPS** band.
**Probes:** the thin caption bracket (`method.md`: 27 comfortable, 37
unreadable, 50 "serviceable but imperfect") that the ledger explicitly wants
the next data point on.
**Hypothesis:** produces a real observation either way; watch it and record
which side of the line it fell on. Pure ledger value.
*Outcome:* —

### D4 · Sub-10s, 3-beat micro-explainer
Either backend · fastest possible full pipeline.
**Probes:** the "film language reads at explainer scale" claim at the floor
(plan cross-cutting rule 6); also the fastest end-to-end smoke of the whole
toolchain.
**Hypothesis:** works, and is the cheapest way to shake out a broken install or
a toolchain regression before committing render time to a big case.

**Outcome (2026-07-22): PASS on all three axes — hypothesis confirmed, plus
one new finding worth promoting to `film-language.md`.**
Film: `internal/video-tests/d4-noise-cancelling.html` — how noise-cancelling
headphones work. 3 beats / 9.4s / 3 shots, no title card. The anti-wave is
computed as the negation of the source wave's own expression and the sum trace
is `a+b`, so causality is structural rather than co-incidental
(`method.md` Axis 3). Composition converged in **3 rounds**, inside budget.

- **Composition:** pass after 3 rounds (see finding below).
- **Continuity:** `smoke.js` determinism green source+bundled; `motion` reports
  0 dead-air and good variety (1.66 / 10.54 / 9.67 — beat 1 is legitimately
  quieter as an establishing shot, not a failed action); `strip` across the
  0.8s blend into the payoff shows smooth per-cell motion, no pop.
- **Semantics:** passes the cover-the-caption test on all three beats — a wave
  arriving at an earbud, a mirrored wave, two waves summing to a flat line.
- **The floor claim holds.** Shot vocabulary reads fine at 3 beats: WS
  establishing → WS detail on a sub-subject → elevated WS payoff.

**NEW FINDING — the size ladder is height-calibrated and cannot frame a wide
subject.** `SIZES.f` is "subject height ÷ frame height", so the solver derives
distance from height alone and never consults width. On this bench (12.8 wide
× 2.6 tall, `h:4.3`, 40° lens) the frame widths are:

| size | horizontal extent | fits a 13-wide subject? |
|---|---|---|
| EWS | 44.4 | yes (too wide to be useful) |
| WS | 17.8 | yes |
| FS | 9.4 | **no — crops** |
| MS | 5.6 | no |
| MCU | 3.7 | no |

Anything wider than ~1.8x its declared height crops at FS and tighter, so a
wide subject can only use EWS/WS — which collapses the shot variety the ladder
exists to provide. **Inflating `h` is the wrong fix** (it pulls back but leaves
the subject small in a tall empty frame, which was this film's first-round
defect). The right fix is the one the craft already has: push in on a
**narrower named sub-subject**. Here beat 2 reframed from `field` onto `cross`
(the region where the two waves meet, by the earbud) — better cinema *and*
uncropped, because the detail beat is genuinely about that region.
This is a second instance of the postmortem's convention-pre-flight pattern:
the ladder silently assumes an upright subject, the way the first cut of the
table silently assumed MS meant full-shot framing.

**Delivery data point (moving camera, 720px @ 12fps):** AVIF **0.195 MB** vs
WebP **4.577 MB** — **23.5x**. Third measurement of the moving-camera case and
consistent with the existing two (55x on the template scene, 7x held-camera);
the ratio scales with how much of the frame changes per frame.

**Lint observation:** the exposure lint reports `0.0 points` dynamic range on
this scene at both tails, on a film that is correctly exposed by eye. Sparse
bright subjects on a near-black field put *both* p05 and p95 in the background,
so the percentile spread collapses. Same family as the hazard the `neon-dark`
pack predicted for the crush lint — a dark register trips the lint by design.
Judge by looking; do not chase it by moving the threshold.

### D5 · 40s, 8–10 beats, multiple world cuts
3D · dive-in / pull-out structure, two or more worlds under flashes.
**Probes:** the top of the duration range, multi-world hard cuts
(`method.md` Axis 2: "hide the cut under a flash, completely"), pacing
discipline at length.
**Hypothesis:** pacing is the risk — uniform beat durations and repeated
framing read as a slideshow more visibly the longer the film runs. Tests the
holding-keyframe-before-a-cut rule that shipped a re-render once.
*Outcome:* —

### D6 · New-craft-vocabulary calibration
3D · first use of a lens set / shot-size framing the author hasn't calibrated
against real film craft.
**Probes:** the convention-pre-flight rule (postmortem: three same-shaped bugs
where invented vocabulary — shot sizes, ink polarity, gait anchoring — shipped
without being checked against the craft it mirrored).
**Hypothesis:** if the table is checked against actual cinematographic
definitions before the first render, the pattern doesn't recur; if it isn't,
expect the first-cut framing to be wrong in the same quiet way.
*Outcome:* —

---

## Test rounds

Cases are grouped into **rounds**, not a flat ranking. A round is a batch whose
results are read *together*, so each round must be internally diverse — a round
that is all-2D, all-explainer, or all-happy-path tells you about one axis and
lets the others hide.

### The diversity rule

Every round spans these seven dimensions. Check a proposed round against the
list before running it; a deliberate skew is fine, an accidental one is not, so
**name the skew and its rationale** when a round doesn't balance.

| Dimension | Values to spread across |
|---|---|
| Backend | 3D three.js / 2D Canvas2D |
| Style register | cel-cinematic / blueprint / paper-cutout / neon-dark / cross-section |
| Posture | explainer / fun |
| Caption | captioned / uncaptioned |
| Camera | held / moving |
| Delivery | WebP / AVIF / MP4 / HTML |
| Probe type | capability (should work) / negative-or-gap (should break or reveal) |

**Camera** carries more weight than it looks: held-vs-moving is the axis the
whole delivery tradeoff is built on (`delivery.md`), so a round with no held
camera can't say anything about WebP and a round with no moving camera can't
say anything about AVIF.

### Film-level cases vs riders

Not every case needs its own scene file, and treating them as if they did was
the first draft's mistake. Three classes:

- **Film-level** — needs its own scene and full render: A1–A5, B1–B6, D1, D2,
  D4, D5.
- **Shot-level riders** — fold into an existing 3D film as extra shots, costing
  a re-render and no new scene: **C1** (match cut), **C2** (rack focus),
  **C4** (whip pan). All three are `SHOTS[]` entries, which is exactly what
  shots-as-data bought.
- **One-line riders** — nearly free. **C3** (camera energy) is a single
  `CONFIG.energy` swap plus a re-render, the same shape as the bible control
  pair. **D3** (caption density) is one beat's caption authored into the target
  band on whatever film is standing.
- **Not a film** — **D6** (convention pre-flight) is a discipline applied to
  whichever case introduces new craft vocabulary; **C5** (IBL) is gated on the
  render environment, not on scheduling.

Attach **D3 to a different film in each round**: three observations in the
unmapped 37–50 CPS band builds a bracket, where one observation only builds an
anecdote.

---

### Round 0 · Environment check (do this first — minutes, not hours)

**Newly relevant: the whole generalization run executed on a software-GL
container (SwiftShader).** The postmortem's standing recommendation is to
"book a hardware-GL session" to close three opens at once. Confirm what this
machine actually gives Chromium before budgeting any render time, because the
answer changes everything downstream:

- If **hardware GL**: render cost drops ~5–10x, which re-prices every round
  below; **C5 (IBL/PMREM) becomes testable** for the first time; parallel
  capture can be re-measured where it was predicted to win (roadmap item 5's
  open); and the quality-tier question can be honestly re-judged.
- If **software GL**: C5 stays blocked (PMREM `fromScene` blacks out on
  SwiftShader — a bisected negative result), and the rounds stay expensive.

This is the cheapest high-leverage step in the suite. Record the answer here.

**Outcome (2026-07-22, Apple M2 Ultra / 24 cores, Chrome 1223, bun 1.3.14,
ffmpeg 8.1.2): RUN — and it closed three opens at once, one of them by
refutation.**

**Finding 1 — the recorder pins software GL regardless of hardware.**
`shoot.js:177` (and `smoke.js:362`) hardcode
`--use-angle=swiftshader --enable-unsafe-swiftshader`. So "book a hardware-GL
session" was never only about the machine — the tool opts out. Probed three
flag sets on this box:

| flags | renderer | maxTex |
|---|---|---|
| as shipped | ANGLE SwiftShader (software, Vulkan/LLVM) | 8192 |
| `--use-angle=metal` | **ANGLE Metal, Apple M2 Ultra** | 16384 |
| default (no angle flag) | ANGLE Metal, Apple M2 Ultra | 16384 |

**Finding 2 — GL matters enormously, but only on a post-chain scene.** Timing
120 frames at 1920×1080, `seekTo` alone vs `seekTo`+screenshot:

| | template (no post) | toybot (cel + outlines + IK + bloom + DoF) |
|---|---|---|
| `seekTo` only, Metal | 0.4 ms/frame | 3.3 ms/frame |
| `seekTo` only, SwiftShader | 0.4 ms/frame | **182.2 ms/frame** |
| draw speedup from hardware GL | ~1x | **55x** |
| end-to-end PNG, Metal | 164.6 ms/frame | 187.7 ms/frame |
| end-to-end PNG, SwiftShader | 232.8 ms/frame | 489.2 ms/frame |
| end-to-end speedup | 1.4x | **2.6x** |

The SwiftShader column is what validates the control: 182 ms/frame on the
same `seekTo`-only loop proves the timing path really does capture
rasterization, so the template's 0.4 ms is a genuinely cheap draw and not an
async-submit artifact. **Hardware GL is worth 2.6x end-to-end and 55x on the
draw for post-chain scenes, and ~nothing for a flat one.**

**Finding 3 — PNG screenshot is a second, unrecognized bottleneck, and it
dominates as soon as GL is fast.** Same readback path, encode swapped:

| scene / renderer | PNG | JPEG q90 | ratio |
|---|---|---|---|
| template, Metal | 164.6 ms | 29.1 ms | **5.7x** |
| toybot, Metal | 187.7 ms | 28.8 ms | **6.5x** |
| toybot, SwiftShader | 489.2 ms | 269.9 ms | 1.8x |

So there are **two independent bottlenecks** — software rasterization of a
post chain, and PNG encode/CDP transfer — and fixing either alone leaves the
other. On hardware GL, ~95% of capture time is the screenshot, not the film.

*Actionable:* the **review** passes (`sheet`, `strip`, samples) already emit
`.jpg` and could shoot JPEG directly for ~6x, while final MP4/WebP/AVIF
renders keep lossless PNG. Not yet implemented — logged as a roadmap
candidate, not a change made under a test run.

**Finding 4 — parallel capture is refuted on the exact hardware the roadmap
predicted would rescue it.** Roadmap item 5 left the open as "a many-core box
or hardware GL, where one page cannot saturate the machine — plausible,
unmeasured." This is that box (24 cores + Metal), 288 frames @ 24fps:

| workers | Metal | SwiftShader |
|---|---|---|
| 1 | 54.7s | 64.5s |
| 4 | 49.1s (1.11x) | 61.6s (1.05x) |
| 8 | 48.8s (1.12x) | 63.1s (1.02x) |

**~1.1x, not the predicted win.** The premise was wrong at the root: capture
was never GL-parallelism-bound, it is screenshot-bound, and PNG encode
serializes through the browser process. Item 5's remaining open can be closed
as *measured negative on its own predicted best case*.

**Finding 5 — cross-renderer frames are NOT byte-identical, which limits a
checkpoint instrument.** Metal vs SwiftShader on the same scene: **0 of 288
frames identical**, PSNR 57–58 dB (below `method.md`'s 70 dB
imperceptible bar), with differences confined to anti-aliased edges and
specular highlights — invisible at 1x even amplified 20x. Each renderer is
*self*-consistent: `smoke.js`'s determinism byte-check passes under Metal
(4/4 scenes). **Implication for the phase-exit checkpoint:** "re-shoot the
committed examples and compare byte-identical" only holds *within* one
renderer. Switching GL backends invalidates byte-comparison as a regression
instrument and forces the PSNR>70 fallback.

---

### Round 1 · Breadth and baselines

**Purpose:** prove both backends, four distinct style registers, and both
inline formats work end to end — and produce the baselines every later round is
judged against. All cases cheap by design.

| # | Case | Backend | Register | Posture | Camera | Delivery | Probe |
|---|---|---|---|---|---|---|---|
| 1 | **D4** micro-explainer (3 beats, <10s) | 3D | cel | explainer | moving | AVIF | capability + toolchain smoke |
| 2 | **A2** approval flow | 2D | blueprint | explainer | held | WebP | capability (baseline) |
| 3 | **B1** toybot dance | 3D | toybox cel | **fun** | moving | AVIF | **uncaptioned** review |
| 4 | **B5** greeting card | 2D | paper-cutout | **fun** | held | WebP | warmth as register |

**Riders:** C1 (match cut) on B1 — and deliberately break it once, so the
load-time throw is verified as a negative control, not assumed.

**Run D4 first.** It is the fastest complete pass through the toolchain and
will surface a broken install or a regression before you spend real render time
on anything else.

Diversity: 2/2 backend, 4 distinct registers, 2 explainer / 2 fun, 2 held /
2 moving, 2 WebP / 2 AVIF, one negative control. Balanced with no skew.

---

### Round 2 · The hard axes

**Purpose:** attack the three things that rounds of *looking* never converge —
semantics, causality, continuity. These are the cases most likely to produce
real ledger entries.

| # | Case | Backend | Register | Posture | Camera | Delivery | Probe |
|---|---|---|---|---|---|---|---|
| 1 | **A3** external doc → film | 3D | per doc | explainer | moving | AVIF | **semantics** (the "Phase 6" stress) |
| 2 | **B3** Rube Goldberg | 3D | cross-section-ish | **fun** | moving | MP4/AVIF | **causality** + compression-hostile |
| 3 | **D1** simulation-shaped scene | 2D | neon-dark | fun/abstract | moving | AVIF | **determinism** negative probe |
| 4 | **C3** handheld energy swap | 3D | (on B1) | — | moving | — | **continuity** / watch-the-loop gap |

**Riders:** C2 (rack focus) on A3 — a reveal shot is natural in an explainer
and gives the rack two genuinely visible subjects, which is the calibration the
first cut got wrong.

**Named skew:** this round is 3D-heavy and entirely moving-camera. That is
deliberate, not accidental — causality, camera energy, and the shot layer all
live in the 3D backend, and every hard axis here involves motion. D1 carries
the 2D representation, and picking neon-dark for it is not arbitrary: the
deterministic **trail idiom is that pack's signature move**, which is exactly
the shape that tempts you into carrying state across frames.

**Sequencing within the round:** spike B3's busiest link before building the
rest of its chain (the hostile-beat rule). C3 is last and nearly free — it
rides on B1 from Round 1.

---

### Round 3 · Ceilings, gaps, and the unbuilt

**Purpose:** find the limits and log earn-in items. Expect at least one case
here to produce a roadmap entry rather than a film.

| # | Case | Backend | Register | Posture | Camera | Delivery | Probe |
|---|---|---|---|---|---|---|---|
| 1 | **D2** a 2D film that wants shots | 2D | any | explainer | wants moving | — | **known-unbuilt gap** |
| 2 | **D5** 40s, 8–10 beats, multi-world | 3D | cinematic | explainer | moving | MP4/AVIF | **ceiling** + world cuts |
| 3 | **A1** heat pump | 3D | **cross-section** | explainer | held | WebP | the third documented register |
| 4 | **B2** generative particle/flow loop | 2D or 3D | neon-dark | **fun** | moving | AVIF | **no subject** + AVIF playback |

**Riders:** C4 (whip pan) on D5 — a hostile transition belongs in the long film
where there is room for it.

**A1 earns its slot** because cross-section is one of the three registers
SKILL.md names and no earlier round touches it; it also has a rule of its own
(internals must sit proud of the front face) that nothing else tests.

**D2's deliverable is a ledger entry, not a film.** If the `{x,y,zoom}` rail
turns out to be enough, that is the finding — and it means the 2D solver stays
correctly unbuilt.

---

### Reserve bench

Pull these when a round has capacity, or when a specific question comes up.
Deliberately not scheduled — the suite should not become a completionist
checklist:

- **A4** photosynthesis — organism geometry, if a biology subject is wanted.
- **A5** market flywheel — the hardest non-character semantics case; overlaps
  A3's probe, so it is redundant *unless* A3 comes back clean.
- **B4** kinetic typography — text-as-hero; pull if B5 suggests the overlay
  layer is a limit.
- **B6** one-joke gag — timing as authorship; cheapest possible fun case.
- **C5** IBL open-sky — **unblocked only if Round 0 reports hardware GL.**
- **D6** convention pre-flight — a discipline, applied to whichever case
  introduces new craft vocabulary.

---

## Maintenance note (not a film)

The plan's postmortem flags one structural risk this suite can't test with a
film: the cinematography solver now exists in **two copies** (the 3D template
and `examples/toybot-walk.html`) with no drift guard — the kernel markers cover
only the deterministic kit, not the solver. Two copies is the repo's tolerated
maximum. If any case here adds a **third** consumer of the solver (a second
3D example, or a new template), extract it or marker-fence it first, per the
CLAUDE.md mirrored-copies-plus-test pattern.
