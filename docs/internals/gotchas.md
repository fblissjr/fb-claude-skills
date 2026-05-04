last updated: 2026-05-04

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
