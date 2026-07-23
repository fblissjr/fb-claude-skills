// Frame shooter for explainer-video scenes. Drives window.seekTo(t) in headless
// Chromium and screenshots each frame — deterministic, so frames can be shot in
// any order, re-shot in ranges, and always match the live HTML loop.
//
// Usage:
//   bun run shoot.js <scene.html> sample 0,2.5,7      -> <scene>_sample_<t>.png
//                                                       (into FRAMES_DIR if set)
//   bun run shoot.js <scene.html> full [fps]          -> frames/f00000.png ... (fps default 30)
//   bun run shoot.js <scene.html> full 30 --workers 4 -> same frames, N pages in parallel
//   bun run shoot.js <scene.html> range <a> <b> [fps] -> re-shoot frames [a,b) after an edit
//   bun run shoot.js <scene.html> beats [frac]        -> one frame per window.BEATS entry,
//                                                         frac (default 0.6) into each beat
//   bun run shoot.js <scene.html> manifest [frac]     -> beats JSON only, shoots nothing
//
// --workers N (or SHOOT_WORKERS=N in the environment, which build.js callers
// inherit) parallelizes `full`. This falls straight out of determinism: frames
// are independent, so N pages each shoot a CONTIGUOUS 1/N of the range with
// zero correctness risk — contiguous rather than strided, so a worker that dies
// leaves one obvious gap instead of a comb the encoder would hide.
//
// Measured before trusting, both halves: 1-worker and 4-worker output of the
// template scene are BYTE-IDENTICAL (48/48 frames). And on a 4-core software-GL
// container the speedup is ~1.0x (25.1s vs 26.1s) — SwiftShader already
// multithreads ONE page's rasterization across the cores, so extra pages only
// contend. Reach for this on a many-core box or hardware GL, where one page
// cannot saturate the machine; that case is plausible and NOT yet measured.
// Do not expect it to rescue a low-core cloud render.
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


/* ---------- GL backend ------------------------------------------------------
   Hardware by default; ANGLE_BACKEND=swiftshader forces software.

   This used to be hardcoded to swiftshader, which cost two things. Speed: on a
   post-chain scene the GL draw alone is 182 ms/frame under SwiftShader against
   3.3 ms on hardware -- 55x -- and 2.6x end to end. Correctness: a Sky-sourced
   PMREM environment map poisons every MeshStandardMaterial fragment under
   SwiftShader, and the shipped pipeline duly produced 342 black frames and a
   black MP4 with no error and exit 0.

   Determinism is unaffected: seekTo purity is a property WITHIN a renderer, and
   smoke.js checks it there. Frames are NOT byte-identical across backends
   (measured PSNR 57-58 dB, differences confined to antialiased edges and
   speculars), so a regression compared byte-wise must fix the backend on both
   sides -- which is why this is one env var rather than a silent default flip
   per machine. */
const ANGLE_OK = ['default', 'swiftshader', 'metal', 'gl', 'vulkan', 'd3d11', 'd3d9'];
function angleArgs() {
  const base = ['--hide-scrollbars', '--no-sandbox'];
  const want = (process.env.ANGLE_BACKEND || 'default').toLowerCase();
  // Allow-list, because a typo used to be accepted silently: `swifthsader`
  // launched on hardware GL while the author believed they were reproducing a
  // software-GL regression byte-for-byte, which is the one thing this variable
  // exists to make possible.
  if (!ANGLE_OK.includes(want)) {
    throw new Error(`ANGLE_BACKEND="${process.env.ANGLE_BACKEND}" is not one of: ${ANGLE_OK.join(', ')}`);
  }
  if (want === 'swiftshader') return ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', ...base];
  if (want === 'default') return base;                 // let Chromium pick the GPU
  return [`--use-angle=${want}`, ...base];
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
      // Both Intel and Apple-Silicon layouts (backported from screenwright):
      // without the -arm64 entries this scan matched NOTHING on Apple Silicon
      // and silently fell through to system Chrome — an auto-updating build,
      // not the one playwright pins.
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

// Clear only the frames WE own (f#####.png), never rmSync the directory itself:
// FRAMES_DIR=. would otherwise erase the scene and everything beside it. Shared
// by `full` and `beats`; `range` deliberately does NOT clear (partial reshoot).
function clearFrames(dir) {
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(dir)) {
    if (/^f\d{5}\.(png|jpg)$/.test(f)) fs.rmSync(path.join(dir, f), { force: true });
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

// One scene page, fully initialized: contract waited on, playback stopped,
// DURATION validated. `full --workers N` opens N of these; every other mode
// opens one. Identical setup per page is what makes the N-worker output
// byte-identical to the 1-worker output.
async function openScenePage(browser, sceneFile) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  // Surface scene errors instead of shooting 600 silently-broken frames. A
  // renamed three API is the usual cause and fails quietly otherwise.
  page.on('pageerror', e => console.error('scene error: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('console: ' + m.text()); });
  // SCENE_QUERY lets a review pass ask the scene for a variant of itself --
  // today `strip=text`, which is how "cover everything except the geometry"
  // became a standing pass instead of a hand-edited copy of the scene.
  const q = process.env.SCENE_QUERY ? '&' + process.env.SCENE_QUERY : '';
  await page.goto(url.pathToFileURL(path.resolve(sceneFile)).href + '?record=1' + q);
  await page.waitForFunction('window.sceneReady === true', { timeout: 20000 })
    .catch(() => { throw new Error('scene never set window.sceneReady — check the errors above'); });
  // The scene declares the frame it was authored for; the recorder follows it.
  // This is the whole mechanism behind non-16:9 output -- a scene that sets
  // FRAME.px = [1080,1920] records vertical with no flag and no other edit.
  // Scenes predating window.FRAME keep the historical 1920x1080 above.
  const framePx = await page.evaluate('window.FRAME && window.FRAME.px');
  if (Array.isArray(framePx) && framePx.length === 2
      && framePx.every(n => Number.isFinite(n) && n > 0)
      && (framePx[0] !== 1920 || framePx[1] !== 1080)) {
    await page.setViewportSize({ width: Math.round(framePx[0]), height: Math.round(framePx[1]) });
  }
  await page.evaluate('window.stopPlayback()');
  // No `|| 20` fallback: a missing DURATION is a contract violation, and
  // defaulting it silently renders a truncated film. Fail loudly instead.
  const dur = await page.evaluate('window.DURATION');
  if (typeof dur !== 'number' || !(dur > 0)) {
    throw new Error(`scene did not set window.DURATION (got ${JSON.stringify(dur)})`);
  }
  return { page, dur };
}

(async () => {
  const [, , sceneFile, mode = 'sample', ...restRaw] = process.argv;
  if (!sceneFile || !fs.existsSync(sceneFile)) {
    console.error('usage: bun run shoot.js <scene.html> sample|full|range|beats|manifest ...'); process.exit(1);
  }
  // Pull --workers out before positional parsing so `full 30 --workers 4` and
  // `full --workers 4 30` both read fps=30. The env form exists so build.js
  // callers (frames/all/loop/avif/sheet) inherit parallelism without every
  // call site growing a parameter.
  const rest = [];
  let workersArg;
  for (let i = 0; i < restRaw.length; i++) {
    if (restRaw[i] === '--workers') { workersArg = restRaw[++i]; continue; }
    rest.push(restRaw[i]);
  }
  const workers = Math.max(1, Math.round(
    num(workersArg !== undefined ? workersArg : process.env.SHOOT_WORKERS, 1, 'workers', { max: 32 })));

  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: angleArgs(),
  });
  const { page, dur } = await openScenePage(browser, sceneFile);

  // FRAMES_DIR lets a caller shoot somewhere other than frames/, so a derived
  // output (build.js loop) cannot clobber the frames a full render produced.
  // Honoured by BOTH full and range: range is the mode a user runs by hand to
  // re-shoot a few seconds after an edit, so an override that skipped it would
  // silently write to the wrong place in exactly the manual case.
  const outDir = process.env.FRAMES_DIR || 'frames';

  /* PNG is lossless and correct for masters. It is also ~164-190 ms/frame of
     encode+transfer against ~29 ms for JPEG q90 over the IDENTICAL readback
     path -- measured, and on hardware GL that is ~95% of all capture time. So
     review passes (sheet/strip/aspect), which already emit .jpg anyway, opt in
     via SHOOT_FORMAT=jpeg. Measurements (motion) and deliverables (frames/all)
     stay PNG: JPEG artifacts would add noise to a frame-difference metric. */
  const FMT = (process.env.SHOOT_FORMAT || 'png').toLowerCase();
  const shotOpts = FMT === 'jpeg' ? { type: 'jpeg', quality: 92 } : {};
  // The extension follows the format. Writing JPEG bytes into a .png name made
  // every downstream check (clearFrames, motion's frame count, ffmpeg's content
  // sniffing) match on a lie, and made it possible to splice lossy frames into a
  // lossless master by re-shooting a range with SHOOT_FORMAT exported.
  const EXT = FMT === 'jpeg' ? 'jpg' : 'png';
  const fname = i => `f${String(i).padStart(5, '0')}.${EXT}`;
  const shot = async (t, file) => {
    await page.evaluate(`window.seekTo(${t.toFixed(4)})`);
    await page.screenshot({ path: file, ...shotOpts });
  };

  if (mode === 'sample') {
    // Honour FRAMES_DIR and prefix with the scene. Sample filenames used to be
    // timestamp-derived and scene-independent, written to CWD regardless of
    // FRAMES_DIR -- so two scenes sampled at the same t silently overwrote each
    // other, which duly happened in a shared workspace.
    const sDir = process.env.FRAMES_DIR || '.';
    fs.mkdirSync(sDir, { recursive: true });
    const sBase = path.basename(sceneFile).replace(/\.[^.]+$/, '');
    // sample was left out of the num() hardening: `sample 3O` produced NaN,
    // drove the scene with t=NaN and wrote sample_NaN.png with exit 0 -- the
    // exact typo cited as num()'s motivation, in the one mode it skipped.
    for (const t of (rest[0] || '0').split(',').map((x, i) => num(x, null, `sample time #${i + 1}`, { allowZero: true }))) {
      const f = path.join(sDir, `${sBase}_sample_${String(t).replace('.', '_')}.png`);
      await shot(t, f);
      console.log('sample', t, '->', f);
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
    // Contiguous chunks: worker k owns [floor(k*n/W), floor((k+1)*n/W)). A
    // worker that dies leaves one hole with clean edges — the encoder then
    // fails loudly on the missing sequence numbers instead of interleaving
    // stale frames into a comb nobody notices.
    const W = Math.min(workers, Math.max(1, n));
    let done = 0;
    const shootChunk = async (pg, a, b) => {
      for (let i = a; i < b; i++) {
        await pg.evaluate(`window.seekTo(${(i / fps).toFixed(4)})`);
        await pg.screenshot({ path: path.join(outDir, fname(i)), ...shotOpts });
        if (++done % 60 === 0) console.log(`frame ${done}/${n}`);
      }
    };
    if (W === 1) {
      await shootChunk(page, 0, n);
    } else {
      console.log(`workers: ${W} (contiguous chunks)`);
      const extras = await Promise.all(
        Array.from({ length: W - 1 }, () => openScenePage(browser, sceneFile).then(r => r.page)));
      const pages = [page, ...extras];
      await Promise.all(pages.map((pg, k) =>
        shootChunk(pg, Math.floor(k * n / W), Math.floor((k + 1) * n / W))));
      // browser.close() below reaps the extra pages; nothing to do per-page.
    }
    console.log(`done: ${done} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  } else if (mode === 'range') {
    const a = num(rest[0], null, 'start frame', { allowZero: true }), b = num(rest[1], null, 'end frame'),
          fps = num(rest[2], 30, 'fps');
    fs.mkdirSync(outDir, { recursive: true });
    for (let i = a; i < b; i++) await shot(i / fps, path.join(outDir, fname(i)));
    console.log('range done');
  } else if (mode === 'aspects') {
    // One moment, several window shapes, relative to the scene's OWN design
    // frame — so this is meaningful for a vertical or square scene too. Feeds
    // `build.js aspect`; the settle wait matters because the scene resizes its
    // canvas in a resize handler and sampling before that lands reads a stale
    // canvas (the bug that first made this check report nonsense).
    const at = num(rest[0], 0, 'time', { allowZero: true });
    const ar = (await page.evaluate('window.FRAME && window.FRAME.aspect')) || 16 / 9;
    const shapes = [
      { tag: 'design', w: 1280, h: Math.round(1280 / ar) },
      { tag: 'narrow', w: 1100, h: Math.round(1100 / (ar * 0.72)) },
      { tag: 'square', w: 1000, h: Math.round(1000 / (ar * 0.56)) },
      { tag: 'wide',   w: 1600, h: Math.round(1600 / (ar * 1.33)) },
    ];
    const aDir = process.env.FRAMES_DIR || '.aspectframes';
    clearFrames(aDir);
    for (let i = 0; i < shapes.length; i++) {
      await page.setViewportSize({ width: shapes[i].w, height: shapes[i].h });
      await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
      await page.evaluate(`window.seekTo(${at.toFixed(4)})`);
      await page.screenshot({ path: path.join(aDir, fname(i)), ...shotOpts });
    }
    console.log(JSON.stringify({ shapes }));
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
        await shot(b.t, path.join(beatsDir, fname(b.i)));
      }
    }
    console.log(beatsManifest({ synthetic, beats }));
  } else {
    console.error('unknown mode: ' + mode); process.exit(1);
  }
  await browser.close();
})();
