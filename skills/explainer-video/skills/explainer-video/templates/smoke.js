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
// Advisory checks (print `warn` lines, never fail the build or touch the exit
// code) — these are judgment calls bracketed on a handful of scenes, and a
// scene author may legitimately overrule them; a lint that blocks a release
// on a taste call just gets bypassed:
//   5. caption reading speed, when window.BEATS is present
//   6. caption overflow against the nowrap caption pill, when window.BEATS is present
//   7. exposure — both overexposed clipping and underexposed crushing
//
// Requires: bun, playwright-core, a Chromium (see shoot.js resolution order).
// Exits non-zero on any failure, so it can gate a release.
const { chromium } = require('playwright-core');
const { execFileSync } = require('child_process');
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
const VIEWPORT = { width: 640, height: 360 };

// capFade fallback when a scene's CONFIG global isn't reachable (or omits it).
// Matches CONFIG.capFade in scene.template.html.
const CAP_FADE_DEFAULT = 0.35;
// Caption reading speed: chars/sec above which a viewer can't actually read the
// line in the time it's fully legible. Observed, not derived — 27 cps was
// watched and read comfortably, 37 was watched and did not. Warn at 30: inside
// the unresolved gap, biased toward the confirmed-good end. This was briefly 25,
// which flags a density directly observed to read fine — a lint should not fire
// on the one value we have positive evidence for.
const CPS_WARN_THRESHOLD = 30;
// #cap is white-space:nowrap (scene.template.html), so it never wraps — it
// just extends past the viewport with no visible error. Warn before it
// actually reaches the edge, not exactly at it.
const CAP_OVERFLOW_FRACTION = 0.92;
// The viewport the film actually ships at — shoot.js renders every frame at
// 1920x1080. The caption is sized in fixed CSS px, so it must be measured here
// and not at VIEWPORT above, which exists only to keep the render checks cheap.
const SHIP_VIEWPORT = { width: 1920, height: 1080 };

// Exposure thresholds — PROVISIONAL. Bracketed on a handful of scenes only;
// re-bracket as more scenes are checked. Named here so that re-bracketing is
// a one-line edit instead of a hunt through the check.
const EXPOSURE_LUMA_CLIP = 250;          // luma above this counts as clipped-to-white
const EXPOSURE_LUMA_CRUSH = 8;           // luma below this counts as crushed-to-black
const EXPOSURE_CLIPPED_THRESHOLD = 0.06; // warn if worst-case clipped fraction exceeds this
const EXPOSURE_CRUSHED_THRESHOLD = 0.35; // warn if worst-case crushed fraction exceeds this
// Warn if worst-case (p95 - p05) falls below this. BOUNDED ON ONE SIDE ONLY:
// the shipped diagrammatic example measures 22.9 and is deliberately minimal and
// legible, so the line has to sit below that. There is no confirmed-BAD
// observation anywhere, so this is a floor for "nearly blank", not a considered
// judgement about what reads. It was 40, which fired on that known-good example
// — a threshold with no observation beneath it is a guess wearing a number.
const EXPOSURE_DYNRANGE_THRESHOLD = 18;
const EXPOSURE_SAMPLE_WIDTH = 320;       // downscale width for the offscreen luma sample
const EXPOSURE_SAMPLE_TIMES = [0.25, 0.5, 0.8]; // fractions of DURATION to sample and take the worst of

async function checkScene(browser, file) {
  const fails = [];
  const warnings = [];
  const noise = [];
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 1 });
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
    // Threshold scales with the viewport instead of being a magic constant: a
    // uniform PNG costs roughly a byte per 40 pixels, so anything below that is
    // flat fill. Hardcoding 6000 silently mis-calibrated the moment VIEWPORT
    // changed, which is exactly the kind of coupling nobody notices.
    const blankFloor = Math.round((VIEWPORT.width * VIEWPORT.height) / 40);
    if (a.length < blankFloor) {
      fails.push(`frame looks blank (${a.length} bytes compressed, floor ${blankFloor})`);
    }

    // --- advisory checks below: judgment calls, never fail the build --------
    // Each is wrapped so an unexpected error becomes a warning, not a FAIL —
    // an advisory check crashing must never flip the exit code.
    const beats = await page.evaluate('window.BEATS');

    // CHECK: caption reading speed. A caption is only fully legible between its
    // fade-in and fade-out, so the readable window is (dur - 2*capFade), not the
    // whole beat. Flags a beat where the caption is too long to actually read
    // before it fades — see CPS_WARN_THRESHOLD above for where 25 comes from.
    try {
      if (!beats) {
        warnings.push('caption reading speed: skipped, window.BEATS not present');
      } else {
        const capFade = await page.evaluate(
          'typeof CONFIG !== "undefined" && CONFIG.capFade !== undefined ? CONFIG.capFade : null');
        const fade = capFade === null ? CAP_FADE_DEFAULT : capFade;
        for (const b of beats) {
          if (!b.cap) continue;
          const effectiveWindow = Math.max(b.dur - 2 * fade, 0.01);
          const cps = b.cap.length / effectiveWindow;
          if (cps > CPS_WARN_THRESHOLD) {
            warnings.push(`caption reading speed: beat "${b.name}" at ${cps.toFixed(1)} cps — "${b.cap}"`);
          }
        }
      }
    } catch (e) {
      warnings.push('caption reading speed: check errored — ' + e.message.split('\n')[0]);
    }

    // CHECK: caption overflow. #cap is white-space:nowrap, so an over-long
    // caption doesn't wrap — it silently extends past the viewport with no
    // error anywhere, just a clipped pill. This mutates #cap.textContent
    // directly (bypassing seekTo), so it MUST run after the determinism check
    // above, and MUST call seekTo() again afterward to put the caption back to
    // whatever the scene itself renders at t — otherwise this would leave the
    // page in a synthetic state that a later check reads.
    try {
      if (!beats) {
        warnings.push('caption overflow: skipped, window.BEATS not present');
      } else {
        // Measure at the SHIPPING viewport, not this file's small check viewport.
        // The caption is sized in fixed CSS px (30px in the template), so the
        // pill occupies ~3x the frame width at 640 that it does at 1920 — the
        // first run of this check measured at 640 and reported the shipped
        // template as overflowing, which is a measurement artifact, not a
        // finding. Anything comparing an element against the frame has to be
        // measured at the size the frame is actually rendered.
        await page.setViewportSize(SHIP_VIEWPORT);
        for (const b of beats) {
          if (!b.cap) continue;
          const { width, innerWidth } = await page.evaluate(`(() => {
            const el = document.getElementById('cap');
            el.textContent = ${JSON.stringify(b.cap)};
            return { width: el.offsetWidth, innerWidth: window.innerWidth };
          })()`);
          const limit = innerWidth * CAP_OVERFLOW_FRACTION;
          if (width > limit) {
            warnings.push(`caption overflow: beat "${b.name}" measured ${width}px wide against ${innerWidth}px viewport (limit ${limit.toFixed(0)}px)`);
          }
        }
        await page.setViewportSize(VIEWPORT);
        await page.evaluate(`window.seekTo(${t})`); // restore — see comment above
      }
    } catch (e) {
      try { await page.setViewportSize(VIEWPORT); } catch (e2) {}
      warnings.push('caption overflow: check errored — ' + e.message.split('\n')[0]);
      try { await page.evaluate(`window.seekTo(${t})`); } catch (e2) {}
    }

    // CHECK: exposure, both tails. This template's renderer uses ACES tone
    // mapping (scene.template.html), which blows out pale materials — but a
    // dark-palette scene fails the opposite way, coming out crushed and muddy.
    // Checking only for overexposure would fire the wrong way on half of all
    // scenes. Sampled at three points across the film and aggregated by worst
    // case, since a scene can be fine at one timestamp and clip or crush at
    // another. Measured in-page with an offscreen 2D canvas (drawImage +
    // getImageData) rather than pulling in an image-decoding dependency — see
    // the file header. Does not depend on window.BEATS: #c is part of the base
    // contract, not the beats extension.
    try {
      const times = EXPOSURE_SAMPLE_TIMES.map(f => f * dur);
      let worstClipped = 0, worstCrushed = 0, worstSpread = Infinity;
      for (const et of times) {
        await page.evaluate(`window.seekTo(${et})`);
        const stats = await page.evaluate(`(() => {
          const src = document.getElementById('c');
          const w = ${EXPOSURE_SAMPLE_WIDTH};
          const h = Math.max(1, Math.round(src.height / src.width * w) || Math.round(innerHeight / innerWidth * w));
          const off = document.createElement('canvas');
          off.width = w; off.height = h;
          const ctx = off.getContext('2d');
          ctx.drawImage(src, 0, 0, w, h);
          const data = ctx.getImageData(0, 0, w, h).data;
          const lumas = [];
          let clipped = 0, crushed = 0;
          for (let i = 0; i < data.length; i += 4) {
            const luma = 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
            lumas.push(luma);
            if (luma > ${EXPOSURE_LUMA_CLIP}) clipped++;
            if (luma < ${EXPOSURE_LUMA_CRUSH}) crushed++;
          }
          lumas.sort((x, y) => x - y);
          const pct = p => lumas[Math.floor(p * (lumas.length - 1))];
          return { clipped: clipped / lumas.length, crushed: crushed / lumas.length,
                    p05: pct(0.05), p95: pct(0.95) };
        })()`);
        worstClipped = Math.max(worstClipped, stats.clipped);
        worstCrushed = Math.max(worstCrushed, stats.crushed);
        worstSpread = Math.min(worstSpread, stats.p95 - stats.p05);
      }
      await page.evaluate(`window.seekTo(${t})`); // restore after sampling across the film

      if (worstClipped > EXPOSURE_CLIPPED_THRESHOLD) {
        warnings.push(`exposure [provisional threshold]: washed out — ${(worstClipped * 100).toFixed(1)}% of pixels clipped to white — lower CONFIG.exposure and desaturate/darken pale materials`);
      }
      if (worstCrushed > EXPOSURE_CRUSHED_THRESHOLD) {
        warnings.push(`exposure [provisional threshold]: crushed — ${(worstCrushed * 100).toFixed(1)}% of pixels near black — raise exposure or add a fill/rim light`);
      }
      if (worstSpread < EXPOSURE_DYNRANGE_THRESHOLD) {
        warnings.push(`exposure [provisional threshold]: low dynamic range — the frame is nearly flat, ${worstSpread.toFixed(1)} points between p05 and p95`);
      }
    } catch (e) {
      warnings.push('exposure: check errored — ' + e.message.split('\n')[0]);
      try { await page.evaluate(`window.seekTo(${t})`); } catch (e2) {}
    }
  } catch (e) {
    fails.push(e.message.split('\n')[0]);
  }
  await page.close();
  return { fails: fails.concat(noise), warnings };
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
    execFileSync('bun', ['run', path.join(__dirname, 'build.js'), 'vendor'], { stdio: 'inherit' });
  }

  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--no-sandbox'],
  });

  let failed = 0;
  let warned = 0;
  for (const scene of scenes) {
    const variants = [scene];
    try {
      const out = execFileSync('bun', ['run', path.join(__dirname, 'build.js'), 'bundle', scene],
                               { encoding: 'utf8' });
      const m = out.match(/bundled -> (.+)/);
      if (m) variants.push(m[1].trim());
    } catch (e) {
      console.log(`FAIL ${scene} [bundle] — ${e.message.split('\n')[0]}`);
      failed++;
    }
    for (const v of variants) {
      const { fails, warnings } = await checkScene(browser, v);
      const label = v.endsWith('.bundled.html') ? 'bundled' : 'source';
      if (fails.length) {
        failed++;
        console.log(`FAIL ${v} [${label}]`);
        for (const f of fails) console.log('       ' + f);
      } else {
        console.log(`ok   ${v} [${label}]`);
      }
      // Advisory: printed after the ok/FAIL line, never counted toward `failed`
      // or the exit code — a scene with only warnings still prints `ok` and
      // still exits 0.
      if (warnings.length) {
        warned += warnings.length;
        console.log(`warn ${v} [${label}]`);
        for (const w of warnings) console.log('       ' + w);
      }
    }
  }
  await browser.close();
  console.log(failed ? `\n${failed} check(s) failed` : '\nall scenes pass');
  console.log(`${warned} advisory warning(s)`);
  process.exit(failed ? 1 : 0);
})();
