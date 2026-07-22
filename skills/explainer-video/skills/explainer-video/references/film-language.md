# Film language: shots as data

The cinematography layer: framing described the way a cinematographer would —
sizes, angles, lenses, cuts — compiled onto the camera per frame by the solver
in `scene.template.html`. Raw camera keyframes are gone from the template on
purpose: coordinates were never the author's intent; framing was.

Implemented in the **3D template** and proven on `examples/toybot-walk.html`,
which is authored with zero hand-written keyframes. The 2D backend keeps its
simpler `{x,y,zoom}` rail; a 2D solver analog is deliberately unbuilt until a
2D film wants shot vocabulary.

## The pieces

**SUBJECTS** — named things a camera can frame: `pos` is a pure function of
`t` returning the subject's center, `h` its height. A moving subject is a
tracking shot for free. Craft rule, learned by rendering: track a subject's
*travel*, not its jumps — leave vertical action out of `pos` so it moves in
the frame instead of being cancelled by the camera.

**SIZES** — the ladder, calibrated to what a cinematographer means:

| size | subject height ÷ frame | aim anchor | reads as |
|---|---|---|---|
| EWS | 0.20 | .5 | speck in the world |
| WS | 0.50 | .5 | full body with air |
| FS | 0.95 | .5 | full body tight |
| MS | 1.6 | .68 | waist up |
| MCU | 2.4 | .78 | chest up |
| CU | 3.6 | .84 | head |
| ECU | 6 | .88 | detail |

The first cut of this table shipped MS at full-shot framing and the rack's
second subject fell out of frame — sizes are conventions with meanings, not
free parameters. Per-shot `anchor:` overrides the aim height when a
composition needs it (the toybot rack aims low to hold the sign in frame).

**The solver** — `dist = h / f / (2·tan(fov/2))`: size and lens give
distance; `angle`/`elev` place the camera on that sphere; the aim rides the
subject. `size2`/`angle2` ease across the shot's duration — push-in,
pull-out, orbit — and a moving subject makes any shot a tracking shot.

**Cuts** — how a shot ENTERS: `hard` (default), `whip` (0.16s snap), `blend`
(0.8s dolly-morph). `match: true` is the match-cut constraint: the entry must
carry identical framing vocabulary (size/angle/elev/fov/anchor) to the
previous shot — checked at load, throws loud. The toybot open is the worked
instance: MS on the sign plate, hard cut, MS on the bot's torso — the frames
rhyme because the compiler guarantees they must.

**Focus** — each shot's DoF plane sits on `focus` (default: its subject);
`shotFocus` is solved per frame for scenes with a BokehPass. **A rack focus
is two adjacent shots differing only in `focus`, joined by `blend`** — the
focus distance interpolates with the same ease as the camera. No manual
distance math survives in scene code.

**Camera energy** — `CONFIG.energy`: `locked` (tripod), `steadicam` (gentle
drift), `handheld` (documentary nerves) — seeded `noise1` tracks, amplitude
riding `CONFIG.sway` so `build.js loop`'s held-camera warning stays honest.

## Deliberately not built yet

Earn-in rule: vocabulary enters when a film needs it, not before.

- **Dissolve / wipe** — needs a two-target composite; no film has wanted one.
- **ffmpeg-side edit lists** (`xfade`) — would fork the MP4 from the HTML
  artifact; stays out until something needs it, and then as an opt-in.
- **Cut rhythm as a style parameter** — belongs to the style bibles (Phase 4).
- **2D solver analog** — when a 2D film wants shot vocabulary.
