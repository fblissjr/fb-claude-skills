last updated: 2026-08-03

# Gotchas

Repo-specific weirdness that bites if you don't know it.

## best_practices.md has two copies

Two files, same content, sync-required:

- `.skill-maintainer/best_practices.md` — the **working copy**. This is what `skill-maintain quality` reads. Edit this one.
- `skills/skill-maintainer/references/best_practices.md` — the **bundled reference**. Seed for `skill-maintain init` in new repos.

If you only edit the bundled copy, fresh `init` runs in other repos pull stale rules. The skill-maintainer plugin ships a PostToolUse hook (`skill-maintainer-sync-bundled-ref.sh`) that auto-mirrors the working copy → bundled reference on Edit/Write of `.skill-maintainer/best_practices.md`. The hook is `cmp -s`-gated, silent on no-op, exit 0 always.

A `sync-best-practices` subcommand or a symlink would close this loop more robustly but hasn't been implemented. The hook is the current safety net; if it didn't fire, copy the working copy over the bundled one by hand. The manual skill that wrapped that one `cp` was removed on 2026-07-26 -- a skill whose whole body is a command the hook already runs automatically is a second place for the same logic to drift.

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

## SessionStart hooks from our own plugins are disabled here

Three plugins are disabled in this repo only, via `enabledPlugins: false` in `.claude/settings.json`: `dev-conventions`, `dimensional-modeling`, `mece-decomposer`. (`env-forge` is deprecated, not disabled — the `renames` map in `marketplace.json` handles its removal. An `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.) Their SessionStart hooks inject roughly 3,500 characters of directive text per session — conventions this repo already has written down in `.claude/rules/general.md` and in the user's global CLAUDE.md. Loading both is pure duplication with no benefit.

The hooks are not removed from the plugins themselves. They exist for repos that have nothing written down yet — a fresh clone of some other project has no `.claude/rules/general.md`, so the injected directive is doing real work there. This repo is the exception, not the rule the plugins are designed around.

A future session should not "helpfully" re-enable these plugins to restore consistency with other repos. The setting is intentional and repo-specific; if it looks like an oversight, check `.claude/settings.json` and this section before touching it.


## Removing a frontmatter field can break the pre-commit hook

Hit for real on 2026-07-21, when `metadata.version` was removed from all SKILL.md files. The pre-commit hook extracted the version with a pipeline shaped like:

```bash
sed -n '/^---$/,/^---$/p' SKILL.md | grep '^ *version:' | head -1 | sed 's/.*: *//'
```

Under `set -euo pipefail`, a `grep` that matches nothing exits non-zero, and with `pipefail` that non-zero propagates out of the pipeline. That aborted the whole hook — silently, with exit 1 and no error message printed. Commits appeared to vanish: `git commit` returned to the prompt having done nothing, with nothing in the terminal explaining why.

The trap: tolerating an absent field in a *comparison* (`if [ -z "$version" ]; then skip; fi`) is not the same as tolerating it in the *extraction* that feeds the comparison. The extraction ran first and killed the script before any tolerant comparison logic got a chance to run.

Fixed by appending `|| true` to the end of the whole command substitution — `sk_ver=$(sed ... | grep ... | head -1 | sed ... || true)` — so a no-match yields an empty string instead of aborting, leaving the downstream logic to handle it. Putting it on the `grep` alone also works, but the substitution-level form covers every step in the chain. Any hook step built on `grep`/`sed` chains under `pipefail` needs the same treatment whenever the thing being matched can legitimately be absent — check other extraction pipelines in the hook for the same pattern before removing another field from frontmatter.
