# changelog

## 0.48.1

### changed
- **CLAUDE.md**: invariant 2 corrected. It said every path "must resolve under the repo root", which reads as permission for `/Users/<name>/<this-repo>/x` — and that is exactly how five paths carrying a username survived 157 days and a full docs triage. The hooks do permit that shape by design; it still leaks the username. The invariant now says so and points at the whole-tree audit that catches the second class. Invariant 1 gains the clause that editing `tools/<plugin>/src/` *triggers* the cascade — it previously listed `tools/<plugin>/pyproject.toml` as a target without saying what causes one, and skill-maintainer shipped two commits at 0.13.0 through that gap.
- **CLAUDE.md**: fixed three self-contradictions and a stale date. The working agreements listed `env-forge` among the disabled SessionStart hooks while invariant 6 correctly calls it deprecated; the "Where to find what" table advertised captured upstream docs two rows above a row stating nothing upstream is copied in; the SKILL.md count was wrong. Last-updated moved from 2026-05-04 despite same-day rewrites.
- **README.md**: `skill-dashboard` was listed in two plugin tables and missing from the install block entirely despite shipping in the marketplace — all 18 plugins are now installable from the README. Removed references to the deleted `docs/reports/` synthesis, and rewrote the `docs/analysis/` description, which still advertised a tagged wiki of domain reports rather than the three files that survived triage.

### added
- **docs/internals/gotchas.md**: two operational hazards that cost real time. `/code-review ultra` with no argument diffs against `origin/main`, so pushing first empties the review target; it also caps at 8,000 lines, which this repo exceeds routinely. Splitting a diff across branches to fit that cap manufactures false positives — reviewers report content as missing when it only lives in the half they cannot see, which accounted for four findings in the 2026-07-21 review. Also: `git add -A` with two sessions in one worktree, which swept work three times and permanently detached two changelog entries from their commits.

## 0.48.0

A nine-angle max-effort review of the previous seven commits returned 26 verified findings, all in code written that day and most of them inside *fixes*. They collapsed to six root causes; fixing the roots rather than the symptoms is what this release does.

### fixed
- **path-privacy 0.5.0 -> 0.6.0**: the installer no longer assembles the hooks path by hand. One `git rev-parse --git-path hooks` call replaces four separate defects: installing into a repo *subdirectory* fabricated a dead `.git/hooks` and reported success; worktrees and submodules crashed with `mkdir: Not a directory` while the changelog claimed they were supported; and a `core.hooksPath` of `~/hooks` created a directory literally named `~` inside the work tree. It now also **refuses** when `core.hooksPath` comes from global config (a per-repo install would have gated every repo on the machine, and `--uninstall` anywhere would have removed it everywhere) and when the hooks directory is tracked (the wrapper embeds a machine-specific absolute path, so committing it would plant the leak class this plugin polices and hand teammates a path that fails closed).
- **path-privacy**: the fail-closed guarantee was defeated one delegation level down. The wrapper carefully selects an *executable* entry script; that script then found its own scanner missing and exited 0 — `# fail open by design` — so a leak committed with rc=0. Both entry scripts now fail closed, matching the wrapper.
- **path-privacy**: the recovery search reached every neighbouring project on disk. A broken checkout at `~/dev/plugin-a` silently ran `~/dev/plugin-zzz`'s scanner — arbitrary sibling code, or on a shared machine another user's, executed as a commit gate. It also matched `<plugin>.backup` snapshots, which sort *above* the real directory. Group 1 is now the frozen tree itself, and the cache group sorts by the version component alone rather than by whole path (where the marketplace directory outranked the version, so `mp-z/0.0.1` beat `mp-a/9.9.9`).
- **explainer-video 0.5.0 -> 0.5.1**: `shoot.js full` recursively deleted its output directory, and that directory comes from `FRAMES_DIR` — so `FRAMES_DIR=. shoot.js scene.html full` erased the scene file and everything beside it. Reproduced independently by three reviewers. It now deletes only `f#####.png`, which is all the stale-tail bug ever required; verified the stale tail is still cleared and a non-frame file in the same directory survives.
- **explainer-video**: `range 0 60` — re-shooting the opening beat, the documented purpose of the mode — threw `invalid start frame: "0"`, because the new validator conflated "not a number" with "zero" on a 0-based index. And `sample` was left out of that validation entirely, still writing `sample_NaN.png` with exit 0 on the exact typo cited as the validator's motivation.
- **explainer-video**: `video()` read `frames/` while `shoot.js` honoured `FRAMES_DIR`, so a hand-run reshoot wrote one place and the encoder read another — silently shipping the previous film.
- **skill-maintainer 0.13.0 -> 0.14.0**: `check_path_privacy` was **built on a wrong diagnosis**, stated as fact in three places. The scanner does not "only see added lines" — `--staged` reads whole files. The 157-day leak survived because `find-external-paths.sh` exempts paths resolving *inside* the repo root, which is exactly what its documented rule says. The two checks enforce genuinely different rules — resolves-outside-root versus carries-a-real-username — and the docstring now says so instead of claiming a parity that never existed.
- **skill-maintainer**: the audit missed a bare `/Users/<name>` with no trailing slash; exempted any file merely *quoting* the `skip-file` marker anywhere (including this CHANGELOG and path-privacy's own SKILL.md); dropped non-ASCII filenames by splitting `git ls-files` on newlines instead of NUL; and returned `[]` on git failure, emitting no row at all so the check silently vanished from the suite.
- **skill-maintainer**: `check_changelog_version` hard-failed Poetry-shaped repos that the regex it replaced handled, and still failed a *populated* `## [Unreleased]` section — only an empty one passed, defeating the exemption's stated purpose. `check_version_alignment` dereferenced marketplace sources that escape the repo root (verified reading `/etc` via a traversal source).
- **skill-maintainer**: the version cascade was never run for this plugin — `plugin.json`, the marketplace entry and `pyproject.toml` all sat at 0.13.0 while its source changed across two commits, so `marketplace update` would not have refreshed installed users at all. The omission is listed in the common-mistakes section of the document being edited in the same branch.

## 0.47.0

### removed
- **docs/analysis**: deleted the seven bannered survivors and `docs/reports/claude_ecosystem_synthesis.md`. `docs/` is now 184K across the essentials.

  This reverses the compromise reached earlier the same day, and the reasoning is recorded in `docs/analysis/log.md` rather than left to look like churn. **The banners did not work.** Retrieval here is frequently grep-based, and a grep hit lands mid-file, below the banner, on unbannered stale prose — the mitigation only protects a whole-file read, which is not how these are consumed. `subagents_and_agent_teams.md` still asserted "subagents cannot spawn other subagents" as a key constraint in its body, which is false and load-bearing for anyone designing delegation.

  Everything durable in the deleted cohort is superseded by `.skill-maintainer/best_practices.md` (which is *maintained*), duplicated by tracked upstream snapshots, shipped in `skills/mcp-apps/references/`, or describes in-repo code that is its own source of truth. The synthesis report went too: 13 of its 15 analysis links were dead, and a 706-line synthesis of documents that no longer exist is worse than none.

  **Kept:** `data_centric_agent_state_research.md` — the one irreplaceable file, holding the comparative survey and DuckDB rationale behind `tools/agent-state`, where `VISION.md` asserts the conclusion but not the comparison. Plus `mcp_protocol_and_servers.md` (verified current) and the log.

### added
- **docs/internals/plugin-patterns.md**: a hook anti-pattern section salvaged before deletion — but only the items that are environmental or that we verified independently. Importing the unverified remainder into a maintained document would have moved the problem rather than solved it. Includes the lesson from this session's own leak: a diff-scoped check cannot enforce a whole-tree invariant.

### fixed
- **branches**: removed two stale local review branches and their worktrees. Verified first that neither held unmerged content — both were squashed snapshots strictly behind `main`. Also confirmed `origin/claude/romantic-brattain` (Feb 2026) is fully landed: its `mcp-app` sources are byte-identical to `main`'s copies under `apps/`, and its `commands/` became `main`'s `skills/`. It reads as unmerged only because the `apps/` restructure moved the paths.

## 0.46.0

### added
- **skill-maintainer**: `check_path_privacy` — a whole-tree audit for absolute home paths carrying a real username, wired into `test_repo_hygiene`.

  The path-privacy pre-commit hook scans the **diff**, so it only ever sees added lines. A leak introduced before the hook existed, or in a file since touched only elsewhere, survives indefinitely. That is not hypothetical: five absolute paths carrying a username sat in a tracked doc for **157 days** and through a full docs triage, because every commit that touched the file added lines somewhere else. The hook was working exactly as designed; the invariant it claims to enforce ("every path in repo content") is broader than what a diff scan can reach.

  This audits content rather than changes, so a pre-existing leak cannot hide behind a clean diff. It honours the same `path-privacy: skip-file` and `path-privacy: ignore` markers the plugin's scanner uses, so the plugins that legitimately contain these patterns stay silent, and treats `/Users/Shared`, regex/substitution syntax, and conventional stand-in names as non-leaks — a check that cries wolf gets bypassed, and this one is meant to gate.

  Seven regression tests, both directions, and mutation-tested: neutering the check turns two of them red.

## 0.45.1

### fixed
- **docs**: reconciled repo documentation with the repo's actual state, from a parallel consistency review.
  - `CLAUDE.md` and `docs/internals/gotchas.md` both said **four** plugins are disabled via `enabledPlugins`; `settings.json` has three. Corrected to three, with the reason recorded: `env-forge` is *deprecated*, not disabled — the `renames` map handles its removal, and an `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.
  - `README.md` listed `explainer-video` twice in the plugins table with conflicting descriptions, twice in the install block, and twice in the invocation list. It also still advertised an "environment synthesis" grouping whose section was removed with env-forge, and omitted `pyright-autoconfig` entirely despite it shipping in the marketplace.
  - `docs/internals/plugin-versioning.md` contradicted itself: the header still described a four-source cascade, and the worked example walked the reader through adding `metadata.version` and `metadata.last_verified` to six SKILL.md files — twenty lines after the document says the field was removed and must not be re-added. A reader skimming for the procedure would have landed on step-by-step instructions to do the forbidden thing. The example is now seven files with no SKILL.md, and the common-mistakes list reflects the checks that actually exist.
  - `docs/internals/upstream_drift_backlog.md` still listed `renames` as absent and the hook-entry count as 9; both were resolved or wrong.

## 0.45.0

### fixed
- **skill-maintainer**: discovery matched `SKIP_DIRS` against the **absolute** path, so a repo checked out beneath any directory named `internal`, `coderef`, `.venv`, `node_modules` or `_deprecated` found zero skills and zero plugins and the suite reported green having scanned nothing — the worst failure available to a checker, since it looks exactly like success. Matching is now relative to the repo root. Verified both ways: a nested repo under `internal/` is now visible, and this repo still excludes its own `internal/` and `_deprecated/`.
- **skill-maintainer**: restored the `.backup` **suffix** rule, which the above refactor dropped — `plugin-toolkit.backup` is a snapshot directory, not a unit to check. Both rules now live in one place instead of one of them getting lost in a refactor, which is precisely what happened.
- **skill-maintainer**: `check_version_alignment` no longer aborts the entire run on a malformed marketplace entry. A non-dict entry, or the object-form `source` the official schema allows (`{"source": "github", ...}`), raised out of the function and killed every later check in `test_repo_hygiene` with no summary printed. External sources are skipped (no local manifest to compare); malformed entries are reported.
- **skill-maintainer**: a plugin whose `plugin.json` parses but has no `name` was silently invisible to the reverse sweep — contradicting the "do NOT skip" reasoning one branch above, in the check whose whole purpose is finding plugins nobody can install.
- **skill-maintainer**: `check_changelog_version` parsed pyproject with a regex that took the first `version = "..."` anywhere in the file, so a `[tool.*]` table above `[project]` won; and single quotes, missing spaces, or a dynamic version made it return success while unable to run at all. Now uses `tomllib`, fails loudly on an unparseable file, and treats declared-dynamic versioning as the legitimate shape it is.
- **skill-maintainer**: the changelog check rejected keep-a-changelog headings (`## [1.2.3] - 2024-01-01`), prerelease suffixes, and a conventional `## Unreleased` section above the top version. This tool runs against arbitrary repos via `--dir`, where all three are standard — a false positive on a correct changelog is how a gate gets ignored.

Each change was verified against a constructed instance of the failure it addresses, and against a legitimate configuration it must not fire on.

## 0.44.0

### fixed
- **path-privacy 0.4.0 -> 0.5.0**: five installer defects found by the parallel review, two of which could affect a user's own repository and shipped in 0.4.0.
  - **`core.hooksPath` repos got a successful-looking no-op.** The installer wrote to `.git/hooks` regardless, so every husky/lefthook repo printed "installed" and git never ran the hooks — the plugin promised a gate it never installed. Same fail-open class as the wrapper bug 0.4.0 fixed, one level up, and it would have shipped alongside that fix. Now honours `core.hooksPath` and says where it installed.
  - **The installer wrote through symlinked hooks.** `.git/hooks/pre-commit` symlinked into the work tree (`ln -s ../../scripts/pre-commit.sh`) meant `cat >` followed the link and overwrote the user's *tracked source file* with the wrapper, which they could then commit. The link is now replaced, never written through.
  - **Discovery picked a candidate before testing executability**, so a newest copy with the exec bit lost blocked every commit while a working older copy sat beside it. And `sort -V` over a merged list compares the marketplace directory before the version, so a stale copy from another marketplace outranked a newer one from your own tree. Groups are now tried in order, newest-executable-first within each.
  - Install refuses rather than silently overwriting when a `.local` already exists and the live hook is not ours; uninstall no longer restores over a hook the user wrote themselves.
  - Worktrees and submodules (`.git` is a file, not a directory) are no longer rejected with a misleading "not a git repo".

Verified by control in throwaway repos: the user's tracked source survives a symlinked-hook install, the wrapper lands in `.husky` and not `.git/hooks`, a real leak is still blocked, clean content still commits, and discovery falls through to an executable older copy rather than failing closed.

## 0.43.0

### fixed
- **explainer-video 0.4.3 -> 0.5.0**: findings from a parallel review pass, most of them defects that shipped.
  - **The committed inline demo was corrupt.** `examples/skill-retrieval.webp` played 22.8s of animation for an 11.0s scene — it contained frames from an unrelated render. Root cause: `shoot.js full` never cleared its output directory, so a re-render producing fewer frames left the previous run's tail in place and the encoder appended it. `full` now clears (`range` deliberately does not — partial re-shooting is its purpose). Artifact rebuilt: 204 KB, 11.0s. The size and beat-count claims in README/SKILL.md/method.md described the corrupt file and are corrected.
  - **`bundle` could destroy the source scene.** `bundleName` returns its input unchanged when the name does not end in exactly `.html`, so `bundle scene.htm` wrote the inlined output over the source and reported success. Now refuses.
  - **A highlight was fully lit before its beat began.** Widening the sweep to ±0.9 to fix a flicker put slab 0 at `bump(0,-0.9,0.9)` = 1.0 for the entire title card. The sweep now starts off the left end. A regression introduced by an earlier fix.
  - **Frame determinism was violated by text antialiasing.** Chrome re-rasterized the DOM overlay with a different AA mode after opacity round-tripped through 0, so the same `t` differed by a few pixels depending on seek *order* — breaking the frames-in-any-order guarantee for any frame with overlay text. `will-change:opacity` pins the layer.
  - Bad numeric args reported success while doing nothing (`full 3O` printed "done: NaN frames", exit 0); `loop` leaked temp dirs on error paths; `file://` URLs broke on `#`/`%` in a path; `ss`/`bump` returned NaN for a zero-width span; `during`/`secAt` bypassed the unknown-beat guard; Chromium build directories sorted lexicographically.
  - Corrected a comment claiming the explicit file list dodges `ARG_MAX` — `execFileSync` argv goes through the same `execve` limit. What it actually buys is deterministic ordering and a loud empty-match failure.

## 0.42.1

### added
- **explainer-video 0.4.2 -> 0.4.3**: `method.md`'s "Build the control" section gains "Verify the control actually ran". The rule as shipped had its own failure mode and did not warn about it: a control testing the wrong thing still returns a number, and the number looks like evidence. Three real instances across today's work — a blank-scene check that never modified the scene, a does-it-fail-without-X run where X was still present, and a summarizing fetch whose silence was read as absence. A green control you did not really run is worse than no control, because it converts an open question into a settled one that nobody revisits.

## 0.42.0

### fixed
- **path-privacy 0.3.2 -> 0.4.0: three defects in the fail-closed wrapper, all found by cross-review, all landing before the push because the marketplace update is what arms the fuse.**
  - **The `rm` remediation destroyed the user's own hook.** The wrapper also *chains* `<hook>.local`, which is where an existing pre-commit hook is preserved at install time. Telling a blocked user to `rm` the wrapper silently took their previous hook with it — our gate fails loudly, theirs died quietly. The message is now conditional: with a `.local` present it says `mv <hook>.local <hook>` and states that this restores what they had before path-privacy.
  - **Discovery assumed a marketplace-cache install.** A local checkout or `--plugin-dir` install has a frozen path that never lived under `<HOME>/.claude/plugins/cache/`, so once it broke the glob found nothing and the user was hard-blocked by a message naming a directory their install was never in. Discovery now searches the frozen path's own tree first (sibling version dirs, then the tree itself) before falling back to the cache, and the error names both locations.
  - **The message had no "why now."** It fires roughly 14 days after a plugin update, on an unrelated commit. It now leads with the cause — the plugin updated and the old cached copy was cleaned up — which turns a mystery block into a recognisable event.
- Verified by control across four paths: `.local` present (user hook runs, `mv` advice shown), local-checkout frozen path with a sibling version (recovers and still blocks a real leak), no `.local` with every discovery source neutered (fails closed, `rm` advice), and the ordinary valid-path case. Two of those controls were wrong on the first attempt — one committed clean content so the exit code proved nothing, and one left the real cache glob intact so the hook legitimately recovered — and were re-run before being recorded.

## 0.41.1

### fixed
- **path-privacy 0.3.1 -> 0.3.2: the wrapper's fallback picked the lexicographically last cached version, not the newest.** Found by cross-review. Glob order is lexicographic, so with `0.1.9` and `0.1.10` both cached the last-wins loop selected `0.1.9` — the older scanner. Verified against a constructed cache: last-wins picks `0.2.0` from `{0.1.6, 0.1.9, 0.1.10, 0.2.0, 0.10.0}` while `sort -V` correctly orders `0.1.6 -> 0.1.9 -> 0.1.10 -> 0.2.0 -> 0.10.0` and picks `0.10.0`. Now uses `sort -V | tail -1`. Narrow — the fallback only runs once the frozen path is gone, which usually leaves one version — but it is reachable when two updates land inside the 14-day orphan window, and "newest" has to mean newest. All three controls re-run after the change: frozen path valid passes, frozen path broken self-heals and still blocks a real leak, nothing found fails closed with the full diagnostic.

## 0.41.0

### added
- **`check_changelog_version`**, proposed by the concurrent session during cross-review: the top `## X.Y.Z` heading in `CHANGELOG.md` must equal the root `pyproject.toml` version. Both of their changelog failures — an insert that matched `# changelog` instead of the version heading, leaving an entry with no version, and the repo version left unbumped — violate that single comparison. Nothing in the repo would have caught either: `check_version_alignment` compares plugin manifests, and the pre-commit only warns when content changes with no version file staged, and version files *were* staged. It is exact rather than heuristic, so it can legitimately gate, and it returns no findings when either file is absent. Verified by reconstructing both historical failures against the real repo, not just synthetic fixtures: each is caught with a specific message, and the tree goes green again on restore. Five regression tests, written red-first.

## 0.40.5

### fixed
- **`check_version_alignment`: two defects found by cross-review, both in the newest logic in my half.**
  - `lstrip("./")` strips a character *set*, not a prefix. A marketplace `source` of `./.claude/thing` became `claude/thing`, so the check would report "plugin.json does not exist" while pointing at a path that was never right — sending someone to hunt a missing file rather than a mangled one. Every current entry happens to be safe, so it passed today and would have broken the first time a plugin lived under a dot-directory. `removeprefix("./")` is the fix. Same class as the `$&` bug in the bundler: a string method doing something adjacent to what it reads like.
  - The reverse sweep swallowed unreadable manifests with `except Exception: continue`. The forward loop reports them. So a corrupt `plugin.json` made a plugin invisible to the exact check meant to catch plugins nobody can install, and the check reported green — the same silent-drift failure the function exists to prevent. It now reports the unreadable manifest.
- Both covered by regression tests written red-first (17 tests, all green).

## 0.40.4

### fixed
- **explainer-video 0.4.1 -> 0.4.2**: three instances of post-refactor staleness, all documentation that never caught up with the 0.2.0 beats change.
  - `references/audio.md` told you to "slow the beat down in `CONFIG`" — but `CONFIG` has held no timing since 0.2.0, and the same file says four lines later that the beats table is the single source of timing truth. Following it literally sent you to the wrong file to find nothing.
  - `references/audio.md` also keyed narration by numeric beat index (`{beat: 1}`) when beats have been named since 0.2.0. Rewritten around named beats and aligned with the roadmap's `narration-drives-timing` design, which is implementable only *because* beats are named data — a measured clip duration cannot be written back into a positional index.
  - `docs/internals/explainer_video_roadmap.md` still specified the addressing helper as `u()` in four places. It was renamed to `ramp()` during the refactor itself, to avoid shadowing the local `u` in `setCamera`.

The first was found by cross-review, the other two by sweeping for the same class afterwards — including one in a file the original sweep had looked at and passed. A sweep scoped to the symptom rather than the class.

## 0.40.3

### fixed
- **explainer-video 0.4.0 -> 0.4.1**: two defects found by cross-review, both in the newest code.
  - **`loop` and `poster` failed on a fresh checkout.** Neither ensured `three.global.js` existed before rendering, so a clean directory produced `THREE is not defined` — loud, but pointing at the scene contract when the cause was a missing build step. `bundle()` had auto-vendored since the start and `smoke.js` gained a conditional version later; the two newest entry points never got it. Now share an `ensureVendor` guard using the same needs-three test, so a non-three backend is still never forced to build a bundle it will not load.
  - **`FRAMES_DIR` was honoured by `shoot.js full` but ignored by `range`.** `range` is the mode a user runs by hand to re-shoot a few seconds after an edit, so the override added in 0.4.0 to stop `loop` clobbering `frames/` silently did not apply in the one case someone drives manually. Both modes now use it.

Both verified by control from clean directories: `poster` and `loop` complete with no vendored bundle present, and `FRAMES_DIR=alt shoot.js range` writes 5 files to `alt/` and 0 to `frames/`.

## 0.40.2

### changed
- **Sharpened the summarising-fetch caveat into a categorical rule.** It read as a caution about large pages losing a sentence. The stronger and correct form, from the concurrent session: **a summary can never source a claim that the docs do not say something**, because absence is precisely what summarisation discards — its silence is not evidence. Not a caveat, a category error. Both sessions made it the same way on the same day: one summarising query against the 230KB hooks page returned "not stated for any hook type" for a sentence that appears three times in the raw text. Recorded in `plugin-patterns.md` and `best_practices.md`.

## 0.40.1

### changed
- **Timeout citations are now verbatim quotes plus a URL, not line numbers into a gitignored snapshot.** The concurrent session could not reproduce the Agent SDK callback sentence via a summarising fetch of the hooks page and said so rather than accepting the correction — the right call. It does reproduce: the sentence sits under `### PreToolUse` in the raw page at <https://code.claude.com/docs/en/hooks>, which is over 230KB, and a single sentence is easy to lose in summarisation. But the citation form was the real problem: the snapshots are gitignored and renumber on every fetch, so a line number is unverifiable by exactly the person who most needs to check it. Both quotes are now inline, and the guidance notes to grep the raw text rather than trust a summary.
- **Corrected an overstatement of my own.** I described the Agent SDK callback case as "the one directly-analogous documented case". It is the same *event* (`PreToolUse`) on a different *mechanism* — an SDK callback, not a `command` hook in `hooks.json`. That makes it weak evidence, not an analogy, and the guidance now says so. The conclusion is unchanged: command-hook timeout behaviour is unspecified, and the 30s value was chosen so that the unknown cannot matter.

## 0.40.0

### fixed
- **Corrected an inference I had written into guidance as documented fact.** The previous entry claimed a canceled `PreToolUse` hook "reports no decision, so the call proceeds and the check fails open". That is not documented for `command` hooks. It was generalized from the HTTP-hook section, which fails open but opens with "Error handling differs from command hooks" and closes with "Unlike command hooks" — a passage that explicitly excludes the case I applied it to. The one directly-analogous documented case says the **opposite**: an Agent SDK callback hook on `PreToolUse` that exceeds its timeout *blocks* the tool call. Command-hook timeout behaviour is genuinely unspecified, and `plugin-patterns.md` and `best_practices.md` now say so and name both conflicting passages. Caught by the concurrent session; it is the same failure the docs triage existed to remove — reading an adjacent section and treating it as the source.
- **path-privacy 0.3.0 -> 0.3.1: `PreToolUse` timeout 3s -> 30s.** With the failure mode unknown, the value should be chosen so it cannot matter. Crossing {fails open, fails closed} against {too short, too long} leaves exactly one catastrophic cell — too-short *and* fails-open, a silent bypass where the gate skips and the write proceeds with no message. Every other outcome is a visible stall or a loud block. So for anything that gates, err long: 30s is ~120x headroom over the measured 0.25s, still diagnosable inside one turn, and 20x below upstream's own 600s default. The earlier 3s bet on a failure mode we cannot confirm. `pyright-autoconfig` deliberately stays at 5s — it gates nothing, has no silent-bypass mode, and its only real risk is stalling session start.
- Also corrects the framing in 0.38.0: upstream's default is 600s, so `3000` was five times the default rather than an obvious outlier, which is part of why it read as plausible through review and a version cascade.

## 0.39.0

### fixed
- **path-privacy 0.2.1 -> 0.3.0: the git-hook wrapper died on a 14-day fuse after every plugin update, and failed open when it did.** `install-git-hooks.sh` froze an absolute path to the scanner at install time, pointing into the **version-stamped** plugin cache (`.../path-privacy/0.1.6/...`). Updating the plugin writes a new version directory and orphans the old one, which Claude Code deletes 14 days later (plugins-reference: "removed automatically 14 days later"). For those 14 days the hook silently ran the *old* scanner, so a fix to the scanner never reached the repo; after 14 days the guard `if [ -x "$PATH_PRIVACY_SCRIPT" ]` went false and the wrapper `exit 0`'d — the leak gate silently doing nothing, in every repo it had ever been installed into. Verified by constructing the pruned state: the old wrapper exits 0 with no output.
- The generated wrapper now re-resolves to the newest installed copy when the frozen path is gone, and if it still cannot find the scanner it **fails closed** with a message naming what it looked for and how to reinstall or remove it. A leak gate that cannot run must not let the commit through quietly. Verified across three cases: frozen path valid (passes), frozen path broken (self-heals via discovery and still blocks a real leak), no copy anywhere (exits 1 with remediation).

### note
- **Existing installs are not self-correcting.** Any repo where `install-git-hooks.sh` was run before this release still has the old frozen-path wrapper. Re-run the installer there to pick up the hardened version.

## 0.38.0

### fixed
- **Two hook timeouts were wrong by 1000x and would have gone live with the next marketplace update.** Upstream documents `timeout` as *seconds*; `path-privacy` had `3000` (fifty minutes) on its `PreToolUse` hook and `pyright-autoconfig` had `5000` (eighty-three minutes) on `SessionStart`. Both were wrong from the commit that introduced them, survived review and a version cascade, and were spotted only because the exec-form conversion moved the field next to `args` in a diff. Corrected to 3 and 5. The `PreToolUse` one had the real blast radius: it gates every Write and Edit, so a hung hook stalls the session for the whole window — and a canceled hook reports no decision, so the call proceeds and the check fails open. A wrong timeout does not make the gate stricter, only the stall longer. Values were measured before being set: the path-privacy scan runs 0.25s against a deliberately extreme 1.4MB/20,000-line payload (12x headroom at 3s), pyright-autoconfig 0.03s (~170x at 5s).

### added
- **The seconds unit is now stated in `plugin-patterns.md` and `best_practices.md`.** Milliseconds are the instinct from every other JS API in this repo, which is why it needed saying — and this was a documented field nobody had checked against its own documentation.

## 0.37.3

### changed
- **The exec-form rule in `plugin-patterns.md` now covers plugin scripts, not just `hooks.json`.** It described a `hooks.json` convention when the underlying problem is spawning a subprocess with an interpolated path, which plugin scripts do too via `execSync`. The rule addressed one surface of a two-surface bug; explainer-video's scripts were living proof of the other. Adds the `execSync` -> `execFileSync` array-argument form, notes that quoting fixes the space case but leaves `;`/`$`/backticks, and records two traps in the same family: a shell-expanded glob silently caps out at `ARG_MAX`, and a derived output written into a source directory destroys the source (a preview build overwriting the full-resolution frames behind an mp4).

## 0.37.2

### fixed
- **explainer-video 0.3.4 -> 0.4.0**: fixed the four defects that were about to be handed to a code review as known-but-unfixed, which is the wrong trade — a review's value is finding what you do not already know.
  - **Shell-free process calls.** Every `execSync` with an interpolated path became `execFileSync` with an argument array. A directory containing a space broke the build outright. This is the same class as the exec-form hook rule added to `plugin-patterns.md` today; that rule covers `hooks.json` and says nothing about plugin scripts, so the guidance addressed one surface of a two-surface bug.
  - **`build.js loop` no longer destroys `frames/`.** It reused the shared directory, so producing a README loop silently overwrote the full-resolution frames a previous `build.js all` had shot — deleting the source of your mp4 with no warning. It now shoots into its own `.loopsrc`, via a new `FRAMES_DIR` override in `shoot.js`.
  - **No shell glob in the WebP encode.** `img2webp ${tmp}/*.png` was never tested past ~100 frames; a 60s film at 12fps is 720 files and can exceed `ARG_MAX`. Now an explicit file list, which also fails loudly when scaling produced nothing.
  - **`smoke.js`'s blank-frame floor derives from the viewport** instead of a hardcoded 6000 bytes, which silently mis-calibrated the moment the viewport changed.

All four verified by control, per the rule added in 0.3.4: `frames/` confirmed intact at 275 files across a `loop` run, a build run to completion from a directory with spaces in its name, and the blank-scene check confirmed still failing (1453 bytes against a derived floor of 5760).

## 0.37.1

### changed
- **The staleness banners added in 0.37.0 were reframed after review from the concurrent session.** They read "Stale -- not re-derived", which describes pending work; in three months that becomes furniture nobody reads. All eight documents are the same case -- wrong in places, still the best available, no rewrite scheduled -- so the banner now says exactly that and states it is permanent rather than a to-do. `data_centric_agent_state_research.md` is reframed as a historical record of what was considered, in the same spirit as `log.md`. The critique was correct and self-directed: a banner with nothing forcing action on it is the same pattern as the permanently-red board.

### added
- **`maintenance.md` records the availability-vs-staleness trade** behind deleting the local upstream copies, rather than leaving it implied. An absent doc announces itself; a stale undated doc teaches something false with confidence. The section says plainly not to quietly re-add local copies on a fetch failure, and what to do instead.
- **`maintenance.md` gains "Designing a new check"**, from two rules earned in the concurrent session. *A proxy can reject but cannot approve*: give a heuristic authority only over its confident region and stay **silent** elsewhere, because a warning band over the uncertain region trains people to skim past the loud case too. *Build the control*: a technique needs a without-it comparison, a check needs a constructed failing case, a threshold needs bracketing by a confirmed-bad and a confirmed-fine observation.
- **A fourth instance of the decayed-signal pattern is recorded** in the drift backlog: freshness checks detect drift over time and catch nothing that was wrong on the day it was written. `method.md` has always specified 3-4 seconds per beat while the example shipped at 2.4/2.4/3.2, under its own floor. Nothing was stale; the doc and the artifact disagreed from the start. We have no general consistency check for a documented threshold against the artifact it governs.

## 0.36.4

### added
- **explainer-video 0.3.3 -> 0.3.4**: `method.md` gains "Build the control", generalizing a discipline that had appeared three times as separate instances. For any claim that a technique improves something, build the version without it and confirm that one is worse — otherwise you have measured your own effort rather than the effect. Three forms tabulated (technique needs a without-it render, check needs a constructed failing case, threshold needs bracketing above and below), each with the worked instance that changed an outcome: the blank-frame check verified against a deliberately blank scene, the caption floor bracketed by a watched-bad 37 CPS and a watched-fine 27 CPS, and phase-locking flagged as claimed-but-uncontrolled. Names the seductive failure it prevents — applying a technique, seeing a good result, and concluding the technique caused it when the result would have looked fine anyway.

### changed
- **roadmap**: recorded that the ~35 CPS caption floor is bracketed by observation on both sides, which the original 17-21 threshold never was, but is still one viewer and two data points. Tighten as more scenes get watched rather than treating it as settled.

## 0.37.0

### removed
- **`docs/` triaged: 26 files deleted, 972K -> 400K.** All 20 of `docs/claude-docs/` -- frozen 2026-02-19 copies of upstream Claude Code docs that had become roughly a third of current content (hooks 64KB -> 235KB, plugins-reference 24KB -> 88KB) while carrying **no date header**, so nothing signalled their staleness. They were wrong in load-bearing ways: `allowed-tools` described as restricting when it grants, hook exit 0 described as success when it reports no decision. Plus six analysis reports: three were the same Anthropic skills-guide PDF restated three times (superseded by `.skill-maintainer/best_practices.md`), `self_updating_system_design.md` described a CDC pipeline never built, and two were point-in-time snapshots pinned to a pre-reorg layout.

### changed
- **Upstream docs are no longer copied into the repo.** `settings`, `permissions` and `mcp` -- the three deleted pages that had no live tracking -- were added to `upstream_urls`, bringing tracked pages to twelve. `skill-maintain upstream` fetches them into gitignored state with per-page deltas. A stale copy is worse than no copy: a clone can refetch in seconds but cannot know that what it is reading is five months old.
- **Eight surviving analysis reports gained staleness banners** naming their specific false claims rather than a generic warning. They share one shape -- durable original synthesis (anti-pattern catalogs, design checklists, comparison matrices) sitting on rotted API specifics. `subagents_and_agent_teams.md` is the sharpest: it asserts three times that subagents cannot spawn subagents, which current docs reverse, and that is load-bearing for delegation design.

### fixed
- **Two documents linked from `CLAUDE.md` as live references were wrong.** `cross_surface_compatibility.md` claimed PreToolUse "exit 0 = approve" (it reports no decision; approval needs `permissionDecision: "allow"`). `mcp_apps_and_ui_development.md` cited `coderef/ext-apps/` and `coderef/mcp-ui/`, neither of which exists -- the real paths are under `coderef/mcp/`. Both corrected in place.
- Link-rot from the deletions repaired across eight files, including relative-path breakage introduced during the redirect; `skill-maintain lint` is clean.

## 0.36.3

### added
- **explainer-video 0.3.2 -> 0.3.3**: `method.md` gains "Where you will be tempted to break this" under the determinism rules. The closed-form requirement is easy to keep until the subject *is* a physical process — any scene depicting momentum, decay, accumulation, charge, wear, growth or trails pulls toward integrating from the previous frame, which breaks `seekTo` purity and beat independence at once. Gives the closed-form replacements (`ω0*exp(-k*(t-t0))` for a coast-down, `count*ramp(...)` for accumulation, N samples of the position function for a trail) and says plainly that physical-metaphor scenes are both the most likely to reach for a simulator and the most likely to expose the divergence on a loop's second pass.
- **explainer-video**: `method.md` gains "Motion that reads vs causality that reads". A sweep only has to be perceived as motion; a beat whose job is "A drives B" fails if the viewer perceives A moving and B moving. The lever is phase and derivation rather than duration — drive B from A's expression, not independently from `t` — and the verification is a control: break the phase relationship deliberately and confirm the broken version reads differently. Marked untested.

### changed
- **roadmap**: the caption lint is redesigned rather than dropped. The surviving rule is general — **a proxy can reject, it cannot approve**. Characters-per-second correctly identified a 37 CPS caption as unreadable and was wrong at 27, so the error was granting its whole range decision authority when it has a confident region and an uncertain one. The lint that earns its place is a floor (~35+ CPS), silent below it with no warning band, reporting the effective window rather than "too long". Not built yet: the JS is stable pending review and this adds to it.

## 0.36.2

### fixed
- **explainer-video 0.3.1 -> 0.3.2**: two items found by the cold run (following `SKILL.md` literally in a clean directory rather than editing files already understood). Step 2's scaffold command used bare `${CLAUDE_SKILL_DIR}`, which expands to empty in a shell and yields `cp: /templates/...: No such file or directory` if an agent copies it verbatim; it is now quoted and annotated as a load-time substitution rather than a shell variable. Step 1's caption guidance was `<70 chars` -- a character count cannot reference beat duration, so the same line is comfortable over 4s and impossible over 1.5s. Replaced with a per-second budget against the caption's *effective* window (beat duration minus fade, minus any `capEnd` trim), marked as observed rather than derived.

## 0.36.1

### fixed
- **explainer-video 0.3.0 -> 0.3.1**: overlay fades now complete **inside** their own beat rather than straddling the boundary. The title fade was centred on `t1`, so title pixels bled 0.3s into the next beat and retiming the title silently moved content into its neighbour. Fixed in the template and the worked example.
- **explainer-video**: retimed the worked example after watching it. It ran 2.4 / 2.4 / 3.2s against `method.md`'s own stated 3-4s-per-beat guidance, and the sweep read as a flicker. Now 3.2 / 4.2 / 3.6, with the sweep highlight widened from ±0.55 to ±0.9 slab-units. Width mattered more than duration — lengthening the beat alone just spaced the flickers further apart.

### added
- **explainer-video**: a "Dwell: measured, not derived" section in `method.md`, recording the two values above as observations rather than rules. Also records that a beat can pass a caption reading-speed check and still be too fast to follow, so motion pacing and caption pacing are separate problems.

### changed
- **explainer-video**: the caption reading-speed lint proposed for a future release is **not** shipping as designed. Its threshold came from arithmetic (17-21 CPS) and was contradicted by one person watching three seconds of video: a 27 CPS caption read fine. If it ships at all it should guard only the egregious case, not act as a pacing tool.

## 0.36.1

### changed
- **docs reconciled with the 0.35.0 process changes.** `CLAUDE.md`, `.claude/rules/plugins.md`, `docs/internals/{maintenance,gotchas,plugin-versioning,plugin-patterns}.md`, and both skill-maintainer READMEs now describe the three-file cascade, `review_interval_days`, the `last_verified` semantics, `_deprecated`, `check_version_alignment`, the `--strict` pre-commit gate, and hook exec form. `docs/analysis/`, `docs/claude-docs/` and `docs/reports/` were deliberately left alone -- they are captured upstream documentation and point-in-time reports, not statements of our conventions.
- **`.claude/rules/plugins.md`** gains the version-cascade, deprecation, and exec-form rules, and now says plainly that upstream requires only `name` in `plugin.json` -- the other four fields are this repo's convention, enforced by our own test suite.

### fixed
- **`CLAUDE.md` had been truncated.** The 0.35.0 edit replaced from invariant 5 to end-of-file, silently deleting the "Where to find what", "State", and "Cross-repo" sections. Recovered from `9bbb7e1` and updated: the doc table gains rows for the versioning doc and the upstream drift backlog, and "State" now describes `review_interval_days` and `apps/_deprecated/`.

### added
- **model-routing installed into this repo**: `.claude/rules/model-delegation.md` plus the `fast-executor` and `task-coder` agents. The feedback layer was deliberately skipped -- it appends always-loaded text that only pays off with the `agent-state` CLI in active use.

## 0.36.0

### changed
- **explainer-video 0.2.0 -> 0.3.0**: generalized the skill beyond the single domain its first build happened to come from. The procedural-asset cookbook in `method.md` is now organized by **shape problem** rather than by subject, and leads with a derivable method (decompose to primitives, silhouette first, oversize the signature feature ~30%, costume beats anatomy, signal over realism) so an uncovered domain can be handled without a matching recipe. Recipes are split into ones actually built versus sketched, so the earned material stays distinguishable. `SKILL.md` gains a `domain` field in the spec, a third style mode (cross-section), and an explicit statement that only geometry and caption register vary by field — never the contract, beats or pipeline.
- **explainer-video**: widened the skill description, which is the retrieval surface. It previously read software- and character-flavoured and would not have triggered on "animate how a heat pump works" or "show how our approval process flows". Now spans process, mechanism, system, organism, market, supply chain, building and policy, and mentions the WebP inline-in-README output that 0.1.2 added.
- **explainer-video**: replaced the longer worked example. It is no longer bundled; `skill-retrieval.html` remains as the diagrammatic reference. The playful/moving-camera style now ships without an example — the template scaffold plus the `method.md` recipes are the starting point. Worth replacing with a neutral-subject example when one is needed.

## 0.35.0

### changed
- **version cascade is now three files, not 3+N.** `metadata.version` removed from all 39 SKILL.md. It duplicated `plugin.json`, and the only thing that ever read it was the check confirming the duplicate still matched — storing a value in N places so a hook can verify all N agree is work that produces no information. A `skill-maintainer` bump used to force 6 SKILL.md edits; `dev-conventions`, `mece-decomposer` and `env-forge` 5 each. Now: `plugin.json` + `marketplace.json` + `CHANGELOG.md`. Both consumers already treated the field as optional (`[ -n "$sk_ver" ]` in the pre-commit, `if (meta?.version)` in skill-dashboard), so a stray re-addition is still caught rather than silently drifting. One code change *was* needed and I initially missed it: the pre-commit's *extraction* is a pipeline (`sed | grep '^ *version:' | head | sed`), and under `set -euo pipefail` a grep that matches nothing aborts the entire hook with a silent exit 1. Tolerating absence in the comparison is not the same as tolerating it in the extraction. Fixed with `|| true`.
- **`metadata.last_verified` is out of the cascade too.** It asserts a human reviewed the skill against its source, which a version bump does not establish. Documented in CLAUDE.md invariant 1, `docs/internals/plugin-versioning.md`, the `sync-versions` skill, and best_practices.
- **`dev-conventions`, `dimensional-modeling`, `mece-decomposer` disabled in this repo** via `enabledPlugins: false`. Their SessionStart hooks inject ~3,500 chars of convention text every session, and those conventions are already stated twice here — `.claude/rules/general.md` and the user's global CLAUDE.md. The hooks stay in the plugins because they are the entire point for a repo with nothing written down; they are redundant only *here*.

### added
- **skill-maintainer 0.10.0 -> 0.11.0**: `_deprecated` added to `SKIP_DIRS`, so units kept for reference but no longer published stop producing permanently-red rows (an unpublished plugin legitimately fails "listed in marketplace.json", and its skills legitimately go stale).
- **pre-commit**: `claude plugin validate . --strict` gates any staged `marketplace.json`. Unknown top-level fields are warnings by default so a manifest can double as `package.json`; `--strict` promotes them to errors, which is what a hand-edited manifest wants. Verified by injecting `keywords` as a string — the commit is blocked. Skipped when the CLI is absent, so the hook still works without Claude Code installed.

### removed
- **env-forge deprecated.** Moved to `apps/_deprecated/env-forge/`, dropped from `marketplace.json` `plugins[]` and the uv workspace, removed from the README. Code kept, not deleted. `marketplace.json` gains `"renames": {"env-forge": null}` — the documented graceful-removal path, so existing installs get a "removed from the marketplace" notice instead of `plugin-not-found`. That map is append-only. Staleness failures 11 -> 6.

## 0.35.0

### changed
- **explainer-video 0.1.3 -> 0.2.0**: beat timing is now data. A named `BEATS` array is the single source of timing truth; captions, camera keyframes and `DURATION` all derive from it, and `animate()` addresses beats by name. `SKILL.md` has claimed since 0.1.0 that "retiming a beat is a one-line edit" -- it was false, because timing lived in `CONFIG.captions`, in `ss(t, 5.0, 6.9)` literals scattered through `animate()`, and again in the camera rail. It is now true. Durations accumulate rather than being absolute, so lengthening a beat shifts every later beat instead of silently overlapping it.
- **explainer-video**: two addressing forms, and the distinction is load-bearing. `ramp`/`pulse` take **fractions of a beat** and stretch when the beat is retimed; `rampS`/`pulseS`/`secAt` take **seconds from the beat start** and do not. A rise across half a beat should stretch; a 0.25s flash or a 0.06s world cut must not, because stretching a cut window uncovers the cut -- the one bug `method.md` says already cost a re-render.
- **explainer-video**: both worked examples migrated. Verified behavior-preserving by shooting identical timestamps before and after and comparing with `ffmpeg psnr`: 7 of 12 frames byte-identical on the longer scene, the rest 61-97 dB (imperceptible), and **the world-cut transition byte-identical at every sampled frame through it**. The only sub-70 dB frames were caption-fade boundaries, confirmed via difference images to be localized to the caption pill and the title -- a consequence of captions now spanning their beat instead of a hand-kept gap. A `capEnd` field covers the case that genuinely needs an early-ending caption, where it must clear a flash.

### added
- **explainer-video**: `method.md` gains "Beats are data, not comments" (including how to verify a migration with psnr and difference images) and "Spike the hostile beat first" -- build the beat that is both load-bearing and compression-hostile before committing to the full table, since it answers "does it read" and "does it encode small enough" in a few seconds of work.

### fixed
- **explainer-video**: `smoke.js` no longer vendors three unconditionally; it only does so if a scene actually references the bundle. The script tests the contract, not the renderer, so a 2D or SVG backend should not be forced to materialize a three bundle it never uses.

## 0.34.0

### fixed
- **explainer-video 0.1.2 -> 0.1.3**: corrected the mechanism given for why a repo-relative mp4 does not render as a player. 0.33.0 said `raw` serves video as `application/octet-stream`; it actually serves it as `text/plain; charset=utf-8` with `X-Content-Type-Options: nosniff`. Verified by fetching both formats from the URL a repo-relative reference resolves to. The conclusion was right and the reason was wrong, which matters because the real reason is a **content-type allowlist** -- `.webp` comes back as `image/webp` while video does not -- and that is exactly why the WebP loop path works at all. Independent verification also confirmed the animation chunks survive byte-intact.

### added
- **explainer-video**: two traps documented in `method.md` and `SKILL.md`. Never track the loop under Git LFS -- `raw` returns the pointer file, not the image, and the README shows a broken image; this catches most repos that ship demo media. And no format gives inline motion *with audio*: GIF, WebP and APNG are all silent, so the narration path and the inline path are necessarily different artifacts. APNG is flagged unverified rather than assumed.

## 0.34.0

### added
- **skill-maintainer 0.9.1 -> 0.10.0**: `check_version_alignment` in the repo-hygiene suite compares every `plugin.json` against its `marketplace.json` entry, in both directions -- a marketplace entry pointing at a plugin that does not exist, and a plugin on disk nobody can install. The pre-commit hook only ever inspected plugins a given commit happened to touch, which is why `path-privacy` drifted five releases before anything noticed. Verified by re-injecting that exact drift: it fails, and goes green when restored.

### changed
- **all 8 hook-shipping plugins**: hooks converted from shell form to **exec form** (`"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]`). Shell form hands the whole string to `sh -c`, so a plugin root containing a space -- a user account named `First Last` -- splits at the space and the hook dies with `sh: /Users/First: No such file or directory`. Demonstrated the failure and the fix before converting; output and exit codes are byte-identical for the path-privacy blocker. `bash` is named as the executable with the script in `args` rather than making the script path the `command`, because a `.sh` file is not spawnable on Windows -- the same reason the upstream docs recommend `node` plus a script path.  <!-- path-privacy: ignore -->
- Affected: `dev-conventions` 0.6.0 -> 0.7.0, `dimensional-modeling` 0.3.2 -> 0.4.0, `env-forge` 0.3.1 -> 0.4.0, `mece-decomposer` 0.4.1 -> 0.5.0, `path-privacy` 0.1.6 -> 0.2.0, `pyright-autoconfig` 0.1.2 -> 0.2.0, `skill-maintainer` 0.9.1 -> 0.10.0, `tui-design` 0.3.1 -> 0.4.0.
- **best_practices.md / plugin-patterns.md**: document exec vs shell form, including the Windows constraint and the `${user_config.*}` shell-form rejection (v2.1.207+).

### fixed
- **version cascade convention**: the cascade re-dates `metadata.last_verified` alongside `metadata.version`, which conflates "this file changed" with "someone checked this is still correct". Bumping eight plugins for a hook-invocation change would have silently marked 17 unreviewed skills as freshly verified and dropped staleness failures 11 -> 5 on no evidence. Those dates were restored. The two plugins that kept today's date are the ones actually exercised. Worth reconsidering whether `last_verified` belongs in the cascade at all -- see docs/internals/upstream_drift_backlog.md.

## 0.33.1

### added
- **docs**: `docs/internals/explainer_video_roadmap.md` — design for the queued explainer-video work. The headline item is replacing scattered literal timings with a named-beats table as the single source of timing truth: `SKILL.md` currently claims "retiming a beat is a one-line edit" and that is false, since beat timing lives in `CONFIG.captions`, in `ss(t, 5.0, 6.9)` literals through `animate()`, and again in the camera rail. The doc argues the ordering (the refactor blocks the contact sheet, narration-driven audio, and the lint; only parallel capture is independent) and records what we are deliberately not building.
- **docs/README.md**: indexed `upstream_drift_backlog.md` and the new roadmap, neither of which appeared in the internals table.

## 0.33.0

### added
- **explainer-video 0.1.1 -> 0.1.2**: two new delivery outputs and a second worked example, driven by verifying how GitHub actually renders things. `build.js loop` produces an animated WebP (the one motion format GitHub renders inline in markdown); `build.js poster` produces a still plus the markdown snippet to paste. `examples/skill-retrieval.html` is an 8s held-camera diagrammatic scene, and its 175 KB WebP is committed and embedded in the plugin README -- the inline story, demonstrated rather than asserted.
- **explainer-video**: `CONFIG.sway` is now a config value rather than a hardcoded `0.06`, so holding the camera is a one-line edit.

### changed
- **explainer-video**: delivery is now a step-1 decision, not an encode-time one, because it constrains the camera and therefore the beats. Measured: the 12s template scene at 960px/24fps encodes to 0.52 MB as mp4 but **15.56 MB** as WebP (worse than GIF's 12.08 MB), because the default sway moves every pixel every frame and defeats inter-frame compression. The same pipeline on an 8s held-camera scene yields a 175 KB WebP -- smaller than its own mp4. So the rule is by scene type, not by squeezing under the 10 MB cap: held camera -> inline loop; moving camera -> poster still linking to an attached mp4; authored diagram -> hand-written animated SVG.
- **explainer-video**: documented that a repo-relative mp4 does **not** render as a player on GitHub (`<video>` is stripped from GFM, and raw serves video as `application/octet-stream`); the working path is an issue/PR attachment URL. Also that `img2webp` is required for loops, since Homebrew's ffmpeg ships without libwebp.
- **explainer-video**: corrected the render-speed figure in `method.md`. It claimed ~1 fps at 1080p, which is true for software GL in a cloud container but read as universal; measured 5.3 fps on local hardware GL (288 frames in 54s). Both cases are now tabulated, and the parallel-capture opportunity that falls out of determinism is noted.

### fixed
- **explainer-video**: `smoke.js` asserted `window.THREE` and read pixels from a WebGL context, which would have failed any non-three backend. The contract (`seekTo`/`DURATION`/`stopPlayback`/`sceneReady`) is the actual product -- three.js is one backend, and a 2D canvas or SVG/CSS timeline implementing those four globals should get frame-exact MP4s from the same pipeline. The renderer assertion is gone and the blank-frame check now measures the screenshot instead of the canvas. Verified with a negative control.
- **README**: `explainer-video` was missing from the root plugins table, install list, and invocation examples -- step 5 of the plugin checklist was skipped when it was added in 0.31.0.

## 0.32.0

### fixed
- **marketplace.json**: `path-privacy` was pinned at 0.1.1 while its `plugin.json` and SKILL.md had moved to 0.1.6 -- the marketplace entry was never updated during those five bumps, so installs resolved a stale version. Caught by the pre-commit version check once an unrelated edit touched the plugin. Reconciled against `plugin.json`, which is the source of truth.

### added
- **skill-maintainer 0.8.1 -> 0.9.0**: per-skill review intervals via `metadata.review_interval_days`, honoured by `test`, `quality`, and `freshness` (falling back to the global 30-day default; `freshness --threshold` still overrides everything). A single global window was the wrong instrument for a repo tracking sources of very different volatility -- the Claude Code docs move weekly, Kimball dimensional modeling has not moved in decades. Forcing both to 30 days kept 31 of 39 skills permanently red, which is how a signal stops being read.
- **all skills**: tiered into 30d (content derived from Claude Code docs), 90d (tracks a third-party SDK/API), and 365d (methodology, or our own code -- we update the skill when the code changes and the date is only a backstop). Staleness failures dropped from 31 to 13, and the remaining 13 are genuine: they track moving surfaces and are past their own declared window.

## 0.31.1

### added
- **explainer-video**: `templates/smoke.js` — a contract and determinism check that renders one frame of every scene, source and bundled, and fails on any console error, missing contract member, blank canvas, or non-deterministic `seekTo`. It found two real bugs in the shipped example on its first run.

### fixed
- **explainer-video**: the worked example never set `window.DURATION`, violating the documented recorder contract. `shoot.js` masked it with a `|| 20` fallback that coincidentally matched the example's length — a 30-second scene would have silently rendered only its first 20 seconds. The example now sets it and the fallback is gone, so a missing `DURATION` fails loudly.
- **explainer-video**: the worked example broke the skill's core determinism invariant. `browL/browR.rotation.z` were set at build time and mutated only inside the finale branch, so nothing reset them for `t < 17.7`. The MP4 renders 0->N once and looked correct, but the HTML loop's second pass showed finale brows during the early beats — the exact HTML/MP4 divergence the architecture claims is impossible. Brows are now restated every frame.
- **explainer-video**: reframed one beat of a worked example. The subject sat in the upper third against `method.md`'s own middle-third rule; it now centers.

## 0.31.0

### added
- **explainer-video 0.1.0**: new plugin for deterministic animated explainer sequences (3D or diagrammatic), delivered as a self-contained looping HTML page, a frame-exact MP4, or both. The whole film is a pure function of time `t`, so one scene file drives both the live HTML loop and the headless render — no second copy to keep in sync. Ships a runnable scaffold, a headless frame shooter, a vendor/bundle/frames/video pipeline, a design-method reference, and a worked 20s example.

### changed
- **explainer-video**: promoted from a bare skill directory to a plugin (`.claude-plugin/plugin.json`, README, `skills/explainer-video/`), added `metadata.version`/`last_verified`, renamed `reference/` -> `references/`, and converted the toolchain from npm/node to bun.
- **explainer-video**: pinned `three@0.185.1` and `playwright-core@1.61.1` (from `three@0.149.0`, unpinned playwright). This was a migration, not a bump — three removed its UMD build after 0.160, and `outputEncoding`, `sRGBEncoding` and `useLegacyLights` are gone in r185. Because `THREE.<removed>` evaluates to `undefined` rather than throwing, the old code would have rendered with silently wrong colors. three is now vendored locally as an IIFE bundle (`build.js vendor`) instead of loaded from a CDN, so renders never touch the network.

### fixed
- **explainer-video**: `build.js bundle` corrupted every bundled artifact. The inline step used a string replacement, where `$&` is a substitution pattern, and minified three contains `if($&$.isStackTrace)` — splicing the matched script tag into the middle of the library. Now uses a function replacement. This bug predated the version migration.
- **explainer-video**: the vendored bundle must be IIFE format. An ESM bundle loaded as a classic script leaks top-level identifiers into global scope, where a minified `MW` collided with a scene variable and broke the worked example.
- **explainer-video**: `shoot.js` now surfaces page and console errors and fails fast when a scene never becomes ready, instead of silently shooting hundreds of broken frames. Playwright's Chromium cache is scanned by build rather than pinned to a stale build number.

## 0.30.2

### changed
- **pyright-autoconfig 0.1.1 -> 0.1.2**: code-review fix for a config-overwrite regression. 0.1.1's "is this config ours?" test was a loose `grep reportMissingModuleSource`, so a user's OWN hand-written `pyrightconfig.json` that set that key would be misclassified as ours and silently overwritten (losing their other settings). Ownership is now **exact**: the hook only ever recognizes/rewrites its own byte-for-byte template output (venv or venv-less), and self-heals only its exact venv-less template once `.venv` appears. Any other config is left completely untouched. Verified: a user config containing `reportMissingModuleSource` is now preserved; self-heal + idempotency still pass. (Unrelated but same session: hardened the user-scope `block-network-exfil.sh` PreToolUse hook against full-path curl and `<(curl)`/`$(curl)`/`| xargs sh` bypasses -- that hook is a personal `~/.claude/hooks/` file, not part of this repo.)

## 0.30.1

### changed
- **pyright-autoconfig 0.1.0 -> 0.1.1**: post-review hardening of the SessionStart hook.
  - **Self-healing venv pointer (real bug fix)**: previously, a config written before `.venv` existed (the clone-then-`uv sync` order) was venv-less and the idempotent early-exit meant it never gained `venvPath`/`venv` -- so imports never resolved, defeating the plugin's main purpose. The hook now rewrites its own config once `.venv` appears (verified: venv-less on first run, venv pointer added on the next).
  - **Subtable-aware config detection**: the "respect an existing pyright config" guard now matches a bare `[tool.pyright]` header OR any `[tool.pyright.<subtable>]` (e.g. `executionEnvironments`) -- a subtable alone is valid TOML and a written `pyrightconfig.json` would otherwise shadow it.
  - **Write-gated exclude**: `.git/info/exclude` is only touched after the config write actually succeeds (no more orphan exclude entry on a failed write).
  - **jq-missing signal**: a missing `jq` now emits one stderr line instead of a fully silent no-op.
  - **De-duplicated the config builder** (single `desired` string, was two near-identical heredocs). SessionStart matcher intentionally omitted (repo convention is no-matcher; the hook is idempotent + cheap, and an unverified matcher risks the hook never firing).

## 0.30.0

### added
- **pyright-autoconfig 0.1.0** (new plugin): a one-hook plugin that makes the Claude Code Pyright LSP quiet and useful across all Python projects without per-repo setup. On SessionStart, if cwd is a Python project (`pyproject.toml`/`setup.py`/`setup.cfg`/`.venv`) with no existing Pyright config, it drops a personal `pyrightconfig.json` pointing Pyright at the uv `.venv` (`venvPath`/`venv` -> imports resolve -> real cross-file type intel) and setting `reportMissingImports`/`reportMissingModuleSource` to `none` (kills the dominant noise; Claude Code surfaces all severities, so only `none` actually removes a diagnostic). Registers the file in the repo's `.git/info/exclude` so it never commits and never shows in `git status` -- no global git config, nothing to replicate by hand on other machines. Idempotent (exits once a config exists), non-destructive (never overwrites an existing `pyrightconfig.json` or `[tool.pyright]` block), silent (no injected context), and a fast no-op outside Python projects. Solves the flood that pyright-lsp produces when it can't find the venv (worst on files it can't root: sibling repos, `/tmp` scratch). Prerequisite: the official `pyright-lsp` plugin + `pyright-langserver` on PATH.

## 0.29.2

### changed
- **README**: added an `### updating` section under installation — how to pull plugin updates (`claude plugin marketplace update` + `claude plugin update`), the startup auto-update behavior, and a note on scripting a one-command sweep across machines. Closes the gap where install/uninstall were documented but keeping plugins current was not.

## 0.29.1

### changed
- **README plugins section**: regrouped the flat 17-row plugin table into six purpose-based categories (development conventions & authoring; decomposition & model routing; plugin & skill maintenance; MCP servers & apps; privacy & pre-share safety; environment synthesis). Every plugin preserved verbatim; project-scoped and package sections unchanged.
- **VISION.md restructure**: reordered so the concrete loading model leads — retrieval problem, then "what gets loaded and when", then principles, then the architecture worldview (was architecture-first). Intro rewritten to match. Validated the L1/L2/L3 loading table against the captured `docs/analysis/memory_and_rules_system.md` and upstream docs: all existing rows accurate (incl. the "~2% of context" SKILL.md frontmatter figure); added a note on three L1 sources present in Claude Code but unused here (managed-policy CLAUDE.md, `CLAUDE.local.md`, user-level `<HOME>/.claude/rules/`). Added an ASCII tree-topology diagram to the architecture section; fixed a now-stale "below" -> "above" cross-reference. Both edits produced by down-tier subagents (sonnet) and verified in the main loop — a dogfood of the model-routing pattern.

### changed
- **model-routing 0.2.0 -> 0.3.0**: made the base rule genuinely standalone and split the agent-state coupling into an opt-in layer. The `agent-state` recording block moved out of `references/model-delegation.md` into a new `references/feedback-addon.md`, which the installer appends only when the user asks for it ("with feedback" / "with agent-state"). The base `.claude/rules/model-delegation.md` now has zero external-tool references — it loads into every session of every project where it's installed, so the feedback text (which only pays off when the CLI is present) shouldn't ride along by default. Three independent install layers now: base rule (always), agents (opt-in), feedback (opt-in). SKILL.md, plugin/marketplace descriptions, and READMEs updated; no change to `fast-executor` / `task-coder`.

## 0.28.1

### changed
- **Path-privacy cleanup** ahead of a repo push: replaced a few external path references with generic forms across `tools/agent-state/BACKLOG.md`, `apps/readwise-reader/.../enrichment/pipeline.py` (stub comment), and `skills/scan-for-secrets/.../SKILL.md` (References list). Functional behavior unchanged.
- **scan-for-secrets 0.1.0 -> 0.1.1**: version cascade for the SKILL.md content change above (plugin.json, marketplace entry, sub-skill `metadata.version`, `last_verified`). No functional change.

## 0.28.0

### changed
- **dev-conventions 0.5.0 -> 0.6.0**: refresh for current tooling and scope.
  - **Lock file fix**: `bun.lockb` -> `bun.lock` everywhere (javascript directive, `bun-tooling` and `doc-conventions` skills, README, and the hook's marker detection). Bun switched to the text-based `bun.lock` in 1.2 (default since); every bun project in this repo already uses it, so the plugin now matches reality. The hook detects both `bun.lock` and legacy `bun.lockb`.
  - **Slimmed directives to policy**: the `python.md` and `javascript.md` SessionStart directives no longer teach `uv add`/`uv run`/`bun add`/`bunx` command mappings (current models default to these unprompted). They now carry only the non-inferable policy: which manager is mandated, the pinning strategy, no-auto-lint, and don't-hand-edit-lockfiles, plus a pointer to the L2 skill for full tables.
  - **Dropped orjson from the plugin**: `python-tooling` no longer mandates `orjson` over stdlib `json`, and the plugin/marketplace descriptions drop it from the injected list. JSON-library choice is a per-project preference, not a near-universal default like uv/bun/TDD; the skill now says so and points to the project's own `CLAUDE.md`/`.claude/rules/`. This repo keeps its orjson rule in `.claude/rules/general.md`, where it belongs and is genuinely used.
  - All five sub-skills bumped to 0.6.0 / `last_verified` 2026-07-05.

## 0.27.0

### added
- **agent-state 0.2.1 -> 0.3.0**: delegation feedback loop. Schema v3 adds `fact_delegation` (append-only; grain: one row per delegated subagent task, recorded when the orchestrator verifies the result; deterministic MD5 surrogate key so re-recording identical inputs is a no-op) and `v_delegation_stats` (acceptance rate per model/domain). New `delegations.py` module (`record_delegation`, `get_delegation_stats`, `get_recent_delegations`), `DelegationOutcome` enum (accepted / revised / redone / escalated), and `agent-state delegation record|stats|list` CLI. TDD: 10 new tests in `test_delegations.py`; existing schema-version assertions updated to v3; suite at 45 passing.

### changed
- **model-routing 0.1.0 -> 0.2.0**: the installer now optionally copies pre-shaped agent definitions into the target project's `.claude/agents/` — `fast-executor` (haiku, mechanical execute-to-spec) and `task-coder` (sonnet, implement-to-spec with verification), both templated verbatim in the skill's `references/agents/`. The installed rule prefers those agents when present and, when the `agent-state` CLI is on PATH, records each verified delegation outcome (`agent-state delegation record ...`) so acceptance rates can tune delegation criteria from data; recording is optional and never blocks work.
- **agent-state BACKLOG**: captured follow-up to expose `fact_delegation` through agent-state-mcp's read-only tools.

## 0.26.0

### added
- **model-routing 0.1.0** (new plugin): opt-in per-project model delegation. One skill, `model-routing`, installs `.claude/rules/model-delegation.md` into the current project by verbatim copy from the skill's `references/model-delegation.md` template (diff-and-confirm if a local copy exists; removal is deleting the file). The rule routes well-specified, mechanical, verifiable data/coding tasks to the cheapest capable model in a subagent and keeps design, ambiguity, user interaction, and verification of returned work in the main loop; model tiers appear only as examples so the rule survives lineup changes. Pure markdown skill, stays out of the uv workspace. Registered in `marketplace.json` and the root README plugins table, install list, and invocation examples.

### changed
- **VISION.md**: new architecture subsection "route to the cheapest capable model" — routing has two axes (context a subagent sees, model tier that executes it); decomposition quality and model tiering are complements; delegation rules should be stated as task properties with tiers as examples. Matching bullet in "what this means for this repo" pointing at the model-routing plugin as the implementation. The L1/L2/L3 loading table gains a `Type` column (Instructions / Memory / Rule / Skill / Settings / Reference / Script) so each loaded artifact is named by kind, not just by path.

## 0.25.0

### added
- **writing 0.1.0** (new plugin): the repo's first writing-skills bundle. Ships one skill, `govuk-style`, which applies the GOV.UK / Government Digital Service house style — plain English, active voice, front-loaded content, sentence case, and no bold or italics for emphasis. Pure markdown skill (no Python), so it stays out of the uv workspace. Registered in `marketplace.json` and the root README plugins table, install list, and invocation examples. Adapted from a skill shared by [@fofr](https://twitter.com/fofr); credited in the SKILL.md `metadata.credit` field, the skill body, and the README.

## 0.24.8

### changed
- **skill-maintainer 0.8.0 -> 0.8.1**: `/simplify` follow-up pass on the three commits that landed today.
  - `lint.py`: extracted `_count_analysis_reports` and `_count_captured_docs` named functions, replacing two byte-identical lambdas in `COUNT_PATTERNS`. Drift surface eliminated -- if the exclusion set changes (e.g., `_index.md` is added later), only one place to update.
  - `lint.py`: added `_safe_read(path)` helper that returns `None` on `OSError` / `UnicodeDecodeError`. `find_count_drift` and `find_broken_links` use it instead of bare `path.read_text()`. Honors the documented "exit 0 always" contract -- a dangling symlink or non-UTF-8 file in the doc tree no longer crashes the pass.
  - `lint.py`: `find_count_drift` memoizes counter results per call (`actual_cache: dict[int, int]` keyed by `id(counter)`). A file with multiple lines matching the same pattern now triggers one filesystem glob, not N. Real concern only on duplicated prose in long files; cheap fix.
  - `pre-commit.sample` (and the live `.git/hooks/pre-commit`): inline comment in `claude_md_size_check` documenting that the `4000`-token threshold mirrors `shared.TOKEN_BUDGET_WARN`. The shell can't import Python; the comment is the only available drift signal.
- **README.md**: skill-maintainer plugin row gains the new `lint` capability and the tracked pre-commit hook scaffolding (both shipped today). agent-state-mcp row scrubbed of `~/.claude/...` path leak (now `<HOME>/.claude/...`). The `docs/internals/` line in the documentation highlights was wrong -- said "API reference, DuckDB schema, troubleshooting"; replaced with the actual contents (versioning cascade, plugin patterns, maintenance commands, gotchas) plus a new pointer to `docs/analysis/index.md` since that's now a real wiki-style index. The skill-maintainer CLI section gains the new `init` hook-scaffolding behavior and `lint` in the example commands.
- **CLAUDE.md**: added missing `last updated:` line at top. Caught by the docs-staleness sweep -- root CLAUDE.md was the only file in the active doc tree without one.

### notes
- The staleness sweep across the doc tree (38 files with `last updated:` dates older than 30 days) found **no date-vs-content drift** -- every file's commit date aligns with its stated `last updated:` line within 7 days. The dates are accurate signals of when content was last touched. Did not blind-bump the 36 stable analysis/reference files; doing so would make the dates *less* accurate as audit signals. The two real audit candidates (`apps/readwise-reader/CLAUDE.md` and `README.md`, 88 days) remain deferred -- they need someone with that codebase's context.

## 0.24.7

### added
- **skill-maintainer 0.7.0 -> 0.8.0**: two new capabilities, both closing real gaps surfaced by the hub-and-spoke restructure.

  **(1) Pre-commit hook is now a tracked, installable artifact.** The hook source moved from `.git/hooks/pre-commit` (untracked, lost on every fresh clone) to `tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample` (bundled with the Python package). New `scaffold.py` module exposes `install_pre_commit_hook(root, force)`. `skill-maintain init` now calls it on every run: idempotent (skip if up-to-date), refuses to clobber a divergent existing hook unless `--force-hook` is passed (which preserves the prior hook as `.git/hooks/pre-commit.local` first), and degrades gracefully (`skipped: not a git repository`) outside git repos. The bundled hook is portable: version-alignment checks no-op in repos without `.claude-plugin/plugin.json`, the CLAUDE.md size guard no-ops if CLAUDE.md isn't staged. Replaces the brittle "copy from a teammate's clone" instruction in `docs/internals/gotchas.md`. The `init-maintenance` SKILL is refactored to delegate to `skill-maintain init` instead of writing its own minimal hook.

  **(2) Lint v2 -- markdown link-rot detection.** `skill-maintain lint` gains a third pass: scans `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/internals/*.md`, `docs/analysis/*.md`, and `VISION.md` for `[text](path)` links resolving to files that don't exist. Skips `http(s)://`, `mailto:`, and pure anchor (`#section`) links. Anchor fragments are stripped before existence checks. Links escaping the repo root are skipped (don't flag legitimate sibling-repo references). Caught one real broken link on its first run -- `docs/analysis/cross_surface_compatibility.md:401` pointed at `abstraction_analogies.md` which lives in sibling repo `star-schema-llm-context`, not here. Replaced with a path-privacy-clean prose reference.

- `docs/analysis/log.md` seeded with two real entries (the wiki layer bootstrap and the 2026-05-04 upstream delta); accumulates forward from here. Historical operational events stay in `.skill-maintainer/state/changes.jsonl` (machine-readable) and are not backfilled into the narrative.

## 0.24.6

### added
- **skill-maintainer 0.6.5 -> 0.7.0**: new `skill-maintain lint` subcommand (wiki-sanity pass) plus the wiki layer it operates on.
  - `skill_maintainer/lint.py` implements two checks today: (1) **orphan detection** in `docs/analysis/` — files on disk not linked from `docs/README.md` or `docs/analysis/index.md`; (2) **count drift** — scans `README.md`, `CLAUDE.md`, `docs/README.md`, and `docs/internals/*.md` for assertions matching `\b\d+\s+(domain reports|reports covering|captured docs)\b` and compares each claim to the filesystem. Soft findings (exit 0); not a CI block. Cross-reference and stale-claim heuristics deferred to a future minor.
  - `docs/analysis/index.md` (new): wiki-style index tagged by kind (entity / concept / audit / synthesis). Complements `docs/README.md`'s umbrella index by retrieving by intent.
  - `docs/analysis/log.md` (new): append-only narrative log of ingests, updates, and audits with verb-prefixed `H2` headers (`ingest | update | audit`). Complements `.skill-maintainer/state/changes.jsonl` (operational, machine-readable) with the human-readable why behind significant updates.
  - `docs/internals/maintenance.md` gains a `skill-maintain lint` row in the on-demand commands table.
  - `cli.py` registers `lint` in `COMMANDS`, lists it in `--help`.
  - Inspired by [Karpathy's LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the model is appropriate specifically for `docs/analysis/` (an accumulating knowledge corpus about external systems) and not for CLAUDE.md / READMEs / SKILL.md (which have other purposes).
- The lint pass paid for itself on its first run: caught a "16 domain reports" example I'd written into `docs/internals/gotchas.md` while documenting the rule that prose shouldn't include hardcoded counts. Rephrased without a count.

## 0.24.5

### changed
- **CLAUDE.md restructured to hub-and-spoke.** Trimmed root `CLAUDE.md` from ~270 lines to ~60 by lifting four content domains into `docs/internals/` spokes loaded by reference:
  - `docs/internals/plugin-versioning.md` — full version cascade, sync-versions coverage gaps, sub-skill alignment block, worked example using the most recent skill-maintainer 0.6.4 bump.
  - `docs/internals/plugin-patterns.md` — required structure, hooks-vs-skills, composable directives, agents, catalog-as-exemplar, bash 3.2 portability, greenfield-vs-production schema evolution.
  - `docs/internals/maintenance.md` — full keep-fresh table, on-demand commands, state files, workspace member table.
  - `docs/internals/gotchas.md` — best_practices.md duality, security-guidance hook disable, pre-commit hook re-installation, path-privacy interaction, CLAUDE.md size creep rule, count-drift rule.
- The new CLAUDE.md is a hub: identity + working agreements + 5 repo invariants (the rules that bite on first edit) + a "Where to find what" index pointing at the spokes + state + cross-repo. Path leaks scrubbed (`~/.claude/...` → `<HOME>/.claude/...`; `~/claude/agentskills` description genericized).
- Companion fix: the `last updated` date on `docs/README.md` refreshed and the "15 reports covering..." count claim dropped (the filesystem is the source of truth; counts in prose are drift surfaces). Same fix on root README's "16 domain reports" claim — was the wrong number anyway.

### added
- **skill-maintainer 0.6.4 -> 0.6.5**: pre-commit hook gains a CLAUDE.md size guard. When CLAUDE.md is staged AND its size exceeds 150 lines OR ~4000 tokens (chars/4 heuristic), the hook prints a stderr warning recommending the author move detail into a `docs/internals/<topic>.md` spoke. Warning only — does not block. Same exit semantics as the existing "unbumped content changes" warning. Implemented as a function `claude_md_size_check()` invoked in both exit paths of the hook so it fires regardless of whether plugin content was also staged. Bash 3.2 portable; uses `wc -l` and `wc -c` only.

## 0.24.4

### changed
- **skill-maintainer 0.6.3 -> 0.6.4**: deduplicated `agents/session-log-drafter.md` "house style" against `dev-conventions/doc-conventions` and CLAUDE.md global rules. Four of the nine numbered items in the drafter's house-style block (last-updated date, document-the-why, no-emojis-no-filler, session-log file location) were verbatim restatements of rules already codified elsewhere -- effectively turning the drafter into a third source of truth for the same rules and creating a drift surface every time doc-conventions evolves. Replaced with a one-line pointer to `/dev-conventions:doc-conventions` plus the six remaining session-log-specific rules (heading format, lowercase section headers, narrative-not-transcript, mandatory follow-ups section, explicit file paths, date-stamping relative time references). Behavior of generated logs is unchanged -- the deleted rules still apply via doc-conventions and CLAUDE.md, the drafter just no longer carries its own copy. last_verified bumped on all six sub-skills.

## 0.24.3

### fixed
- **skill-maintainer 0.6.2 -> 0.6.3**: `skill-maintain log` crashed with `AttributeError: 'dict' object has no attribute 'split'` whenever the tail window included an `upstream_check` event written by v0.4.0+. Background: in v0.4.0, `upstream._log_event` was upgraded to record each changed page as a dict (`{"url", "status", "lines_added", "lines_removed", "chars_delta"}`) so subsequent `upstream` runs could compute deltas; `log.py` was not updated and still treated `changed_pages` entries as bare URL strings, calling `.split('/')` on the dict. The log file now mixes both shapes (older entries are strings, post-0.4.0 entries are dicts), so the formatter has to handle both. Fixed in `log.py:62-64` by extracting `url` if the entry is a dict, otherwise using the value directly, then taking the basename via `rstrip('/').split('/')[-1]`. Verified by re-running `skill-maintain log --tail 5` on this repo's `changes.jsonl`, which contains both shapes.

## 0.24.2

### changed
- **skill-maintainer 0.6.1 -> 0.6.2**: code-clarity polish in `hooks/maybe-draft-session-log.sh` (no behavior change). Combined the test-then-capture pair `if ! git rev-parse ...; then exit 0; fi; repo_root=$(git rev-parse ...)` into one capture-with-fallback `repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0` -- saves one fork in the hot path and removes the small worktree-changed-between-calls TOCTOU window. Wrapped the Linux `stat -c "%y" | cut` branch in `{ ... ; }` so the `||` / `|` operator precedence is unambiguous to a future reader; the macOS branch never paired with `cut` at runtime, but the unwrapped form looked like `cut` was a shared post-process for both branches. Same five-scenario regression suite from 0.6.1 still passes. last_verified bumped on all six sub-skills.

## 0.24.1

### fixed
- **skill-maintainer 0.6.0 -> 0.6.1**: two bugs in the `Stop` hook `maybe-draft-session-log.sh`. (1) The Linux-fallback branch parsed `stat -c "%y"` output with `cut -dc -f1`, which uses `c` as the delimiter -- a no-op on `2026-04-25 14:45:10.123 -0500`-style output, returning the entire timestamp string and never matching `today`. So on Linux the "log already updated today, exit early" short-circuit never fired and the hook always proceeded to the count step. Fixed to `cut -d' ' -f1`. (2) The substantive-files counter pipeline ended `... | grep -Ev "^(internal/log/|...)"` -- when the input pipeline produced no lines (e.g., a session with no diffs and no untracked files, or a session that touched only excluded paths), `grep -Ev` exits 1 because nothing matched the negation. Combined with the script's `set -euo pipefail`, that exit-1 killed the script before the trailing `exit 0`, surfacing as a non-zero hook exit on Stop. Fixed by wrapping the grep in `{ ... || true; }` so an empty pipeline doesn't propagate. Both reproduced on macOS by feeding `{}` on stdin into a fresh repo with no changes; both pass after the fix. Also bumped `last_verified` on all six sub-skills to today since the plugin content changed.

## 0.24.0

### added
- **path-privacy 0.1.0** (new plugin): enforces a single rule -- every path written into a repo must be relative to the repo root. Anything that resolves outside the repo (other repos on disk, `~/.claude/<plan>`, `/Users/<name>/...`, `/home/<name>/...`, `$HOME`-based paths) is treated as a leak. Three layers of enforcement: (1) a `SessionStart` hook that injects the rule into Claude's context whenever a session opens in a git repo, so paths outside the repo are never written in the first place; (2) a `pre-commit` git hook that hard-blocks any commit whose staged file content contains a leak; (3) a `commit-msg` git hook that hard-blocks any commit whose message body or current branch name contains one. Single shared scanner script (`find-external-paths.sh`, ripgrep-based) backs all three. Pattern shapes mirror `scan-for-secrets/regex-scan.sh` for `/Users/`, `/home/`, `~/`, and `$HOME`-anchored paths; placeholder usernames (`USERNAME`, `<user>`, `$USER`, `me`, `you`, etc.) are skipped so documentation snippets like `/Users/USERNAME/foo` don't false-flag. Per-line opt-out via the literal token `path-privacy: ignore`. Hooks installer (`install-git-hooks.sh`) writes wrappers into `.git/hooks/` and preserves any pre-existing hook as `.local`. Skill triggers on "scan for path leaks", "check for leaked paths", "are we leaking my home path", "scrub external paths", "install path-privacy hooks", and similar. Sibling to `scan-for-secrets`: that plugin scans for arbitrary secret shapes; this one enforces the narrower repo-scoped-paths rule at commit time with a hard block.

## 0.23.0

### added
- **scan-for-secrets 0.1.0** (new plugin): pre-share scanner that wraps [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (Apache 2.0) for literal matching with JSON/URL/HTML/backslash/unicode-escape variants, and composes a bundled ripgrep wrapper (`regex-scan.sh`) for shape-based patterns the literal pass can't express. Two shipped scripts: `privacy-tokens.sh` emits identity literals from the environment (HOME, USER, git email/name, macOS ComputerName/LocalHostName, Linux GECOS, Apple ID, SSH pubkeys, gh/npm/aws/gcloud logins) as a ready-made `scan-for-secrets -c` config; `regex-scan.sh` sweeps for other users' home paths, emails, IPv4, MAC addresses, SSH fingerprints, and (via `--api-keys`) common API-token shapes (OpenAI/Anthropic/GitHub/AWS/Google/JWT/Slack/PEM). Invoked via `uvx scan-for-secrets` (no install pollution). Skill triggers on "scan for secrets", "pre-share scan", "redact home paths", "PII scan", and similar. Simon's tool stays unmodified; all extension work is composition.

## 0.22.15

### added
- **skill-maintainer 0.5.2 -> 0.6.0**: new `Stop` hook `maybe-draft-session-log.sh`. When the model tries to stop, checks whether the session touched >= 3 "substantive" files (excluding log files, lock files, and `.skill-maintainer/state/`) AND today's `internal/log/log_YYYY-MM-DD.md` doesn't exist or wasn't modified today. If both true, prints a one-line stderr nudge pointing Claude at `/skill-maintainer:finish-session`. Never blocks (exit 0 always). Honors `stop_hook_active=true` so repeated stops don't loop-nudge.
- **agent-state-mcp 0.1.3 -> 0.2.0**: new `/agent-state-mcp:enable` skill. One-shot `.mcp.json` promotion that moves the `agent-state` entry from `_available_servers` (opt-in convention) into `mcpServers` (active), using an idempotent `jq` transform that no-ops on double-runs. Verifies with `uv run agent-state-mcp --list-tools`, tells the user to restart Claude Code, never commits. Closes the "easy to miss the opt-in" friction called out in 0.22.8.

## 0.22.14

### added
- **dimensional-modeling 0.3.1 -> 0.3.2**: kimball-principles directive gains the "facts don't join to facts" rule. Route through a conformed dimension instead of joining two fact tables on a shared FK. Auto-injected via SessionStart hook when DuckDB markers are detected, so any session touching star-schema work sees the rule without having to re-state it.
- **CLAUDE.md**: new "Schema evolution: greenfield default" subsection under Key patterns. Captures the user's stated preference to prefer `CREATE OR REPLACE VIEW` + schema re-init over migration bridges for local/dev DBs (agent_state, readwise-reader, etc.). Production-facing schemas (marketplace, published plugins) remain the exception.

## 0.22.13

### fixed
- **agent-state 0.2.0 -> 0.2.1**: /simplify pass findings.
  - `get_run_messages` gained an optional `limit` parameter that pushes `LIMIT ?` into the SQL. Previously the MCP layer fetched all rows for a run and sliced in Python (`rows[:limit]`), transferring unbounded data from DuckDB only to discard most of it. `get_run_messages_tool` in the MCP layer now requests `limit + 1` rows and uses overflow as the truncation signal -- no extra COUNT round-trip needed.
  - `get_failed_runs` now binds statuses via `RunStatus.FAILURE.value` / `RunStatus.PARTIAL.value` instead of literal strings, so the `models.RunStatus` enum remains the single source of truth. If enum values ever change, the query fails loudly at load time rather than silently returning zero rows.
  - `get_failed_runs` `dim_skill_version` subquery is now a CTE (`WITH sv AS ...`), binding `skill_name` once (not three times) and giving the planner one scan to reference from both IN clauses.
  - `get_failed_runs` bug: CTE parameter must come first in the params list (SQL-text order, not insertion order). Fixed by splitting into `cte_params` + `body_params` and assembling at the call site. Previous code was positionally shifted when `skill_name` was supplied, causing DuckDB to interpret status strings as CTE lookups and cutoff timestamps as status values -- a silent correctness bug this /simplify pass caught before it reached production.
  - `get_failed_runs` now computes the `since_days` cutoff as a Python datetime and binds it directly instead of `CURRENT_TIMESTAMP - (? * INTERVAL 1 DAY)`. Multi-typed parameter binding in that expression tripped DuckDB's BIGINT/DOUBLE overload resolver.
  - `get_run_stats` dropped the redundant per-field `or 0` guards -- the tuple fallback already covers the only case where COUNT(*) could yield NULL (table dropped mid-query).
- **agent-state-mcp 0.1.2 -> 0.1.3**: `get_run_messages_tool` passes `limit` through to the underlying query helper; no in-Python slicing. Behavior unchanged when under the limit; with the previous code, memory-bound. `_envelope` `extra_meta` still surfaces `truncated: true` when the overflow row is seen.
- **agent_state.sql**: `v_latest_watermark` outer projection switched from an explicit 9-column list to `SELECT * EXCLUDE (rn)`. Removes a maintenance hazard where adding a column inside the inner `ranked` subquery would silently drop from the view output.

## 0.22.12

### changed
- **agent-state 0.1.0 -> 0.2.0**: cleanup of the three findings deferred in 0.22.11.
  - `agent_state.query` gained four functions previously carried as inline SQL in the MCP layer: `get_failed_runs(db, since_days, skill_name, limit)`, `get_tracked_domains(db)`, `get_run_sources(db)`, `get_watermark_sources(db)`. Now reachable from the CLI package too, and testable directly against the schema rather than only through the MCP transport.
  - `get_run_stats` consolidated four scalar counts (total_runs, active_watermarks, tracked_skills, total_messages) into one query via scalar subqueries. The two GROUP BYs (by_status, by_type) remain separate because PIVOT / UNION-with-discriminator hurts readability more than it saves round-trips. 6 queries -> 3.
  - `v_latest_watermark` view rewritten from a correlated `MAX(watermark_id)` subquery to `ROW_NUMBER() OVER (PARTITION BY watermark_source_key ORDER BY watermark_id DESC)`. DuckDB now resolves the latest row per source in a single pass.
  - **Bug fix along the way**: `dim_run_source` query in `list_run_sources` was GROUPing on columns that don't exist (`identifier`, `display_name` -- those live on `dim_watermark_source`). Fixed to use the actual columns (`source_name`, `source_version`, `config_hash`, `first_seen_at`, `last_seen_at`). The bug was latent because the function was never exercised before this refactor.
- **agent-state-mcp 0.1.1 -> 0.1.2**: `tools.py` no longer carries inline SQL for `find_failed_runs`, `list_tracked_domains`, `list_run_sources`, `list_watermark_sources`. Each delegates to the corresponding `agent_state.query` function.

### notes
- The view rewrite uses `CREATE OR REPLACE VIEW` so existing databases pick up the change automatically on next schema init. No migration required.
- Dimensional-modeling discipline verified: all new queries route fact -> dim or dim -> fact; no fact-to-fact joins introduced.

## 0.22.11

### fixed
- **agent-state-mcp 0.1.0 -> 0.1.1**: three post-review fixes.
  - Connection cache: `_open_db` now yields a singleton `AgentStateDB` per `db_path` for the life of the server instead of opening+closing on every tool call. Schema DDL (15 CREATE TABLE, 10 CREATE INDEX, 4 CREATE VIEW) no longer re-executes per invocation. `atexit` hook closes cached connections on server shutdown.
  - Envelope consistency for single-row tools: `get_run`, `get_active_skill_version`, `resolve_skill_version_by_hash` now return `{data: null, _meta: {...}}` on not-found/missing-DB paths, matching their docstring contract. Previously returned `rows: []` which would `KeyError` callers expecting `data`.
  - `find_failed_runs` SQL: replaced the f-string WHERE-clause interpolation (structurally unsafe, though not currently exploitable because the interpolated fragment was literal) with list-concatenation construction where every user value binds via `?`.
  - `get_run_messages_tool` gained an explicit `limit: int = 500` param (max 5000) with a `_meta.truncated=true` flag when the cap is hit. Previously returned unbounded rows.
  - `get_run_tree` server-side docstring now mentions `_meta` in its Returns line, matching the SERVER_INSTRUCTIONS envelope contract.
- **skill-maintainer 0.5.1 -> 0.5.2**: `hooks/sync-bundled-ref.sh` bug fixes.
  - `jq` extractor now picks up `tool_input.edits[].file_path` (MultiEdit shape) in addition to the Edit/Write `tool_input.file_path`. Previously MultiEdit touches to `best_practices.md` silently skipped the sync.
  - `repo_root` derivation now handles relative paths correctly by resolving absolute first. Previously `.skill-maintainer/best_practices.md` as a relative path derived `repo_root` as `$PWD` (the `dirname/..` of `.skill-maintainer` is the current directory, not the repo root), which happened to work when CWD was already the repo root but would break otherwise.

## 0.22.10

### changed
- **skill-maintainer 0.5.0 -> 0.5.1**: README now documents the v0.5.0 skills (sync-bundled-ref, finish-session), the session-log-drafter agent, and the PostToolUse bundled-ref sync hook. Version bump is doc-only; no behavioral changes. `tools/skill-maintainer/README.md` also picked up the per-page snapshot note on the `upstream` subcommand row (behavior landed in 0.4.0, never reflected).

## 0.22.9

### added
- **skill-maintainer v0.5.0**: three new pieces for end-of-session workflow.
  - `sync-bundled-ref` skill: manual mirror of `.skill-maintainer/best_practices.md` -> `skills/skill-maintainer/references/best_practices.md` (the seed copied by `skill-maintain init` in new repos). Fixes the silent drift gap documented this session.
  - `sync-bundled-ref.sh` PostToolUse hook at `skills/skill-maintainer/hooks/`: fires on Edit/Write/MultiEdit of the working copy and auto-mirrors. `cmp -s` gated so no-op edits are silent; exits 0 always.
  - `finish-session` composed skill: orchestrates `session-log-drafter` subagent -> bundled-ref sync check -> version-bump detection -> quality scan. Single entrypoint before commits.
  - `session-log-drafter` agent (at `skills/skill-maintainer/agents/`): forked subagent that reads conversation + `git diff` and drafts a house-style entry for `internal/log/log_YYYY-MM-DD.md`. Returns content only; main session writes to disk.
- **skill-maintainer**: `sync-versions` skill gained step 3c-alt for multi-skill plugins -- discovers all sub-skill SKILL.md files under the plugin and bumps each `metadata.version` + `metadata.last_verified`. Closes the gap that required manual sub-skill bumps for skill-maintainer itself.

### changed
- **skill-maintainer**: bumped plugin + Python package to v0.5.0. All six SKILL.md files (init-maintenance, maintain, quality, sync-versions, sync-bundled-ref, finish-session) carry `metadata.version: 0.5.0`.
- Root `.claude/settings.json`: added `env.ENABLE_SECURITY_REMINDER=0` to disable the `security-guidance` plugin's PreToolUse hook for this repo. Hook substring-matches on tokens that appear in prose (code-eval builtin names, serialization libs, DOM sinks) with no path awareness; false-positive rate on docs is high. Trade-off documented in CLAUDE.md "Security hook gotcha" section.
- Root `CLAUDE.md`: added "Canonical best_practices.md" subsection, "Security hook gotcha" subsection, and a `state/pages/<slug>.md` bullet to the State section. Updated plugin versioning paragraph to flag sub-skill bump requirement.

## 0.22.8

### added
- **agent-state-mcp** (new plugin, v0.1.0): stdio MCP server at `apps/agent-state-mcp/` that exposes `~/.claude/agent_state.duckdb` to Claude Code as 18 read-only tools (`list_recent_runs`, `get_run_tree`, `find_failed_runs`, `get_watermark_status`, `list_skills_by_domain`, `get_flywheel_metrics`, etc.). Thin wrapper over the existing `agent-state` Python package; designed so Claude reaches for MCP tools instead of shelling out to the `agent-state` CLI. Structured return envelopes (`{rows, _meta}` with row_count, duration_ms, schema_version), parameterized queries, graceful fallback when the DB is missing. Includes a single `agent-state-mcp` skill teaching Claude the question-to-tool mapping.
- Root `.mcp.json` now documents an opt-in `agent-state` server entry under `_available_servers` (commented out by default; copy into `mcpServers` to enable).

### changed
- Root `pyproject.toml` workspace now includes `apps/agent-state-mcp`.
- Root `.claude-plugin/marketplace.json` registers the new plugin.
- Root `CLAUDE.md` repo structure and workspace dependencies table updated.

## 0.22.7

### added
- **skill-maintainer**: `upstream` command now retains per-page content snapshots under `.skill-maintainer/state/pages/<slug>.md`, so subsequent runs report concrete `+added / -removed lines, ±chars` deltas instead of just "changed". Delta metadata is also persisted in `changes.jsonl`.
- **skill-maintainer**: `.skill-maintainer/best_practices.md` gains HTML-comment source anchors (`<!-- source: <url> | last_verified: <date> -->`) under each section, routing upstream doc changes to the specific rules they affect. Grep by URL to find rules to re-verify.

### changed
- **skill-maintainer**: bumped plugin + Python package to v0.4.0. Bundled reference (`skills/skill-maintainer/references/best_practices.md`) re-synced from this repo's working copy so new inits pull the latest rules (AGENTS.md compat, 1% description budget, `when_to_use` frontmatter field, corrected hook exit codes, 25KB MEMORY.md cap, 1536-char skill-listing truncation, compaction budget details).
- **mlx-skills** (sibling repo): bootstrapped with `skill-maintain init`, seeded best_practices.md, tracked_repos configured for mlx/mlx-lm/mlx-vlm/mlx-embeddings/mlx-examples, baseline page snapshots captured.

## 0.22.6

### fixed
- **mece-decomposer**: bump to v0.4.1 so marketplace update refreshes stale hooks.json cache (array->object fix from v0.22.4 was never picked up)
- **dimensional-modeling**: bump to v0.3.1 (same stale cache issue)
- **env-forge**: bump to v0.3.1 (same stale cache issue)
- **tui-design**: bump to v0.3.1 (same stale cache issue)

## 0.22.5

### added
- **dev-conventions**: new `dep-audit` skill -- dependency security auditing via `uv audit` (Python) and `bun audit` (JS/TS), transitive analysis, remediation workflow, CI integration
- **dev-conventions**: version pinning conventions in python.md and javascript.md directives -- applications pin exact, libraries use floors/caret ranges
- **dev-conventions**: dependency change tracking in doc-conventions -- session logs now include a structured table of package changes

### changed
- **dev-conventions**: bumped plugin to v0.5.0
- Global rule (`.claude/rules/general.md`) now includes version pinning guidance for both uv and bun

## 0.22.4

### added
- **tui-design**: SessionStart hook auto-injects Five Principles when Rich/Textual/Questionary/Click imports detected. Directive: `hooks/directives/tui-principles.md`. Bumped to v0.3.0.
- **dimensional-modeling**: SessionStart hook auto-injects Kimball principles when DuckDB imports, .duckdb files, or fact_/dim_ SQL patterns detected. Directive: `hooks/directives/kimball-principles.md`. Bumped to v0.3.0.
- **mece-decomposer**: SessionStart hook auto-injects MECE principles when Agent SDK imports or decomposition files detected. Directive: `hooks/directives/mece-principles.md`. Bumped to v0.4.0.
- **env-forge**: SessionStart hook auto-injects task-first design principles when `.env-forge/` directory or fastapi-mcp usage detected. Directive: `hooks/directives/env-forge-principles.md`. Bumped to v0.3.0.

### changed
- **dev-conventions**: refactored SessionStart hook to composable directive files (`hooks/directives/*.md`). Each directive declares its trigger signal (`python`, `javascript`, `docs`, `any`) on line 1. Adding a new convention = dropping a file, no shell editing.
- **dev-conventions**: promoted doc-conventions (last-updated dates, lowercase filenames, document-the-why) to auto-loaded directive alongside TDD and session logging
- **dev-conventions**: bumped plugin to v0.4.0

## 0.22.3

### added
- **json-query**: added to marketplace -- installable plugin for jg/jq tool selection and syntax guidance (from schema-bench research)

### changed
- **dev-conventions**: SessionStart hook now detects project markers up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, etc.

### fixed
- **dev-conventions**: replaced bare `python3` calls in SessionStart hook with `jq` -- eliminates stdlib json usage and bare python3 convention violations

## 0.22.2

### changed
- **dev-conventions**: SessionStart hook now injects TDD as a directive (not a hint) and adds session logging directive when `internal/` directory exists
- **dev-conventions**: bumped plugin to v0.3.0

## 0.22.1

### changed
- **VISION.md**: added `## the architecture` section (trees not workflows, harness coupling, context isolation, use-before-prepare, structured outputs as state, compound feedback loops)
- **VISION.md**: broadened intro paragraph to frame both architecture and retrieval
- **VISION.md**: extended `## what this means for this repo` with 4 new bullets (agent topology, harness-native design, state management, compound feedback)
- **CLAUDE.md**: updated blockquote to reference architectural worldview alongside retrieval
- **CLAUDE.md**: updated "Context as retrieval" subsection to match new VISION.md language
- **README.md**: updated VISION.md blockquote to match new language, dropped overly specific detail
- **docs/analysis/memory_and_rules_system.md**: updated auto memory description to reflect VISION.md architecture section

## 0.22.0

### added
- **skill-dashboard**: Phase B -- drill-down, measure, verify
  - `skill-measure` tool: per-file token breakdown for a single skill (path, chars, tokens, pctOfTotal)
  - `skill-verify` tool: app-only tool that updates `metadata.last_verified` in SKILL.md frontmatter on disk
  - sidebar UI: click any skill row to open file breakdown table with percentage bars and budget status
  - "Mark Verified" button: updates SKILL.md and refreshes quality data
  - two-panel layout (main + sidebar) with grid-based responsive design
  - new components: SkillSidebar, FileBreakdownTable
  - refactored `measureTokens` into `measureTokensDetailed` (returns per-file entries) + thin wrapper
  - `findSkillPath` helper for resolving skill name to SKILL.md path
  - bumped to v1.1.0

## 0.21.0

### changed
- **skill-dashboard**: rebuilt as ext-apps MCP App (TypeScript, React, same pattern as mece-decomposer)
  - replaced Python rawHtml server with interactive ext-apps UI
  - `skill-quality-check` tool: discovers skills/plugins, runs 5 per-skill + 3 per-plugin + 5 repo checks
  - optional `filter` parameter for skill name substring matching
  - all check logic ported to native TypeScript (gray-matter for frontmatter, no Python dependency)
  - components: SummaryBar, SkillTable with token budget bars, PluginTable, RepoChecks with status dots
  - dual transport: stdio + HTTP (port 3002)
  - version sync check: validates plugin.json, marketplace.json, SKILL.md, pyproject.toml alignment
  - removed Python files: server.py, templates/dashboard.html, pyproject.toml
  - removed from uv workspace members (no longer a Python package)
  - bumped to v1.0.0

### added
- **skill-maintainer**: `/skill-maintainer:sync-versions <plugin> <version>` -- bump a plugin's version across all sources (plugin.json, marketplace.json, SKILL.md, pyproject.toml) atomically

### fixed
- **version alignment**: synced plugin.json across 4 plugins that had drifted from marketplace.json
  - dimensional-modeling: 0.1.0 -> 0.2.0
  - tui-design: 0.1.0 -> 0.2.0
  - skill-maintainer: 0.1.0 -> 0.3.0
  - readwise-reader: marketplace 0.1.0 -> 1.0.0 (aligned with plugin.json/SKILL.md)

## 0.20.1

### added
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:quality` (filter by skill name, substring match)
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:init-maintenance` (target directory path)
- **skill-maintainer**: cross-reference validation in quality skill (checks `load the \`X\` skill` patterns resolve)
- **skill-maintainer**: reference file date check in quality skill (checks `last updated:` line in references/*.md)

## 0.20.0

### added
- **skill-maintainer**: new installable plugin at `skills/skill-maintainer/`
  - `/skill-maintainer:maintain`: full maintenance pass (upstream, sources, quality, best practices review) -- replaces legacy `.claude/commands/maintain.md`
  - `/skill-maintainer:quality`: quick quality check (spec, tokens, freshness, description quality) -- no CLI install required
  - `/skill-maintainer:init-maintenance`: set up `.skill-maintainer/` config and state in any repo
  - `references/best_practices.md`: machine-parseable checklist bundled with the plugin
  - skills embed maintenance knowledge directly (thresholds, rules, checks) -- falls back to CLI if available but doesn't require it
  - registered in marketplace.json

### changed
- **skill-maintainer** (CLI): README updated to note plugin is the primary interactive interface, CLI is for CI/headless
- CLAUDE.md: updated repo structure, installation list, maintenance table for plugin

### removed
- `.claude/commands/maintain.md`: replaced by `/skill-maintainer:maintain` plugin skill
- `.claude/commands/` directory: empty after command removal

## 0.19.0

### added
- **dev-conventions**: SessionStart hook for automatic project-type detection
  - detects Python/JS markers in cwd, injects uv/orjson/bun/TDD conventions as additionalContext
  - skills reframed as on-demand references (no longer claim background auto-trigger)
  - bumped plugin version to 0.2.0

## 0.18.3

### fixed
- **skill-maintainer**: `measure_tokens()` now counts only `.md` files (was counting `.py`, `.json`, `.sh`, etc. that are executed, not loaded into context)
  - mece-decomposer dropped from 23,283 to 16,647 tokens (scripts/validate_mece.py was 6,636 phantom tokens)

## 0.18.2

### changed
- **mece-decomposer**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `decompose`, `interview`, `validate`, `export` now use Agent Skills frontmatter (proper `skills/<name>/SKILL.md` layout)
  - removed `commands/` directory (legacy format caused "Legacy format" separator in Cowork)
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **mece-decomposer**: bumped plugin version to 0.3.0
- **mece-decomposer**: updated main skill and README references from "commands" to "skills"
- **env-forge**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `browse`, `forge`, `launch`, `verify` now use Agent Skills frontmatter
  - removed `commands/` directory
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **env-forge**: bumped plugin version to 0.2.0
- **env-forge**: updated main skill and README references from "commands" to "skills"
- CLAUDE.md: updated stale `apps/env-forge/commands/forge.md` path reference

## 0.18.1

### added
- **agent-state**: `domain`, `task_type`, `status` columns on `dim_skill_version` for routing and lifecycle management
- **agent-state**: new workspace package for DuckDB audit and state tracking
  - Kimball star schema: `fact_run`, `fact_run_message`, `fact_watermark`, `dim_run_source`, `dim_skill_version`, `dim_watermark_source`
  - `RunContext` context manager: atomic watermark commits on success, automatic rollback on failure
  - skill version lineage: `dim_skill_version` connects pipeline outputs to agent inputs
  - watermark tracking: replaces `upstream_hashes.json` with queryable history (`v_latest_watermark`)
  - views: `v_run_tree` (recursive hierarchy), `v_flywheel` (producer->skill->consumer), `v_restartable_failures`
  - migration from `changes.jsonl` and `upstream_hashes.json`
  - CLI: `agent-state init|status|runs|tree|watermarks|flywheel|migrate`
  - storage: single global DuckDB at `~/.claude/agent_state.duckdb`

## 0.18.0

### changed
- **repo structure**: reorganized from flat layout to type-based grouping
  - `skills/`: pure markdown skill bundles (tui-design, dimensional-modeling, cogapp-markdown, dev-conventions, mcp-apps, plugin-toolkit)
  - `apps/`: MCP server applications (mece-decomposer, env-forge, skill-dashboard, heylook-monitor, readwise-reader)
  - `tools/`: CLI packages (skill-maintainer)
- **readwise-reader**: migrated from `~/claude/cowork-plugins/readwise-reader` into `apps/readwise-reader/`
  - flattened `plugin/readwise-reader/` contents to top level
  - converted build system from setuptools to hatchling
  - skill-maintainer dep changed from git URL to workspace reference
  - removed non-portable artifacts (certs, models, zip, .venv, scripts/package_plugin.sh)
- workspace member paths updated: `skill-maintainer` -> `tools/skill-maintainer`, `env-forge` -> `apps/env-forge`, etc.
- readwise-reader excluded from default workspace (requires Python 3.13+)
- skill-dashboard `PROJECT_ROOT` fixed for new `apps/` depth
- marketplace.json source paths updated for all plugins
- root `.mcp.json` server path updated
- skill-maintainer git-install subdirectory updated to `tools/skill-maintainer`

### fixed
- **readwise-reader**: added `metadata.last_verified`, `metadata.author`, `metadata.version` to all 3 SKILL.md files
- **readwise-reader**: fixed description quality (added WHAT verb + WHEN trigger) on all 3 skills
- **readwise-reader**: added `repository` field to plugin.json
- stale path references in READMEs and rules from pre-reorg layout (skill-maintainer git-install path, skill-dashboard server.py path, mece-decomposer dev setup path)
- general.md state path corrected to `.skill-maintainer/state/`
- marketplace_distribution_patterns.md section 4.1 updated for current repo layout
- create-mcp-app and migrate-oai-app descriptions fixed (added WHAT verb)
- docs/claude-docs: flattened 2 files from nested .md-named directories, added to index
- docs/README.md: removed empty internals section, added memory and best_practices to claude-docs index
- removed stale web-tdd references from 4 analysis docs (deleted in v0.14.0)
- mcp_ecosystem_audit: updated for current plugin set (added readwise-reader, env-forge, dev-conventions)
- claude_ecosystem_synthesis.md: fixed 9 stale path/config references for v0.17.0/v0.18.0 changes
- claude_ecosystem_synthesis.md: rewrote section 8 for property-driven maintenance (was stale CDC pipeline from v0.12.x), fixed report count 15->16
- skills_guide_analysis.md: config.yaml -> .skill-maintainer/config.json

## 0.17.0

### changed
- **skill-maintainer**: converted from `package = false` scripts to a proper installable Python package
  - new `src/skill_maintainer/` package with CLI entry point `skill-maintain`
  - git-installable: `uv add git+<repo>#subdirectory=skill-maintainer`
  - all commands accept `--dir <path>` to target any skill repo (default: `.`)
  - subcommands: init, validate, quality, freshness, measure, test, upstream, sources, log
  - per-repo config in `.skill-maintainer/config.json` (upstream URLs, tracked repos)
  - per-repo state in `.skill-maintainer/state/` (hashes, changes log)
  - best_practices.md moved to `.skill-maintainer/best_practices.md`
  - version bumped to 0.2.0
- **skill-dashboard**: replaced `sys.path.insert` hack with proper `skill-maintainer` workspace dependency
  - imports now: `from skill_maintainer.tests import ...` and `from skill_maintainer.shared import ...`
  - removed unused `sys` import

## 0.16.0

### changed
- **skill-dashboard**: rewritten to show full run_tests.py dataset (was: 5 columns from file scan; now: skills + plugins + repo hygiene pass/fail)
  - server.py imports test_skills/test_plugins/test_repo_hygiene from run_tests.py (no more duplicated discovery/measurement code)
  - HTML template: skills table with spec, description quality, freshness, budget, body size; plugins table with manifest/marketplace/README checks; repo hygiene section
  - dropped pyyaml dependency (no longer parses frontmatter directly)
  - bumped to v0.3.0
- **skill-dashboard**: moved `.mcp.json` from `skill-dashboard/` to project root so Claude Code auto-discovers the MCP server
- **skill-maintainer**: consolidated `measure_tokens()` and `check_description_quality()` into `shared.py` (was duplicated in run_tests.py and quality_report.py)

## 0.15.1

### added
- **skill-maintainer**: `run_tests.py` -- red/green test suite encoding best_practices.md as pass/fail checks
  - three categories: skills (spec, budget, body size, staleness, description), plugins (manifest, marketplace, README), repo hygiene (gitignore, hooks, state, duplicates, freshness)
  - `--verbose` shows all results; `--category skills|plugins|repo` runs one category
  - no network calls, no file writes, pure read-only
- **skill-maintainer**: `/maintain` slash command for full maintenance passes
  - orchestrates pull_sources.py -> check_upstream.py -> quality_report.py -> best_practices.md review
  - Claude proposes edits to best_practices.md based on detected changes; user approves before any writes
- **skill-maintainer**: `pull_sources.py` script for pulling 10 tracked coderef repos and detecting changes
  - records HEAD SHAs in `upstream_hashes.json["local_repos"]`, captures commit logs for changed repos
  - appends `source_pull` events to `changes.jsonl` audit log
  - CLI flags: `--no-pull`, `--no-save`, `--no-log`
- `VISION.md`: design principles document -- skills as retrieval, precision/recall framework, progressive disclosure, always-loaded context justification
- **skill-maintainer**: `shared.py` -- added `discover_plugins()` function (mirrors `discover_skills()` for plugin directories)

### changed
- `query_log.py`: added `source_pull` event type display
- `.claude/rules/plugins.md`: removed stale references to config.yaml and monitored_sources.md (removed in v0.13.0)
- **skill-maintainer**: `best_practices.md` rewritten as machine-parseable checklist with sections mapped to VISION.md principles
- **skill-maintainer**: `README.md` rewritten with full workflow section (before/after changes, periodic maintenance, individual checks table)

### removed
- PostToolUse hook on Skill tool (was firing on every skill invocation across all sessions; staleness now checked on-demand via `/maintain` or `check_freshness.py`)
- `.claude/hooks/check-skill-freshness.sh`: dead hook script (PostToolUse hook removed)
- `.gitignore`: removed blanket `.claude/` ignore; project-shared files (rules, commands, hooks, settings.json) are now tracked

## 0.15.0

### changed
- **pyproject.toml**: restructured as uv workspace with four members (skill-maintainer, env-forge, skill-dashboard, mece-decomposer)
  - each subfolder declares its own dependencies instead of a monolithic root
  - removed `coderef/` editable paths that broke on clone (local-only symlinks)
  - `skills-ref` now installed from PyPI; `mcp-ui-server` from git (github.com/idosal/mcp-ui)
  - root is a workspace coordinator with dev-only deps (pytest, ruff)
  - setup: `uv sync --all-packages`; existing `uv run` commands unchanged

### added
- **dev-conventions**: new installable plugin extracting global CLAUDE.md into selective skills
  - `python-tooling` (background): enforces uv over pip, orjson over json
  - `bun-tooling` (background): enforces bun over npm/yarn/pnpm
  - `tdd-workflow` (user-invocable): red/green TDD workflow
  - `doc-conventions` (user-invocable): last-updated dates, lowercase filenames, session logs, document the "why"

## 0.14.0

### removed
- **web-tdd**: removed plugin (generic TDD workflow that duplicates Claude's built-in knowledge; stack preferences belong in CLAUDE.md)

### changed
- migrated all JS/TS tooling references from npm/npx to bun/bunx across package.json scripts, SKILL.md files, READMEs, and settings
- replaced package-lock.json with bun.lockb in heylook-monitor and mece-decomposer/mcp-app

## 0.13.0

### changed
- **skill-maintainer**: replaced pipeline-driven model with property-driven maintenance
  - removed: SKILL.md (no longer a skill), DuckDB store (store.py, migrate_state.py), CDC pipeline (docs_monitor.py, source_monitor.py, update_report.py, apply_updates.py), journal system (journal.py), config.yaml, state.json
  - added: pre-commit git hook (validates staged SKILL.md files with skills-ref)
  - added: PostToolUse Claude Code hook (checks last_verified age when any skill is invoked)
  - added: quality_report.py (unified CLI: validation, token budget, last_verified, description quality)
  - added: check_upstream.py (on-demand upstream doc change detection via llms-full.txt hashing)
  - added: query_log.py (query append-only changes.jsonl audit log)
  - simplified: validate_skill.py, measure_content.py, check_freshness.py (removed DuckDB deps, auto-discover skills)
  - added `.claude/settings.json` with PostToolUse hook config
  - added `.claude/hooks/check-skill-freshness.sh`
- all 10 SKILL.md files: added `metadata.last_verified: 2026-02-25` to frontmatter
- `pyproject.toml`: removed `duckdb` dependency
- `CLAUDE.md`: removed DuckDB/CDC/pipeline docs, updated maintenance section with hook/CLI model

## 0.12.1

### changed
- **env-forge**: extracted `scripts/shared.py` module from duplicated code in catalog.py and materialize.py (constants, download_file, load_jsonl, ensure_dir)
- **env-forge**: materialize.py now compile-checks generated server.py and verifiers.py before writing (WARNING on error, never blocks)
- **env-forge**: verifier assembly deduplicates imports across verifier records instead of raw code concatenation
- **env-forge**: forge.md adds new step 2 "Reference from Catalog" (search AWM-1K for structural exemplar before generating from scratch)
- **env-forge**: README.md expanded with Quick Start, Status (Phase 1 vs 2), and Patterns sections
- `docs/README.md`: expanded to authoritative documentation index (16 analysis reports, synthesis, internals, 18 captured claude-docs)
- `CLAUDE.md`: replaced 36-line documentation index with pointer to docs/README.md; added catalog-as-exemplar pattern and huggingface-hub dependency; fixed domain report count (15 -> 16); net ~20 lines removed

## 0.12.0

### added
- **env-forge**: new installable plugin for generating database-backed MCP tool environments
  - SKILL.md: task-first environment design methodology extracted from AWM synthesis pipeline
  - 2 commands (browse, forge) + 2 Phase 2 stubs (launch, verify)
  - references: schema_patterns.md, api_design_rules.md, verification_patterns.md, fastapi_mcp_template.md, catalog_index.md
  - scripts: catalog.py (search/browse AWM-1K on HF), materialize.py (fetch and write environment), validate_env.py (structural validation)
  - two modes: browse 1000 pre-generated environments from AWM-1K catalog, or forge new ones from scenario descriptions
  - covers: SQLite schema synthesis, RESTful API design, FastAPI+MCP server generation, DB state verification, self-correction patterns
  - fetches data from Snowflake/AgentWorldModel-1K on HF at runtime (no large files in repo)

## 0.11.3

### added
- `skill-dashboard`: new project-scoped Python MCP App plugin
  - pure Python server (FastMCP + mcp-ui rawHtml) -- no Node.js or build step
  - reads skill registry from `skill-maintainer/config.yaml`, SKILL.md frontmatter for versions
  - queries DuckDB store for freshness and token budget data; falls back to file mtime scan
  - self-contained HTML dashboard (Tailwind CDN + Alpine.js CDN) with color-coded status, budget bars, and filter buttons
  - reference implementation for the Python-native MCP App pattern
  - `mcp-ui-server` editable dependency added to `pyproject.toml`
- `.claude/rules/general.md`: always-loaded general conventions (package manager, JSON, logs, READMEs)
- `.claude/rules/skills.md`: path-scoped to `**/SKILL.md` -- trigger phrases, 1024-char limit, script paths, 500-line limit
- `.claude/rules/plugins.md`: path-scoped to `**/.claude-plugin/**`, `**/plugin.json` -- new plugin checklist, auto-discovery, required fields

### changed
- `skill-maintainer/config.yaml`: added `https://code.claude.com/docs/en/memory` to `anthropic-skills-docs` watched pages
- `CLAUDE.md`: removed Conventions section (~28 lines); replaced with one-liner pointing to `.claude/rules/`; fixed domain report count (14 -> 15)

## 0.11.2

### added
- `docs/analysis/memory_and_rules_system.md`: domain report covering the six-level memory hierarchy, auto memory storage and behavior, CLAUDE.md import syntax, `.claude/rules/` modular path-scoped rules, glob patterns, organization-level management, and how this repo uses memory
- `docs/reports/claude_ecosystem_synthesis.md`: new section 2.5 (Memory and Rules System) with hierarchy table, auto memory details, import syntax, rules comparison table
- `docs/reports/claude_ecosystem_synthesis.md`: memory & rules row added to Component Maturity Assessment (section 4)
- `docs/reports/claude_ecosystem_synthesis.md`: memory mentions added to Solo (CLAUDE.local.md, auto memory) and Team (.claude/rules/) building strategies (section 5), and Enterprise (managed policy CLAUDE.md) tier (section 5)
- `docs/reports/claude_ecosystem_synthesis.md`: auto memory and project memory rows added to This Repo as Reference (section 10)
- `docs/reports/claude_ecosystem_synthesis.md`: memory report added to Report Index (section 11)

### changed
- `skill-maintainer/SKILL.md`: added disambiguation note in journal section distinguishing DuckDB session journal from Claude's built-in auto memory system

## 0.11.1

### fixed
- **mece-decomposer MCP App**: VALIDATE_SCRIPT path resolution broken when running from compiled `dist/index.cjs` -- `import.meta.dirname` polyfills to `__dirname` (= `mcp-app/dist/`), so `..` resolved to `mcp-app/` instead of `mece-decomposer/`. Added `PLUGIN_ROOT` constant with source vs dist detection.
- **mece-decomposer MCP App**: HTTP server bound to `0.0.0.0` (all interfaces) creating DNS rebinding risk. Changed to `127.0.0.1` (localhost only).
- **mece-decomposer MCP App**: stale build artifacts (`index.js`, `server.js`) accumulating in `dist/` from older builds. Added `prebuild` script to clean dist before each build.

## 0.11.0

### added
- **7 domain reports** in `docs/analysis/`: comprehensive coverage of the Claude extension ecosystem
  - `plugin_system_architecture.md`: plugin anatomy, schema, component types, auto-discovery, implementation audit of all 7 repo plugins
  - `marketplace_distribution_patterns.md`: marketplace schema, source types, monorepo patterns, enterprise distribution
  - `mcp_protocol_and_servers.md`: MCP protocol fundamentals, primitives, transports, TypeScript/Python SDKs, inspector, registry
  - `mcp_apps_and_ui_development.md`: MCP Apps SDK, MCP UI SDK, tool-UI linkage, React hooks, framework templates, bundling
  - `hooks_system_patterns.md`: all 14 event types, 3 hook types, matchers, security/automation patterns, plugin hooks
  - `subagents_and_agent_teams.md`: custom agents, built-in agents, tool control, agent teams, delegation patterns
  - `cross_surface_compatibility.md`: 7 surfaces, feature compatibility matrix, transport requirements, permission model differences
- **synthesis report** in `docs/reports/claude_ecosystem_synthesis.md`: executive summary, architecture decision tree, component maturity assessment, building strategies, cross-surface strategy, maintenance problem, report index

### changed
- `CLAUDE.md`: refactored to cover full ecosystem (plugins, MCP, hooks, agents), added documentation index section, added plugin/MCP development sections, streamlined from 251 to 256 lines
- `README.md`: added documentation section with links to all 14 domain reports and synthesis, organized by domain/existing/synthesis/internals categories

## 0.10.0

### added
- **mece-decomposer MCP App**: interactive tree visualization companion for MECE decompositions
  - 4 MCP tools: mece-decompose (tree render), mece-validate (structural validation), mece-refine-node (app-only editing), mece-export-sdk (Agent SDK code generation)
  - React UI with recursive tree view, expand/collapse, node selection, dependency badges
  - streaming support via useStreamingTree hook (progressive tree building as Claude generates)
  - sidebar panels: metadata, node detail (editable), validation report with score gauges, export preview with copy
  - SDK code generation: walks tree recursively, emits Agent() for agent atoms, orchestration functions for branches
  - follows ext-apps SDK patterns (basic-server-react structure, threejs-server wrapper pattern)
  - validation tool spawns validate_mece.py via subprocess with graceful fallback if uv unavailable
  - co-located at mece-decomposer/mcp-app/

## 0.9.0

### added
- **mece-decomposer**: new installable plugin for MECE decomposition of goals, tasks, and workflows
  - SKILL.md: 4 commands (decompose, interview, validate, export)
  - references: decomposition_methodology.md, sme_interview_protocol.md, validation_heuristics.md, agent_sdk_mapping.md, output_schema.md
  - scripts: validate_mece.py for deterministic structural validation of decomposition JSON
  - dual output: human-readable tree for SME validation + structured JSON mapping to Agent SDK primitives
  - covers: MECE scoring rubrics, depth-adaptive rigor, atomicity criteria, cross-branch dependency scanning

### fixed
- restored root pyproject.toml (was accidentally overwritten by mece-decomposer-specific one)
- restructured mece-decomposer to standard plugin layout (skills/mece-decomposer/)

## 0.8.0

### added
- **tui-design**: new installable plugin for terminal UI design
  - SKILL.md: 5 principles (semantic color, responsive layout, right component, visual hierarchy, progressive density)
  - references: rich_patterns.md, questionary_patterns.md, anti_patterns.md, layout_recipes.md
  - covers: Rich component selection, Questionary interactive prompts, 9 anti-patterns with before/after, 4 complete layout recipes
  - 16-color safe palette with semantic meanings, pipe-safe output patterns

## 0.7.0

### added
- **dimensional-modeling**: new installable plugin for Kimball-style star schema design
  - SKILL.md: router skill teaching dimensional modeling patterns for DuckDB agent state
  - references: schema_patterns.md, query_patterns.md, key_generation.md, anti_patterns.md, dag_execution.md
  - covers: SCD Type 2 dimensions, hash surrogate keys, fact table design, analytical views, agent execution DAG
- star-schema-llm-context: repo cleanup
  - deleted ~3950 lines of dead knowledge graph code (graph_algorithms.py, mcp_server.py, schema.sql, db_manager.py, setup.py, requirements.txt, Makefile, ARCHITECTURE.md, config.yaml)
  - rewrote README.md with clear vision statement (pattern library, not code library)
  - rewrote CLAUDE.md to reflect current state
  - added pyproject.toml
  - replaced speculative expansion roadmap (embeddings, graph DB) with DAG execution model and automation patterns

## 0.6.0

### changed
- **store.py**: complete rewrite from OLTP to Kimball dimensional model
  - MD5 hash surrogate keys on all dimensions (replaced integer PKs and MAX(id)+1 pattern)
  - SCD Type 2 on all dimension tables (effective_from/to, is_current, hash_diff for change detection)
  - no PRIMARY KEY constraints on dimensions (SCD Type 2 requires multiple rows per entity)
  - no primary keys on fact tables (dropped all 6 sequences; grain = composite dimension keys + timestamp)
  - no FK constraints (join by convention, validate at application layer)
  - metadata columns on all tables: record_source, session_id, inserted_at
  - meta_schema_version table for schema evolution tracking
  - meta_load_log table for operational visibility (script execution tracking)
  - merged fact_session into fact_session_event (session boundaries are events with event_type='session_start'/'session_end')
  - all views updated to filter is_current = TRUE and join on hash_key
  - automatic v1 -> v2 schema migration (detects old schema, drops and recreates)
- **migrate_state.py**: added --force flag for clean schema recreation, integrated with meta_load_log
- **source_monitor.py**: explicit record_source='source_monitor' on change records
- **journal.py**: rewritten for merged session/event model (no more fact_session table)
- duckdb_schema.md: complete rewrite reflecting v2 Kimball schema

### added
- `v_skill_budget_trend` view and `--budget-trend` CLI flag: token budget trend over time per skill (meta-cognition: "am I getting fatter?")
- `docs/analysis/abstraction_analogies.md`: unified framework document -- selection under constraint, five invariant operations (decompose/route/prune/synthesize/verify), database analogy for skills, DAG hierarchy model
- CLAUDE.md: selection-under-constraint design principle, dimensional model section, three-repo architecture
- README.md: design philosophy section
- star-schema-llm-context design docs: library_design.md and abstraction_analogies.md (canonical home)

### fixed
- SCD Type 2 bug: removed PRIMARY KEY from dimension tables that would cause constraint violations when closing old rows and opening new ones (hash_key must appear in multiple rows for SCD Type 2)

## 0.5.0

### added
- DuckDB-backed relational store (`store.py`) replacing flat `state.json` overwrite pattern
  - star schema: dimension tables (dim_source, dim_skill, dim_page, skill_source_dep) + append-only fact tables (fact_watermark_check, fact_change, fact_validation, fact_update_attempt, fact_content_measurement, fact_session, fact_session_event)
  - pre-built views: v_latest_watermark, v_latest_page_hash, v_skill_freshness, v_skill_budget, v_latest_source_check
  - WAL mode for concurrent access from hooks
  - backward-compatible state.json export via `Store.export_state_json()`
- `migrate_state.py`: one-time migration from state.json into DuckDB with round-trip verification
- `measure_content.py`: token budget tracker for all tracked skills
  - walks skill directories, classifies files, measures line/word/char/token counts
  - budget thresholds: 4000 tokens (warn), 8000 tokens (critical)
  - records measurements in fact_content_measurement for historical tracking
- `journal.py`: session activity logger with three modes
  - append: fast JSONL buffer for hooks (no DuckDB access, <50ms)
  - ingest: batch import JSONL into DuckDB
  - query: show recent session activity with filters
- `/skill-maintainer budget` command for token budget measurement
- `/skill-maintainer history` command for temporal change queries
- `/skill-maintainer journal` command for session activity queries
- `docs/internals/duckdb_schema.md`: full schema documentation
- `docs/analysis/data_centric_agent_state_research.md`: strategic research on star schema patterns for LLM agent systems (10 use cases analyzed)
- `duckdb>=1.0` dependency

### changed
- `docs_monitor.py`: migrated from load_state/save_state to Store class
- `source_monitor.py`: migrated from load_state/save_state to Store class
- `check_freshness.py`: migrated from JSON traversal to DuckDB v_skill_freshness view
- `apply_updates.py`: records update attempts and validations in DuckDB
- `validate_skill.py`: records validation results in fact_validation table
- `update_report.py`: reads changes from DuckDB instead of state dict
- skill-maintainer SKILL.md version bumped to 0.2.0 with new commands documented

## 0.4.0

### changed
- migrated all plugins to canonical `.claude-plugin/plugin.json` manifest location (was `plugin.json` at root)
- removed non-standard `skills` and `agents` array fields from plugin manifests (auto-discovery handles these)
- added `repository` field to all plugin manifests
- created root `.claude-plugin/marketplace.json` making this repo a proper plugin marketplace
- rewrote README.md installation section with correct CLI commands (`install`/`uninstall`, not `add`/`remove`)
- README.md now documents the marketplace-based install flow (`/plugin marketplace add fblissjr/fb-claude-skills`)
- README.md usage section updated with correct namespaced skill invocations
- updated CLAUDE.md repo structure and installation sections to match new layout
- replaced docs/claude-docs/ HTML scrapes with clean markdown from live site (3 replaced, 2 new)
- added docs/claude-docs/claude_docs_discover_plugins.md and claude_docs_plugin_marketplaces.md
- updated docs/README.md with claude-docs contents table
- added discover-plugins and plugin-marketplaces to skill-maintainer config.yaml watched pages
- updated docs/analysis/skills_guide_analysis.md with v0.4.0 compliance section
- added skill-maintainer/README.md (was the only module without one)

## 0.3.1

### added
- heylook-monitor: MCP App dashboard for heylookitsanllm local LLM server
  - live monitoring: models, system metrics (RAM/CPU), per-model performance (TPS, latency)
  - quick inference panel for testing prompts against local models
  - 4 tools: show_llm_dashboard, poll_status, quick_inference, list_local_models
  - server-side API proxying (no CSP issues), auto-polling with graceful degradation
  - follows system-monitor-server reference implementation pattern

### changed
- web-tdd: restructured as installable plugin (SKILL.md moved to `skills/web-tdd/SKILL.md`, added plugin.json, metadata fields)
- cogapp-markdown: restructured as installable plugin (SKILL.md moved to `skills/cogapp-markdown/SKILL.md`, added plugin.json, metadata fields)
- all plugin READMEs: standardized with installation commands, skills table, invocation examples
- root README.md: added comprehensive installation guide (clone + install, GitHub install, project-scoped, uninstall, usage)
- CLAUDE.md: added Installation section, updated repo structure to reflect plugin layout, added READMEs convention

## 0.3.0

### added
- mcp-apps: new skill module for building and migrating MCP Apps (interactive UIs for MCP)
  - create-mcp-app skill: guides building MCP Apps from scratch (framework selection, tool+resource registration, theming, streaming, testing)
  - migrate-oai-app skill: step-by-step migration from OpenAI Apps SDK to MCP Apps SDK with API mapping tables and CSP checklist
  - plugin.json: plugin manifest with both skills
  - references/: local copies of upstream docs (overview, patterns, testing, specification, migration guide) for offline use
  - README.md: user-facing documentation
- skill-maintainer: ext-apps source added to config.yaml for upstream change detection
  - monitors 7 upstream files (2 skills, 1 spec, 4 docs)
  - create-mcp-app and migrate-oai-app tracked as managed skills
- docs/internals/: technical documentation for skill-maintainer system
  - api_reference.md: function signatures, parameters, return types for all Python scripts
  - schema.md: formal schemas for state.json and config.yaml
  - troubleshooting.md: common issues, error messages, recovery procedures
- docs/README.md: documentation index linking all doc sections
- CLAUDE.md: added "adding a new skill module" checklist and direct skills-ref validate shortcut

## 0.2.1

### changed
- docs_monitor.py: rewritten as CDC pipeline (detect -> identify -> classify)
  - detect: HEAD request comparing Last-Modified header (zero bandwidth if unchanged)
  - identify: fetch llms-full.txt, split by page, hash each watched page
  - classify: keyword heuristic on diff text
  - removed markdownify dependency (no longer needed)
- config.yaml: sources use llms_full_url + pages instead of individual urls
- state.json: new format with _watermark (per-source) and _pages (per-page) with last_changed tracking
- check_freshness.py, apply_updates.py, update_report.py: updated for new state format

### removed
- .github/workflows/skill-maintenance.yml and validate-skills.yml: local freshness hooks are sufficient; CI adds overhead without value for solo use

## 0.2.0

### added
- skill-maintainer: new skill for automated skill maintenance and monitoring
  - docs_monitor.py: hash-based change detection for Anthropic docs URLs
  - source_monitor.py: git-based upstream code change detection (generalized from mlx-skills)
  - update_report.py: unified change report generation
  - apply_updates.py: update pipeline with report-only, apply-local, and create-pr modes
  - validate_skill.py: extended validation wrapping skills-ref with best practice checks
  - check_freshness.py: lightweight staleness check for hooks integration
  - config.yaml: source registry and skill tracking configuration
  - references/: best practices, monitored sources, update patterns documentation
  - state/: versioned state for content hashes, timestamps, versions
- docs/analysis/: structured reference documentation
  - skills_guide_structured.md: full extraction from Anthropic skills guide PDF
  - skills_guide_analysis.md: gap analysis and actionable findings
  - self_updating_system_design.md: cross-reference of all sources with architecture decisions
- GitHub Actions workflows
  - skill-maintenance.yml: daily cron + manual dispatch for automated monitoring
  - validate-skills.yml: PR validation for skill file changes
- pyproject.toml: uv-based dependency management with skills-ref integration

### fixed
- docs_monitor.py: content extraction now extracts main content div instead of capturing raw JS/CSS from Next.js pages

### changed
- plugin-toolkit/skills/plugin-toolkit/SKILL.md: added metadata.version field
- CLAUDE.md: comprehensive get-up-to-speed guide for the repo (Phase 8)

## 0.1.0

### added
- plugin-toolkit: plugin analysis, polish, and feature management skill
- web-tdd: test-driven development workflow for web applications
- cogapp-markdown: auto-generate markdown sections using cogapp
