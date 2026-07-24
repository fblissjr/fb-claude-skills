last updated: 2026-07-23

# screenwright: founding plan

A new skill for deterministic, generated moving pictures of any register — an
explainer, a game cutscene, a meme, a character short — built clean on the
three.js WebGPU/TSL node stack, structured from day one so the same core can
later drive interactive experiences. `screenwright` inherits everything
explainer-video proved (the window contract, the determinism discipline, the
instruments, the review method) and rebuilds everything the old renderer stack
constrained (materials, post, characters, physics).

Companion documents: [explainer_video_generalization_plan.md](explainer_video_generalization_plan.md)
(the predecessor's arc, including its postmortem),
[explainer_video_test_cases.md](explainer_video_test_cases.md) (the measured
findings screenwright must not re-learn the hard way). The WebGPU migration
research that triggered this lives in `internal/threejs_explainer_research/`
(uncommitted, externally authored) — treat it as a capability map, not a
migration plan; its defects are catalogued below.

---

## Decision: a new skill, not a migration

The generalization plan decided "generalize the existing skill, do not create a
second one," and its reasoning was correct *for its conditions*. Three of those
conditions have changed; the fourth was that plan's own stated revisit trigger.

1. **The tooling fork is forced regardless.** The old argument was "one copy of
   the contract and tooling; a second skill duplicates it and the copies
   drift." But moving to `WebGPURenderer` + node materials forks the vendor
   entry, the template bootstrap (async init), the post chain (node passes
   replace `EffectComposer`), and every instrument calibration — inside one
   skill or across two, the fork happens. Two *live* copies drift; one live
   copy and one **frozen** copy do not. explainer-video freezes (below).
2. **The trigger surface genuinely broadens.** "Make me a cutscene for my
   game," "make this meme," "make it interactive later" are not the explainer
   intent. The old plan named its own split condition: "if the film-language
   layer grows a genuinely different workflow, revisit." Cutscenes and
   interactive experiences are that.
3. **Greenfield is this repo's stated default** for anything not
   production-facing, and a renderer-stack replacement is the textbook case:
   porting in place means every intermediate commit half-works on two stacks.
4. **The measurement ledger does not fragment — it transfers.** The measured
   knowledge (caption brackets, exposure two-tail rule, motion-detector
   negative result, AVIF decode cost) is recorded in the frozen skill's
   references and in `docs/internals/explainer_video_test_cases.md`.
   screenwright imports the conclusions and re-verifies only what the renderer
   change invalidates (per-backend calibrations), appending to its own ledger.

**explainer-video's disposition: frozen, published, bugfix-only.** It works,
it has examples, it stays installed. screenwright supersedes it when its
explainer register is verifiably better on the same test cases; then the
marketplace `renames` map retires it, the same mechanism that retired
env-forge.

**The prime directive carries over verbatim** — the two rules that are never
negotiable, because everything else derives from them:

- The scene is a pure function of `t`.
- Tooling talks only to the window contract, never to scene internals.

Anything that cannot be had under those rules is reformulated (bake at build
time, play back pure) or not had.

---

## Decisions taken at founding (2026-07-23)

Settled with the owner; each is expensive to reverse, which is why it is
recorded here with its rationale.

| Decision | Choice | Why |
|---|---|---|
| Name | `screenwright` | A wright builds — shipwright, playwright. A maker of screen-things across registers. The pipeline literally runs on Playwright. |
| Character assets | **Scaffold-as-data** | Parametric rigs and base meshes ship inside the skill as data tables (vertices, weights, morph deltas) — not model files, not primitives-only. Output stays a single self-contained file; any character is the same scaffold under different proportions, shells, shaders. Raises the ceiling far above primitives without becoming an asset pipeline. |
| Human quality bar | **Stylized-cinematic** | AAA-cutscene stylization (SSS skin, real facial rig, hair, hands — the Arcane/Pixar register). Photoreal is the hardest asset in CG and approaches the uncanny valley from the wrong side, where almost-right reads worse than stylized. Stylized is achievable, ages well, and reads better at every delivery size this skill ships. |
| Old skill | **Freeze, keep published** | See above. |

## Architecture: the layer split that makes "interactive later" free

The old skill's architecture had two layers: scene (pure `f(t)`) and tooling
(talks to the window contract). screenwright splits the scene layer once more,
because "the film is `f(t)`" quietly welds together two things — *what the
world is at a state* and *how time advances*:

```
kernel     pure functions: pose(state), materials(state), camera(state)
           — no clock, no input, no side effects; state is a plain value
driver     produces the state stream:
           - timeline driver: state = g(t) from BEATS   (the film — built first)
           - input driver:    state = g(events)          (interactive — later)
contract   window.seekTo / DURATION / BEATS / FRAME / sceneReady — unchanged,
           implemented by the timeline driver
tooling    build / shoot / smoke / instruments — talk only to the contract
```

The timeline driver composed with the kernel IS today's `f(t)` — nothing about
film-making gets harder. But because the kernel never touches a clock, an input
driver later reuses every character, material, camera solver, and instrument
unchanged. This is a structuring rule, not extra machinery; Phase 6 proves it
with a spike and until then it costs only discipline.

## The render stack (verified 2026-07-23, session spike)

Facts established empirically on `three@0.185.1`, recorded here because they
are otherwise only in a conversation:

- `three/webgpu` + `three/tsl` + TSL display nodes bundle to a classic-script
  IIFE with bun, run over `file://`, single file, no network. **1.09 MB** vs
  0.77 MB for the old stack (+0.3 MB per scene, accepted).
- `WebGPURenderer` transparently falls back to its WebGL2 backend when no
  WebGPU adapter exists (verified headless: same scene, same TSL materials and
  node bloom, both backends, visually identical composition). One template
  serves hardware and CI.
- Byte-determinism of `seekTo` holds on **both** backends (seek away and back,
  SHA-256-identical PNG). Cross-backend frames are *not* byte-identical —
  same as the old stack's Metal-vs-SwiftShader finding; byte comparison stays
  valid only within one backend.
- Speed with a node post chain at 960×540, screenshots included: **37 ms/frame
  WebGPU-Metal vs 87 ms/frame WebGL2-backend** (~2.3x).
- **The flag landmine:** `--enable-unsafe-webgpu` (with or without
  `--enable-features=Vulkan`) on macOS headless yields a SwiftShader-WebGPU
  adapter that renders **pure black, silently, exit 0**. The working macOS
  flag is `--use-angle=metal`. Default policy: launch with **no** WebGPU flags
  (fallback handles it); hardware WebGPU is per-platform opt-in. smoke's
  near-black check must be proven, not assumed, to catch this signature.
- `renderAsync()` is deprecated in r185 (warning observed); the contract is
  `await renderer.init()` once, then synchronous `render()` in `seekTo`.
- Present in the bundle and relevant to this plan: `MeshPhysicalNodeMaterial`
  (transmission, dispersion, sheen, iridescence), `MeshSSSNodeMaterial`,
  `MeshToonNodeMaterial`, `SkinnedMesh`, MaterialX noise nodes
  (`mx_fractal_noise_float`, `mx_worley_noise_float`, `mx_aastep`), ~45 TSL
  display nodes (bloom, dof, film, chromatic aberration, GTAO, godrays).
- Known-bad for this architecture, prohibited: `ComputeNode` / storage buffers
  (no WebGL2 fallback, stateful), temporal post passes (TAA, accumulation
  blur), the auto-incrementing TSL `time` node (drive a `uniform(0)` from
  `seekTo` instead).

On the research folder: its API surface is largely accurate (`RenderPipeline`
exists; the deprecations are real) but its upgrade diffs are internally
contradictory — one recipe loads three from a CDN importmap, violating the
offline contract it claims to demonstrate; its flag recipe is the black-frame
landmine above; it never considers the 2D sibling or the instruments. Capability
map, not migration plan.

### Framework survey (reviewed 2026-07-23)

A second external corpus, `internal/web3d_frameworks_comparison/` (uncommitted),
surveys eight frameworks and concludes three.js WebGPU/TSL is the right 3D
foundation. Reviewed twice — directly and by an independent agent — verdict:
**zero-weight confirmation.** Its conclusion converges with this plan's, but
its "Gartner Magic Quadrant" is fabricated framing (Gartner does not cover this
space, and the chart's own normalization note admits placements were moved to
fit the quadrant story), its figures are unsourced, it contradicts itself
(R3F's bundle is "~35KB" in one file and "~2.5MB+" in another), and it audited
a stale copy of the old skill. Nothing in it is citable evidence; this plan
cites only what was verified against the package or measured in the spike.
Three things it surfaced that survive scrutiny:

- **Pre-warm shaders before `sceneReady`:** `await renderer.compileAsync(scene,
  camera)` after `init()`, before signaling ready (verified present in r185).
  Adopted into the Phase 0 template contract — it closes the black-first-frame
  window the spike brushed against.
- **2D backend decision, made explicit:** the survey recommends PixiJS v8 for
  2D. Rejected for now. The Canvas2D template already satisfies every
  constraint for flat scenes at zero bundle cost and zero vendor step; PixiJS
  buys sprite/filter scale no current test case needs. Revisit only if a 2D
  case demands what Canvas2D cannot do; recorded here so the "no" is a
  decision, not an omission.
- **Alternatives ranked, once, so this does not reopen:** Babylon.js is the
  only workable substitute (real determinism path, strong procedural API) and
  loses on bundle economics and WASM-physics inlining with no capability this
  workflow needs; PlayCanvas's component `update(dt)` model is
  delta-accumulative by design; Bevy requires a Rust-to-WASM compile per
  generated scene, unusable when the scene author is an LLM writing code into
  an HTML file; R3F puts a React reconciler between `seekTo(t)` and the scene
  for zero benefit; Spline has no code-level procedural API. Editor-centric
  and toolchain-centric engines fail this skill's constraints structurally,
  not by degree.

## What carries over, what is rebuilt, what is dropped

**Verbatim (proven, renderer-agnostic):** the window contract; `BEATS` /
`CONFIG` / `FRAME` and beat addressing (`ramp`/`pulse`/`rampS`/`latch`/`warp`);
the seeded-PRNG determinism kit; the three failure axes and the review method;
the instrument *philosophy* (every check ships with its measured bracket and
its blind spots — `instruments.md` is the crown jewel); delivery forensics
(WebP/AVIF/MP4/HTML tradeoffs); style bibles as one object constraining
palette, lights, post, lens, cut pace; the Canvas2D 2D template (untouched by
any of this — it has no renderer to migrate).

**Rebuilt on the node stack:** the vendor entry; the 3D template bootstrap
(async init, `uniform(0)` time, backend report); the post chain (node passes
replace `EffectComposer`); material packs (TSL); every instrument
*calibration* (exposure lints, bloom brackets, blank-frame signatures were
measured on GL and are per-backend facts).

**Dropped or retired:** GLSL-era workarounds; the Sky/PMREM half-float
SwiftShader workaround chain — re-test the node-stack sky/environment path
from scratch before importing any of that scar tissue (the failure was
backend-specific and may simply not exist here).

## The character system (the new capability, staged)

Scaffold-as-data, three tiers of the same idea:

1. **Skeleton + proportions.** One parametric skeleton family (biped,
   quadruped, generic-creature: chains for spine/tail/neck), stored as data.
   Proportions are a small vector (limb lengths, torso ratios, head scale) —
   "a bear" and "a human" and "the creature you just described" are points in
   proportion space plus a shell choice. Analytic IK ports from the old skill
   and extends to spine/tail chains.
2. **Shells and surfaces.** Body surfaces generated over the skeleton
   (capsule/metaball-like hulls as vertex data, morphable by the proportion
   vector), shaded by TSL packs: SSS skin, fur (shell layers), cloth, chitin,
   toon. This is where stylized-cinematic lives — shading does the work
   geometry alone cannot.
3. **Face and hands.** Morph-delta tables on the head mesh (brow/lid/jaw/
   mouth-corner deltas — a compact FACS-like basis, authored once as data),
   driven per-beat exactly like any other pure function of `t`. Hands as
   posed-shape presets before per-finger articulation.

Secondary motion (hair, cloth follow-through, jiggle) is procedural or baked —
never integrated at runtime. Primary motion stays authored/IK. The scaffold
data is authored once, by a build-time generation pipeline that is itself
committed — the skill must never grow a runtime asset-fetch path.

## Test-case portfolio

Diversity is the point: each case exists to break a different assumption, and
each phase gate names the cases it must pass. These are specs, not committed
films; build them as they gate.

| Case | Register | What it stress-tests |
|---|---|---|
| `gearbox` | technical explainer | Regression baseline against frozen explainer-video: same beats, node stack, must not be worse on any instrument |
| `market-crash` | data/abstract explainer | No characters at all — proves character work taxed nothing; charts and glyphs as sets |
| `bear-and-bees` | character short / comedy | Quadruped scaffold, fur shells, comedic timing (pause-then-fast) |
| `boss-intro` | game cutscene | A creature invented from a text description on the generic scaffold; dramatic node lighting; title card; cut language |
| `the-briefing` | human two-shot | THE hard one: face rig, expressions readable in the nocap pass, SSS skin in closeup, rack focus between speakers |
| `crowd-cross` | scale | ~100 figures from one scaffold via instancing, individual gait phase offsets, LOD shading |
| `rube-goldberg` | physics | Build-time Rapier bake to sampled trajectories; byte-determinism preserved through the bake |
| `meme-remix` | meme | Speed of authoring is the metric: joke format, fast cuts, text overlays, made start-to-shipped in one session |
| `museum-walk` | interactive spike | Same kernel, input driver instead of timeline driver; walk the camera through a built set |

Formats (vertical 9:16, square) are exercised inside these via `FRAME`, not as
separate cases — that contract carries over and already works.

**Chart tier (decided 2026-07-23).** Below the films sits a second class of
test scene: charts — static grids of patches, one primitive per cell,
smoke-gated and byte-compared per backend. Films integrate; charts isolate.
The portfolio above is sufficient at the film tier (it already reserves a
film for every place a borrowed technique lands: `the-briefing` for skin,
`crowd-cross` for LOD shading, `rube-goldberg` for the bake); what it lacked
was anywhere to land a borrowed *primitive* alone — the Phase 1 lesson
(isolate one class of new variable) says a new hash or noise function must
not debut inside a film. Pipeline: chart proves the primitive, showcase
(materials.html's tier) proves the pack, film proves the register. Every
ported primitive lands chart-first (source map: appendix at the end of this
doc). First chart SHIPPED
same day (screenwright 0.12.0, `examples/noise-chart.html`): 8 cells —
MaterialX baseline row (fbm, worley, aastep, palette-fbm), ported row (HWS
value noise, HWS cells, domain warp) plus the classic sin-hash as a
deliberate drift control, structurally identical to the HWS-cells cell
except the hash. Measured: 20/20 smoke green (15 WebGPU-Metal, 5 WebGL2
fallback), control included. **Negative finding on the metal 1-in-6 FAIL:**
dense noise/hash coverage alone — no shadows, no characters, single locked
shot — did NOT reproduce it in 15 metal runs, which narrows the suspect
space toward the machinery bear-and-bees has and the chart lacks (shadowed
fur shells, multi-shot solver traffic, the character rig). The sin-hash
control also stayed clean at this sample size; the classic drift claim
remains unconfirmed on this stack — keep the control in place, it costs
nothing and the chart re-runs free.

## Phases and gates

Each phase ends at a gate a reviewer can check. No phase starts until the
previous gate is green — except documentation, which trails every phase.

**Phase 0 — Foundation. DONE 2026-07-23 (screenwright 0.1.0).** Plugin
scaffold (`skills/screenwright/`), vendor entry for the node stack (SkyMesh —
the node-stack Sky — kept), 3D template with async init + `compileAsync`
pre-warm before `sceneReady` + `uniform(0)` time + backend report, port of the
deterministic kit and all tooling, per-platform flag policy in the recorder,
instrument recalibration begun. *Gate, met:* template scenes pass smoke on
WebGPU-Metal **and** the WebGL2 fallback (plus the 2D sibling); the
flat-frame catch was demonstrated firing in the real instrument (playwright
headless-shell + `WEBGPU=swiftshader` → shipped-frame FAIL), not assumed;
determinism byte-check green on both backends. Four measured findings shipped
in the tools — the shadow `frameId` guard, the presentation settle, the
shipped-frame check with its spread bracket, the arm64 Chromium resolution
fix — recorded in CHANGELOG 0.69.0 and `references/webgpu-stack.md`.

**Phase 1 — Regression, post, shading.** Reshaped after Phase 0 (2026-07-23):
the gate work runs in this order, each step isolating one class of new
variable.

1. *Structural chores first:* a shared same-task render-and-read sampling
   helper in smoke.js — three checks independently hit the buffer-clears-
   after-composite trap in Phase 0; the rule becomes construction, not
   convention. **DONE 2026-07-23** (`sampleAt()`, both consumers refactored,
   crop-control re-verified).
2. *`gearbox` before any new capability.* The regression case has zero new
   variables, so it separates porting gaps from feature bugs, and it is the
   first real film through the instruments smoke does not cover (`motion`'s
   frame-difference metric, `strip`, the delivery encoders) on node-stack
   output. Judged against its explainer-video twin by the honest comparison:
   same beats spec on both skills, instruments green on screenwright, and a
   side-by-side visual review (sheets, squint strips, watched loops) judged
   no worse. NOT "every instrument matches" — the two skills' instruments
   now differ, and frames are not byte-comparable across renderers.
   **DONE 2026-07-23** (screenwright 0.2.0, `examples/gearbox.html`): the
   strategy paid immediately — gearbox exposed the sortObjects draw-order
   uniform corruption (now determinism rule #5, template default) and the
   stale frustum-cull decision (rule #6), both invisible to the 4-mesh
   template. Twin judged no worse. Both follow-up investigations closed
   same-day by subagents: the "~3% framing delta" was a capture-viewport
   artifact in the original A/B — at equal viewport, rendered geometry is
   sub-pixel identical across all three renderer configurations, so the
   inherited SIZES ladder is calibrated correctly (the real cross-stack
   difference is tone/shading only); and the sortObjects defect was
   confirmed by minimal reproduction (3 meshes, both backends, 40/40 vs
   39/40) with two refinements — the trigger is a REVISITED state after a
   depth-order change (object motion suffices; camera cuts are the common
   case), and it is 100% deterministic on revisit, not flaky. An
   independent film review then found two HIGH semantic defects in gearbox
   (ring parked off the interlock; ratio trails asserting 1:1 against a
   3:1 caption) plus an uncovered loop seam — all fixed in 0.2.1, with the
   loop made seamless BY CONSTRUCTION (SPIN derived from TOTAL so both
   gears complete whole turns; final shot matches the opening shot). A doc
   audit caught three doc-vs-code drifts (inert vendor invocation, 2D
   contract overclaim, a nonexistent MaterialX export name), all fixed.
3. *Post plumbing active by default.* The template runs a pass-through
   `RenderPipeline` (neutral look; bloom behind a `STYLE` flag) so smoke's
   determinism and shipped-frame checks ride the post path on every scene —
   Phase 0's lesson is that the untested path is the broken path.
   **DONE 2026-07-23** (screenwright 0.3.0): pass-through preserves the
   direct-render look (identical exposure statistics), smoke green on both
   backends through the pipeline, `STYLE.bloom` and `STYLE.dof` verified
   deterministic and visually working, DoF wired to the solver's
   `shotFocus` — the `focus` shot property is no longer inert. gearbox
   regenerated on the post-path template and re-shipped.
4. *Material packs, trimmed:* toon, SSS skin, glass/dispersion — each
   verified on a small showcase subject. Fur and fabric move to Phase 2,
   where characters exist to test them on.
   **DONE 2026-07-23** (screenwright 0.4.0, `examples/materials.html` +
   `references/materials.md`): all three verified on both backends under
   byte-determinism. Two measured r185 traps now in the doc: the plain
   `transmission` PROPERTY never engages (the node slot works — recipe
   rule: node slots are the reliable interface), and Chang-SSS has no
   thickness input (thin/thick modeled as two materials). Cel is
   TSL-native banding — structurally immune to the ambient-wash failure.
   The glass beat carries the overlapping-transparency ordering case:
   farther-first creation composites correctly under sortObjects=false. **The glass pack pays the
   sortObjects bill:** unsorted drawing (determinism rule #5) composites
   transparency in creation order, and glass is nothing but overlapping
   transparency. The pack must ship an explicit ordering discipline
   (create/order farther-first; renderOrder where creation order cannot
   express it) and a test scene where transparent objects genuinely overlap
   and pass both determinism and a visual correctness look.
5. *Brackets re-measured, not imported.* The old bloom rule (threshold above
   sky-lit luminance, 3.2/8.0/14.0) was measured against `UnrealBloomPass`,
   which reads pre-tone-mapped values; the TSL bloom node is a different
   implementation and the numbers are presumptively stale. Same pass settles
   the template palette's standing crushed-exposure advisory.
   **PARTIAL 2026-07-23:** first TSL-bloom observations measured and
   recorded in materials.md (monotone, no cliff at 1.0 — appears
   pre-tone-map; emissives behind transmission barely feed it; palette-
   conditional as before). A full bracket waits for the first film that
   leans on bloom; the crushed-exposure advisory on the template palette
   remains open.
6. Style bibles v2 on the new stack.
   **DONE 2026-07-23** (screenwright 0.5.0, `references/bibles.md`): a
   bible IS the STYLE object — the solver and template already consume
   exposure/bloom/dof/lens/cutDur/energy, so the mechanism landed with no
   new machinery. gearbox ships the committed control pair
   (`workshop`/`neon`, one line apart): verified categorically different
   films, both byte-deterministic on both backends.

*Gate:* `gearbox` passes the comparison in (2); a committed control pair (two
bibles, one line apart, same beats) produces categorically different films;
the three material packs each demonstrated under byte-determinism.
**GATE MET 2026-07-23 — PHASE 1 COMPLETE** (screenwright 0.5.0): gearbox
comparison closed in 0.2.x, packs in 0.4.0, control pair in 0.5.0. Open
carry-forwards into later phases: full bloom bracket (first film that leans
on bloom), template-palette crushed-exposure advisory, `WEBGPU=vulkan`
unverified, upstream repro for the sortObjects defect unfiled.

*Post-gate quality pass (2026-07-23, screenwright 0.6.0):* the deliberately
deferred simplify review ran four angles (reuse, simplification, efficiency,
altitude) over the whole founding range and applied ~30 deduped findings —
shared `templates/backend.js` (browser/flag policy/settle, one copy for
recorder and gate), `RIG`/`DRIVER` parity fences covering all three
load-bearing determinism guards, contract exports over internals probing
(`window.CAPFADE`; flashes resolved once), `energy` single-homed in STYLE,
per-run vendor cache, and the `motion` second-browser launch removed.
Verified look-neutral: pre/post example frames byte-identical. Full ledger:
CHANGELOG 0.74.0. **Standing maintenance rule from this pass:** the fenced
blocks span `templates/` AND `examples/`, but a smoke run only checks the
files it is pointed at — after editing any fenced block, run
`bun run smoke.js --parity-only templates/*.html examples/*.html` (cross-
directory) before committing; a per-directory green does not cover the
template↔example boundary.

**Phase 2 — Character scaffold.** Skeleton family + proportion vectors +
shells; IK ported and extended; gait on the new rig; fur-shell and fabric
packs land here, tested on the characters they exist for. *Gate:*
`bear-and-bees` plus a human plus a text-invented creature, all from one
scaffold; each squint-distinct; walk cycles plant (no sliding feet on the
strip check).

*Step 1 DONE 2026-07-23 (screenwright 0.7.0):* the scaffold kit shipped as
`templates/scene.character.template.html` with a fifth parity fence
(`CHARACTER`) — skeleton family as one topology × proportion vector,
lathed/capsule shells from pure code (no data tables needed until morph
deltas arrive in Phase 3), ported two-bone IK generalized by bend direction,
plant-grid gait generalized to any planted-limb set, closed-form neck/tail
chains. Both the biped demo and a quadruped vector verified walking on both
backends; strip check confirms planted feet hold. `references/characters.md`
carries the vocabulary.

*Step 2 DONE 2026-07-23 (screenwright 0.8.0):* fur (shell layers in the
CHARACTER fence — normal-displaced geometry per layer, TSL noise coverage,
alphaTestNode discard so fur never touches the transparency-ordering bill;
byte-deterministic both backends on the quadruped) and fabric (sheen node
recipe on MeshPhysicalNodeMaterial, verified rendering — node slots, per the
transmission lesson).

*Step 3 DONE 2026-07-23 (screenwright 0.9.0):* `examples/menagerie.html` —
bear + human + text-invented strider from one buildCharacter, squint-distinct
(measured on the squint strip), planted (strip-checked per character),
byte-deterministic both backends, film-reviewer-reviewed with all HIGH
findings fixed (the look beat now carries on geometry in the nocap pass).
Kit addition from the review round: `rig.centerX` (subject aim at the visual
center, not the root — a root-aimed quadruped FS rendered a wall of rump).
**Phase 2 gate reading:** the scaffold criteria (three characters, one
scaffold, squint-distinct, planted) are demonstrated by menagerie;
`bear-and-bees` the comedy short remains open as the phase's film deliverable
and carries the comedic-timing half of the gate.

*Post-gate code review (2026-07-23, screenwright 0.9.1):* five-agent pass
over the 0.6.0–0.9.0 range. Fixed: shoot.js's swiftshader refusal had gone
dead in the backend.js extraction (called `angleArgs()` without
`refuseSwiftshaderShip: true` — the documented asymmetry existed only in
comments); the template demo missed two fixes that landed only in menagerie
(subject aim without `rig.centerX` cropped the FS at the feet — verified on
before/after sheets — and the backOut(ramp) breath held the walker 4%
squashed from frame 0); `solveLimb`'s clamp floor (absolute .2) inverted for
rigs with reach under .21, posing limbs beyond their own length — floor now
`min(.2, reach-.02)`, a proven no-op at shipped scales but load-bearing for
insect-scale rigs (the bees). Docs: webgpu-stack.md overclaimed
`MeshToonNodeMaterial` as exercised; film-language.md still said
`CONFIG.energy`. New carry-forward, dispositioned not fixed: character
material colors are hex literals in `buildCharacter` calls, not STYLE keys —
bibles.md's rule ("a hex literal in a material is a look decision hiding
from the bible switch") applies when the first character bible pair arrives;
palette keys move into STYLE then, not before.

*Simplify pass over the same range (2026-07-23, screenwright 0.10.0):* the
sixth parity fence, `HTML` — the shared page scaffold (overlay CSS + caption
DOM, carrying the will-change compositor hint) had silently reached five
identical unfenced copies; now HTML-comment-fenced in all five 3D scenes and
in smoke's parity loop (a second regex arm, since the block lives outside
`<script>`). Plus four small cleanups; ledger in CHANGELOG 0.78.0. The
standing cross-directory parity rule now covers six fences.

*Phase 2 GATE MET 2026-07-23 (screenwright 0.11.0):*
`examples/bear-and-bees.html` — the comedy short, carrying the
comedic-timing half of the gate (2.6s hush against a 1.1s eruption, locked
tableau camera, gag fully readable in the nocap pass). Film-reviewer pass
found three HIGHs, all fixed and re-measured: the flee launch clipped the
hive before the duck opened (now +0.01..+0.24 clearance through the pass);
the face never faced the camera (a `face` 3/4-turn envelope spot→hush puts
the blink and glance on screen); and the boop was a z-axis miss faked by
the camera (contact-bug class instance five — restaged to a probe-measured
surface graze, normalized 1.02, all three axes). Method notes: the paw-swipe
staging died on probe data (the muzzle out-reaches the foreleg on this
vector — a quadruped paw can never pass its own nose), and the neck-curl
sign convention was bracketed empirically (+z RAISES this rig's head —
menagerie's comment implies the opposite; trust the probe, not the comment).
New carry-forwards: one intermittent WEBGPU=metal smoke determinism FAIL
(1 in ~6 runs at t=17.04, never reproduced, cause unmeasured — the bee
visibility gate added in the same round is hygiene, NOT the fix); a
per-shot camera-energy override (the hush wanted `locked` while the film
wanted `steadicam` — no vocabulary for it, so the film went all-locked,
which suits this register but will not suit the next one).

**Phase 3 — The human.** Face morph basis, expression library, hands, hair
shells; `the-briefing`. *Gate:* the two-shot survives all three review axes;
expressions carry the beat in the nocap pass — the caption is not doing the
acting.

**Phase 4 — Physics bake.** Build-time Rapier step: simulate once, emit
sampled trajectories as scene data, play back pure. *Gate:* `rube-goldberg`
byte-deterministic across seeks and across re-bakes with the same seed;
`crowd-cross` if instancing wants baked variety.
*OWNER PRIORITY (2026-07-23):* the owner chose bake-time simulation as the
next creative direction after `bear-and-bees` ships — "simulated creativity
without an LLM". Phase 4 moves ahead of Phase 3 in priority. Runtime
determinism stays; the sim happens once at build time. Constraints, red
lines against tier drift, eval criteria and the spike list:
[physics_bake_proposal.md](physics_bake_proposal.md) — read it before
writing any Phase 4 code.
*Sibling direction (owner-agreed 2026-07-23):* the same tier-1 shape applied
to illumination — a **light bake** (path-traced GI / radiosity / probe solve
at build time, shipped as data, playback pure). Recorded in the same
proposal doc, including the finding that reflections themselves need NO bake
(SSR node, planar reflector, GTAO, environment lighting are pure functions
of scene state — available at runtime today at zero determinism cost).

**Phase 5 — Registers.** Cutscene and meme film-language extensions (dialogue
staging, comedic timing, title cards); `boss-intro` and `meme-remix`.
*Gate:* `meme-remix` authored start-to-shipped in one session by following the
skill docs alone.

**Phase 6 — Interactive spike.** Input driver over the unchanged kernel;
`museum-walk`. *Gate:* the spike reuses kernel, characters, materials, and at
least one instrument with zero modification — proving the layer split held.
This phase decides whether interactivity becomes a sibling skill or a
screenwright register; that decision is explicitly out of scope until the
spike exists.

## Examples policy (decided 2026-07-23, measured on a live install)

Examples stay in the plugin dirs. The mechanics, verified on this machine:
`/plugin marketplace add` shallow-clones the ENTIRE repo (~18 MB, of which
examples are ~9.8 MB) regardless of which plugin the user wants;
`/plugin install` then copies just that plugin's subtree — examples included —
into a per-version cache. So yes, examples ship; and no, it does not matter
for the concern that would actually bite: the Agent Skills spec loads ONLY
SKILL.md into context — `examples/` never auto-loads, so films are pure disk
weight, zero ambient-context cost. Moving them out would break what they pay
for: SKILL.md teaches by pointing at in-tree baselines, READMEs embed the
AVIFs by relative path, and delivery.md's own doctrine forbids the LFS
workaround (raw serves pointer files, breaking embeds).

Amended same day after owner pushback, and the amendment is better: the
teaching HTML files stay in-plugin (bundled — self-containment is doctrinal
and there is genuinely no way around embedding three without reopening the
shipped-broken-example class), but **rendered AVIF previews live in the
repo-level `docs/media/`, outside every plugin subtree**. They are
human-browsing artifacts with zero skill value (Claude never reads them;
only the HTML teaches). Examples READMEs embed them by relative path
(GitHub resolves across the tree), the per-version install cache stops
duplicating them, and no release-asset uploads are ever needed. The one
rule: SKILL.md must never cite anything outside the plugin subtree — the
install cache lacks `docs/`, so such pointers dangle for installed users.
Remaining disciplines: ship only examples something cites; cap AVIF encodes
near the ~0.3–1 MB band (the frozen skill's 2.3 MB pelican outlier is the
cautionary case). Related measured note: always-loaded SKILL.md size is the
real ambient cost (the frozen skill's is ~6.8K tokens, over the spec's <5K
guidance) — screenwright's SKILL.md stays lean by policy.

Amended 2026-07-23 (owner directive, clarified same day): the gate is
**owner approval, not rendering**. Nothing enters `examples/` until the
owner has seen it and approved it; test and interim scenes (and any interim
renders) live under gitignored `internal/` until promoted. But **once a
scene IS tracked in `examples/`, the preview set is mandatory and
consistent**: an AVIF in repo-level `docs/media/`, embedded in the examples
README so it renders on GitHub, alongside a link to the `.html` and a
description of what the example is and showcases. The examples README also
carries a standing callout above the listing: the AVIF is to the film what
a thumbnail is to a full image (720px/12fps/inline budget) — the HTML is
the artifact. The HTML remains the full-quality deliverable; the AVIF
exists so a browser of the repo can see the films without cloning.

## Anti-template principle

The recurring user fear to design against: tools so constrained they become
WordPress themes. The rule, stated once here and enforced in review: **the
skill ships contracts, kits, and vocabularies — never finished scenes.** A
style bible constrains *how* things look, not *what* is in the scene; the
character scaffold parameterizes *any* figure rather than shipping five
mascots; the film-language reference teaches shot grammar, not shot lists.
The test is always "could the user ask for something we did not anticipate and
have the pieces compose?" — the portfolio's text-invented `boss-intro`
creature exists to keep that test honest.

## Risks

- **Uncanny valley creep.** The stylized bar is a defense; the risk is drift
  toward realism one "just slightly more real" decision at a time. The bible
  system is the control: realism level is a bible property, reviewed there.
- **Instrument recalibration is real work.** Every measured bracket is
  per-backend. Budget it in Phase 0-1 rather than discovering it per-film.
- **Platform flag matrix.** WebGPU headless behavior differs by OS and
  Chromium build; the recorder owns a tested per-platform policy and smoke
  proves the black-frame catch on every platform the repo ships from.
- **Scaffold authoring cost.** The character data must be generated by
  committed build tooling, authored once — if it turns into per-character
  hand-authoring, the policy has silently become an asset pipeline.
- **Scope creep toward a game engine.** The driver split is the fence:
  screenwright ships films; interactivity is one spike behind a gate, and
  engine-shaped features (input handling, game state, audio mixing) are
  non-goals until Phase 6 reopens the question.
- **The three pin is now load-bearing beyond the API surface.** `seekTo`
  ticks `renderer._nodes.nodeFrame.update()` (private API) to defeat the
  shadow frameId guard. The upgrade ritual for any pin bump, in order: grep
  the new build for `nodeFrame`; run the full smoke matrix (fallback, metal,
  swiftshader-must-fail); re-run the bloom/exposure brackets if the post
  implementation changed. An upgrade that skips the ritual inherits Phase
  0's bugs with none of its instruments proven against the new build.

## Non-goals

- Photoreal humans.
- Runtime physics integration, runtime asset fetching, CDN anything.
- Editing existing video files, screen recordings, slide decks (unchanged
  from explainer-video).
- Audio: inherits the designed-but-unwired status; revisit after Phase 5.

## Appendix: external shader sources — portability and license reality

Internal reference only — deliberately NOT shipped with the plugin, and
shipped files carry no source annotations; the ledger below is the record.
The TSL third-party ecosystem is thin by design, so most looks get
hand-ported from published work; this map is where a port starts, and the
license check happens before the port.

**Classification rule.** Transliterated code inherits the source license —
record it in the ledger below.
Re-implementing an algorithm from a paper or article is not a license
event; a citation is traceability courtesy, nothing more. Runtime vs bake:
a noise function belongs in the node graph (runtime determinism rules do
not bend); anything iterative or stochastic — integrators, verlet,
relaxation, GI solves — belongs in the Phase 4 bake, seeded and pinned,
because its output ships as data.

**Port freely (permissive):**
- iquilezles.org (Inigo Quilez) — MIT article snippets. Cosine palettes,
  fbm/domain warping, smooth-min, the 2D SDF zoo.
- three.js source + `webgpu_*` examples — MIT. The TSL idiom cookbook.
- "Hash Without Sine" (Dave Hoskins, shadertoy 4djSRW) — MIT. The hash for
  custom lattices; no trig, no large intermediates.
- Google Filament PBR docs — Apache 2.0. Charlie sheen, cloth BRDF, skin
  SSS survey. Penner "Pre-Integrated Skin Shading" (SIGGRAPH 2011),
  Kajiya-Kay, GPU Gems fur — papers, cite on re-implementation.
- tsl-textures (boytchev) — MIT. Vendor per-generator, pin the commit.
- pmndrs/postprocessing — zlib. WebGL-bound code; pass-merging and
  dithering ideas transfer.

**Ideas only (no code copying):**
- lygia — Prosperity license (non-commercial). Use as an index; follow its
  headers to the permissive original and port from there.
- Shadertoy — default CC BY-NC-SA; check each shader's own header.
- Theatre.js — never embed (stateful runtime editor vs pure-f(t) and
  self-containment); its authoring ideas are free.
- Aggregator directories (threejsresources.com etc.) — index only;
  evaluate license and quality at each linked item's own source.

**Ledger of ports in shipped scenes:**

| Where | What | Source | License |
|---|---|---|---|
| 3D template + packs | MaterialX noise nodes (via `three/tsl`) | MaterialX, shipped in three | Apache 2.0 |
| `CHARACTER` fence (`addFur`) | Shell fur | GPU Gems "Fur — Fins and Shells" (idea) | citation |
| fabric recipe | Sheen via `sheenNode` | three.js / Filament lineage | MIT / Apache 2.0 |
| `examples/noise-chart.html` | `hws12` hash + value noise | Dave Hoskins, Hash Without Sine | MIT |
| `examples/noise-chart.html` | Cosine gradient palette | iquilezles.org/articles/palettes | MIT |
| `examples/noise-chart.html` | Domain-warped fbm (algorithm) | iquilezles.org/articles/warp (idea) | citation |
