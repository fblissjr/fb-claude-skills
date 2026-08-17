last updated: 2026-08-04

# Gotchas

Repo-specific weirdness that bites if you don't know it.

## security-guidance plugin's PreToolUse hook is disabled

The `security-guidance` plugin (when installed at the user level) ships a PreToolUse hook (`security_reminder_hook.py`) that substring-matches several English tokens that appear in doc prose:

- code-evaluation builtins with parens (e.g., `eval(`, `exec(`)
- serialization library names
- DOM sink method names
- OS exec function names

No path or context awareness. Fires on MLX docs, session logs, and any prose that happens to contain these tokens.

**Disabled for this repo** via `.claude/settings.json`:

```json
{
  "env": { "ENABLE_SECURITY_REMINDER": "0" }
}
```

If you reset settings or clone fresh, re-disable. Trade-off: this repo gives up all of the plugin's checks, but content here is mostly markdown and Python without those patterns in source code, and the repo's own pre-commit + TDD workflow provide other safety nets. Upstream fix would be a path-aware exemption for `.md` files.

## Pre-commit hook is not tracked by git

`.git/hooks/pre-commit` validates staged SKILL.md files (via `skill-maintain validate`, the Claude Code schema gate), checks plugin version alignment across all sources, warns when plugin content changes are staged without a version bump, and warns on CLAUDE.md size creep (>150 lines or ~4000 tokens). **It's not tracked by git** (git refuses to track `.git/`) — must be re-applied on fresh clones.

To install on a fresh clone:

```bash
uv sync --all-packages           # installs the skill-maintainer package
uv run skill-maintain init       # writes .skill-maintainer/config.json + installs the pre-commit hook
```

`skill-maintain init` is idempotent: re-running on a repo that already has the hook prints `already up to date`. To replace an existing hook (e.g., after a hook update), use `skill-maintain init --force-hook` — the prior hook is preserved as `.git/hooks/pre-commit.local` before the new one is written.

The hook source lives in the Python package at `tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample`, copied into `.git/hooks/pre-commit` by the installer. Updating the bundled hook is a normal plugin content change — bump skill-maintainer, refresh the sample, run `skill-maintain init --force-hook` in any clone that needs the new version.

The hook uses `jq` for JSON parsing (not python3/orjson) since it runs outside the project venv. Bash 3.2 portability rules apply (see [plugin-patterns.md](plugin-patterns.md)).

### Local secret gate in pre-commit.local (this machine only)

`.git/hooks/pre-commit.local` carries a gitleaks stage (section 1c) added 2026-08-03. Rationale: GitHub push protection does not cover `google_api_key` or `google_gemini_api_key` (alerts only, per GitHub's supported-patterns table), and the one real secret handled around this repo is a Gemini key — so a leaked key would push successfully and only alert after it was public. The stage scans the staged diff with gitleaks 8.30.1, pinned at `<HOME>/.local/bin/gitleaks`, installed by hand with its sha256 verified against the release checksums file. Default ruleset, no config: measured against this repo's tree and full history, it produces zero findings, so there is no allowlist to maintain. Fails closed when the binary is missing.

Two things to know:

- **It is machine-local and untracked**, like everything in `.git/hooks/`. A fresh clone gets nothing until the stage is re-added and the binary reinstalled.
- **`skill-maintain init --force-hook` clobbers it**: that flag preserves the *current* `pre-commit` as `pre-commit.local`, overwriting the existing `.local` file — which is where the gitleaks stage lives. Re-add the stage after any forced hook reinstall.

Deliberately NOT shipped in the skill-maintainer hook template: that would impose a fail-closed binary dependency on every repo using the plugin. An adversarial review (2026-08-03, session log) concluded CI scanners (gitleaks or betterleaks) add little over GitHub's native scanning for this repo; the pre-commit stage exists solely to close the Google-key push-protection gap.

## path-privacy interaction

The path-privacy plugin's pre-commit and commit-msg hooks hard-block any commit whose staged content, message, or branch name references an absolute path outside the repo root. This includes `~`, `$HOME`, and `/Users/<name>/...` shapes.  <!-- path-privacy: ignore -->

For paths that legitimately need to mention an external-looking path (regex source, doc example, system reference), append `path-privacy: ignore` to that line. Use sparingly.

For system-level references in prose (e.g., "the global agent-state DB lives at `<HOME>/.claude/agent_state.duckdb`"), the placeholder `<HOME>` is the canonical replacement — passes the rule, communicates the meaning.

If pre-commit blocks a leak you didn't write, it's likely grandfathered content from before path-privacy was installed. Fix the leak in the same commit; don't `--no-verify`.

## Reviewing a large diff

`/code-review ultra` with no argument diffs against `origin/main` — **pushing first empties the review target**. Pass an explicit base instead. It also rejects diffs over 8,000 lines, which this repo hits easily once doc deletions are involved.

Splitting a diff across branches to fit that cap manufactures false positives: reviewers report content as "missing" when it only lives in the half they cannot see. Four findings in the 2026-07-21 review were exactly this. Prefer an explicit base that excludes bulk deletions over splitting by path.

## Two sessions in one worktree

`git add -A` sweeps the other session's uncommitted work into your commit. This happened three times on 2026-07-21 and permanently detached two CHANGELOG entries from the commits that describe them — unfixable without a history rewrite. Stage explicit paths and check `git status --short` before committing whenever another session is active.

## CLAUDE.md size creep

The hub-and-spoke restructure (skill-maintainer 0.6.5) trimmed CLAUDE.md from ~270 lines to ~70. The pre-commit hook now warns when CLAUDE.md exceeds 150 lines or ~4000 tokens. The warning catches the slow drift back into single-file-everything; treat it as a prompt to move content into a spoke (`docs/internals/`) or remove duplication with SessionStart-injected directives. The warning does not block — discretion stays with the author.

## Shell snippets in shipped docs inherit the reader's working directory

Several plugins here ship commands in their skill bodies for a reader to run. A
snippet carries an implicit working directory: the author's, wherever they
happened to be. The reader's is wherever the task put them, and nothing in the
snippet records the difference or reveals it in the output.

`dangling-refs` 0.1.0 shipped with `git ls-files | xargs grep -ln 'name'` as the
sweep a user runs before deleting a unit. `git ls-files` lists files under the
**cwd**, not the repo — and the most natural place to run a pre-deletion sweep is
inside the unit being deleted. Measured here: sweeping for `gemini-bridge` from
inside `apps/gemini-bridge/` returned 12 files, all of them inside that directory
and therefore about to be deleted anyway; from the repo root, 26. The 14 it could
not see were the entire point. It did not error, and it did not return zero — it
returned a plausible list of the wrong files, which is the failure mode you
cannot detect from the output.

Prefer commands that state their scope over commands that inherit it:

| Instead of | Write |
|---|---|
| `git ls-files \| xargs grep …` | `git grep -F -- 'term' :/` |
| `git ls-files '*.py' \| xargs …` | `git grep -- 'term' :/ -- '*.py'` |

`git grep` also handles paths containing spaces (which `xargs` splits on), avoids
GNU `xargs` running the utility with no operands when nothing matches (it blocks
on stdin — passes on macOS, hangs on Linux), and takes `-F` for literal matching
so a unit named `foo.js` is not treated as a regex.

The general rule, which applies to any snippet this repo ships: **if a command's
answer depends on where it runs, testing it from one directory tells you
nothing.** Run it from the location a reader would actually be in — usually not
the repo root, because that is where the author was.

## Count drift across files

Multiple places in the repo (root `README.md`, `docs/README.md`, historically `CLAUDE.md`) have at various times asserted counts of files — domain reports, captured docs, sub-skills, plugins. These drift independently as the filesystem evolves, and any single number falls out of sync within a release or two.

The fix: don't include numbers in prose. Say "domain reports" rather than a hardcoded count. The filesystem is the source of truth; descriptions that don't claim a count never go stale.

`skill-maintain lint` enforces this. It scans `README.md`, `CLAUDE.md`, `docs/README.md`, and `docs/internals/*.md` for count assertions matching `\b\d+\s+(domain reports|reports covering|captured docs)\b` and compares each claim to the filesystem reality. Soft finding (exit 0); not a CI block.

## SessionStart hooks from our own plugins were disabled here (fully retired 2026-08-04)

**This section is history.** All three disables are gone — dev-conventions re-enabled 2026-08-03, the other two retired 2026-08-04; see the dated resolutions below. The prose in between is the record of why each disable existed and how its premise expired.

Two plugins were disabled in this repo only, via `enabledPlugins: false` in `.claude/settings.json`: `dimensional-modeling`, `mece-decomposer`. (`env-forge` is deprecated, not disabled — the `renames` map in `marketplace.json` handles its removal. An `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.) Their SessionStart hooks inject directive text into every session — conventions this repo already has written down in `.claude/rules/general.md` and in the user's global CLAUDE.md. Loading both is pure duplication with no benefit.

The hooks are not removed from the plugins themselves. They exist for repos that have nothing written down yet — a fresh clone of some other project has no `.claude/rules/general.md`, so the injected directive is doing real work there. This repo is the exception, not the rule the plugins are designed around.

A future session should not "helpfully" re-enable these plugins to restore consistency with other repos. The setting is intentional and repo-specific; if it looks like an oversight, check `.claude/settings.json` and this section before touching it.

**Resolved 2026-08-03, same day: the owner approved the re-enable.** `dev-conventions` is out of the disable list; its enforcement hooks are active here again and its ambient blocks stay silent via ground coverage. The paragraph below is the premise record that drove the decision, kept for history:

**Premise change, 2026-08-03 — recorded, not acted on.** dev-conventions 0.15.x silences each directive per block wherever the repo's own files cover its ground, and a test arm (`test_this_repo_stays_fully_covered` in `tools/skill-maintainer/tests/test_dev_conventions_directives.py`) runs the hook against this repo live on every suite run: complete silence, all four grounds covered — if a rewording of CLAUDE.md or `.claude/rules/` ever slips past the ground patterns, that arm goes red before a re-enabled plugin starts broadcasting here. So for dev-conventions specifically, the duplication this disable prevents no longer occurs, and the disable's remaining effect is losing the PreToolUse enforcement hooks (pip/npm/lockfile blocks). Re-enabling dev-conventions here would now cost zero ambient text and restore enforcement. That flip is the owner's decision — this paragraph exists so the next session weighs the current facts instead of the 2026-07 ones. The rationale still holds unchanged for `dimensional-modeling` and `mece-decomposer`, which have no coverage detection.

**Resolved 2026-08-04: the remaining two disables retired; the whole section is now history.** The premise expired for the other pair too, differently — not by coverage detection but by removal at the source: dimensional-modeling's SessionStart hook was dropped in `e3a8044` and mece-decomposer's in `09d455d`, both 2026-07-26, so since then the `enabledPlugins: false` entries disabled plugins that ship no hooks. Nothing watched that pair (the disable's rationale vs. the hooks it named); the first control-audit census caught it as finding S1 — an `enabledPlugins: false` entry whose stated reason named SessionStart hooks that both plugins had already deleted, so the disable was suppressing nothing and the rationale was the only thing keeping it alive — and the owner chose retirement over re-rationalizing. `.claude/settings.json` now carries no `enabledPlugins` key; both plugins' skills are available here again, which matches the dogfooding policy (the home repo runs what installs get). The env-forge caution stands: never add an `enabledPlugins` entry for a plugin in the `renames` map — Claude Code auto-deletes it, mutating a tracked file.

**Closing note, 2026-08-17: the machinery this whole section reasons about no longer exists.** dev-conventions 0.17.0 deleted both hooks, all five directives, the ground-coverage mechanism, `init`, `configure` and `.dev-conventions.json`. Two sentences above are therefore false as present-tense statements and are kept only as the record of what was believed at the time: "its enforcement hooks are active here again and its ambient blocks stay silent via ground coverage", and the tripwire claim about `test_this_repo_stays_fully_covered` running the hook live on every suite run — that test file was deleted in the same change, so the guarantee it offered is gone rather than merely untested. Nothing here should be read as describing current behaviour. The env-forge caution in the paragraph above is the one part that still stands, because it is about the `renames` map rather than about this plugin.


## Bare `pytest` from the repo root does not work; run per package

`uv run pytest` with no path collects everything, including the `coderef/`
symlinked foreign clones and `research/`, and dies with ~165 collection
errors before reaching any real test. There is no root `testpaths` config —
the house practice is per-package runs: `uv run pytest tools/skill-maintainer/tests/`
is the repo-wide suite (version alignment, changelog claims, path privacy,
the dev-conventions hook bracket). Related: a fresh or stale venv fails
imports (`No module named 'mcp'`) until `uv sync --all-packages`. Both cost a
detour on 2026-08-03; recorded here so the next session greps this instead of
rediscovering.

## Removing a frontmatter field can break the pre-commit hook

Hit for real on 2026-07-21, when `metadata.version` was removed from all SKILL.md files. The pre-commit hook extracted the version with a pipeline shaped like:

```bash
sed -n '/^---$/,/^---$/p' SKILL.md | grep '^ *version:' | head -1 | sed 's/.*: *//'
```

Under `set -euo pipefail`, a `grep` that matches nothing exits non-zero, and with `pipefail` that non-zero propagates out of the pipeline. That aborted the whole hook — silently, with exit 1 and no error message printed. Commits appeared to vanish: `git commit` returned to the prompt having done nothing, with nothing in the terminal explaining why.

The trap: tolerating an absent field in a *comparison* (`if [ -z "$version" ]; then skip; fi`) is not the same as tolerating it in the *extraction* that feeds the comparison. The extraction ran first and killed the script before any tolerant comparison logic got a chance to run.

Fixed by appending `|| true` to the end of the whole command substitution — `sk_ver=$(sed ... | grep ... | head -1 | sed ... || true)` — so a no-match yields an empty string instead of aborting, leaving the downstream logic to handle it. Putting it on the `grep` alone also works, but the substitution-level form covers every step in the chain. Any hook step built on `grep`/`sed` chains under `pipefail` needs the same treatment whenever the thing being matched can legitimately be absent — check other extraction pipelines in the hook for the same pattern before removing another field from frontmatter.

## A retired unit's directory can outlive its retirement

Three specimens on 2026-08-04 alone: `skills/explainer-video/` (retired in
changelog 0.91.0) still existed on disk holding `.DS_Store` files and a
stray skill-maintainer state log, and `apps/agent-state-mcp/` (retired
`54ada95`) held only ruff caches and `__pycache__`. Both listed in `ls`
like live units and misled a session into treating one as an active plugin.

The mechanism: `git rm -r` removes tracked files only. Untracked build
debris — caches, `.DS_Store`, gitignored state — survives, and the
surviving directory is invisible to every tracked-content sweep by
construction (`git grep`, `git ls-files`, the retire skill's verification
all read the index, not the disk). So the one place the leftovers show up
(`ls`, tab-completion, a session's mental model) is exactly where they lie.

Practice: after any retirement, `rm -rf` the directory itself once
`git ls-files <dir>` returns empty, and glance at what falls — debris
deletes silently; anything surprising gets looked at first. Filed for
dangling-refs' next release: add this as an explicit final step in the
retire procedure (its current verify section stops at tracked content).
