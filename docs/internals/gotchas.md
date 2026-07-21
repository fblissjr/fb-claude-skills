last updated: 2026-07-21

# Gotchas

Repo-specific weirdness that bites if you don't know it.

## best_practices.md has two copies

Two files, same content, sync-required:

- `.skill-maintainer/best_practices.md` — the **working copy**. This is what `skill-maintain quality` reads. Edit this one.
- `skills/skill-maintainer/references/best_practices.md` — the **bundled reference**. Seed for `skill-maintain init` in new repos.

If you only edit the bundled copy, fresh `init` runs in other repos pull stale rules. The skill-maintainer plugin ships a PostToolUse hook (`sync-bundled-ref.sh`) that auto-mirrors the working copy → bundled reference on Edit/Write of `.skill-maintainer/best_practices.md`. The hook is `cmp -s`-gated, silent on no-op, exit 0 always.

A `sync-best-practices` subcommand or a symlink would close this loop more robustly but hasn't been implemented. The hook is the current safety net; if it didn't fire, run `/skill-maintainer:sync-bundled-ref` manually.

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

`.git/hooks/pre-commit` validates staged SKILL.md files (via `agentskills validate`), checks plugin version alignment across all sources, warns when plugin content changes are staged without a version bump, and warns on CLAUDE.md size creep (>150 lines or ~4000 tokens). **It's not tracked by git** (git refuses to track `.git/`) — must be re-applied on fresh clones.

To install on a fresh clone:

```bash
uv sync --all-packages           # installs the skill-maintainer package
uv run skill-maintain init       # writes .skill-maintainer/config.json + installs the pre-commit hook
```

`skill-maintain init` is idempotent: re-running on a repo that already has the hook prints `already up to date`. To replace an existing hook (e.g., after a hook update), use `skill-maintain init --force-hook` — the prior hook is preserved as `.git/hooks/pre-commit.local` before the new one is written.

The hook source lives in the Python package at `tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample`, copied into `.git/hooks/pre-commit` by the installer. Updating the bundled hook is a normal plugin content change — bump skill-maintainer, refresh the sample, run `skill-maintain init --force-hook` in any clone that needs the new version.

The hook uses `jq` for JSON parsing (not python3/orjson) since it runs outside the project venv. Bash 3.2 portability rules apply (see [plugin-patterns.md](plugin-patterns.md)).

## path-privacy interaction

The path-privacy plugin's pre-commit and commit-msg hooks hard-block any commit whose staged content, message, or branch name references an absolute path outside the repo root. This includes `~`, `$HOME`, and `/Users/<name>/...` shapes.

For paths that legitimately need to mention an external-looking path (regex source, doc example, system reference), append `path-privacy: ignore` to that line. Use sparingly.

For system-level references in prose (e.g., "the global agent-state DB lives at `<HOME>/.claude/agent_state.duckdb`"), the placeholder `<HOME>` is the canonical replacement — passes the rule, communicates the meaning.

If pre-commit blocks a leak you didn't write, it's likely grandfathered content from before path-privacy was installed. Fix the leak in the same commit; don't `--no-verify`.

## CLAUDE.md size creep

The hub-and-spoke restructure (skill-maintainer 0.6.5) trimmed CLAUDE.md from ~270 lines to ~70. The pre-commit hook now warns when CLAUDE.md exceeds 150 lines or ~4000 tokens. The warning catches the slow drift back into single-file-everything; treat it as a prompt to move content into a spoke (`docs/internals/`) or remove duplication with SessionStart-injected directives. The warning does not block — discretion stays with the author.

## Count drift across files

Multiple places in the repo (root `README.md`, `docs/README.md`, historically `CLAUDE.md`) have at various times asserted counts of files — domain reports, captured docs, sub-skills, plugins. These drift independently as the filesystem evolves, and any single number falls out of sync within a release or two.

The fix: don't include numbers in prose. Say "domain reports" rather than a hardcoded count. The filesystem is the source of truth; descriptions that don't claim a count never go stale.

`skill-maintain lint` enforces this. It scans `README.md`, `CLAUDE.md`, `docs/README.md`, and `docs/internals/*.md` for count assertions matching `\b\d+\s+(domain reports|reports covering|captured docs)\b` and compares each claim to the filesystem reality. Soft finding (exit 0); not a CI block.

## SessionStart hooks from our own plugins are disabled here

Four plugins are disabled in this repo only, via `enabledPlugins: false` in `.claude/settings.json`: `dev-conventions`, `dimensional-modeling`, `mece-decomposer`, `env-forge`. Their SessionStart hooks inject roughly 3,500 characters of directive text per session — conventions this repo already has written down in `.claude/rules/general.md` and in the user's global CLAUDE.md. Loading both is pure duplication with no benefit.

The hooks are not removed from the plugins themselves. They exist for repos that have nothing written down yet — a fresh clone of some other project has no `.claude/rules/general.md`, so the injected directive is doing real work there. This repo is the exception, not the rule the plugins are designed around.

A future session should not "helpfully" re-enable these plugins to restore consistency with other repos. The setting is intentional and repo-specific; if it looks like an oversight, check `.claude/settings.json` and this section before touching it.

## `_deprecated/` is skipped by all tooling

`apps/_deprecated/` holds plugins that are kept on disk but withdrawn from circulation — currently `env-forge`, moved there and removed from `marketplace.json` and the root `pyproject.toml` workspace members. `_deprecated` was added to `SKIP_DIRS`, so nothing under it is scanned for skills or plugins by `discover_skills`, `discover_plugins`, `measure_tokens`, or the version-alignment check.

Why skip rather than just delete the marketplace entry and leave the code in place: a plugin that still exists on disk but isn't listed in `marketplace.json` would otherwise fail `check_version_alignment`'s "plugin on disk not in marketplace" check forever. That check is supposed to catch a plugin someone forgot to register, not flag a plugin that was deliberately retired. A permanently-red board trains everyone to ignore it — the whole point of the check is that a failure means something needs action.

If a deprecated plugin needs to come back, move it out of `_deprecated/`, re-add it to `marketplace.json` and the workspace members, and it re-enters every check automatically.

## Removing a frontmatter field can break the pre-commit hook

Hit for real on 2026-07-21, when `metadata.version` was removed from all SKILL.md files. The pre-commit hook extracted the version with a pipeline shaped like:

```bash
sed -n '/^---$/,/^---$/p' SKILL.md | grep '^ *version:' | head -1 | sed 's/.*: *//'
```

Under `set -euo pipefail`, a `grep` that matches nothing exits non-zero, and with `pipefail` that non-zero propagates out of the pipeline. That aborted the whole hook — silently, with exit 1 and no error message printed. Commits appeared to vanish: `git commit` returned to the prompt having done nothing, with nothing in the terminal explaining why.

The trap: tolerating an absent field in a *comparison* (`if [ -z "$version" ]; then skip; fi`) is not the same as tolerating it in the *extraction* that feeds the comparison. The extraction ran first and killed the script before any tolerant comparison logic got a chance to run.

Fixed by appending `|| true` to the end of the whole command substitution — `sk_ver=$(sed ... | grep ... | head -1 | sed ... || true)` — so a no-match yields an empty string instead of aborting, leaving the downstream logic to handle it. Putting it on the `grep` alone also works, but the substitution-level form covers every step in the chain. Any hook step built on `grep`/`sed` chains under `pipefail` needs the same treatment whenever the thing being matched can legitimately be absent — check other extraction pipelines in the hook for the same pattern before removing another field from frontmatter.
