# path-privacy

<!-- path-privacy: skip-file -->

last updated: 2026-09-24

Keeps personal identifiers out of committed artifacts. Two rules: every path
written into the repo is relative to the repo root, and the git `user.name`
full name is never written at all. The GitHub handle and git email are fine.

The plugin fixes what it safely can and blocks the rest. It does not load
anything into context unless it has something to tell you.

## What it does

| Where | Behaviour |
|---|---|
| PreToolUse, Write/Edit | An absolute or `~`/`$HOME` spelling of a path **inside** the repo is rewritten to repo-relative before the write lands (`updatedInput`, no permission change), with one line of context saying so. A path **outside** the repo, or the full name, blocks the call |
| PreToolUse, Bash | A `git`/`gh` command containing the full name is blocked. Commit, tag and PR message text (heredoc bodies included) and new branch names are scanned for external paths |
| git pre-commit | Staged files are scanned whole for external paths. **Added** lines are scanned for the full name, so a name already in history does not block unrelated commits |
| git commit-msg | Message and current branch name, for both. A `Signed-off-by:` trailer from `git commit -s` is allowed |
| SessionStart (startup only) | Refreshes this repo's frozen hook wrappers when the template changes. Emits nothing in a repo whose gate is installed and current; says once per repo when the gate is missing |

Every block message ends with the one rule no hook can enforce: the correction
is routine, and commit messages, branch names and changelog entries do not
mention it. That used to be a SessionStart directive injected on every start,
resume, clear and compact. It now appears only when a correction is under way.

### What counts as a leak

A path leaks when it resolves outside the repo root and says something about
this machine: `~/code/secret-project`, `$HOME/development/OtherRepo`,
`/Users/<your-name>/...`, or the dash-joined `-Users-<your-name>-...` form in
Claude Code's scratch and project directories.

These name nothing and pass: `~/.claude/...`, `$HOME/.config/...`,
`~/Library/...`, `~/AppData/...`, bare `$HOME` and `$HOME/$variable` in shell
code, placeholder users (`/Users/USERNAME`, `/Users/dev`, `/home/runner`), and
`<HOME>/...`. A generic location that spells the username still leaks.

The full name is read from `git config user.name` at run time; nothing in the
plugin stores it, and no message prints it. It is matched in any case, middle
names optional, joined by spaces, dots, dashes, underscores or nothing (the
home-directory form). A one-word `user.name` is a handle and guards nothing.
`LICENSE` files are exempt.

Full rules: `skills/path-privacy/references/patterns.md`.

## Install

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install path-privacy@fb-claude-skills
```

The PreToolUse and SessionStart hooks are active in every repo once the plugin
is installed. The git hooks are per repo:

```
# from inside the repo you want to protect:
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh"

# to remove them again:
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh" --uninstall
```

The installer writes `.git/hooks/pre-commit` and `.git/hooks/commit-msg`
wrappers. An existing hook is kept as `<hook>.local` and runs first.

## Skills

| Skill | Description |
|-------|-------------|
| `path-privacy` | Scan files, directories, staged changes or strings for external paths; find the full name; scrub with a suggestion config; install, remove and inspect the git hooks |

Trigger phrases: "scan for path leaks", "check for leaked paths", "are we
leaking my home path", "is my name in this repo", "scrub external paths",
"install path-privacy hooks", "find absolute paths in this repo", "remove $HOME
references", "block path leaks".

Invocation examples:

```bash
# sweep the working tree for external paths
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/find-external-paths.sh" -d .

# list tracked lines carrying the full name, as file:line (never the name itself)
git grep -n -i -E "$(bash -c '. "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/_name_guard.sh"; pp_name_regex .')" | cut -d: -f1,2

# which repos under a root have the gate, at what version
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh" --doctor <root>
```

## Which repos are actually protected?

Hooks live in `.git/`, so they are per repo, uncommittable and installed by
hand. `--doctor` is the inventory: per repo and per hook it reports the version
stamp, `fail-closed` vs `FAILS OPEN`, whether the frozen scanner path still
resolves, and `not installed`. Exit 1 if anything needs attention. It is
read-only and needs an explicit root to sweep more than the current repo.

`FAILS OPEN` means a pre-0.6.0 wrapper, which exits 0 when the scanner is
missing. Re-run the installer in that repo.

## Keeping installed hooks current

The wrapper in `.git/hooks` locates the plugin, so a plugin update cannot
rewrite it; its logic is frozen at install. The scripts it calls
(`git-pre-commit`, `git-commit-msg`, the scanner, the name guard) are resolved
from the newest installed plugin version on every commit, so most changes,
including the name guard, need no reinstall.

When the wrapper template itself changes, the SessionStart hook regenerates the
wrapper in place, touching only files that carry the plugin's own stamp. A
wrapper newer than the running plugin is left alone and reported. If the
refresh fails (read-only `.git`, `core.hooksPath` elsewhere), the hook says so.

## How to remove a leak

A block prints `<file>:<lineno>: <match>` (or `<file>:<lineno>` for the name).
Replace the path with a repo-relative reference or a generic name, and the name
with the GitHub handle or `<author>`. Re-stage and re-commit with a vague
message ("docs: minor edits"). Never `--no-verify`.

For leaks already in history, see
`skills/path-privacy/references/scrub_workflow.md`.

## Dependencies

- `ripgrep` (`brew install ripgrep`)
- `jq`
- `git`
- `bash` (3.2 or later)
