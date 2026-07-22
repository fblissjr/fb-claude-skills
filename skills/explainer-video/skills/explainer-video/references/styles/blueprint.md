# Style pack: blueprint

**Backend:** Canvas2D (`scene2d.template.html`).

**For:** technical/architectural register — system diagrams, data flow,
infrastructure, anything where the claim is precision. The look is an
engineering drawing: line work on a deep blue ground, no fills, everything
draws itself on.

## STYLE block

```js
const STYLE = {
  bg:      '#122e4c',                        // blueprint ground
  ink:     '#dcebff',                        // near-white line work
  faint:   'rgba(220,235,255,.22)',          // construction lines / grid
  accents: ['#7fd4ff', '#ffd166', '#8affc1'],// cyan signal, amber warn, green ok
  fontFamily: '"Avenir Next","Segoe UI",system-ui,sans-serif',
  stroke:  0.45,                             // fine lines — precision register
  titleInk:'#dcebff',
};
```

## Register

- **Easing:** `ss()` only. No overshoot, no elastic, no stop-motion — a
  drawing does not bounce. Personality comes from *draw-on order*, not curves.
- **Draw-on is the entire vocabulary:** boxes trace their outlines
  (`drawOn` around the perimeter), connectors extend, hatching fills.
  Nothing pops into existence.
- **No fills.** Emphasis = double-stroke, hatching, or an accent-colored
  outline — never a filled shape. The one exception: a payload dot may be
  solid, because it is the subject.
- **Camera:** locked. `sway: 0`, zooms only between beats if at all. The
  drawing is the star; the camera is a drafting table.
- **Grid:** a faint construction grid (from `faint`, spacing ~8 world units)
  grounds the register — draw it first, at low alpha, held for the whole film.

## Hazards

- `stroke: 0.45` may vanish on the squint strip — check the silhouette pass
  and thicken toward 0.6 before adding detail. (Predicted, not yet bracketed.)
- Dark ground + thin light lines sits in the exposure lints' territory by
  intent. **Observed:** the dynamic-range lint fired at 10.2 on this pack
  applied to the placeholder scene, with every frame legible on review —
  judge by looking, not by the percentile.
- Labels on accent fills must go through `contrastOn()` — the first version
  of that helper assumed dark-ink-on-light-paper and put light text on this
  pack's amber fill; it now picks whichever of ink/bg is farther in luminance
  from the fill, which is polarity-safe.
