# Style pack: paper-cutout

**Backend:** Canvas2D (`scene2d.template.html`) — this is its default look,
documented here so it is a *choice*, not an accident.

**For:** warm, friendly process explainers — onboarding, how-a-thing-works,
anything where the register is "hand-made diagram", not "engineering drawing".

## STYLE block

```js
const STYLE = {
  bg:      '#f4efe7',                        // paper
  ink:     '#26221c',                        // linework and canvas labels
  faint:   'rgba(38,34,28,.28)',             // not-yet-active linework
  accents: ['#e05d3d', '#2a9d8f', '#e9b44c'],// warm red, teal, mustard
  fontFamily: '"Avenir Next","Segoe UI",system-ui,sans-serif',
  stroke:  0.7,                              // chunky — thin lines break the cutout illusion
  titleInk:'#26221c',
};
```

## Register

- **Easing:** `backOut` for arrivals (things land with a settle), `elasticOut`
  budgeted for ONE payoff, `quant(t, 8)` on decorative motion — the stop-motion
  wobble is what sells "hand-made".
- **Camera:** mostly held (`sway: 0`); one push-in per film is plenty. This
  pack ships as an inline WebP loop comfortably because so much of the frame
  is flat paper.
- **Cuts:** hard cuts under flashes read fine; dissolves fight the flat look.
- **Fills:** accents arrive WITH their beat (ramp the fill alpha), never
  pre-filled — the film's color accumulating is the progress indicator.

## Hazards (observed)

- Label ink on accents must go through `contrastOn()` — white-on-mustard
  shipped once in the template's first render.
- The dynamic-range lint can read low on this style; that is the metric's
  blind spot, not a defect — **observed**: the committed film in this pack
  (`examples/one-scene-every-format.html`) measures 0.0 at its flattest
  sample with every frame legible on review. Judge frames by looking (see
  the threshold note in `smoke.js`).
