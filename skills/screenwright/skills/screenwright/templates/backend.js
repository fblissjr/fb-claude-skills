// Shared browser + backend policy for shoot.js (the recorder) and smoke.js
// (the gate). ONE copy on purpose: the two files must resolve the SAME
// Chromium binary and the SAME flag set, or the gate checks a different
// configuration than the recorder ships. That drift is not hypothetical —
// smoke.js once carried an inline copy of this logic that had silently lost
// the ANGLE_BACKEND allow-list, so a typo the recorder rejects loudly sailed
// straight through the gate.
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Chromium resolution order: $CHROMIUM_PATH, playwright's managed browser,
// then common system locations. `bunx playwright install chromium` if none.
function chromiumPath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try { const p = chromium.executablePath(); if (p && fs.existsSync(p)) return p; } catch (e) {}
  // Playwright's cache is versioned (chromium-<build>); scan rather than pin a
  // build number, which goes stale on every playwright bump. Numeric by build:
  // lexicographic sorts chromium-1099 above chromium-1223, so the gate and the
  // recorder could resolve different browsers on the same machine.
  for (const cache of [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers',
                       path.join(os.homedir(), 'Library/Caches/ms-playwright'),
                       path.join(os.homedir(), '.cache/ms-playwright')]) {
    if (!cache || !fs.existsSync(cache)) continue;
    const byBuild = (a, b) => (parseInt(b.replace(/\D+/g, ''), 10) || 0) - (parseInt(a.replace(/\D+/g, ''), 10) || 0);
    for (const d of fs.readdirSync(cache).filter(d => d.startsWith('chromium')).sort(byBuild)) {
      // Both Intel and Apple-Silicon layouts. Without the -arm64 entries this
      // scan matched NOTHING on Apple Silicon and fell through to system
      // Chrome — a different (auto-updating) build than the one playwright
      // pins, discovered when the two binaries disagreed about WebGPU.
      for (const rel of ['chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
                         'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
                         'chrome-headless-shell-linux64/chrome-headless-shell',
                         'chrome-headless-shell-mac-arm64/chrome-headless-shell',
                         'chrome-mac/headless_shell']) {
        const p = path.join(cache, d, rel);
        if (fs.existsSync(p)) return p;
      }
    }
  }
  for (const c of [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
  ]) if (fs.existsSync(c)) return c;
  throw new Error('No Chromium found. Set CHROMIUM_PATH or run: bunx playwright install chromium');
}

/* ---------- GL / WebGPU backend flags ---------------------------------------
   Hardware GL by default; ANGLE_BACKEND=swiftshader forces software GL.
   WEBGPU is the hardware-WebGPU opt-in, and OFF is the deliberate default:
   with no flags, headless Chromium exposes no WebGPU adapter and
   WebGPURenderer falls back to its WebGL2 backend transparently — same scene,
   same TSL materials, deterministic, works everywhere including GPU-less CI.
   The opt-in exists because hardware WebGPU measured ~2.3x faster end to end
   (37 vs 87 ms/frame with a node post chain, screenshots included).

   Both values are allow-lists because the failure modes here are silent:
   - An ANGLE_BACKEND typo (`swifthsader`) used to be accepted silently and
     launched hardware GL while the author believed they were reproducing a
     software-GL regression byte-for-byte.
   - On macOS, `--enable-unsafe-webgpu` WITHOUT `--use-angle=metal` hands
     Chromium a SwiftShader-WebGPU adapter that renders every frame pure
     black with exit 0 (measured on r185, this pipeline).

     WEBGPU=off     (default) no WebGPU flags; WebGL2 fallback path
     WEBGPU=auto    metal on darwin, vulkan elsewhere
     WEBGPU=metal   macOS hardware adapter (verified)
     WEBGPU=vulkan  linux hardware adapter (UNVERIFIED here; smoke's
                    near-black check is the guard — run it before trusting)
     WEBGPU=swiftshader  software WebGPU. Ships flat frames on the playwright
                    headless-shell build (measured; warmth-dependent on other
                    builds) — diagnostic-only; shoot.js refuses it for shoots.

   Frames are NOT byte-identical across backends (GL vs WebGPU, hardware vs
   software), so a byte-wise regression must fix the backend on both sides —
   which is why these are explicit env vars, not per-machine defaults. */
const ANGLE_OK = ['default', 'swiftshader', 'metal', 'gl', 'vulkan', 'd3d11', 'd3d9'];
const WEBGPU_OK = ['off', 'auto', 'metal', 'vulkan', 'swiftshader'];

// refuseSwiftshaderShip: shoot.js passes true. SwiftShader-WebGPU is
// diagnostic-only for SHOOTING — measured on r185 it half-works depending on
// GPU-process warmth (real frames in the drawing buffer, a flat clear-color
// wash at the compositor), so a shoot can write 600 flat frames with exit 0
// even after a smoke pass. smoke.js may probe this configuration (its
// shipped-frame check exists exactly for it); a full shoot on it requires
// acknowledging the risk explicitly via WEBGPU_UNSAFE_SHIP=1.
function angleArgs({ refuseSwiftshaderShip = false } = {}) {
  const base = ['--hide-scrollbars', '--no-sandbox'];
  const want = (process.env.ANGLE_BACKEND || 'default').toLowerCase();
  if (!ANGLE_OK.includes(want)) {
    throw new Error(`ANGLE_BACKEND="${process.env.ANGLE_BACKEND}" is not one of: ${ANGLE_OK.join(', ')}`);
  }
  let webgpu = (process.env.WEBGPU || 'off').toLowerCase();
  if (!WEBGPU_OK.includes(webgpu)) {
    throw new Error(`WEBGPU="${process.env.WEBGPU}" is not one of: ${WEBGPU_OK.join(', ')}`);
  }
  if (webgpu !== 'off') {
    if (want !== 'default' && !(want === 'metal' && webgpu === 'metal')) {
      throw new Error(`WEBGPU=${webgpu} conflicts with ANGLE_BACKEND=${want}: the WebGPU adapter rides the ANGLE choice, and mixing them is how the silent black-frame configuration happens. Set one or the other.`);
    }
    if (webgpu === 'auto') webgpu = process.platform === 'darwin' ? 'metal' : 'vulkan';
    if (webgpu === 'metal') return ['--enable-unsafe-webgpu', '--use-angle=metal', ...base];
    if (webgpu === 'vulkan') return ['--enable-unsafe-webgpu', '--enable-features=Vulkan', ...base];
    if (refuseSwiftshaderShip && process.env.WEBGPU_UNSAFE_SHIP !== '1') {
      throw new Error('WEBGPU=swiftshader ships flat frames non-deterministically (compositor half-dead on r185). '
        + 'It exists for smoke.js diagnostics. Set WEBGPU_UNSAFE_SHIP=1 if you really mean to shoot with it.');
    }
    return ['--enable-unsafe-webgpu', '--use-webgpu-adapter=swiftshader', '--enable-unsafe-swiftshader', ...base];
  }
  if (want === 'swiftshader') return ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', ...base];
  if (want === 'default') return base;                 // let Chromium pick the GPU
  return [`--use-angle=${want}`, ...base];
}

/* Settle one presented frame between seekTo (or a viewport resize) and the
   screenshot/sample that follows. LOAD-BEARING, measured: on the node stack
   renderer.render() QUEUES GPU work; the compositor can present it a frame
   late, so an immediate capture sometimes reads the PREVIOUS composite —
   observed as a flaky determinism FAIL whose in-page canvas pixels were
   byte-identical (the scene was pure; the capture was racing presentation).
   The double-rAF forces at least one composite containing the new frame
   before the capture's own BeginFrame. Scene contract unchanged: seekTo
   stays synchronous. ONE copy here — this incantation is determinism-
   critical and was hand-typed at four sites before it was shared. */
const settle = pg => pg.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');

// Window shapes for the aspect-invariance instruments, expressed RELATIVE to
// the scene's own design aspect so they stay meaningful for vertical/square
// scenes. shoot.js `aspects` uses all four; smoke.js's framing check uses the
// three non-square shapes (each shape costs a resize+settle cycle per sample).
const aspectShapes = ar => [
  { tag: 'design', w: 1280, h: Math.round(1280 / ar) },
  { tag: 'narrow', w: 1100, h: Math.round(1100 / (ar * 0.72)) },
  { tag: 'square', w: 1000, h: Math.round(1000 / (ar * 0.56)) },
  { tag: 'wide',   w: 1600, h: Math.round(1600 / (ar * 1.33)) },
];

module.exports = { chromiumPath, angleArgs, settle, aspectShapes, ANGLE_OK, WEBGPU_OK };
