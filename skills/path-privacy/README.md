# path-privacy

<!-- path-privacy: skip-file -->

last updated: 2026-04-25

Stops absolute and home-relative filesystem paths from leaking into committed artifacts. One rule: every path written into the repo must be relative to the repo root.

## What it does

- **SessionStart directive**: when a session opens in a git repo, the rule is injected into Claude's context so paths outside the repo are never written in the first place.
- **Pre-commit hook**: hard-blocks any commit whose staged file content references a path resolving outside the repo root.
- **Commit-msg hook**: hard-blocks any commit whose message body or current branch name references such a path.
- **On-demand skill**: scan a working tree, a single file, or an arbitrary string for leaks.

The plugin treats "fixing leaks" as a sensitive activity. The directive instructs Claude to keep branch names, commit titles, commit messages, and changelog entries vague when removing leaks — never advertise the cleanup.

## Install

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install path-privacy@fb-claude-skills
```

After install, the SessionStart directive is active in any git repo you open a session in. The git hooks are opt-in per repo:

```
# from inside the repo you want to protect:
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh"
```

This writes `.git/hooks/pre-commit` and `.git/hooks/commit-msg` wrappers that delegate to the plugin's scanner. If hooks already exist, they are preserved as `.local` and the wrapper invokes them first.

To uninstall in a repo:

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh" --uninstall
```

## Skills

| Skill | Description |
|-------|-------------|
| `path-privacy` | Scan files, directories, staged changes, or strings for paths that resolve outside the repo root. Hard-block at commit time via git hooks. |

Trigger phrases: "scan for path leaks", "check for leaked paths", "are we leaking my home path", "scrub external paths", "install path-privacy hooks", "find absolute paths in this repo", "remove $HOME references", "block path leaks".

## How "leak" is defined

After expanding `~`, `$HOME`, and `${HOME}`, if the absolute path does NOT live under the current repo root, it is a leak. Repo-relative paths and generic placeholders (`/Users/USERNAME/foo`, `<HOME>/.claude/...`) are not flagged. Per-line `path-privacy: ignore` opts a specific line out.

Full pattern reference: `skills/path-privacy/references/patterns.md`.

## How to remove a leak

Pre-commit hook fires, prints `<file>:<lineno>: <match>`, exits 1. Open the file, replace the absolute portion with a repo-relative reference or a generic name. Re-stage, re-commit with a vague message ("docs: minor edits"). Do not announce that a leak was fixed.

For paths already in git history, see `skills/path-privacy/references/scrub_workflow.md`.

## Dependencies

- `ripgrep` (`brew install ripgrep`)
- `jq` (for the SessionStart hook)
- `git`
