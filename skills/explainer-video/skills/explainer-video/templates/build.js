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
//
// Prereqs: bun add three@0.185.1 playwright-core@1.61.1 ; ffmpeg on PATH.
const { execSync } = require('child_process');
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
    execSync(`bun build ${entry} --target=browser --format=iife --minify --outfile ${out}`, { stdio: 'inherit' });
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

function frames(scene, fps = 30) {
  execSync(`bun run ${path.join(__dirname, 'shoot.js')} ${scene} full ${fps}`, { stdio: 'inherit' });
}

function video(name, fps = 30) {
  const out = name.replace(/(\.bundled)?\.html$/, '') + '.mp4';
  execSync(
    `ffmpeg -y -framerate ${fps} -i frames/f%05d.png -c:v libx264 -preset slow ` +
    `-crf 17 -pix_fmt yuv420p -movflags +faststart ${out}`, { stdio: 'inherit' });
  console.log('encoded -> ' + out);
}

const [, , step, target, fpsArg] = process.argv;
const fps = Number(fpsArg || 30);
if (step === 'vendor') vendor(target ? path.resolve(target) : process.cwd());
else if (step === 'bundle') bundle(target);
else if (step === 'frames') frames(target, fps);
else if (step === 'video') video(target, fps);
else if (step === 'all') { const b = bundle(target); frames(b, fps); video(target, fps); }
else { console.error('usage: bun run build.js vendor|bundle|frames|video|all <scene.html> [fps]'); process.exit(1); }
