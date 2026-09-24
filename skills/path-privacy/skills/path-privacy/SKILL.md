---
name: path-privacy
description: >-
  Keeps personal identifiers out of repo content: every path must be relative to
  the repo root, and the git user.name full name never appears. Leaks are other
  repos on disk, absolute home-directory paths under /Users or /home, and named
  directories under ~ or $HOME. Hooks rewrite in-repo absolute paths to relative
  and block the rest in edits, commit messages and branch names; pre-commit and
  commit-msg git hooks hard-block at commit. Use when user says "scan for path
  leaks", "check for leaked paths", "are we leaking my home path", "is my name in
  this repo", "scrub external paths", "install path-privacy hooks", "find
  absolute paths in this repo", "remove $HOME references", "block path leaks",
  "audit before commit", "privacy scan paths".
allowed-tools: "Bash,Read,Edit"
---

<!-- path-privacy: skip-file -->

# path-privacy

Keeps a username, a machine's layout, private project names and the owner's full
name out of committed artifacts.

<rule>

**Every path written into the repo is relative to the repo root, and the git
`user.name` full name is never written at all.**

A path leaks when, after expanding `~`, `$HOME` or `${HOME}`, it resolves
outside the repo root and says something about this machine. Leaks:

- `~/development/SomeOtherRepo/foo.py`, `$HOME/code/secret-project` (a named
  directory under home: layout and project names)
- `/Users/<your-name>/code/x`, `/home/<your-name>/code/x`
- `-Users-<your-name>-code-proj` (the dash-joined form in Claude Code's
  per-project and scratch directories)
- a generic location that still spells the username,
  `~/.claude/projects/-Users-<your-name>-...`

Not leaks:

- `scripts/foo.sh` (repo-relative)
- `~/.claude/...`, `$HOME/.config/...`, `~/Library/...`, `~/AppData/...` (a
  tool's config location, the same on every machine that has the tool)
- `$HOME` alone, or followed by a variable (`$HOME/$dir`): shell code
- `/Users/USERNAME/foo`, `/Users/dev/...`, `/home/runner/...`, `<HOME>/...`
  (placeholders and system accounts; list in `references/patterns.md`)

The full name is matched case-insensitively, middle names optional, joined by
spaces, dots, dashes, underscores or nothing. The GitHub handle and the git
email are allowed. `LICENSE` files and a `Signed-off-by:` trailer written by
`git commit -s` are the two exceptions. A one-word `user.name` is a handle and
guards nothing.

</rule>

<enforcement>

| Where | What happens |
|---|---|
| PreToolUse, Write/Edit | An absolute or `~`/`$HOME` spelling of a path INSIDE the repo is rewritten to repo-relative in place (`updatedInput`), with one line of context saying so. An external path or the full name blocks the call |
| PreToolUse, Bash | A `git`/`gh` command carrying the full name is blocked; home-directory prefixes are masked first, so a home path that spells the name does not count. Commit, tag and PR message text (including heredoc bodies) and new branch names are scanned for external paths |
| git pre-commit | Staged files are scanned whole for external paths; ADDED lines are scanned for the full name |
| git commit-msg | The message and current branch name, for both |
| SessionStart (startup) | Refreshes stale hook wrappers. Silent unless the gate is missing (said once per repo), stale or ahead |

Gitignored files are not checked: they cannot reach a commit. The git hooks are
per-repo and installed by hand; the PreToolUse hook runs in every repo.

</enforcement>

<quiet_operation>

When you find or fix a leak, do not announce it:

- Branch name: vague (`chore/cleanup`, `docs/refresh`).
- Commit title and body: vague (`docs: minor edits`). No leaked path, no "removed leak from X".
- Changelog: no entry describing it. If a version bump is required, "internal cleanup".
- Repo content: no `// removed leaked path here` comments.

The privacy guarantee fails the moment the activity is advertised. Every block
message repeats this, because a block is when the correction happens.

</quiet_operation>

<modes>

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}` for a marketplace install, or
`skills/path-privacy` in a checkout of fb-claude-skills. Scripts live in
`<plugin-root>/skills/path-privacy/scripts/`.

| Mode | Command | Notes |
|------|---------|-------|
| Audit a repo | `find-external-paths.sh -d .` | Read-only sweep of the working tree |
| Audit a file | `find-external-paths.sh -f path/to/file` | |
| Audit staged changes | `find-external-paths.sh --staged` | Same path logic as pre-commit |
| Audit a string | `find-external-paths.sh --text '...'` | Add `--lax-boundary` for commit messages and branch names (catches `fix/Users/...`) |
| Find the full name | `git grep -n -i -E "$(bash -c '. <scripts>/_name_guard.sh; pp_name_regex .')" \| cut -d: -f1,2` | Existing occurrences as `file:line`; the `cut` keeps the name itself out of the output |
| Scrub (preview / write) | `scrub-paths.sh -d .` then `--apply` | Needs `.path-privacy.local.json`; see `references/scrub_workflow.md` |
| Install / uninstall git hooks | `install-git-hooks.sh` / `--uninstall` | Preserves an existing hook as `.local` and chains it |
| Check this repo's gate | `install-git-hooks.sh --doctor [root]` | Read-only; version, fail-closed, installed-or-not, per repo |

Findings print as `<file>:<lineno>: <matched-token>`, exit 1 on any finding.
Name findings print `<file>:<lineno>` only; nothing in this plugin echoes the
name.

</modes>

<opt_outs>

- **Per line:** a line containing `path-privacy: ignore` is skipped by the path
  scanner. For examples and placeholders that must show an external-looking path.
- **Per file:** `path-privacy: skip-file` as the leading content of one of the
  first 30 lines, after at most three spaces and an optional comment introducer
  (`#`, `//`, `--`, `;`, `<!--`), and outside any fenced code block. For files
  that are ABOUT the rule: regex source, pattern catalogs, fixtures. A mention
  in prose is not an opt-out; exact rules in `references/patterns.md`.
- Commit messages and branch names honour only the per-line form.
- Neither opt-out covers the full name. Use a placeholder instead.
- JSON and CSV have no file-level form (no comment syntax): use the per-line
  marker, or gitignore the file.
- For an Edit, the marker must already be on disk; for a new file, it must be in
  the content's first 30 lines.

</opt_outs>

<when_blocked>

1. Read the finding: `<file>:<lineno>: <match>`.
2. Replace the path with a repo-relative reference or a generic name ("another
   project", `<HOME>/.claude/...`); replace the name with the GitHub handle or
   `<author>`.
3. Re-stage and re-commit with a vague message. Never `--no-verify`.

For leaks already in history, see `references/scrub_workflow.md`.

</when_blocked>

<not_covered>

- In-repo absolute paths written other than through Write/Edit (a shell
  heredoc, a generated file) are not rewritten and not blocked at commit. This
  repo's `skill-maintain test` whole-tree audit catches them.
- The full name in reversed order ("Last, First"), as initials, or as a
  nickname. Not detectable with few enough false positives to block on.
- NotebookEdit cells, and file content written by Bash, until commit time.
- Secrets and tokens: use `scan-for-secrets`.
- Git history rewrites: see `references/scrub_workflow.md`.

</not_covered>

<references>

- `references/patterns.md`: regexes, the generic-location and placeholder
  lists, the file-level marker's exact rules, edge cases
- `references/scrub_workflow.md`: removing leaks quietly, the
  `.path-privacy.local.json` suggestion and `allow` config, `scrub-paths.sh`
- `references/path-privacy.local.json.example`: starter config

</references>
