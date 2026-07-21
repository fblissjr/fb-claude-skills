// Frame shooter for explainer-video scenes. Drives window.seekTo(t) in headless
// Chromium and screenshots each frame — deterministic, so frames can be shot in
// any order, re-shot in ranges, and always match the live HTML loop.
//
// Usage:
//   bun run shoot.js <scene.html> sample 0,2.5,7      -> sample_<t>.png previews
//   bun run shoot.js <scene.html> full [fps]          -> frames/f00000.png ... (fps default 30)
//   bun run shoot.js <scene.html> range <a> <b> [fps] -> re-shoot frames [a,b) after an edit
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
function num(v, dflt, label) {
  if (v === undefined || v === '') {
    if (dflt === null) throw new Error(`missing ${label}`);
    return dflt;
  }
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) throw new Error(`invalid ${label}: ${JSON.stringify(v)}`);
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

(async () => {
  const [, , sceneFile, mode = 'sample', ...rest] = process.argv;
  if (!sceneFile || !fs.existsSync(sceneFile)) {
    console.error('usage: bun run shoot.js <scene.html> sample|full|range ...'); process.exit(1);
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
    for (const t of (rest[0] || '0').split(',').map(Number)) {
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
    fs.rmSync(outDir, { recursive: true, force: true });
    fs.mkdirSync(outDir, { recursive: true });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await shot(i / fps, path.join(outDir, `f${String(i).padStart(5, '0')}.png`));
      if (i % 60 === 0) console.log(`frame ${i}/${n}`);
    }
    console.log(`done: ${n} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  } else if (mode === 'range') {
    const a = num(rest[0], null, 'start frame'), b = num(rest[1], null, 'end frame'),
          fps = num(rest[2], 30, 'fps');
    fs.mkdirSync(outDir, { recursive: true });
    for (let i = a; i < b; i++) await shot(i / fps, path.join(outDir, `f${String(i).padStart(5, '0')}.png`));
    console.log('range done');
  } else {
    console.error('unknown mode: ' + mode); process.exit(1);
  }
  await browser.close();
})();
