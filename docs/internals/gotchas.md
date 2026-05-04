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

`.git/hooks/pre-commit` validates staged SKILL.md files (via `agentskills validate`), checks plugin version alignment across all sources, warns when plugin content changes are staged without a version bump, and warns on CLAUDE.md size creep (>150 lines or ~4000 tokens). **It's not tracked by git** — must be re-applied on fresh clones.

To install on a fresh clone, until a scaffolding command is wired in:

1. Copy the hook from a teammate's clone (`.git/hooks/pre-commit`), or
2. Re-create from this repo's history — the most recent committed plugin source for the hook lives in skill-maintainer's release notes (search CHANGELOG.md for "pre-commit").

The hook uses `jq` for JSON parsing (not python3/orjson) since it runs outside the project venv. Bash 3.2 portability rules apply (see [plugin-patterns.md](plugin-patterns.md)).

## path-privacy interaction

The path-privacy plugin's pre-commit and commit-msg hooks hard-block any commit whose staged content, message, or branch name references an absolute path outside the repo root. This includes `~`, `$HOME`, and `/Users/<name>/...` shapes.

For paths that legitimately need to mention an external-looking path (regex source, doc example, system reference), append `path-privacy: ignore` to that line. Use sparingly.

For system-level references in prose (e.g., "the global agent-state DB lives at `<HOME>/.claude/agent_state.duckdb`"), the placeholder `<HOME>` is the canonical replacement — passes the rule, communicates the meaning.

If pre-commit blocks a leak you didn't write, it's likely grandfathered content from before path-privacy was installed. Fix the leak in the same commit; don't `--no-verify`.

## CLAUDE.md size creep

The hub-and-spoke restructure (skill-maintainer 0.6.5) trimmed CLAUDE.md from ~270 lines to ~70. The pre-commit hook now warns when CLAUDE.md exceeds 150 lines or ~4000 tokens. The warning catches the slow drift back into single-file-everything; treat it as a prompt to move content into a spoke (`docs/internals/`) or remove duplication with SessionStart-injected directives. The warning does not block — discretion stays with the author.

## Count drift across files

Three places in the repo claim file/report counts that drift independently: `README.md` (root), `docs/README.md`, and (historically) `CLAUDE.md`. The fix: don't include numbers. Say "domain reports" or "sub-skills", not "16 domain reports" or "6 sub-skills". The filesystem is the source of truth; descriptions that don't claim a count never go stale.

This rule will be partially enforced once `skill-maintain lint` ships (planned next minor): orphan + count-drift detection across the doc tree.
