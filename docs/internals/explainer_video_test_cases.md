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
*Outcome:* —

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
*Outcome:* —

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
*Outcome:* —

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

## Recommended priority run

Covers the most surface *and* the most opens, cheap-first:

1. **B1 · toybot dance** — asset exists, fast, fun, tests review-without-captions.
2. **A3 · external doc** — the highest-value untested claim (semantics on
   someone else's subject).
3. **D1 · simulation-shaped scene** — the prime directive under active pressure.
4. **C1 · match cut** — verifies a headline feature actually enforces.
5. **B3 · Rube Goldberg** — fun + causality + compression-hostile in one film.
6. **A2 · approval flow** — the clean happy-path baseline to anchor the rest.

---

## Maintenance note (not a film)

The plan's postmortem flags one structural risk this suite can't test with a
film: the cinematography solver now exists in **two copies** (the 3D template
and `examples/toybot-walk.html`) with no drift guard — the kernel markers cover
only the deterministic kit, not the solver. Two copies is the repo's tolerated
maximum. If any case here adds a **third** consumer of the solver (a second
3D example, or a new template), extract it or marker-fence it first, per the
CLAUDE.md mirrored-copies-plus-test pattern.
