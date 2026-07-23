# The node stack: WebGPURenderer, TSL, and the recorder

The renderer-specific half of screenwright's 3D backend. The universal method —
failure axes, beats discipline, determinism rules — is `method.md`; the shot
vocabulary is `film-language.md`. This file is what changed when the stack
moved from `WebGLRenderer` + GLSL to `WebGPURenderer` + TSL, and every claim in
it was measured on `three@0.185.1` during Phase 0 (2026-07-23).

## One renderer, two backends

`WebGPURenderer` resolves its backend at `init()`: a WebGPU adapter if the
browser offers one, else a transparent WebGL2 fallback — same scene code, same
TSL materials, visually identical composition (measured). Frames are NOT
byte-identical across backends, so byte-wise regressions must pin the backend
on both sides. The scene exports which backend actually ran as
`window.BACKEND` (`'webgpu' | 'webgl2'`), because the answer depends on both
launch flags and the Chromium build, and inferring it goes wrong.

The recorder's policy (`shoot.js` / `smoke.js`, same logic):

| Env | Effect |
|---|---|
| (nothing) | No WebGPU flags. Headless usually has no adapter; WebGL2 fallback. The universal, CI-safe default. |
| `WEBGPU=metal` | macOS hardware adapter (`--enable-unsafe-webgpu --use-angle=metal`). Verified. ~2.3x faster end to end (37 vs 87 ms/frame with post chain, screenshots included). |
| `WEBGPU=vulkan` | Linux hardware adapter. UNVERIFIED here; run smoke first. |
| `WEBGPU=auto` | metal on darwin, vulkan elsewhere. |
| `WEBGPU=swiftshader` | Software WebGPU. Diagnostic-only: ships flat frames on the playwright headless-shell build, warmth-dependently on others. `shoot.js` refuses it without `WEBGPU_UNSAFE_SHIP=1`; smoke's shipped-frame check exists exactly for it. |
| `ANGLE_BACKEND=...` | GL backend selection for the fallback path, unchanged from the old stack. Conflicts with `WEBGPU=` are rejected loudly. |

**The landmine that motivated all of this:** on macOS, `--enable-unsafe-webgpu`
WITHOUT `--use-angle=metal` hands Chromium a SwiftShader-WebGPU adapter whose
compositor ships the flat clear color — every frame, exit 0, deterministic,
captions crisp on top. Four instruments passed on it before the shipped-frame
check existed. Never hand-roll WebGPU flags; go through the env policy.

## The async boot contract

```js
await renderer.init();                       // resolves the backend
await renderer.compileAsync(scene, camera);  // pre-warms every material
window.BACKEND = renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2';
window.seekTo(0);
window.sceneReady = true;                    // ONLY now may the recorder capture
```

`renderAsync()` is deprecated in r185; after boot, the synchronous
`renderer.render()` inside `seekTo` is the verified path on both backends.

## The six determinism rules the node stack adds

1. **Time reaches shaders through one uniform.** `const uTime = THREE.uniform(0)`,
   set from `seekTo`. The TSL `time` node auto-increments off a wall clock —
   never import it. A node graph reading uTime is exactly as pure as a
   property set from `t`.
2. **The nodeFrame tick in seekTo is load-bearing.** Shadow maps update at
   most once per `nodeFrame.frameId` (`ShadowNode.updateBefore` — its guard
   overrides even `shadow.needsUpdate`), and frameId only advances in the
   renderer's internal rAF loop, never in `render()`. Two seeks in one browser
   tick would leave the second rendering with the first's shadow map —
   measured as a flaky byte-determinism failure confined to shadowed regions.
   `window.seekTo` therefore calls `renderer._nodes.nodeFrame.update()` before
   rendering. Private API, pinned at 0.185.1; smoke fails loudly if an upgrade
   renames it. Do not remove it because everything looks fine without it —
   everything looked fine without it.
3. **No temporal passes.** TRAA, afterimage, accumulation motion blur carry
   state across frames. The bundled TSL display passes (bloom, dof, film,
   chromaticAberration) are per-frame pure.
4. **No `ComputeNode` / storage buffers.** Stateful across dispatches, and the
   WebGL2 fallback cannot run them at all.
5. **`renderer.sortObjects = false` stays off.** Found by the gearbox
   regression film: with depth sorting on, a camera CUT reorders the draw
   list and per-object uniform state goes stale — objects render at a
   previous seek's pose, sticky across re-renders and settle time, on BOTH
   backends (~12% of determinism checks on a 25-mesh multi-shot scene).
   Isolated by ascending bisection: the same world under one static shot was
   clean; multiple shots broke it; sorting off fixed it 16/16. Not settle
   length (0.5s changed nothing), not culling, not transparency, not the
   internal animation loop, not nesting — each refuted in isolation.
   Consequence: transparent objects draw in CREATION order, so when
   transparent things overlap on screen, create the farther one first.
6. **`frustumCulled = false` on every mesh** (the template's `mesh()` helper
   does it). The per-mesh cull decision was measured consuming a stale pose:
   a mesh near the frustum edge rendered or vanished depending on which t the
   camera arrived from. Scenes here are tens of meshes; culling buys nothing.

## Recorder mechanics that differ from the old stack

- **Settle before screenshot.** `render()` queues GPU work; the compositor can
  present it a frame late, so the recorder settles one double-rAF between
  `seekTo` and every screenshot. Measured before the fix: flaky screenshot
  hashes over byte-identical canvas content. Scene contract is unchanged —
  `seekTo` stays synchronous.
- **The drawing buffer is cleared after compositing.** An in-page
  `drawImage(canvas)` readback in a LATER task reads zeros; render-and-read
  must share one `evaluate`. smoke's exposure sampler does this; copy that
  pattern for any new in-page pixel check.
- **smoke's shipped-frame check** opens a caption-stripped page (`?strip=text`)
  cold — before the main check page warms the GPU process — and fails if every
  sampled `t` ships the identical image or if the RICHEST sampled frame's luma
  spread is under `SHIPPED_SPREAD_FLOOR` (bracket: broken 1.7, healthy 3D
  161.3, flat 2D register 120.9). It measures the exact bytes the recorder
  writes, which is the only layer where "it renders" means anything.
- **Chromium resolution matters.** The managed-cache scan includes Apple
  Silicon layouts; without them the tools silently fell through to system
  Chrome — an auto-updating build that disagreed with playwright's pinned one
  about WebGPU. `CHROMIUM_PATH` overrides; keep the gate and the recorder on
  the same binary.

## The gearbox regression twin (measured 2026-07-23)

The same scene body (beats, worlds, shots, animate) injected into this
skill's template and frozen explainer-video's renders near-identically:
composition, lighting, and read match cell for cell on the contact sheets;
both pass their own smoke. Two honest residuals: a small constant framing
delta (~3% zoom) between the stacks at identical `t` — visible only in
direct A/B, unexplained, parked; and shadow acne on extruded faces at
closeup in BOTH stacks until `key.shadow.normalBias = .035` (a scene-rig
setting, not a stack difference). The shipped example is
`examples/gearbox.html` / `examples/gearbox.avif`.

## Node materials in scene code

Everything from `three/webgpu` and `three/tsl` is spread flat onto `THREE` by
the vendor bundle, plus `SkyMesh` and the display passes `bloom`, `dof`,
`film`, `chromaticAberration`. The template's demo material is the pattern:

```js
const mat = new THREE.MeshStandardNodeMaterial({ roughness: .35 });
const veins = THREE.mx_fractal_noise_float(
  THREE.positionLocal.mul(1.6).add(uTime.mul(.25)), 4, 2.0, .5, 1.0).mul(.5).add(.5);
mat.colorNode = THREE.mix(THREE.color(0x2a9d8f), THREE.color(0x8ad5c9), veins.smoothstep(.35, .8));
```

Zero assets: MaterialX noise (`mx_perlin_noise_float`, `mx_worley_noise_float`,
`mx_fractal_noise_float`, `mx_aastep`) computes on the GPU. Available and not
yet exercised here: `MeshPhysicalNodeMaterial` (transmission, `dispersion`,
sheen, iridescence — dispersion verified rendering in the founding spike),
`MeshSSSNodeMaterial`, `MeshToonNodeMaterial`. Post chains compose through
`THREE.RenderPipeline` (`PostProcessing` is its deprecated alias) — a
scene-plus-bloom chain passed byte-determinism on both backends in the spike;
wiring it into the template is Phase 1 work.

Bundle cost: 1.09 MB embedded per scene (vs 0.77 MB for the old WebGL stack).

## r185 notes carried over

`PCFSoftShadowMap` deprecated (use `PCFShadowMap`); `outputColorSpace`, not
`outputEncoding`; physical lighting is the only mode. `THREE.<removed>` is
`undefined`, not an error — smoke treats console warnings as failures for
exactly this class.
