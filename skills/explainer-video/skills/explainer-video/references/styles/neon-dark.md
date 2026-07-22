# Style pack: neon-dark

**Backends:** Canvas2D today; the natural 3D pack once the Phase 2 post chain
lands (its whole premise — glow — is bloom, which 2D fakes with layered
strokes and 3D will do properly with emissives + `UnrealBloomPass`).

**For:** energetic product/tech explainers — pipelines at night, "data as
light", anything whose register is momentum and signal rather than warmth or
precision.

## STYLE block (2D)

```js
const STYLE = {
  bg:      '#0b0e1a',                        // near-black blue
  ink:     '#8892b0',                        // muted structure — glow carries emphasis
  faint:   'rgba(136,146,176,.18)',
  accents: ['#ff3d81', '#00e5ff', '#ffe14d'],// magenta, cyan, electric yellow
  fontFamily: '"Avenir Next","Segoe UI",system-ui,sans-serif',
  stroke:  0.55,
  titleInk:'#e8ecff',
};
```

## Register

- **Fake bloom (2D):** draw a glowing element twice — once wide at low alpha
  (`lineWidth: stroke*4`, `globalAlpha: .25`), once tight at full. Budget it:
  structure stays in muted `ink`; only the *subject of the beat* glows. If
  everything glows, nothing does.
- **Easing:** `elasticOut` fits this register better than anywhere else —
  signals ring. `backOut` for UI-ish arrivals. Keep `quant` out; stop-motion
  fights the electric feel.
- **Camera:** movement reads well here — pushes and drifting sway are on
  brand. That makes this the pack where **AVIF vs WebP matters**: a moving
  camera on a dark field is exactly the moving-camera delivery case in
  `delivery.md`.
- **Trails:** the deterministic trail idiom (N samples of the position
  function at `t - i*dt`, alpha falling with i) is this pack's signature move.

## Hazards (predicted, not yet bracketed)

- The crush lint WILL be near its threshold by design — a near-black ground
  is the point. Judge by frames; a subject that separates cleanly at squint
  size is correct regardless of the percentile math.
- Accent-on-accent (magenta label on cyan fill) fails contrast both ways;
  labels stay `titleInk`/`ink`, never an accent.
