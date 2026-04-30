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
  version: 0.1.4
  last_verified: 2026-04-30
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
| Use a custom suggestion config | `... --config path/to/config.json` | Override the auto-resolved `<repo-root>/.path-privacy.local.json`. See "Per-repo suggestions" below. |
| Scrub (preview) | `bash <plugin-root>/skills/path-privacy/scripts/scrub-paths.sh -d .` | Dry-run by default; prints unified diff per file. Reads same `.path-privacy.local.json` config. |
| Scrub (write) | `... --apply` | Apply the substitutions in place. |
| Install git hooks | `bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh` | Adds pre-commit + commit-msg into the current repo, preserving existing hooks |
| Uninstall git hooks | `bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh --uninstall` | Restores any preserved `.local` hook |

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}` when the plugin is installed via the marketplace, or `skills/path-privacy` when running from a checkout of fb-claude-skills.

## How findings look

Each finding is one line: `<file>:<lineno>: <matched-token>`. After all findings, a one-line remediation hint. Exit code is 1 on any finding, 0 when clean.

## Per-line opt-out

A line containing the literal token `path-privacy: ignore` is skipped by the scanner. Use sparingly — only on lines that are themselves examples or placeholders that legitimately need to mention an external-looking path (e.g., the regex source, a doc snippet showing what the rule catches).

## Per-repo suggestions (optional)

Drop a `.path-privacy.local.json` at the repo root (gitignore it!) to enrich
each finding with an actionable replacement specific to your machine. With it,
a finding line is followed by `→ use: <substituted form>` instead of the
generic "use a relative path" message. The same config drives the
`scrub-paths.sh` script (see "Scrubbing" below). The scanner auto-loads the
file when present; absent, behavior is unchanged.

```json
{
  "suggestions": [
    {"match": "/Users/foo/code/myrepo/", "suggest": "<repo>/"},
    {"match": "/Users/foo/",             "suggest": "<home>/"},
    {"match": "~/Library/Caches/",       "suggest": "<cache>/"}
  ]
}
```

Each entry's `match` is a literal substring (not a regex); `suggest` is the
text that replaces it. Entries are auto-sorted longest-match-first so the
most specific entry wins regardless of how you order them. Requires `jq`;
silently no-ops if `jq` is missing or the file is malformed.

To use a config file at a non-default path, pass `--config <path>` to the
scanner.

A starter template lives at `references/path-privacy.local.json.example`.

## Scrubbing

Once a `.path-privacy.local.json` is in place, `scrub-paths.sh` applies the
same substitutions to files in the working tree. Two-phase: dry-run by
default (prints `diff -u`), `--apply` writes.

```bash
# Preview what would change across the repo
bash <plugin-root>/skills/path-privacy/scripts/scrub-paths.sh -d .

# Preview a single file
bash <plugin-root>/skills/path-privacy/scripts/scrub-paths.sh -f docs/foo.md

# Preview the staged set (same selection as the pre-commit hook)
bash <plugin-root>/skills/path-privacy/scripts/scrub-paths.sh --staged

# Once the diff looks right, write
... --apply
```

The scrub honors the same `path-privacy: skip-file` marker as the scanner
(file-level opt-out via the first 30 lines), and is a no-op on files that
contain none of the configured `match` substrings. Substitutions are applied
longest-first so a more-specific entry wins over a less-specific one.

This is a literal substring substitution; it does not rewrite quoted strings,
escape paths in code, or do any AST-aware transformation. Always review the
diff before `--apply`.

## Workflow when a leak is found

### Pre-commit hook fired

1. The hook prints `<file>:<lineno>: <match>` for each finding.
2. Open the file, replace the absolute portion with a repo-relative path or a generic name. (Or: `scrub-paths.sh --staged` to preview a config-driven fix.)
3. Re-stage. Re-commit. Use a vague commit message — not "remove leaked path".
4. Move on.

### Existing leak found in `git log` history

History rewrites are out of scope for v0.1.0. If you must:

- Use `git filter-repo` (not `git filter-branch`).
- Do it on a topic branch with a vague name. Force-push without announcement.
- See `references/scrub_workflow.md` for the rest.

## What this plugin does NOT do

- It does not auto-apply fixes without explicit `--apply`. Default is dry-run with diff preview, since auto-replace can mangle code.
- It does not scan for arbitrary secrets (API keys, JWTs, etc.). For that, use the `scan-for-secrets` plugin.
- It does not rewrite git history.

## References

- `references/patterns.md` — exact regex shapes, placeholder allowlist, edge cases
- `references/scrub_workflow.md` — how to remove leaks quietly (current changes and historical commits)
- `references/path-privacy.local.json.example` — starter suggestion config
- Sister plugin: `scan-for-secrets` (broader privacy/secret sweep)
