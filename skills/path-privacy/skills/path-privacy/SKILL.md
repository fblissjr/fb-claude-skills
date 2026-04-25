---
name: path-privacy
description: >-
  Enforces a single rule: every path in repo content must be relative to the repo root.
  Anything resolving outside the repo (other repos on disk, ~/.claude/<plan>, /Users/<name>/...,
  /home/<name>/..., $HOME-based paths) is a leak. Ships a SessionStart directive plus
  pre-commit and commit-msg git hooks that hard-block. Use when user says
  "scan for path leaks", "check for leaked paths", "are we leaking my home path",
  "scrub external paths", "install path-privacy hooks", "find absolute paths in this repo",
  "remove $HOME references", "block path leaks", "audit before commit", "privacy scan paths".
metadata:
  author: Fred Bliss
  version: 0.1.1
  last_verified: 2026-04-25
allowed-tools: "Bash,Read,Edit"
---

<!-- path-privacy: skip-file -->

# path-privacy

Stops absolute and home-relative filesystem paths from leaking into committed artifacts.

## The rule

**Every path written into the repo must be relative to the repo root.**

A "leak" is any string that, after expanding `~`, `$HOME`, or `${HOME}`, resolves to an absolute path that does NOT live under the current repo root. Examples that leak:

- `~/development/SomeOtherRepo/foo.py`
- `~/.claude/plans/<plan-name>.md`
- `/Users/<your-name>/code/x`
- `/home/<your-name>/code/x`
- `$HOME/...` when `$HOME` is outside the repo

Examples that do NOT leak:

- `./scripts/foo.sh`, `scripts/foo.sh` (repo-relative)
- `/Users/USERNAME/foo` (placeholder username)
- `<HOME>/.claude/...`, `the agent state DB` (generic reference)

For external dependencies, name them generically: "another project", "SecondRepo", "the agent-state DB", `<HOME>/.claude/...`. Never paste an actual absolute path.

## Quiet operation

When you find or fix a leak, do **not** announce it:

- Branch name: vague (`chore/cleanup`, `docs/refresh`). Do not name what was scrubbed.
- Commit title: vague (`docs: minor edits`). Do not name leaked content.
- Commit message body: do not paste the leaked path. Do not write "removed leak from X".
- Changelog: no entry describing the leak. If a version bump is required, the entry is a generic "edits" or "internal cleanup".
- Repo content: no comments saying `// removed leaked path here`. Just remove and move on.

The privacy guarantee fails the moment the activity is advertised.

## Modes

| Mode | Command | Notes |
|------|---------|-------|
| Audit a repo | `bash <plugin-root>/skills/path-privacy/scripts/find-external-paths.sh -d .` | Read-only sweep of the working tree |
| Audit a single file | `... -f path/to/file` | One file |
| Audit staged changes | `... --staged` | Same logic as the pre-commit hook |
| Audit a string (file-content tone) | `... --text 'see /Users/jamie/proj'` | Strict boundary; mirrors the file-content scan |
| Audit a commit message or branch name | `... --text 'fix/Users/jamie/path' --lax-boundary` | Lax boundary catches `/Users/` segments embedded right after a word char (e.g. `fix/Users/...`). Used by the commit-msg hook for both message body and branch name. |
| Install git hooks | `bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh` | Adds pre-commit + commit-msg into the current repo, preserving existing hooks |
| Uninstall git hooks | `bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh --uninstall` | Restores any preserved `.local` hook |

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}` when the plugin is installed via the marketplace, or `skills/path-privacy` when running from a checkout of fb-claude-skills.

## How findings look

Each finding is one line: `<file>:<lineno>: <matched-token>`. After all findings, a one-line remediation hint. Exit code is 1 on any finding, 0 when clean.

## Per-line opt-out

A line containing the literal token `path-privacy: ignore` is skipped by the scanner. Use sparingly — only on lines that are themselves examples or placeholders that legitimately need to mention an external-looking path (e.g., the regex source, a doc snippet showing what the rule catches).

## Workflow when a leak is found

### Pre-commit hook fired

1. The hook prints `<file>:<lineno>: <match>` for each finding.
2. Open the file, replace the absolute portion with a repo-relative path or a generic name.
3. Re-stage. Re-commit. Use a vague commit message — not "remove leaked path".
4. Move on.

### Existing leak found in `git log` history

History rewrites are out of scope for v0.1.0. If you must:

- Use `git filter-repo` (not `git filter-branch`).
- Do it on a topic branch with a vague name. Force-push without announcement.
- See `references/scrub_workflow.md` for the rest.

## What this plugin does NOT do

- It does not auto-redact found leaks. Removal is manual — that is intentional, since auto-replace can mangle code.
- It does not scan for arbitrary secrets (API keys, JWTs, etc.). For that, use the `scan-for-secrets` plugin.
- It does not rewrite git history.
- It does not run as a `PreToolUse` hook on `Edit`/`Write`. The git hooks plus the SessionStart directive are sufficient.

## References

- `references/patterns.md` — exact regex shapes, placeholder allowlist, edge cases
- `references/scrub_workflow.md` — how to remove leaks quietly (current changes and historical commits)
- Sister plugin: `scan-for-secrets` (broader privacy/secret sweep)
