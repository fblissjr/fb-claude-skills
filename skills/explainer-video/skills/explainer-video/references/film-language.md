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
`t` returning the subject's center, `h` its height, and optionally `w` its
width. A moving subject is a tracking shot for free. Craft rule, learned by
rendering: track a subject's *travel*, not its jumps — leave vertical action
out of `pos` so it moves in the frame instead of being cancelled by the camera.

**`h` means "the extent that must stay in frame", not "the subject's height".**
Three films cropped their own payoff by declaring the figure and forgetting the
prop: a robot's antenna, a cross-section's outer stations, a pelican's umbrella.
If a beat pays off on it, it is inside `h`.

**Declare `w` for anything wider than it is tall.** The size ladder below is
calibrated to subject HEIGHT — `f` is a fraction of the frame's height — and
the solver originally consulted nothing else. That is correct for an upright
subject and silently wrong for a wide one: on a bench 12.8 wide and 2.6 tall,
every rung tighter than WS framed less width than the subject occupied, so it
cropped. Measured at `h:4.3` on a 40° lens, the frame widths are EWS 44.4,
WS 17.8, FS 9.4, MS 5.6, MCU 3.7 — only the two widest rungs fit a 13-wide
subject at all, which collapses the variety the ladder exists to provide.
With `w` declared, framing binds on whichever axis is tighter, so the rungs
keep their cinematographic meaning on a timeline, an org chart, a waveform or
a supply chain. An upright subject (`w <= h * FRAME.aspect`) is unchanged.

Inflating `h` is NOT the fix — it pulls the camera back but leaves the subject
small in a tall empty frame. The other honest move is the one a
cinematographer would make anyway: push in on a **narrower named sub-subject**
for the detail beat, rather than trying to frame the whole wide thing tight.

**SIZES** — the ladder, calibrated to what a cinematographer means:

| size | subject height ÷ frame | aim anchor | reads as |
|---|---|---|---|
| EWS | 0.20 | .5 | speck in the world |
| WS | 0.50 | .5 | full body, generous air |
| FSA | 0.70 | .5 | full body with a little air — the workhorse |
| FS | 0.95 | .5 | full body tight |

| MS | 1.6 | .68 | waist up |
| MCU | 2.4 | .78 | chest up |
| CU | 3.6 | .84 | head |
| ECU | 6 | .88 | detail |

The first cut of this table shipped MS at full-shot framing and the rack's
second subject fell out of frame — sizes are conventions with meanings, not
free parameters. Per-shot `anchor:` overrides the aim height when a
composition needs it (the toybot rack aims low to hold the sign in frame).

**Subjects may name several things.** `subject: ['plank','hammer']` frames the
union box. Every causal beat is two objects and the space between them, and
hand-authoring a composite subject with an invented centre is the thing this
vocabulary exists to abolish. `focus:` takes a list too.

**`d` (depth), optional.** Declare it and the solver fits the **projected** box,
rotating the extent by the shot's angle. Measured on a real scene: identical
rung, identical declared size, varying only `angle` — 0° fitted, **−26° clipped
at the frame edge**, −45° fitted. An axis-aligned width is non-monotonic in
angle. With `d` undeclared the subject is treated as billboarded, which is what
every scene written before this assumed.

**`anchorX`, optional.** The ladder had a vertical anchor and none horizontal, in
both backends. That is why framing a named subject put its most important feature
at the frame edge, and why an author porting the ladder to 2D used one of its
seven rungs and framed regions instead.

**The solver** — `dist = max(h/f, wProj/(f·aspect)) / (2·tan(fov/2))`: size and
lens give distance, binding on whichever axis is tighter; `angle`/`elev` place the camera on that sphere; the aim rides the
subject. The projected fit rotates the box by **azimuth only** — a near-top-down shot of
a deep subject can still clip on depth. `size2`/`angle2` ease across the shot's duration — push-in,
pull-out, orbit — and a moving subject makes any shot a tracking shot.

**Cuts** — how a shot ENTERS: `hard` (default), `whip` (0.16s snap), `blend`
(0.8s dolly-morph). **`whip` is a fast cut, not a whip pan** — it differs from
`blend` only in duration, and without directional blur the ~3 transit frames read
as a snap with a stutter rather than a smear. Measured; use it for pace, not for
the effect its name suggests. `match: true` is the match-cut constraint: the entry must
carry identical framing vocabulary (size/angle/elev/fov/anchor) to the
previous shot — checked at load, throws loud. The toybot open is the worked
instance: MS on the sign plate, hard cut, MS on the bot's torso — the frames
rhyme because the compiler guarantees they must.

**Focus** — **requires a post chain with a `BokehPass`, which the base template
does not have.** `shotFocus` is solved every frame regardless, so a scene
scaffolded from the template that sets `focus:` gets silence; see
`examples/toybot-walk.html` for a scene that wires the chain. Each shot's DoF
plane sits on `focus` (default: its subject);
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
