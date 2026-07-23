# screenwright

last updated: 2026-07-23

Deterministic animated films of any register — an explainer, a game cutscene,
a meme, a character short — as a self-contained HTML page, a frame-exact MP4,
or an animated WebP/AVIF that plays inline in a README. The successor to
`explainer-video` (now frozen), rebuilt on the three.js node stack:
`WebGPURenderer` with transparent WebGL2 fallback, TSL node materials, and
MaterialX procedural noise — zero assets, one file per scene.

The founding plan, architecture, and phase gates: `docs/internals/screenwright_plan.md`
in this repo.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install screenwright@fb-claude-skills
```

## Skills

| Skill | Description |
|---|---|
| `screenwright` | The full pipeline: spec -> scaffold -> three-axis review -> smoke gate -> delivery, on two backends (three.js node stack 3D, Canvas2D 2D) under one window contract |

## Requirements

**WebGPU is NOT required.** Scenes use three.js `WebGPURenderer`, which falls
back to its WebGL2 backend transparently when no WebGPU adapter exists — any
WebGL2-capable browser plays a scene, and the recorder's default headless path
is the WebGL2 fallback (CI-safe, no GPU needed). Hardware WebGPU is an opt-in
speedup for the recorder only (`WEBGPU=metal` on macOS, measured ~2.3x
faster); see `references/webgpu-stack.md` for the flag policy.

Tooling: `bun`, `three@0.185.1` + `playwright-core@1.61.1` (pinned), ffmpeg
on PATH; `avifenc` (libavif) for AVIF loops, `img2webp` (webp) for WebP loops.

## Invocation examples

- "Make a 30-second video of how our approval process flows"
- "Animate a boss-intro cutscene for this creature: ..."
- "Turn docs/data-flywheel.md into an explainer"
- "Make this joke an animated meme"

## Status

Phases 0 (foundation) and 1 (regression, post, shading) are complete:
templates, recorder, and instruments on the node stack, gated green on both
backends; the `gearbox` regression film judged no worse than its
frozen-skill twin; the cel/SSS/glass material packs verified under
byte-determinism; style bibles v2 with the committed `workshop`/`neon`
control pair. Phase 2 (the character scaffold) is demonstrated: one
parametric skeleton family with two-bone IK, planted gait, neck/tail
chains, and fur/fabric packs — `examples/menagerie.html` walks a bear, a
human, and an invented creature from one `buildCharacter`, squint-distinct
and strip-checked. The phase's film deliverable (`bear-and-bees`) and later
phases (physics bake, registers, the interactive spike) land as they pass
their gates.
