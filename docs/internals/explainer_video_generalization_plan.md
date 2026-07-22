last updated: 2026-07-22

# explainer-video: generalization plan

Multi-phase plan for taking the `explainer-video` plugin from one visual
language (three.js primitives, soft shadows, one caption style) to a system
that can produce films across artistic styles — up to and including cinematic
3D with cinematographer-grade shot language, editorial vocabulary, and
replicable style "bibles."

Companion to [explainer_video_roadmap.md](explainer_video_roadmap.md), which
tracks per-item history. This document is the arc; the roadmap remains the
ledger. Where a phase lands an open roadmap item, it says so.

---

## Decision: generalize the existing skill. Do not create a second one.

Considered and rejected: a new `cinematic-video` (or similar) sibling skill.

**Why one skill:**

1. **The valuable assets are already renderer-agnostic, and there is exactly
   one copy of each.** The window contract (`seekTo`/`DURATION`/`BEATS`/
   `sceneReady`), the tooling (`build.js`/`shoot.js`/`smoke.js` never look
   inside a scene — they talk only to the contract), the three-axis review
   method, the determinism discipline, and the delivery forensics. A second
   skill either duplicates all of that (two copies drift — the exact failure
   class the sibling ccutils repo documents with its project-boundary rule) or
   depends on this one awkwardly.
2. **The measured knowledge must not fragment.** The caption bracket, the
   motion-detector negative result, the exposure two-tail rule, the AVIF
   decode-cost observation — these are small-n observations that only tighten
   if every film feeds the same ledger. Two skills means two ledgers.
3. **The trigger surface is identical.** "Make a video / animation /
   explainer" — a user asking for a cel-shaded character film and a user
   asking for a flat diagram are invoking the same intent. Skills are
   retrieval; two entries with the same trigger compete for the same match and
   lower precision (VISION.md's own constraint).
4. **The overfit is internal, not at the boundary.** SKILL.md already claims
   domain-agnostic and is right about the pipeline; what's missing is style
   breadth *inside* the skill. You fix an internals problem with internals
   restructuring, not a new front door.

The one condition that would justify a split later: if the film-language layer
(Phases 3-4) grows a genuinely different *workflow* (screenplay-first
multi-scene productions with a different review loop), revisit. Until observed,
one skill, progressive disclosure.

**The prime directive across all phases** — the two things that are never up
for negotiation, because everything else derives from them:

- The film stays a pure function of `t`.
- Tooling talks only to the window contract, never to scene internals.

Any feature that cannot be had under those two rules is either reformulated
(bake, then play back — Phase 5) or not had.

---

## Execution status (back-to-back mode, started 2026-07-22)

| Phase | Status |
|---|---|
| 0 | **DONE** — shipped as explainer-video 0.7.0. Checkpoint: split verified lossless (every heading and spot-checked measured fact present in exactly one new home), `smoke.js` green source+bundled on the template scene, code untouched so frame regression is trivially satisfied. |
| 1 | **IN PROGRESS** — parallel capture landed (0.8.0; byte-identical verified, ~1.0x on a 4-core software-GL box — see roadmap item 5). Canvas2D template + easing personalities + first STYLE block landed (0.9.0; smoke green on both backends 4/4 runs, 3D output byte-identical after the kit addition; two composition bugs found by frame review — fp-residue gate leak, luminance-blind label ink — and one smoke.js sampling race found because its symptoms masqueraded as scene findings, all fixed). **DONE** — gate met with the proving film `examples/one-scene-every-format.html` (0.11.0): Canvas2D backend end-to-end through unchanged tooling, determinism byte-check green, style-pack swap verified categorically different, full three-axis review applied (composition: 2 rounds; continuity: strip caught and fixed a tangled handoff; semantics: every beat carries its idea in geometry). Also this phase: parallel capture (0.8.0, honest ~1.0x negative on 4-core software GL), Canvas2D template + easing personalities + STYLE split (0.9.0), style packs + drift-proof KERNEL block (0.10.0). Exit checkpoint: harvest done (dynrange below-floor observation now real; kernel rules), release 0.11.0, regression green (skill-retrieval untouched, kernels byte-identical), prune reviewed (noise1 kept: consumed by the 2D camera's sway path; flagged for Phase 3, which formalizes camera energy). Kernel extraction resolved as marked-block-plus-drift-test rather than a build step — scenes stay single-file. |
| 2 | **DONE** (0.12.0 spike + 0.13.0 close). Spike gate met: `examples/toybot-walk.html` — cel + outlines riding IK pivots, analytic two-bone IK, rack-focus DoF, bloom, post chain byte-deterministic source+bundled; roadmap item 10 closed. World pass landed instancing (+instanced outline trick), lathe, physical, matcap. Two bisected negative results recorded: PMREM fromScene blacks out SwiftShader (IBL recipe documented, unverified on hardware GL); visible Sky lost to the flat-bg control on a low-horizon composition (stays bundled, art-direction-conditional). Exit checkpoint run: harvest in style-3d.md, release 0.13.0, regression green (3 examples + 2 templates + kernel parity), prune reviewed (Sky kept with rationale; quality tiers unbuilt by design, rule pre-decided). |
| 3-4 | not started |
| 5 | demand-gated, out of the run |

## Phase overview

| Phase | Theme | Headline deliverables | Gate (a real film, per the build-the-control rule) |
|---|---|---|---|
| 0 | Doc re-layering | method.md split by audience; SKILL.md slims | No behavior change; smoke green; no knowledge lost |
| 1 | Style axis + second backend | `STYLE` split from `CONFIG`; Canvas2D template; easing personalities; 2-3 style packs; kernel extracted | One real 2D film; tooling runs unchanged on both backends |
| 2 | Cinematic 3D | Post chain (bloom/DoF/grade); cel+outline pack; IBL; instancing; analytic IK; parallel capture; quality tiers | Cel-shaded character beat spike: IK walk, DoF, outlines, smoke green with post on |
| 3 | Film language | Framing solver; `SHOTS` vocabulary; camera energy; transition vocabulary incl. match cut + dissolve | Five-shot film authored with zero hand-written camera keyframes |
| 4 | Style bibles + reuse | Style-bible spec constraining every layer; CAST/SET modules | Control pair: same beats + cast under two bibles → two categorically different films |
| 5 | Production extensions | Asset vendoring; `bake`; audio wiring; `deploy`; path-traced hero frames | Each item ships only when a real film demands it |

Phases 1 and 2 are independent and swappable by appetite: 1 is the cheaper
categorical win (and forces the kernel extraction); 2 is the bigger visible
payoff. 3 wants 2's DoF (rack focus) but not 1. 4 needs 1 (style as data) and
3 (shot/edit vocabulary to constrain). Rough cost: 0 is half a session; 1-3
are 1-2 focused sessions each plus their proving film; 4 is mostly authoring;
5 is open-ended and demand-driven.

The paragraph above assumes demand-driven pacing — phases landing as need
shows up. **If executing all phases back-to-back as one continuous effort,
four adjustments apply; see "Back-to-back execution mode" below.**

---

## Phase 0 — Doc re-layering (no behavior change)

`references/method.md` currently conflates three documents. Split by reader:

- `references/method.md` — the universal core: three failure axes, the
  iteration loop, the controls/bracket discipline ("build the control",
  "verify the control ran", "a proxy can reject, cannot approve").
  Backend-agnostic by construction after the split.
- `references/style-3d.md` — the three.js cookbook: lighting wash/crush,
  silhouette recipes, procedural-asset recipes, r185 API notes. Becomes the
  first *style reference* rather than "the method."
- `references/delivery.md` — the GitHub delivery forensics (content-type
  allowlist, AVIF evidence chain, size tables). Already self-contained inside
  method.md; extraction is mechanical.

SKILL.md keeps: contract, workflow, review axes, delivery decision table, and
grows pointers. Perceptual constants (caption CPS, ~3s content floor, transit
budget) stay in the universal core — they are facts about viewers, not about
renderers.

This is a plugin-content change (`references/` edits) → full version cascade.

Gate: `smoke.js` green on the shipped example; every measured observation
grep-able in exactly one new home; SKILL.md shorter than before.

## Phase 1 — Style as data + the second backend

The overfit is one template = one aesthetic. Fix it with a second concrete
backend, and extract the kernel only from what the two templates *actually*
share — not by designing an abstraction up front.

1. **Split `STYLE` out of `CONFIG`** (palette, typography, material/stroke
   recipe, grain/vignette, caption styling, easing personality). `CONFIG`
   keeps what is neither timing nor look (seed, flashes, sway).
2. **Canvas2D template** (`scene-2d.template.html`) implementing the identical
   window contract: flat-vector illustration, shape morphs, line-draw-on
   (all closed forms of `t`). The roadmap's "Not doing: a 2D backend" set its
   own flip condition — "worth building only when a real 2D sequence is
   wanted" — and this phase is that want. `smoke.js` already stopped asserting
   `window.THREE` in 0.1.2; `build.js ensureVendor` already gates on three
   usage. Nothing blocks this; it was anticipated.
3. **Easing personalities** in the deterministic kit: `easeOutBack`
   (overshoot), exponential-decay elastic, **quantized time**
   (`tq = floor(t*n)/n` — stop-motion feel, perfectly pure), seeded handheld
   noise from the `R[]` pool. Easing temperament is half of what "vibe" means.
4. **2-3 style packs** as one-page references (e.g. `styles/paper-cutout.md`,
   `styles/blueprint.md`, `styles/neon.md`): palette, material/stroke recipe,
   motion temperament, one spiked frame each.
5. **Art-direction round in the workflow**: the existing "spike the hostile
   beat" step doubles as a *style spike* — render that beat under 2-3
   candidate styles, tile as a contact sheet, settle the look before building
   six beats in the wrong one.
6. **Kernel extraction, last**: pull the shared ~120 lines (BEATS resolution,
   ramp/pulse/rampS kit, R[] pool, overlay, driver) into one place only once
   both templates exist and the shared set is observed, not predicted.

Gate: one real 2D film shipped end-to-end; `sheet`/`strip`/`motion`/`smoke`
run unchanged against it; the determinism byte-check passes; a style-pack swap
on the same beats visibly changes the film.

## Phase 2 — Cinematic 3D (the movie/game look)

The gap to "looks like a game cutscene" is mostly shading and post, not
geometry. The architecture is an offline render farm, not a game loop — it can
pay for film tricks realtime engines cannot.

1. **Post-processing chain** (EffectComposer): bloom, bokeh depth of field,
   SSAO, vignette/grain, color-grade LUT. Determinism rule, stated in the
   template: **no temporal passes** (TAA, accumulation motion blur carry state
   across frames and break `seekTo` purity). Motion blur, if wanted, is done
   the film way: N sub-samples at `t ± i·dt`, averaged — pure, N× cost, and
   offline rendering does not care.
2. **Stylized shading packs**: cel/toon (`MeshToonMaterial` + gradient ramp +
   rim light + outline pass) as the flagship "game look" — it reads better at
   explainer scale than photoreal, survives the squint strip, and compresses
   well. Matcaps (procedurally generated gradient spheres) as the cheap
   sculpted-clay/metal look. `MeshPhysicalMaterial` + IBL for the glossy
   product-render look.
3. **Image-based lighting without assets**: procedural `Sky` →
   `PMREMGenerator` environment map; sun position animatable as a function of
   `t`. Kills the "three-light programmer art" flatness at zero asset cost.
4. **Geometry richness**: `InstancedMesh` fields (crowds, forests, particle
   fields — placed and animated from `R[]`), lathe/extrude/tube along curves,
   seeded-noise displacement.
5. **Analytic character animation**: two-bone IK is closed-form (no solver, no
   state) — feet plant, hands reach. Follow-through/overlap as lagged ramps
   down a joint chain (`ramp(t - i*dt, ...)`). Squash-and-stretch and
   anticipation as kit idioms in the style-3d cookbook.
6. **Cost controls, now load-bearing**: parallel frame capture (roadmap item
   5 — "low priority" flips here: a post chain on software GL multiplies the
   ~1 fps floor) and a preview/final quality tier. Rule: the determinism check
   and the shipped film run at *final* tier — preview exists to iterate, never
   to verify.

New composition-axis checks join the style pack, discovered the repo's way
(render the control, look, write the bracket): DoF focused on the wrong
subject; bloom blowing out captions.

Gate: the spike beat — a cel-shaded character with an IK walk, outlines,
bloom, and a rack-focus-capable DoF — passes `smoke.js` with the post chain
enabled, and its squint strip still reads. This doubles as the committed
flagship example the roadmap's item 10 has wanted (character, moving camera).

## Phase 3 — Film language: cinematography and editorial as data

Pull the camera and the cut out of hand-authored coordinates into declarable
vocabulary, compiled onto the existing rail. Data + a small compiler — not an
abstraction layer.

1. **Framing solver** (~100 lines): shot sizes (ECU/CU/MCU/MS/WS/EWS) are
   "subject occupies X of frame height"; given a named subject's bounding box
   and a lens, camera distance falls out of trigonometry. Because subject
   positions are already pure functions of `t`, aiming by name yields tracking
   shots and look-ahead framing for free.
2. **`SHOTS` array** compiled to `KEYS[]`:
   `{beat, size, subject, lens, move, focus, energy}` with a movement
   vocabulary (static, pan, dolly, push-in, pull-out, orbit, crane, whip pan)
   and camera-energy profiles (locked / steadicam / handheld — amplitude and
   frequency of seeded noise). Rack focus = animating DoF focus distance
   between named subjects (needs Phase 2's bokeh pass).
3. **Transition vocabulary**, split by an architectural line:
   - *In-scene, parity-preserving*: hard cut, flash cut (exists), whip-pan cut
     (accelerate, cut mid-smear), and **match cut as a compiler constraint** —
     shot N's exit framing must equal shot N+1's entry framing; the solver can
     verify it, turning the strongest cohesion device in film into a checkable
     property.
   - *Composited*: dissolve/wipe via two render targets blended on a
     fullscreen quad, mix a function of `t` — pure, costs a second render on
     transition frames only. (An ffmpeg-`xfade` edit-decision-list in
     `build.js` is the mp4-only power alternative; it forks MP4 from HTML, so
     it stays opt-in and clearly labeled.)
4. **Cut rhythm** as a parameter (average shot length, cut-on-action vs
   cut-on-rest) — a huge fraction of perceived vibe is this one number.

Vocabulary enters the compiler only after a film needed it: v1 is the solver,
the six sizes, three moves, two cut types. Orbits, match-cut constraints, and
dissolves earn their way in.

Semantics-axis upgrade for method.md: a shot list makes "why this shot?" a
reviewable authorial decision per beat, alongside "cover the caption."

Gate: a five-shot film authored entirely through `SHOTS` — zero hand-written
camera keyframes — including one match cut verified by the solver and one
whip-pan transition.

## Phase 4 — Style bibles and cast/set reuse

"Vibe" is every layer making consistent choices. A style bible is one
reference file that constrains all of them at once — palette and material
finish, lens set, framing rules, camera energy, cut rhythm and transition
vocabulary, easing temperament, texture/grain, caption typography. Descriptive
names (`planimetric-pastel`, `neo-noir`, `saturday-cartoon`,
`documentary-handheld`), never director names.

1. **Bible spec + 2-3 bibles**, each one page, each with a spiked frame.
2. **The control pair** (this phase's gate and its reason to exist): the same
   `BEATS` + cast rendered under two bibles must produce two categorically
   different films with zero beat or geometry edits. If a bible swap does not
   visibly change the film, the layers are not actually separated — that
   result would be a Phase 1-3 bug report, and finding it is the point.
3. **CAST/SET as reusable modules** — a character defined once (rig recipe,
   costume, motion idioms) and referenced by name from shots and blocking.
   Deliberately informal until a second film actually reuses a character;
   promoting it earlier is speculative abstraction.

## Phase 5 — Production extensions (opt-in, demand-driven)

Each of these is designed, none is built until a real film demands it — the
same discipline that has audio.md sitting unwired today.

- **Asset vendoring** (`build.js vendor-assets`): base64-embed a CC0 GLB or
  HDRI into the bundle. Keeps single-file/offline/deterministic
  (`sceneReady` already exists to gate on load). Relaxes the "no files" rule
  per scene, opt-in; bundle-size cost hits the HTML artifact, not the MP4
  path.
- **`build.js bake`**: the film-industry answer to the simulation ban. Run
  cloth/particles/ragdoll once at fixed timestep as a build step, write
  sampled results into the scene as data, play back by interpolation — again
  a pure function of `t`; `smoke.js` still passes. Sim → cache → playback.
- **Audio** (roadmap item 3): narration-drives-timing as designed in
  `references/audio.md` — possible at all because beats are data.
- **`build.js deploy`** (roadmap item 9's forward note): publish the bundled
  HTML scene to Pages / as an Artifact — the only delivery that keeps
  interactivity and sidesteps the raster tradeoff.
- **Path-traced hero frames** (exploratory): deterministic per-frame-seeded
  path tracing for still/short "money shots"; offline capture makes slow
  affordable, parallel capture makes it tolerable.

---

## Back-to-back execution mode

The phase contents above hold; four sequencing/scoping choices change when
the phases run continuously instead of demand-driven.

1. **Parallel frame capture moves to Phase 0/1.** Its "low priority, add
   anytime" verdict (roadmap item 5) assumed occasional films on local
   hardware GL. Back-to-back, render-look-edit is the inner loop for the
   whole effort and Phase 2's post chain multiplies the ~1 fps software-GL
   floor. Infrastructure that cheapens every subsequent iteration ships
   first; it touches no scene code, so pulling it forward is risk-free.
2. **Two persistent proving threads instead of a film per phase.** A 2D
   diagrammatic thread (born in Phase 1) and a 3D character thread (born in
   Phase 2, gains shots/editorial in Phase 3, becomes the Phase 4 control
   pair). Gates attach to the threads' milestones rather than to fresh
   throwaway films. Two threads, never one: a single evolving film would
   overfit the system to itself — the disease this whole plan exists to cure.
3. **Order is fixed: 0 → 1 → 2 → 3 → 4.** The 1↔2 swap option is for
   appetite-driven pacing only. Running continuously, the kernel must be
   extracted (Phase 1) before Phase 2 piles post-chain and quality-tier churn
   onto the 3D template — extracting shared code from a moving target is how
   the extraction goes wrong.
4. **"All phases" means 0-4.** Phase 5 is demand-gated *by design*; building
   bake/asset-vendoring/path-tracing speculatively is exactly the
   overcomplication failure mode. Pull a Phase 5 item into the run only when
   one of the two proving threads concretely hits its need (audio via
   narration-drives-timing is the likeliest candidate).

**Phase-exit checkpoint (mandatory in this mode).** Demand-driven pacing has
natural pauses where observations get harvested; back-to-back momentum blows
through them. Every phase ends with, in order:

- Harvest: new brackets, gotchas, and negative results into `method.md` /
  the style references, and the phase's status into the roadmap ledger.
- Release: cut the plugin version (the cascade), so history stays bisectable
  per phase instead of one mega-release at the end.
- Regress: re-shoot the fixed sample timestamps of every committed example
  and compare (byte-identical or the PSNR technique in `method.md`); a phase
  may not open while a prior phase's example renders differently unexplained.
- Prune: anything built this phase that the proving threads did not use gets
  removed before the next phase starts, not "kept for later."

---

## Cross-cutting rules (all phases)

1. **Every phase gates on a real film**, not on code review — the repo's own
   "build the control" applied to architecture. What the proving film did not
   need does not ship.
2. **Tooling talks only to the window contract.** If a phase tempts a tool to
   parse scene internals, the contract is missing an export (the `window.BEATS`
   precedent) — extend the contract instead.
3. **New perceptual rules ship with brackets** — an observation on each side
   or an honest "unbracketed, single observation" label, per method.md's
   existing standard. New instruments ship with a verified positive control.
4. **Determinism red lines per phase**: no temporal post passes; shared
   materials restated every frame; sims baked, never live; quantized time and
   seeded noise are pure — use them freely.
5. **Version cascade** fires on every phase that touches `templates/`,
   `references/`, or `examples/` (CLAUDE.md invariant 1) — which is all of
   them except this document.
6. **Duration stays the user's spec input; nothing in any phase assumes
   long-form.** "Film language" here means craft density, not runtime: the
   shot vocabulary, editorial grammar, and style bibles must read correctly
   on a 10-second three-shot explainer exactly as on a 40-second piece —
   `duration_s` and the beats table remain the only place length exists,
   set per spec by what the content needs. Every proving film in this plan
   is explainer-scale (the 15-40s SKILL.md pacing guidance), and a phase
   deliverable that only works at length is overfit and fails its gate.
