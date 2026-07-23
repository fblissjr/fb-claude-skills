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

## Invocation examples

- "Make a 30-second video of how our approval process flows"
- "Animate a boss-intro cutscene for this creature: ..."
- "Turn docs/data-flywheel.md into an explainer"
- "Make this joke an animated meme"

## Status

Phase 0 (foundation) of the plan is complete: templates, recorder, and
instruments ported to the node stack and gated green on both backends —
including a demonstrated catch of the flat-frame WebGPU failure mode. Later
phases (TSL material packs, the character scaffold, physics bake, registers,
the interactive spike) land here as they pass their gates.
