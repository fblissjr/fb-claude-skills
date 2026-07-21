#!/usr/bin/env bun
// Smoke test for the scene contract. Every bug this catches was invisible in
// source and obvious on the first render: a renamed three API that evaluates to
// undefined instead of throwing, a bundler that splices a script tag into the
// library, a vendored bundle whose top-level identifiers collide with scene
// variables. Reading the code finds none of them; rendering one frame finds all
// three.
//
//   bun run smoke.js                 -> checks every *.html in cwd (skips .bundled)
//   bun run smoke.js <scene.html>... -> checks the named scenes
//
// Checks per scene, unbundled AND bundled:
//   1. the page loads with zero console/page errors (incl. deprecation warnings)
//   2. seekTo, DURATION, stopPlayback, sceneReady all exist (the contract only —
//      the renderer is deliberately not asserted, so any backend can pass)
//   3. seekTo(t) is deterministic: the same t twice gives byte-identical pixels
//   4. seekTo renders something — not a blank canvas
//
// Requires: bun, playwright-core, a Chromium (see shoot.js resolution order).
// Exits non-zero on any failure, so it can gate a release.
const { chromium } = require('playwright-core');
const { execSync } = require('child_process');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const os = require('os');

function chromiumPath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try { const p = chromium.executablePath(); if (p && fs.existsSync(p)) return p; } catch (e) {}
  for (const cache of [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers',
                       path.join(os.homedir(), 'Library/Caches/ms-playwright'),
                       path.join(os.homedir(), '.cache/ms-playwright')]) {
    if (!cache || !fs.existsSync(cache)) continue;
    for (const d of fs.readdirSync(cache).filter(d => d.startsWith('chromium')).sort().reverse()) {
      for (const rel of ['chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
                         'chrome-headless-shell-linux64/chrome-headless-shell',
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

const CONTRACT = ['seekTo', 'DURATION', 'stopPlayback', 'sceneReady'];

async function checkScene(browser, file) {
  const fails = [];
  const noise = [];
  const page = await browser.newPage({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => noise.push('page error: ' + e.message));
  // Driver performance chatter from the software GL path (our own readPixels
  // provokes it) is not a correctness signal. Everything else stays: three
  // announces silently-changed behaviour via console warnings, which is exactly
  // what this test exists to catch.
  const NOISE = /GL Driver Message|GPU stall|Automatic fallback to software WebGL/i;
  page.on('console', m => {
    if (m.type() !== 'error' && m.type() !== 'warning') return;
    if (NOISE.test(m.text())) return;
    noise.push(`console ${m.type()}: ${m.text()}`);
  });

  try {
    await page.goto('file://' + path.resolve(file) + '?record=1');
    await page.waitForFunction('window.sceneReady === true', { timeout: 20000 });
    await page.evaluate('window.stopPlayback()');

    const missing = await page.evaluate(
      `(${JSON.stringify(CONTRACT)}).filter(k => window[k] === undefined)`);
    if (missing.length) fails.push('missing contract: ' + missing.join(', '));
    // Deliberately NOT asserting window.THREE. The contract is the product here;
    // three.js is one backend. Any scene exposing these four globals — a 2D
    // canvas, an SVG/CSS timeline, a D3 diagram — gets frame-exact MP4s from the
    // same pipeline, and this check must not lock that out.

    const dur = await page.evaluate('window.DURATION');
    const t = Math.min(1, dur / 3);

    // Determinism: same t twice must be byte-identical. Catches accumulated
    // state, Math.random(), and wall-clock leaking into the scene — each of
    // which silently desyncs the MP4 from the HTML loop.
    await page.evaluate(`window.seekTo(${t})`);
    const a = await page.screenshot();
    await page.evaluate(`window.seekTo(${dur})`);          // move away...
    await page.evaluate(`window.seekTo(${t})`);            // ...and back
    const b = await page.screenshot();
    const h = buf => crypto.createHash('sha256').update(buf).digest('hex');
    if (h(a) !== h(b)) fails.push(`seekTo(${t}) not deterministic — scene carries state across frames`);

    // Non-blank, measured on the screenshot rather than the canvas, so this works
    // for any backend (WebGL, 2D canvas, SVG/CSS, plain DOM). PNG compresses a
    // uniform frame to almost nothing: at 640x360 a flat fill lands around 1-3KB,
    // while anything with real content is far larger. A heuristic, but it catches
    // the failure that matters — a pipeline happily shooting 600 empty frames.
    const BLANK_BYTES = 6000;
    if (a.length < BLANK_BYTES) {
      fails.push(`frame looks blank (screenshot only ${a.length} bytes compressed)`);
    }
  } catch (e) {
    fails.push(e.message.split('\n')[0]);
  }
  await page.close();
  return { fails: fails.concat(noise) };
}

(async () => {
  let scenes = process.argv.slice(2);
  if (!scenes.length) {
    scenes = fs.readdirSync(process.cwd())
      .filter(f => f.endsWith('.html') && !f.endsWith('.bundled.html'));
  }
  if (!scenes.length) { console.error('no scenes to check'); process.exit(1); }

  // Bundling is part of what we are testing, so build it rather than trust it.
  // Vendor only if a scene actually asks for three — this script tests the
  // contract, not the renderer, and a 2D or SVG backend must not be forced to
  // materialize a three bundle it never references.
  const needsThree = scenes.some(f => {
    try { return /three\.global\.js/.test(fs.readFileSync(f, 'utf8')); } catch (e) { return false; }
  });
  if (needsThree && !fs.existsSync('three.global.js')) {
    execSync(`bun run ${path.join(__dirname, 'build.js')} vendor`, { stdio: 'inherit' });
  }

  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--no-sandbox'],
  });

  let failed = 0;
  for (const scene of scenes) {
    const variants = [scene];
    try {
      const out = execSync(`bun run ${path.join(__dirname, 'build.js')} bundle ${scene}`,
                           { encoding: 'utf8' });
      const m = out.match(/bundled -> (.+)/);
      if (m) variants.push(m[1].trim());
    } catch (e) {
      console.log(`FAIL ${scene} [bundle] — ${e.message.split('\n')[0]}`);
      failed++;
    }
    for (const v of variants) {
      const { fails } = await checkScene(browser, v);
      const label = v.endsWith('.bundled.html') ? 'bundled' : 'source';
      if (fails.length) {
        failed++;
        console.log(`FAIL ${v} [${label}]`);
        for (const f of fails) console.log('       ' + f);
      } else {
        console.log(`ok   ${v} [${label}]`);
      }
    }
  }
  await browser.close();
  console.log(failed ? `\n${failed} check(s) failed` : '\nall scenes pass');
  process.exit(failed ? 1 : 0);
})();
