# Material packs: cel, subsurface, glass

Three verified recipes on the node stack, each shipped in
`examples/materials.html` and reviewed on the instruments. Every number and
gotcha here was measured on `three@0.185.1`, most of them the hard way.

## The property-vs-node trap (read first)

**The plain `transmission` material PROPERTY never engages on this stack** —
the material stores the value (verified) but renders fully diffuse, on both
backends, direct or through the pipeline. The NODE path works:

```js
const glass = new THREE.MeshPhysicalNodeMaterial({roughness:.06, thickness:.9, ior:1.5, dispersion:.12});
glass.transmissionNode = THREE.float(.95);   // THIS is what turns glass on
```

Assume any physically-featured property may share this fate until seen
rendering; the node slot is the reliable interface. (This is also why the cel
recipe below authors banding in the node graph rather than trusting
`gradientMap`.)

## Cel (toon)

TSL-native: quantize the key-light lambert into three crisp tones in
`colorNode`. Unlit base material, so ambient light CANNOT wash the bands
(the old stack's hemisphere-washes-toon lesson, solved structurally):

```js
const keyDir = THREE.vec3(6, 12, 8).normalize();       // match your key light
const nl = THREE.normalWorld.dot(keyDir).max(0);
const cel = new THREE.MeshBasicNodeMaterial();
cel.colorNode = THREE.mix(
  THREE.mix(THREE.color(0x8a3f1d), THREE.color(0xd9752e), THREE.step(.33, nl)),
  THREE.color(0xffb45e), THREE.step(.72, nl));
```

Outline: the inverted hull carries over unchanged — a `BackSide` dark shell
child at scale ~1.06 (`MeshBasicMaterial`, shadows off). Costume features
(eyes) sit PROUD of the face and the head biases toward the shot's angle so
they read — a face nobody framed is a face nobody sees.

## Subsurface (SSS)

`MeshSSSNodeMaterial`: setting `thicknessColorNode` ENABLES the scattering
term; tune with `thicknessDistortionNode/AttenuationNode/PowerNode/ScaleNode`.
The Chang-style model has **no real thickness input** — a constant
thicknessColor glows the whole mesh uniformly (measured: a lightbomb). Model
thin-vs-thick yourself: one material per regime.

```js
const skin = new THREE.MeshSSSNodeMaterial({color: 0xe8a2a0, roughness: .55});
skin.thicknessColorNode = THREE.color(0xff5f45);
skin.thicknessDistortionNode = THREE.float(.25);
skin.thicknessAttenuationNode = THREE.float(.55);
skin.thicknessPowerNode = THREE.float(2.2);
skin.thicknessScaleNode = THREE.float(2.2);    // THICK parts: subtle
const thin = skin.clone();
thin.thicknessScaleNode = THREE.float(10);     // THIN parts (ears): the glow
```

It only reads with a light BEHIND the subject: a `PointLight` at ~2 world
units behind, intensity ~2.2 (measured: 4.5 clips thin parts to white, 26 is
a supernova), ramped per-beat as a pure function of t.

## Glass

```js
const glass = new THREE.MeshPhysicalNodeMaterial({
  roughness: .06, metalness: 0, thickness: .9, ior: 1.5, dispersion: .12,
  attenuationColor: new THREE.Color(0xd6f2ff), attenuationDistance: 3.5});
glass.transmissionNode = THREE.float(.95);     // see the trap above
```

**Ordering discipline (the sortObjects bill):** with `sortObjects=false`,
transparent and transmissive objects composite in CREATION order. Create
farther-first — in the showcase: emissive core, then glow disc, then far orb,
then near orb. Verified: the overlap zone composites correctly and the scene
is byte-deterministic on both backends. When creation order cannot express
the ordering (objects that swap depth mid-film), set `renderOrder` explicitly
— and accept that a genuinely depth-swapping transparent pair is currently
outside the guarantee.

## Bloom (first observations, not yet a rule)

Measured on the showcase's emissive-behind-glass payoff, sweep .3→1.5:
threshold is monotone with NO cliff at 1.0 (input appears pre-tone-map), but
the spread was ~1 mean-luma point — emissives seen THROUGH transmission
barely feed bloom. The same strength at threshold .55 visibly halated the
template's pale palette. So, as with the old stack: **what blooms is
palette-conditional** — bracket on your film's own palette before trusting
any number, and put emissives you want haloed in direct view, not behind
glass.
