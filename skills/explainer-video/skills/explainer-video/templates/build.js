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
//   bun run build.js loop   <scene.html> [fps] [w] -> <name>.webp, inline in a README
//   bun run build.js poster <scene.html> [t] [w]   -> <name>.jpg still + markdown snippet
//
// Prereqs: bun add three@0.185.1 playwright-core@1.61.1 ; ffmpeg on PATH.
// `loop` also needs img2webp (macOS: brew install webp).
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
const VENDOR = 'three.global.js';
const VENDOR_TAG = /<script src="\.\/three\.global\.js"><\/script>/;
const bundleName = (src) => src.replace(/\.html$/, '.bundled.html');

function vendor(dir = process.cwd()) {
  const out = path.join(dir, VENDOR);
  const entry = path.join(dir, '.three-entry.js');
  fs.writeFileSync(entry, "import * as THREE from 'three';\nglobalThis.THREE = THREE;\n");
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
  console.log('vendored -> ' + out);
  return out;
}

function bundle(src) {
  const dir = path.dirname(path.resolve(src));
  const libPath = path.join(dir, VENDOR);
  if (!fs.existsSync(libPath)) vendor(dir);
  const lib = fs.readFileSync(libPath, 'utf8');
  const html = fs.readFileSync(src, 'utf8');
  if (!VENDOR_TAG.test(html)) { console.log('no vendor tag in ' + src + ' — already bundled?'); return src; }
  const out = bundleName(src);
  // bundleName is a regex replace that returns src UNCHANGED when it does not
  // match -- so `bundle scene.htm` or `scene.HTML` used to write the inlined
  // output over the source file and print "bundled -> scene.htm" as if fine,
  // destroying the one file the header calls the single source of truth.
  if (path.resolve(out) === path.resolve(src)) {
    throw new Error(`refusing to overwrite the source: ${src} must end in .html`);
  }
  // The replacement MUST be a function, not a string: in a string replacement
  // `$&`, `$'` and `` $` `` are substitution patterns, and minified three
  // contains `$&` (`if($&$.isStackTrace)`), which silently splices the matched
  // script tag into the middle of the library. A function replacement disables
  // that interpretation. Also split any literal </script> so the library can't
  // terminate the host tag early.
  const inline = '<script>' + lib.replace(/<\/script>/gi, '<\\/script>') + '</script>';
  fs.writeFileSync(out, html.replace(VENDOR_TAG, () => inline));
  console.log('bundled -> ' + out);
  return out;
}

// Any command that RENDERS a scene needs the vendored bundle present. bundle()
// has auto-vendored since the start; loop and poster were added later and did
// not, so a fresh checkout failed with "THREE is not defined" — loud, but
// pointing at the scene contract when the real cause is a missing build step.
// The needsThree test mirrors smoke.js: only vendor if the scene asks for three,
// so a 2D or SVG backend is never forced to materialize a bundle it never loads.
function ensureVendor(scene) {
  const dir = path.dirname(path.resolve(scene));
  if (fs.existsSync(path.join(dir, VENDOR))) return;
  let src = '';
  try { src = fs.readFileSync(scene, 'utf8'); } catch (e) { return; }
  if (/three\.global\.js/.test(src)) vendor(dir);
}

function frames(scene, fps = 30, dir = 'frames') {
  ensureVendor(scene);
  run('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'full', String(fps)],
      { env: { ...process.env, FRAMES_DIR: dir } });
}

function video(name, fps = 30) {
  const out = name.replace(/(\.bundled)?\.html$/, '') + '.mp4';
  // Honour the same override shoot.js does. video() hardcoded 'frames/' while
  // shoot.js read FRAMES_DIR, so a hand-run `FRAMES_DIR=shots shoot.js ... full`
  // followed by `build.js video` silently encoded the STALE frames/ from a
  // previous render -- shipping the old film, which is the exact failure the
  // stale-tail fix exists to prevent.
  const dir = process.env.FRAMES_DIR || 'frames';
  run('ffmpeg', ['-y', '-framerate', String(fps), '-i', path.join(dir, 'f%05d.png'),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', out]);
  console.log('encoded -> ' + out);
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
// short; see references/method.md.
const LOOP_LIMIT = 10 * 1024 * 1024;

function loop(scene, width = 720, fps = 12) {
  const base = scene.replace(/(\.bundled)?\.html$/, '');
  const out = base + '.webp';
  // Shoot into our OWN directory. `loop` used to reuse frames/, which silently
  // overwrote the full-resolution frames a previous `build.js all` had shot --
  // so making a README loop destroyed the source of your mp4 with no warning.
  const src = '.loopsrc', tmp = '.loopframes';
  const clean = () => { for (const d of [src, tmp]) fs.rmSync(d, { recursive: true, force: true }); };
  clean();
  try {
  frames(scene, fps, src);
  fs.mkdirSync(tmp, { recursive: true });
  run('ffmpeg', ['-y', '-i', path.join(src, 'f%05d.png'), '-vf', `scale=${width}:-2`,
    path.join(tmp, 'f%05d.png')], { stdio: ['ignore', 'ignore', 'inherit'] });

  // Homebrew's ffmpeg ships without libwebp, so `-c:v libwebp` fails with
  // "Encoder not found". img2webp (from the `webp` package) is the reliable
  // encoder and is what we require.
  try { execFileSync('img2webp', ['-version'], { stdio: 'ignore' }); }
  catch (e) { throw new Error('img2webp not found — install it (macOS: brew install webp)'); }

  // Explicit file list rather than a shell glob. This does NOT dodge ARG_MAX --
  // execFileSync argv goes through the same execve limit a glob would, so the
  // earlier comment claiming otherwise was wrong. What it actually buys is
  // deterministic ordering and a loud failure when scaling produced nothing,
  // rather than img2webp receiving an unexpanded literal.
  const pngs = fs.readdirSync(tmp).filter(f => f.endsWith('.png')).sort()
                 .map(f => path.join(tmp, f));
  if (!pngs.length) throw new Error('no scaled frames in ' + tmp);
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
  const base = scene.replace(/(\.bundled)?\.html$/, '');
  const out = base + '.jpg';
  const tag = String(t).replace('.', '_');
  ensureVendor(scene);
  run('bun', ['run', path.join(__dirname, 'shoot.js'), scene, 'sample', String(t)]);
  run('ffmpeg', ['-y', '-i', `sample_${tag}.png`, '-vf', `scale=${width}:-2`,
    '-q:v', '4', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  fs.rmSync(`sample_${tag}.png`, { force: true });
  console.log(`poster -> ${out} (${(fs.statSync(out).size / 1024).toFixed(0)} KB)`);
  console.log(`\nPaste into the README, with VIDEO_URL from dragging the mp4 into an\n` +
              `issue/PR composer (a repo-relative mp4 will NOT render as a player):\n\n` +
              `  [![${path.basename(base)}](${out})](VIDEO_URL)\n`);
  return out;
}

const USAGE = 'usage: bun run build.js vendor|bundle|frames|video|all|loop|poster <scene.html> [fps|t] [width]';
const [, , step, target, fpsArg, widthArg] = process.argv;
if (['bundle', 'frames', 'video', 'all', 'loop', 'poster'].includes(step) && !target) {
  console.error(`${step}: missing <scene.html>\n${USAGE}`); process.exit(1);
}
const fps = Number(fpsArg || 30);
if (step === 'vendor') vendor(target ? path.resolve(target) : process.cwd());
else if (step === 'loop') loop(target, Number(widthArg || 720), Number(fpsArg || 12));
else if (step === 'poster') poster(target, Number(fpsArg || 0), Number(widthArg || 960));
else if (step === 'bundle') bundle(target);
else if (step === 'frames') frames(target, fps);
else if (step === 'video') video(target, fps);
else if (step === 'all') { const b = bundle(target); frames(b, fps); video(target, fps); }
else { console.error('usage: bun run build.js vendor|bundle|frames|video|all|loop|poster <scene.html> [fps|t] [width]'); process.exit(1); }
