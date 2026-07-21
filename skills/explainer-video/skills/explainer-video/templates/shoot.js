// Frame shooter for explainer-video scenes. Drives window.seekTo(t) in headless
// Chromium and screenshots each frame — deterministic, so frames can be shot in
// any order, re-shot in ranges, and always match the live HTML loop.
//
// Usage:
//   bun run shoot.js <scene.html> sample 0,2.5,7      -> sample_<t>.png previews
//   bun run shoot.js <scene.html> full [fps]          -> frames/f00000.png ... (fps default 30)
//   bun run shoot.js <scene.html> range <a> <b> [fps] -> re-shoot frames [a,b) after an edit
//   bun run shoot.js <scene.html> beats [frac]        -> one frame per window.BEATS entry,
//                                                         frac (default 0.6) into each beat
//   bun run shoot.js <scene.html> manifest [frac]     -> beats JSON only, shoots nothing
//
// Then: ffmpeg -framerate 30 -i frames/f%05d.png -c:v libx264 -preset slow \
//              -crf 17 -pix_fmt yuv420p -movflags +faststart out.mp4
//
// Chromium resolution order: $CHROMIUM_PATH, playwright's managed browser,
// then common system locations. `bunx playwright install chromium` if none.
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const os = require('os');
const url = require('url');

// Number() on a typo yields NaN, and `for (i=0; i<NaN; i++)` runs zero times --
// so `full 3O` printed "done: NaN frames", exited 0, and wrote nothing. A mode
// that reports success while doing nothing is the worst failure available here,
// because the next encode silently reuses whatever frames were already there.
function num(v, dflt, label, { allowZero = false, max = Infinity } = {}) {
  if (v === undefined || v === '') {
    if (dflt === null) throw new Error(`missing ${label}`);
    return dflt;
  }
  const n = Number(v);
  // allowZero because frames are 0-based: `range 0 60` re-shoots the opening,
  // which is the documented purpose of the mode. Rejecting 0 there conflated
  // "not a number" with "zero", and fps legitimately wants n > 0.
  // max exists for beats' frac: a frac above 1 seeks past the end of the beat
  // and into the next one, silently shooting the wrong beat's frame under the
  // right beat's label -- the same "reports success while doing the wrong
  // thing" failure this function was written to close off.
  if (!Number.isFinite(n) || n < 0 || (!allowZero && n === 0) || n > max) {
    throw new Error(`invalid ${label}: ${JSON.stringify(v)}`);
  }
  return n;
}

function chromiumPath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try { const p = chromium.executablePath(); if (p && fs.existsSync(p)) return p; } catch (e) {}
  // Playwright's cache is versioned (chromium-<build>); scan rather than pin a
  // build number, which goes stale on every playwright bump.
  for (const cache of [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers',
                       path.join(os.homedir(), 'Library/Caches/ms-playwright'),
                       path.join(os.homedir(), '.cache/ms-playwright')]) {
    if (!cache || !fs.existsSync(cache)) continue;
    const byBuild = (a, b) => (parseInt(b.replace(/\D+/g, ''), 10) || 0) - (parseInt(a.replace(/\D+/g, ''), 10) || 0);
    for (const d of fs.readdirSync(cache).filter(d => d.startsWith('chromium')).sort(byBuild)) {
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

// Clear only the frames WE own (f#####.png), never rmSync the directory itself:
// FRAMES_DIR=. would otherwise erase the scene and everything beside it. Shared
// by `full` and `beats`; `range` deliberately does NOT clear (partial reshoot).
function clearFrames(dir) {
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(dir)) {
    if (/^f\d{5}\.png$/.test(f)) fs.rmSync(path.join(dir, f), { force: true });
  }
}

// One implementation of "place a point `frac` into each segment". A real
// window.BEATS drives it; an older scene without one falls back to 8 even
// segments of DURATION through the SAME map, so there is exactly one code path
// whether the segment is an authored beat or synthetic. `manifest` mode emits
// this without shooting; `beats` mode also screenshots each `t`.
function computeBeats(rawBeats, dur, frac) {
  const synthetic = !(Array.isArray(rawBeats) && rawBeats.length);
  const segments = synthetic
    ? Array.from({ length: 8 }, (_, i) => ({ name: String(i), dur: dur / 8 }))
    : rawBeats;
  let t0 = 0;
  const beats = segments.map((b, i) => {
    const start = t0; t0 += b.dur;
    // Clamp the sample strictly below the beat end. At frac==1, start+frac*dur
    // equals the NEXT beat's start (beats are [t0,t1)), so seekTo would render
    // the next beat's opening frame under THIS beat's label. Nudging just inside
    // keeps beat k active while still reading as "the end of the beat".
    const t = start + Math.min(frac, 1 - 1e-6) * b.dur;
    return { i, name: b.name, start, dur: b.dur, t };
  });
  return { synthetic, beats };
}

// start/dur ride along beyond the {i,name,t} a caller strictly needs, so
// build.js motion can bucket an arbitrary timestamp into a beat from this alone.
function beatsManifest({ synthetic, beats }) {
  return JSON.stringify({
    synthetic,
    beats: beats.map(b => ({
      i: b.i, name: b.name, t: Number(b.t.toFixed(2)),
      start: Number(b.start.toFixed(2)), dur: Number(b.dur.toFixed(2)),
    })),
  });
}

(async () => {
  const [, , sceneFile, mode = 'sample', ...rest] = process.argv;
  if (!sceneFile || !fs.existsSync(sceneFile)) {
    console.error('usage: bun run shoot.js <scene.html> sample|full|range|beats|manifest ...'); process.exit(1);
  }
  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  // Surface scene errors instead of shooting 600 silently-broken frames. A
  // renamed three API is the usual cause and fails quietly otherwise.
  page.on('pageerror', e => console.error('scene error: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('console: ' + m.text()); });
  await page.goto(url.pathToFileURL(path.resolve(sceneFile)).href + '?record=1');
  await page.waitForFunction('window.sceneReady === true', { timeout: 20000 })
    .catch(() => { throw new Error('scene never set window.sceneReady — check the errors above'); });
  await page.evaluate('window.stopPlayback()');
  // No `|| 20` fallback: a missing DURATION is a contract violation, and
  // defaulting it silently renders a truncated film. Fail loudly instead.
  const dur = await page.evaluate('window.DURATION');
  if (typeof dur !== 'number' || !(dur > 0)) {
    throw new Error(`scene did not set window.DURATION (got ${JSON.stringify(dur)})`);
  }

  // FRAMES_DIR lets a caller shoot somewhere other than frames/, so a derived
  // output (build.js loop) cannot clobber the frames a full render produced.
  // Honoured by BOTH full and range: range is the mode a user runs by hand to
  // re-shoot a few seconds after an edit, so an override that skipped it would
  // silently write to the wrong place in exactly the manual case.
  const outDir = process.env.FRAMES_DIR || 'frames';

  const shot = async (t, file) => {
    await page.evaluate(`window.seekTo(${t.toFixed(4)})`);
    await page.screenshot({ path: file });
  };

  if (mode === 'sample') {
    // sample was left out of the num() hardening: `sample 3O` produced NaN,
    // drove the scene with t=NaN and wrote sample_NaN.png with exit 0 -- the
    // exact typo cited as num()'s motivation, in the one mode it skipped.
    for (const t of (rest[0] || '0').split(',').map((x, i) => num(x, null, `sample time #${i + 1}`, { allowZero: true }))) {
      await shot(t, `sample_${String(t).replace('.', '_')}.png`);
      console.log('sample', t);
    }
  } else if (mode === 'full') {
    const fps = num(rest[0], 30, 'fps'), n = Math.round(fps * dur);
    // Clear the directory first. Without this, a re-render that produces FEWER
    // frames than last time (shorter DURATION, lower fps) leaves the old tail in
    // place and the encoder appends it -- the end of your film is the previous
    // film. This silently corrupted a shipped artifact: an 11s scene encoded to
    // 22.8s of animation. `range` deliberately does NOT clear, since partial
    // re-shooting is its whole purpose.
    // Delete only the frames WE own (see clearFrames): the earlier
    // rmSync(outDir, {recursive}) with outDir from FRAMES_DIR let
    // `FRAMES_DIR=. shoot.js ... full` erase the scene and everything beside it.
    clearFrames(outDir);
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await shot(i / fps, path.join(outDir, `f${String(i).padStart(5, '0')}.png`));
      if (i % 60 === 0) console.log(`frame ${i}/${n}`);
    }
    console.log(`done: ${n} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  } else if (mode === 'range') {
    const a = num(rest[0], null, 'start frame', { allowZero: true }), b = num(rest[1], null, 'end frame'),
          fps = num(rest[2], 30, 'fps');
    fs.mkdirSync(outDir, { recursive: true });
    for (let i = a; i < b; i++) await shot(i / fps, path.join(outDir, `f${String(i).padStart(5, '0')}.png`));
    console.log('range done');
  } else if (mode === 'beats' || mode === 'manifest') {
    // beats: screenshot one frame per beat AND print the manifest (build.js
    // sheet tiles the frames). manifest: print the manifest only, no frames --
    // build.js motion needs start/dur but never opens the images, so shooting
    // them was pure waste. One computation (computeBeats) feeds both.
    const frac = num(rest[0], 0.6, 'frac', { allowZero: true, max: 1 });
    const { synthetic, beats } = computeBeats(await page.evaluate('window.BEATS'), dur, frac);
    if (mode === 'beats') {
      // Own directory, default .sheetframes (not frames/), so a beats shoot for
      // a contact sheet never collides with a full render's frames/.
      const beatsDir = process.env.FRAMES_DIR || '.sheetframes';
      clearFrames(beatsDir);
      for (const b of beats) {
        await shot(b.t, path.join(beatsDir, `f${String(b.i).padStart(5, '0')}.png`));
      }
    }
    console.log(beatsManifest({ synthetic, beats }));
  } else {
    console.error('unknown mode: ' + mode); process.exit(1);
  }
  await browser.close();
})();
