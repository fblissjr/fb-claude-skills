#!/usr/bin/env bun
// Build pipeline: scene source -> offline bundle -> frames -> mp4.
// The scene file is the single source of truth; everything here is derived,
// so deriving it is one command instead of shell archaeology.
//
//   bun run build.js vendor                   -> three.global.js beside the scene
//   bun run build.js bundle <scene.html>      -> <scene>.bundled.html (three inlined)
//   bun run build.js frames <scene.html> [fps]-> frames/ via shoot.js
//   bun run build.js video  <name> [fps]      -> <name>.mp4 from frames/
//   bun run build.js all    <scene.html> [fps]-> vendor + bundle + frames + video
//   bun run build.js loop   <scene.html> [fps] [w] -> <name>.webp, inline in a README (decodes smoothly; wants a held camera)
//   bun run build.js avif   <scene.html> [fps] [w] -> <name>.avif, inline, much smaller file (decode-heavy at playback)
//   bun run build.js poster <scene.html> [t] [w]   -> <name>.jpg still + markdown snippet
//   bun run build.js sheet  <scene.html> [w] [frac] -> <name>.sheet.jpg contact sheet + .squint.jpg
//   bun run build.js strip  <scene.html> <t0> <t1> [fps] -> <name>.strip.jpg, consecutive frames
//   bun run build.js motion <scene.html> [fps]     -> per-beat motion profile + dead air, no files kept
//
// Prereqs: bun add three@0.185.1 playwright-core@1.61.1 ; ffmpeg on PATH.
// `avif` needs avifenc (macOS: brew install libavif); `loop` needs img2webp
// (macOS: brew install webp).
// execFileSync, not execSync: no shell means no quoting rules to get wrong, and
// a path containing a space cannot break the command. Same class of bug as the
// exec-form rule for hooks in docs/internals/plugin-patterns.md -- that rule
// covers hooks.json and says nothing about plugin scripts, but the surface is
// identical.
const { execFileSync } = require('child_process');
const run = (cmd, args, opts = {}) => execFileSync(cmd, args, { stdio: 'inherit', ...opts });
const fs = require('fs');
const path = require('path');

// three dropped its UMD build after 0.160 (`build/three.min.js` no longer
// exists), and its ESM build splits across three.module.min.js +
// three.core.min.js. We can't use ESM in the scene either: Chrome CORS-blocks
// module imports over file://, and opening the scene straight from disk is the
// point. So we bundle three ourselves into one classic script that sets
// window.THREE — same ergonomics the old UMD build had, no network, no CDN.
// Review passes capture JPEG: ~6x faster than PNG over the identical readback
// path, and they tile to .jpg anyway. Measurements (motion) and deliverables
// (frames/all) override this back to png -- a frame-difference metric must not
// eat JPEG artifacts, and a master must stay lossless.
const REVIEW_FMT = 'jpeg';
const REVIEW_EXT = REVIEW_FMT === 'jpeg' ? 'jpg' : 'png';
// One place for the output-basename rule, including the .bundled legacy suffix
// now that nothing produces .bundled.html.
const outBase = s => s.replace(/(\.bundled)?\.html$/, '');
const VENDOR = 'three.global.js';
const VENDOR_TAG = /<script src="\.\/three\.global\.js"><\/script>/;

function vendor(dir = process.cwd(), target = null) {
  const out = path.join(dir, VENDOR);
  const entry = path.join(dir, '.three-entry.js');
  // The post-processing addons ride in the same bundle, attached to the THREE
  // namespace (THREE.EffectComposer etc). Always included: they cost bundle
  // bytes when unused, and the alternative — a second vendor file with its own
  // staleness and load-order rules — costs a failure mode. Determinism note
  // for scene authors: every pass here is per-frame pure; temporal passes
  // (TAA, accumulation motion blur) are NOT bundled and must stay out — they
  // carry state across frames and break the seekTo byte-identity contract.
  fs.writeFileSync(entry, [
    "import * as THREE from 'three';",
    "import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';",
    "import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';",
    "import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';",
    "import {BokehPass} from 'three/addons/postprocessing/BokehPass.js';",
    "import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';",
    "import {Sky} from 'three/addons/objects/Sky.js';",
    "globalThis.THREE = Object.assign({}, THREE, {EffectComposer, RenderPass, UnrealBloomPass, BokehPass, OutputPass, Sky});",
    "",
  ].join('\n'));
  try {
    // --format=iife is required, not cosmetic: the scene is a classic script, so
    // an esm/plain bundle's top-level identifiers land in global scope and
    // collide with scene variables (a minified `MW` shadowed one and broke the
    // example). IIFE keeps the library's internals to itself, exactly as the old
    // UMD build did; only globalThis.THREE escapes.
    run('bun', ['build', entry, '--target=browser', '--format=iife', '--minify', '--outfile', out]);
  } finally {
    fs.unlinkSync(entry);
  }
  // EMBED, then delete the .js. The library is a build input, never a shipped
  // artifact: a scene that loads it via <script src> is not self-contained, and
  // the moment anyone copies or commits just the .html it silently renders
  // nothing. That shipped -- a committed 3D example sat in examples/ with a
  // dangling ./three.global.js reference and did not run at all. Embedding is
  // the only form that makes "opens straight from disk" true by construction,
  // so the tooling does it automatically rather than asking authors to remember
  // a bundle step. Cost is ~0.73 MB per scene, paid once, and accepted.
  const embedded = target ? embedInto(target, fs.readFileSync(out, 'utf8')) : [];
  fs.unlinkSync(out);
  if (embedded.length) console.log('embedded three into: ' + embedded.join(', '));
  else console.log('vendored three (no scene in ' + dir + ' had a vendor tag to embed into)');
  return embedded;
}

// Splice the library into every .html in `dir` that still carries the vendor
// tag. Replacement MUST be a function, not a string: in a string replacement
// `$&`, `$'` and `` $` `` are substitution patterns and minified three contains
// `$&`, which would splice the matched tag into the middle of the library. Also
// split any literal </script> so the library cannot terminate the host tag.
function embedInto(target, lib) {
  // ONE file: the scene we were asked about. An earlier version walked the whole
  // directory and rewrote every .html carrying the tag, which meant running any
  // command on a scene sitting beside the template it was copied from silently
  // rewrote `scene.template.html` itself with 0.77 MB of inlined three.js — and
  // the result looks idempotent, so nothing ever flags it.
  const inline = '<script>' + lib.replace(/<\/script>/gi, '<\\/script>') + '</script>';
  const html = fs.readFileSync(target, 'utf8');
  if (!VENDOR_TAG.test(html)) return [];
  fs.writeFileSync(target, html.replace(VENDOR_TAG, () => inline));
  return [path.basename(target)];
}

// bundle() is now an ASSERTION, not a transform. Vendoring embeds the library
// directly into the scene (see vendor/embedInto), so a scene is self-contained
// by the time anything can open it and there is no second ".bundled.html"
// artifact to keep in sync. Kept as a command because callers and habits refer
// to it, and because "make sure this file is self-contained" is still a thing
// worth being able to ask for. Idempotent: safe to run any number of times.
function bundle(src) {
  ensureVendor(src);                       // embeds in place if the tag is still there
  const html = fs.readFileSync(src, 'utf8');
  if (VENDOR_TAG.test(html)) {
    throw new Error(`could not embed three into ${src} — vendor tag still present`);
  }
  // Then assert the PROPERTY, not one spelling of one tag. The check above only
  // knows the canonical `<script src="./three.global.js"></script>`; a scene
  // referencing anything external under any other spelling -- single quotes, a
  // CDN, a differently-named bundle -- passed "self-contained" while pointing at
  // a file that would not travel with it. That failure already shipped once: a
  // committed 3D example carried a dangling reference and rendered nothing at
  // all.
  //
  // Two subtleties, both found by controls rather than by reasoning:
  //  - HTML permits UNQUOTED attribute values, so `src=./evil.js` is valid and
  //    an approximation requiring quotes waves it through -- the same
  //    "knows one spelling" defect one level down. Hence the optional-quote
  //    alternation.
  //  - It is not only <script>. A Canvas2D scene is likelier to pull a font or
  //    stylesheet than a script, so restricting this to <script src> made the
  //    guarantee weakest exactly where it was advertised strongest. <link>,
  //    <img>, <iframe>, <video>, <audio>, <source>, <track> and <embed> travel
  //    the same way. <a href> is deliberately NOT included: a hyperlink is not
  //    an embedded resource and a scene may legitimately link out.
  // data: and blob: URIs are genuinely self-contained and are allowed.
  const EXTERNAL_REF =
    /<(?:script|link|img|iframe|video|audio|source|track|embed)\b[^>]*?\b(?:src|href)\s*=\s*(?:"(?!data:|blob:)[^"]*"|'(?!data:|blob:)[^']*'|(?!["']|data:|blob:)[^\s>]+)/i;
  const ext = html.match(EXTERNAL_REF);
  if (ext) {
    throw new Error(`${src} is not self-contained — external reference remains: ${ext[0].trim()}`);
  }
  console.log(`self-contained -> ${src}`);
  return src;
}
function ensureVendor(scene) {
  const dir = path.dirname(path.resolve(scene));
  let src = '';
  try { src = fs.readFileSync(scene, 'utf8'); } catch (e) { return; }
  if (!VENDOR_TAG.test(src)) return;
  // NEVER embed into a shipped template. Embedding is right for an authored
  // film -- that is what makes it self-contained -- but a *.template.html is a
  // 32 KB starting point that must KEEP its vendor tag to stay readable and
  // copyable. Running any command on one used to silently inflate it with
  // 0.77 MB of inlined three.js, and because the result is idempotent nothing
  // ever flagged it; it reached `git add` once. Copy the template first, then
  // work on the copy -- which is what the workflow says to do anyway.
  if (/\.template\.html$/.test(path.basename(scene))) {
    throw new Error(
      `refusing to embed three into ${path.basename(scene)} — it is a shipped `
      + `template and must keep its vendor tag. Copy it to a working scene first.`);
  }
  vendor(dir, path.resolve(scene));                             // embeds THIS scene only
}

// dir defaults to the SAME expression video() uses, so the shoot half and the
// encode half of `all` can never disagree about where frames live. It used to
// default to a bare 'frames', which then OVERRODE an ambient FRAMES_DIR on its
// way to shoot.js while video() still honoured that ambient value -- so
// `FRAMES_DIR=X build.js all` shot into frames/ and encoded from X/. That is
// the same ship-the-wrong-film failure video()'s comment below describes, just
// reintroduced through the other half of the pair, and it is SILENT whenever X
// already holds frames: measured, a stale single frame in X produced a 0.0 MB
// one-frame mp4 and exit 0. Callers that deliberately own a scratch dir
// (sheet/loop/avif/strip) still pass one explicitly and are unaffected.

/* ---------- workspace: ONE door to scratch space -----------------------------
   Every review command used to hardcode its own dir name in the CWD
   (.sheetframes, .motionframes, .stripframes, .aspectframes, .loopsrc,
   .loopframes, .avifsrc, .avifframes) and rmSync it at entry AND in finally.
   Five independent agents hit the consequence: two commands in one directory
   silently corrupt each other. Measured worst case, two concurrent `frames`
   runs produced a single dir holding 3 frames from one film and 70 from
   another — 73 where one film alone needs 74 — and the next encode would have
   shipped that chimera without a word.

   Suffixing each of the six names with a pid would be the bandaid, and it is
   the wrong shape: the seventh command someone adds will hardcode a seventh
   name. So there is one function, and it is the only way to get scratch space.
   A new command gets isolation for free, which is the whole point. */
function workspace(scene, tag) {
  const base = path.basename(String(scene || 'scene')).replace(/\.[^.]+$/, '').replace(/[^\w.-]/g, '_');
  const dir = `.wk-${base}-${tag}-${process.pid}`;
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}


function frames(scene, fps = 30, dir = process.env.FRAMES_DIR || 'frames') {
  ensureVendor(scene);
  run('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'full', String(fps)],
      { env: { ...process.env, FRAMES_DIR: dir, SHOOT_FORMAT: 'png' } });
}

function video(name, fps = 30) {
  const out = outBase(name) + '.mp4';
  // Honour the same override shoot.js does. video() hardcoded 'frames/' while
  // shoot.js read FRAMES_DIR, so a hand-run `FRAMES_DIR=shots shoot.js ... full`
  // followed by `build.js video` silently encoded the STALE frames/ from a
  // previous render -- shipping the old film, which is the exact failure the
  // stale-tail fix exists to prevent.
  const dir = process.env.FRAMES_DIR || 'frames';
  run('ffmpeg', ['-y', '-framerate', String(fps), '-i', path.join(dir, 'f%05d.png'),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', out]);
  const bytes = fs.statSync(out).size;
  console.log(`encoded -> ${out} (${(bytes / 1048576).toFixed(1)} MB)`);
  // crf 17 is chosen for quality, and for anything past ~20s it lands well over
  // the 10MB ceiling on a GitHub issue/PR attachment -- which is the ONLY way to
  // get a real player, since a repo-relative mp4 is served as text/plain. So the
  // pipeline's own output could not be delivered the way poster() tells you to
  // deliver it, and the fix was left to be rediscovered by hand every time. A
  // 39s film came out at 19MB and needed a manual crf 24 pass to reach 8.3MB.
  if (bytes > ATTACH_LIMIT) {
    const small = out.replace(/\.mp4$/, '-small.mp4');
    // Limit read from the constant, not typed into the string: a forced test of
    // this branch printed "0.2 MB exceeds the 10MB limit", which is the shape of
    // a message that will lie the first time anyone edits the constant.
    console.error(`\nWARNING: ${(bytes / 1048576).toFixed(1)} MB exceeds the ` +
      `${(ATTACH_LIMIT / 1048576).toFixed(0)}MB attachment limit, so this` +
      `\nfile cannot be dragged into an issue/PR composer -- and that is the only route` +
      `\nto an inline player. Re-encode at a higher crf:\n` +
      `\n  ffmpeg -i ${out} -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p \\` +
      `\n         -movflags +faststart ${small}\n`);
  }
}

// GitHub renders animated WebP inline in markdown; it does NOT render a
// repo-relative mp4 as a player. Mechanism (verified by fetching both): GitHub's
// raw endpoint serves .webp as `image/webp`, but serves video as
// `text/plain; charset=utf-8` with X-Content-Type-Options: nosniff, so no
// browser will treat it as media. <video> is stripped from GFM on top of that.
// So `loop` is the output that embeds in a README, and mp4 is the output you
// attach via an issue/PR composer to get a real player.
//
// Do not track the .webp under Git LFS — raw returns the pointer file, not the
// image, and the README shows a broken image.
//
// Sizing is the whole game — GitHub's cap is 10MB. Measured on the 12s template
// scene at 960px/24fps: mp4 0.52MB, gif 12.08MB, webp 15.56MB. WebP loses to GIF
// there because the template's camera sway moves every pixel every frame, which
// defeats inter-frame compression. Hold the camera (CONFIG.sway = 0) and keep it
// short; see references/delivery.md.
//
// ...unless you ship AVIF, which dissolves the size side of that constraint but
// adds a playback cost. Same 12s moving-camera scene re-measured today: webp
// 15.16MB (reproducing the number above), mp4 0.68MB, AVIF 0.28MB. On the
// held-camera example: webp 0.195MB, AVIF 0.029MB. AVIF is an AV1
// keyframe-plus-deltas stream, so it inter-frame compresses the way the mp4 does
// instead of collapsing like WebP. But that same AV1 sequence is decoded in
// software at playback (no hardware video path), so it costs decode CPU and was
// observed to stutter on modest hardware. So `loop` (WebP) and `avif` are peer
// options with different costs -- WebP's is on disk, AVIF's is at playback --
// choose by camera style and audience hardware.
const LOOP_LIMIT = 10 * 1024 * 1024;
// Same 10MB number, different mechanism: LOOP_LIMIT is the inline-image cap a
// committed .webp has to fit under, ATTACH_LIMIT is the issue/PR upload cap an
// .mp4 has to fit under. Named separately so changing one does not silently
// move the other.
const ATTACH_LIMIT = 10 * 1024 * 1024;

// Shoot the scene into srcDir, scale each frame into tmpDir, and return the
// scaled PNG paths in order. The shoot->scale->glob prefix is identical for
// every animated inline export; only the final encoder call differs, so both
// avif() and loop() share this and diverge only at the encode step.
function shootAndScale(scene, fps, width, srcDir, tmpDir) {
  frames(scene, fps, srcDir);
  fs.mkdirSync(tmpDir, { recursive: true });
  run('ffmpeg', ['-y', '-i', path.join(srcDir, 'f%05d.png'), '-vf', `scale=${width}:-2`,
    path.join(tmpDir, 'f%05d.png')], { stdio: ['ignore', 'ignore', 'inherit'] });
  const pngs = fs.readdirSync(tmpDir).filter(f => f.endsWith('.png')).sort()
                 .map(f => path.join(tmpDir, f));
  if (!pngs.length) throw new Error('no scaled frames in ' + tmpDir);
  return pngs;
}

// The small-file inline output. Same shape as loop() -- shoot, scale, encode --
// but avifenc instead of img2webp, and no sway warning, because sway is not what
// costs an AVIF anything. Wins decisively on size, but that is not the whole
// picture: an animated AVIF is an AV1 still-image sequence, decoded in software
// frame by frame with no hardware video path, so it costs decode CPU at playback
// and was observed to stutter on modest hardware (worse in macOS Preview than
// Chrome). loop() (WebP) trades that away -- larger on disk, but smooth to play
// and verified rendering inline. Peer options, chosen by camera style and
// audience hardware, not a ranking. The -s knob below is encode-time only; it
// cannot make an AVIF cheaper to PLAY.
//
// -s 6 is the measured knee on encoder speed: s8 produced files 2.3x larger for
// one second less, s4 gave no further size gain for double the time. Encoding
// 288 frames costs ~11s, negligible against the ~65s it takes to shoot them.
// -q 60 matches what `loop` passes img2webp; decoded frames were inspected and
// hold up (crisp overlay text, smooth gradients, SSIM 0.97 against source).
//
// Verifying the output is animated: use `avifdec --info <file>`, which prints
// "N frames" and the repeat count. Do NOT use ffprobe -- it reports an animated
// AVIF as a single frame, which reads exactly like "avifenc silently wrote a
// still" and would send you rewriting a working encoder. Cross-check by size if
// unsure: one 960px still of this scene is 7.3KB against 290KB for the 288-frame
// sequence, so a sequence that collapsed to a still is off by a factor of 40.
function avif(scene, width = 720, fps = 12) {
  const base = outBase(scene);
  const out = base + '.avif';
  const src = workspace(scene, 'avifsrc'), tmp = workspace(scene, 'avif');
  // workspace() already created these fresh; only the finally-clean is needed.
  const clean = () => { for (const d of [src, tmp]) fs.rmSync(d, { recursive: true, force: true }); };
  try {
    const pngs = shootAndScale(scene, fps, width, src, tmp);
    // Same dependency shape as img2webp for the webp path: a separate encoder
    // binary, because the ffmpeg most people have does not reliably mux an
    // animated AVIF even when it can encode AV1.
    try { execFileSync('avifenc', ['--version'], { stdio: 'ignore' }); }
    catch (e) { throw new Error('avifenc not found — install it (macOS: brew install libavif)'); }

    run('avifenc', ['--fps', String(fps), '-q', '60', '-s', '6',
      '--repetition-count', 'infinite', ...pngs, out]);
  } finally {
    clean();
  }

  const bytes = fs.statSync(out).size;
  const mb = (bytes / 1048576).toFixed(3);
  console.log(`avif -> ${out} (${mb} MB, ${width}px @ ${fps}fps)`);
  if (bytes > LOOP_LIMIT) {
    console.error(`WARNING: ${mb} MB exceeds GitHub's 10MB inline limit. ` +
                  `Shorten it or drop to ${Math.round(width * 0.75)}px.`);
  }
  return out;
}

function loop(scene, width = 720, fps = 12) {
  const base = outBase(scene);
  const out = base + '.webp';
  // Warn about sway BEFORE shooting a single frame. Without this, the 10x-90x
  // size penalty documented above LOOP_LIMIT is only discovered after the full
  // shoot-and-encode has already run -- expensive to find out, and expensive to
  // find out AGAIN if the fix (CONFIG.sway = 0) gets missed and re-run.
  try {
    const sceneSrc = fs.readFileSync(scene, 'utf8');
    const swayMatch = sceneSrc.match(/sway:\s*([0-9.]+)/);
    if (swayMatch && Number(swayMatch[1]) > 0) {
      console.error(`WARNING: ${scene} has CONFIG.sway = ${swayMatch[1]}. Camera sway moves ` +
        'every pixel every frame, which defeats WebP inter-frame compression -- measured ' +
        '10x-90x on file size (see the note above LOOP_LIMIT). Set CONFIG.sway = 0 for an inline loop.');
    }
  } catch (e) { /* unreadable scene source is not this check's problem -- the shoot below will fail loudly instead */ }
  // Shoot into our OWN directory. `loop` used to reuse frames/, which silently
  // overwrote the full-resolution frames a previous `build.js all` had shot --
  // so making a README loop destroyed the source of your mp4 with no warning.
  const src = workspace(scene, 'loopsrc'), tmp = workspace(scene, 'loop');
  // workspace() already created these fresh; only the finally-clean is needed.
  const clean = () => { for (const d of [src, tmp]) fs.rmSync(d, { recursive: true, force: true }); };
  try {
  // Explicit file list (from shootAndScale) rather than a shell glob. This does
  // NOT dodge ARG_MAX -- execFileSync argv goes through the same execve limit --
  // it buys deterministic ordering and a loud failure when scaling produced
  // nothing, rather than img2webp receiving an unexpanded literal.
  const pngs = shootAndScale(scene, fps, width, src, tmp);

  // Homebrew's ffmpeg ships without libwebp, so `-c:v libwebp` fails with
  // "Encoder not found". img2webp (from the `webp` package) is the reliable
  // encoder and is what we require.
  try { execFileSync('img2webp', ['-version'], { stdio: 'ignore' }); }
  catch (e) { throw new Error('img2webp not found — install it (macOS: brew install webp)'); }

  run('img2webp', ['-loop', '0', '-d', String(Math.round(1000 / fps)), '-q', '60',
    ...pngs, '-o', out]);
  } finally {
    // finally, not only on success: a failed run left .loopsrc and .loopframes
    // full of PNGs in the scene directory, where `git add -A` sweeps them in.
    clean();
  }

  const bytes = fs.statSync(out).size;
  const mb = (bytes / 1048576).toFixed(2);
  console.log(`loop -> ${out} (${mb} MB, ${width}px @ ${fps}fps)`);
  if (bytes > LOOP_LIMIT) {
    console.error(`WARNING: ${mb} MB exceeds GitHub's 10MB inline limit. ` +
                  `Shorten it, drop to ${Math.round(width * 0.75)}px, or hold the camera (CONFIG.sway = 0).`);
  }
  return out;
}

// The inline artifact for a MOVING-camera scene. A swooping walkthrough makes a
// multi-megabyte loop AND shows different content than the mp4, so don't make
// one — ship a still that links to the video instead. Costs ~20KB and needs no
// held-camera compromise. Prints the markdown to paste.
function poster(scene, t = 0, width = 960) {
  const base = outBase(scene);
  const out = base + '.jpg';
  const tag = String(t).replace('.', '_');
  ensureVendor(scene);
  // shoot.js writes <scene>_sample_<t>.png into FRAMES_DIR (scene-prefixed so two
  // scenes sampled at the same t cannot overwrite each other). Own a workspace
  // and read from it rather than guessing at a name in the CWD.
  const pdir = workspace(scene, 'poster');
  try {
    run('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'sample', String(t)],
        { env: { ...process.env, FRAMES_DIR: pdir } });
    const shotPath = path.join(pdir, `${path.basename(base)}_sample_${tag}.png`);
    if (!fs.existsSync(shotPath)) throw new Error(`poster: shoot.js did not write ${shotPath}`);
    run('ffmpeg', ['-y', '-i', shotPath, '-vf', `scale=${width}:-2`,
      '-q:v', '4', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  } finally { fs.rmSync(pdir, { recursive: true, force: true }); }
  console.log(`poster -> ${out} (${(fs.statSync(out).size / 1024).toFixed(0)} KB)`);
  console.log(`\nPaste into the README, with VIDEO_URL from dragging the mp4 into an\n` +
              `issue/PR composer (a repo-relative mp4 will NOT render as a player):\n\n` +
              `  [![${path.basename(base)}](${out})](VIDEO_URL)\n`);
  return out;
}

// A contact sheet + a silhouette check, one frame per beat instead of one
// frame per second — the thing you actually want to eyeball before committing
// to a full render. squint.jpg exists because a subject that does not read as
// a distinct shape at 90px will not read at full size either; the tile-of-
// thumbnails forces that check without you having to physically squint at
// your monitor.
// frac is where inside each beat to sample. 0.6 is a reasonable default -- far
// enough in that the beat's action has fired -- but it is exactly the wrong
// place to catch an effect that PARKS at the end of its ramp and never leaves.
// Both instances of that bug in a real scene were found by looking at a later
// frame, so `sheet <scene> 480 0.95` is the pass that surfaces them: every beat
// at its own end, where a station that should be dark is still lit.
// `aspect` — render one moment at several window shapes and tile them.
//
// smoke.js's framing-invariance check can REJECT a scene whose design frame
// changes with the window. It cannot APPROVE one: passing only means nothing
// moved, not that the composition reads at a phone-shaped window. This is the
// looking half, and it is the same division of labour the rest of the method
// uses -- the lint is the floor, the eye is the judgment.
//
// Shapes are expressed RELATIVE to the scene's own FRAME.aspect, so this stays
// meaningful for a 9:16 vertical or 1:1 square scene, not just 16:9.
function aspectSheet(scene, t = 0, width = 520) {
  ensureVendor(scene);
  const out = outBase(scene) + '.aspect.jpg';
  const dir = workspace(scene, 'aspect');
  try {
    const stdout = execFileSync('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'aspects', String(t)],
      { encoding: 'utf8', env: { ...process.env, FRAMES_DIR: dir, SHOOT_FORMAT: REVIEW_FMT,
        ...(stripText ? { SCENE_QUERY: 'strip=text' } : {}) }, stdio: ['ignore', 'pipe', 'inherit'] });
    const shapes = JSON.parse(stdout.trim().split('\n').pop()).shapes;
    const n = shapes.length;
    // Each shape has DIFFERENT pixel dimensions. That rules out both the tile
    // filter (needs uniform inputs) AND the image2 sequence demuxer, which stops
    // reading at the first dimension change -- either way you silently get a
    // sheet containing only the first cell. Feed them as separate inputs, fit
    // each into a common box, and hstack, so every cell shows its window shape
    // at true proportions against the same reference area.
    const inputs = [];
    for (let i = 0; i < n; i++) inputs.push('-i', path.join(dir, `f${String(i).padStart(5, '0')}.${REVIEW_EXT}`));
    const box = `scale=${width}:${width}:force_original_aspect_ratio=decrease,` +
                `pad=${width}:${width}:(ow-iw)/2:(oh-ih)/2:color=0x101010`;
    const chains = shapes.map((_, i) => `[${i}:v]${box}[a${i}]`).join(';');
    const stack = shapes.map((_, i) => `[a${i}]`).join('') + `hstack=inputs=${n}`;
    run('ffmpeg', ['-y', ...inputs, '-filter_complex', `${chains};${stack}`, out]);
    console.log(`aspect -> ${out}`);
    console.log('\nlegend (each cell is the SAME t at a different window shape):');
    shapes.forEach((sh, i) => console.log(`  cell ${i + 1}  ${sh.tag.padEnd(10)} ${sh.w}x${sh.h}  aspect ${(sh.w / sh.h).toFixed(2)}`));
    console.log('\nRead the image. Every cell must show the SAME composition — a subject that\n' +
                'drifts, crops, or reflows between cells is a framing bug the render will hide,\n' +
                'because shoot.js only ever records the design shape.');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

// `strip` here is the text-strip flag, not the strip command: sheet(scene, w,
// frac, true) renders the same beats with every word removed, which is the
// semantics pass. An author used to build this by hand-editing a copy.
function sheet(scene, width = 480, frac = 0.6, stripText = false) {
  ensureVendor(scene);
  const base = outBase(scene);
  const sheetOut = base + (stripText ? '.nocap.sheet.jpg' : '.sheet.jpg');
  const squintOut = base + '.squint.jpg';
  // Own this dir outright rather than trusting ambient FRAMES_DIR, then
  // rmSync it whole in the finally below -- same reasoning as loop()'s
  // .loopsrc/.loopframes. Honouring an inherited FRAMES_DIR here and then
  // recursively deleting it would reopen the "FRAMES_DIR=. erased the scene"
  // failure shoot.js's full-mode comment describes, just one caller removed.
  const dir = workspace(scene, 'sheet');
  try {
    // encoding: 'utf8' (not stdio: 'inherit') so the JSON line shoot.js prints
    // comes back to us instead of straight to our own stdout, where we'd have
    // no way to read the beat list back into this process. stderr still goes
    // through so scene errors are not swallowed.
    const stdout = execFileSync('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'beats', String(frac)],
      { encoding: 'utf8', env: { ...process.env, FRAMES_DIR: dir, SHOOT_FORMAT: REVIEW_FMT,
        ...(stripText ? { SCENE_QUERY: 'strip=text' } : {}) }, stdio: ['ignore', 'pipe', 'inherit'] });
    const { beats } = JSON.parse(stdout.trim().split('\n').pop());
    const n = beats.length;
    const cols = Math.min(4, Math.ceil(Math.sqrt(n)));
    const rows = Math.ceil(n / cols);

    run('ffmpeg', ['-y', '-i', path.join(dir, `f%05d.${REVIEW_EXT}`), '-vf',
      `scale=${width}:-2,tile=${cols}x${rows}:padding=6:color=0x1a1a1a`,
      '-frames:v', '1', '-update', '1', '-q:v', '4', sheetOut]);

    // 90px wide, one row: small enough that detail disappears and only the
    // silhouette is left, which is the point.
    run('ffmpeg', ['-y', '-i', path.join(dir, `f%05d.${REVIEW_EXT}`), '-vf',
      `scale=90:-2,tile=${n}x1:padding=3:color=0x1a1a1a`,
      '-frames:v', '1', '-update', '1', '-q:v', '4', squintOut]);

    console.log(`sheet -> ${sheetOut}`);
    console.log(`squint -> ${squintOut}`);
    // No drawtext burn-in: libfreetype is not guaranteed present in every
    // ffmpeg build, and a hard dependency on it would fail the command on
    // builds that lack it. The legend goes to stdout instead.
    console.log('\nlegend:');
    beats.forEach((b, idx) => {
      const r = Math.floor(idx / cols) + 1, c = (idx % cols) + 1;
      console.log(`  r${r}c${c}  ${b.name}   t=${b.t}`);
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

// Motion defects that don't show up in any still: a property that jumps
// discontinuously at a beat boundary (a "pop"), and motion that stalls to
// zero velocity mid-film (a "stall"). tblend=all_mode=difference diffs each
// frame against its predecessor; signalstats' YAVG on that diff is the mean
// absolute luma change, i.e. a cheap proxy for "how much moved this frame".
// metadata=print writes that number to stdout as text instead of burning it
// into a video, which is the only way to get the numbers back out of a
// filtergraph without decoding to raw and hand-rolling the diff ourselves.
// CONSECUTIVE frames from one narrow window, tiled. The contact sheet shows
// error across BEATS; this shows what happens between ADJACENT FRAMES, which is
// the only pixel-level access anyone gets to the continuity axis without playing
// the film -- and an agent reviewing a scene cannot play anything.
//
// Bracketed on a moving-camera scene, both sides measured, not guessed:
//
//   NOT visible: a 0.35 rad single-frame rotation on one limb (~2% of frame
//     area). Adjacent cells are indistinguishable. Same signal that measured
//     1.00x its local baseline in `motion` -- small localized steps are simply
//     not recoverable from full frames while a camera is moving.
//   VISIBLE: a 1.2-unit whole-body translation (~15% of frame height), injected
//     deliberately as a positive control. Obvious comparing the cells either
//     side of the boundary.
//
// So this catches whole-object and world-level discontinuities, not limb-level
// ones, and it will do better on a held camera where nothing else competes.
// Use it as a look-closer, not a gate, and keep checking the three source
// shapes in references/method.md -- those cover the cases below the bracket.
const STRIP_MAX = 16;
function strip(scene, t0, t1, fps = 30, width = 480) {
  ensureVendor(scene);
  const base = outBase(scene);
  const out = base + '.strip.jpg';
  const a = Math.round(t0 * fps);
  let n = Math.round(t1 * fps) - a;
  if (!(n >= 2)) throw new Error(`strip: ${t0}..${t1} at ${fps}fps is ${n} frame(s) -- widen the window or raise fps`);
  if (n > STRIP_MAX) {
    console.error(`strip: window holds ${n} frames, showing the first ${STRIP_MAX}. ` +
      'A strip is for a suspect MOMENT; narrow the window rather than skimming a whole beat.');
    n = STRIP_MAX;
  }
  const dir = workspace(scene, 'strip');
  try {
    run('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'range',
      String(a), String(a + n), String(fps)], { env: { ...process.env, FRAMES_DIR: dir, SHOOT_FORMAT: REVIEW_FMT } });
    const cols = Math.min(4, n), rows = Math.ceil(n / cols);
    // -start_number because `range` names frames by their GLOBAL index (f00259),
    // not from zero -- that is what makes a re-shot range drop back into a full
    // render, and it means ffmpeg has to be told where the sequence begins.
    run('ffmpeg', ['-y', '-start_number', String(a), '-i', path.join(dir, `f%05d.${REVIEW_EXT}`),
      '-vf', `scale=${width}:-2,tile=${cols}x${rows}:padding=6:color=0x1a1a1a`,
      '-frames:v', '1', '-update', '1', '-q:v', '4', out]);
    console.log(`strip -> ${out}  (${n} consecutive frames at ${fps}fps)`);
    console.log('\nlegend:');
    for (let i = 0; i < n; i++) {
      const r = Math.floor(i / cols) + 1, c = (i % cols) + 1;
      console.log(`  r${r}c${c}  t=${((a + i) / fps).toFixed(4)}s`);
    }
    console.log('\nRead the image and compare ADJACENT cells. Smooth motion moves a similar');
    console.log('amount per cell; a discontinuity moves once and stops. A small localized');
    console.log('step under a moving camera may not be visible here -- see the note in build.js.');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function motion(scene, fps = 12) {
  const dir = workspace(scene, 'motion');
  try {
    frames(scene, fps, dir);
    // Provenance: what we read must be what we wrote. Without this, a clobbered
    // scratch dir produced a completely plausible per-beat profile covering a
    // THIRD of the film -- 65 frames reported for a 254-frame render, exit 0,
    // the only symptom one ffmpeg stderr line nobody reads. A wrong number that
    // looks right is worse than no number.
    const wroteN = fs.readdirSync(dir).filter(f => /^f\d{5}\.png$/.test(f)).length;  // motion is PNG by contract
    if (wroteN < 2) throw new Error(`motion: only ${wroteN} frame(s) in ${dir} — the shoot did not produce a film`);

    const out = execFileSync('ffmpeg', ['-y', '-framerate', String(fps), '-i', path.join(dir, 'f%05d.png'),
      '-vf', 'tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-',
      '-f', 'null', '-'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });

    // Output alternates a `frame:<n>` line and a `lavfi.signalstats.YAVG=<v>`
    // line per frame. Pull them out as a pair rather than assuming a fixed
    // line offset between them -- ffmpeg versions differ in how much other
    // metadata they interleave.
    const series = [];
    let pendingFrame = null;
    for (const line of out.split('\n')) {
      const fm = line.match(/frame:(\d+)/);
      if (fm) { pendingFrame = Number(fm[1]); continue; }
      const vm = line.match(/lavfi\.signalstats\.YAVG=([\d.]+)/);
      if (vm && pendingFrame !== null) { series[pendingFrame] = Number(vm[1]); pendingFrame = null; }
    }

    // Frame 0 has no predecessor, so tblend diffs it against itself (or
    // whatever ffmpeg does at the boundary depending on version) -- not a real
    // motion sample, and left in it would skew the median toward zero.
    // Provenance BEFORE any early return. The one outcome worse than a profile
    // for part of a film is a reassuring line and exit 0 for none of it, and
    // that path used to sit 75 lines above the assertion meant to prevent it.
    // tblend emits exactly one delta per adjacent pair, so N frames -> N-1
    // deltas; anything else means the scratch dir moved under us or ffmpeg
    // stopped early. (The old `series.length < wroteN * 0.9` was wrong both
    // ways: N-1 < 0.9N holds for every N < 10, so short films threw spuriously,
    // while 25 frames could vanish from a 254-frame render undetected.)
    const present = series.filter(v => v !== undefined).length;
    if (present !== wroteN - 1) {
      throw new Error(`motion: ${wroteN} frames written to ${dir} but ${present} deltas parsed `
        + `(expected ${wroteN - 1}). The scratch dir was modified mid-run, or ffmpeg stopped `
        + `early — refusing to report a profile for part of the film.`);
    }
    // FINDING: tblend has ALREADY dropped the unpaired first input, so its
    // frame:0 IS the genuine 0->1 delta at pts 1/fps. Dropping it again hid the
    // film's first inter-frame delta entirely and shifted every reported
    // timestamp one frame early. Verified against ffmpeg output.
    const values = series.filter(v => v !== undefined);
    if (!values.length) { throw new Error('motion: no deltas parsed — nothing to report'); }
    const sorted = [...values].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];

    // Get the beats JSON via shoot.js `manifest` mode, which reads window.BEATS
    // and prints it WITHOUT shooting anything -- we use only start/dur for
    // bucketing, never the frames, so the old `beats` call rendered (and then
    // deleted) one screenshot per beat for nothing. No temp dir to own.
    let beats = null, synthetic = true;
    {
      const beatsOut = execFileSync('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'manifest'],
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });
      const parsed = JSON.parse(beatsOut.trim().split('\n').pop());
      beats = parsed.beats;
      synthetic = parsed.synthetic;
    }
    // Only annotate findings with a beat name when window.BEATS was actually
    // present -- the synthetic 8-way fallback isn't a real beat, and labeling
    // a pop "(3 @ 40%)" against a segment nobody authored would just mislead.
    const beatFor = (t) => {
      if (synthetic || !beats || !beats.length) return '';
      const b = beats.find(b => t >= b.start && t < b.start + b.dur) || beats[beats.length - 1];
      const frac = b.dur > 0 ? (t - b.start) / b.dur : 0;
      return ` [${b.name} @ ${Math.round(frac * 100)}%]`;
    };

    // What this reports, and what it deliberately does NOT.
    //
    // The first version of this command tried to flag pops (a property jumping
    // discontinuously) and stalls (motion decelerating to a dead stop). Both
    // were measured against a scene with a KNOWN discontinuity and a KNOWN
    // pair of stalls, and both failed:
    //
    //   - The pop was a 0.35 rad rotation on one limb. Whole-frame mean luma
    //     change at that boundary measured 1.00x its own local baseline --
    //     literally invisible -- because the camera and six mechanisms were
    //     already moving. A step-halving probe (exploiting seekTo's purity:
    //     smooth motion halves its delta when you halve dt, a step does not)
    //     separated it no better: 1.60 at the known step vs 1.69 at a control
    //     boundary. The signal is real and it is buried.
    //   - Stalls fired at EVERY beat boundary on that scene and ~10 times on a
    //     known-good one, because a film is SUPPOSED to settle between beats.
    //     Pixels cannot tell a deliberate rest from a flywheel that stopped.
    //
    // A detector that returns ten findings on every film trains you to ignore
    // it, and one that reports "0 pops" on a scene that has one is worse than
    // no check at all -- it converts an open question into a settled one. So
    // this command reports only what whole-frame statistics genuinely measure
    // well: how much each beat moves, and where nothing moves at all.
    // Continuity review stays a watch-the-loop activity; the three failure
    // shapes to check in SOURCE are in references/method.md.
    const perBeat = [];
    if (!synthetic && beats && beats.length) {
      for (const b of beats) {
        const lo = Math.max(0, Math.round(b.start * fps) - 1);
        const hi = Math.min(values.length, Math.round((b.start + b.dur) * fps) - 1);
        const slice = values.slice(lo, hi);
        if (!slice.length) continue;
        perBeat.push({ name: b.name, dur: b.dur, mean: slice.reduce((s, v) => s + v, 0) / slice.length });
      }
    }

    // Dead air: an absolute floor, not a fraction of the median. A fraction
    // scales with the scene's own energy, so a held-camera diagram (median
    // 0.16 measured) and a moving-camera walkthrough (median 3.90) would get
    // wildly different definitions of "nothing is happening".
    const DEAD_FLOOR = 0.05, DEAD_MIN_FRAMES = Math.max(3, Math.round(fps * 0.75));
    const dead = [];
    let runStart = -1, runLen = 0;
    values.forEach((v, i) => {
      if (v < DEAD_FLOOR) { if (runLen === 0) runStart = i; runLen++; }
      else { if (runLen >= DEAD_MIN_FRAMES) dead.push([runStart, i - 1]); runLen = 0; }
    });
    if (runLen >= DEAD_MIN_FRAMES) dead.push([runStart, values.length - 1]);
    console.log(`motion: ${values.length} frames at ${fps}fps, median frame-diff ${median.toFixed(2)}`);
    if (perBeat.length) {
      const peak = Math.max(...perBeat.map(b => b.mean)) || 1;
      console.log('\n  per-beat motion (relative bar, not an absolute scale):');
      for (const b of perBeat) {
        const bar = '#'.repeat(Math.max(1, Math.round(24 * b.mean / peak)));
        console.log(`    ${b.name.padEnd(10)} ${b.dur.toFixed(1)}s  ${b.mean.toFixed(2).padStart(6)}  ${bar}`);
      }
      console.log('  A beat far below its neighbours is either a deliberate hold or a beat');
      console.log('  whose action never fires. A run of near-identical bars is a slideshow.');
    } else {
      console.log('  per-beat profile: skipped, window.BEATS not present');
    }
    for (const [s, e] of dead) {
      const t = (s + 1) / fps;
      console.log(`  DEAD AIR  t=${t.toFixed(2)}s-${((e + 1) / fps).toFixed(2)}s — nothing on screen changes${beatFor(t)}`);
    }
    console.log(`\n${dead.length} dead-air stretch(es). This does NOT detect pops or stalls — see the`);
    console.log('comment in build.js for the measurements showing why, and check those in source.');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

const USAGE = 'usage: bun run build.js vendor|bundle|frames|video|all|avif|loop|poster|sheet|aspect|strip|motion <scene.html> [fps|t|t0] [width|t1] [frac|fps]';
const [, , step, target, fpsArg, widthArg, extraArg] = process.argv;
if (['bundle', 'frames', 'video', 'all', 'avif', 'loop', 'poster', 'sheet', 'aspect', 'strip', 'motion'].includes(step) && !target) {
  console.error(`${step}: missing <scene.html>\n${USAGE}`); process.exit(1);
}
const fps = Number(fpsArg || 30);
if (step === 'vendor') { const tp = target ? path.resolve(target) : null;
  vendor(tp ? path.dirname(tp) : process.cwd(), tp); }
else if (step === 'avif') avif(target, Number(widthArg || 720), Number(fpsArg || 12));
else if (step === 'loop') loop(target, Number(widthArg || 720), Number(fpsArg || 12));
else if (step === 'poster') poster(target, Number(fpsArg || 0), Number(widthArg || 960));
else if (step === 'bundle') bundle(target);
else if (step === 'frames') frames(target, fps);
else if (step === 'video') video(target, fps);
else if (step === 'all') { bundle(target); frames(target, fps); video(target, fps); }
else if (step === 'aspect') aspectSheet(target, Number(fpsArg || 0), Number(widthArg || 520));
else if (step === 'sheet') sheet(target, Number(fpsArg || 480), widthArg === undefined ? 0.6 : Number(widthArg), extraArg === 'nocap');
else if (step === 'strip') strip(target, Number(fpsArg), Number(widthArg), Number(extraArg || 30));
else if (step === 'motion') motion(target, Number(fpsArg || 12));
else { console.error(USAGE); process.exit(1); }
