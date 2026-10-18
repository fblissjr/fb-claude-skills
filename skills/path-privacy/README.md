# path-privacy

<!-- path-privacy: skip-file -->

last updated: 2026-10-18

Keeps personal identifiers out of committed artifacts in **Google Antigravity** (`agy` CLI v1.4.0+ and Antigravity App v2.24.0+) and **Claude Code**.

Two rules:
1. **Every path written into the repo is relative to the repo root.**
2. **The git `user.name` full name is never written at all** (the GitHub handle and git email are fine).

The plugin fixes what it safely can in place and blocks the rest. It does not load anything into context unless it has something to tell you.

## What it does

| Where | Behaviour |
|---|---|
| **PreToolUse**, `write_to_file` / `replace_file_content` / `multi_replace_file_content` (and `Write` / `Edit`) | An absolute or `~`/`$HOME` spelling of a path **inside** the repo is rewritten to repo-relative before the write lands (`overwrite` on Antigravity / `updatedInput` on Claude Code, with no permission escalation), plus one line of context saying so. A path **outside** the repo, or the full name, blocks the call (`{"decision": "deny"}` on Antigravity / `exit 2` on Claude Code). Conversation artifacts (`artifactDirectoryPath` / `/.gemini/antigravity*/brain/`) and gitignored files are exempted |
| **PreToolUse**, `run_command` (and `Bash`) | A `git`/`gh` command containing the full name is blocked; home-directory prefixes are masked first, so a home path that spells the name does not count. Commit, tag and PR message text (heredoc bodies included) and new branch names are scanned for external paths |
| **git `pre-commit`** | Staged files are scanned whole for external paths. **Added** lines are scanned for the full name, so a name already in history does not block unrelated commits |
| **git `commit-msg`** | Message and current branch name, for both. A `Signed-off-by:` trailer from `git commit -s` is allowed |
| **SessionStart** | Refreshes this repo's frozen hook wrappers when the template changes. Emits `{}` (Antigravity) or nothing (Claude Code) in a repo whose gate is installed and current; says once per repo when the gate is missing |

Every block message ends with the one rule no hook can enforce: the correction is routine, and commit messages, branch names and changelog entries do not mention it.

### Examples in Antigravity & Claude Code

1. **In-Repo Absolute Path Auto-Rewrite (`write_to_file` / `replace_file_content` / `multi_replace_file_content` & `Write` / `Edit`)**:
   - The agent tries to write `/Users/<your-name>/<repo>/src/index.ts` or `~/<repo>/src/index.ts` into `README.md`.
   - `path-privacy-pre-tool-use.sh` intercepts the tool call and returns `{"decision": "allow", "overwrite": {...}}` in Antigravity or `hookSpecificOutput.updatedInput` in Claude Code, rewriting the path to `src/index.ts` before the file is written.
2. **External or Unbracketed Path Block (`deny` / `exit 2`)**:
   - The agent tries to write `/Users/<your-name>/other-repo/foo.py`, `~/code/secret-project`, or an unbracketed `/home/user/xyz` into a tracked file.
   - `path-privacy-pre-tool-use.sh` blocks the call with the exact file and line number, instructing the agent to use a repo-relative path, `<HOME>/...`, `/Users/<user>/...`, or a generic description.
3. **Commit / PR Message & Branch Guard (`run_command` & `Bash`)**:
   - The agent runs `git commit -m "Ported from ~/other-repo"` or `git checkout -b fix/Users/jsmith/bug`, or includes your `git config user.name` full name in a `gh pr create --body ...` command.
   - `path-privacy-pre-tool-use.sh` blocks the shell call before `git` or `gh` executes.

### What counts as a leak

A path leaks when it resolves outside the repo root and says something about this machine or external directories:
- `~/code/secret-project`, `$HOME/development/OtherRepo`
- `/Users/<your-name>/...`, `/home/<your-name>/...`
- Unbracketed user paths such as `/home/user/xyz`, `/Users/dev/project`, or `/Users/alice/app` (blocked so LLM-sanitized paths that still carry real project directory names are caught)
- The dash-joined `-Users-<your-name>-...` form in per-project and scratch directories

These name nothing and pass:
- Repo-relative paths (`skills/path-privacy/plugin.json`)
- Tool config locations: `~/.gemini/...`, `~/.claude/...`, `$HOME/.config/...`, `~/Library/...`, `~/AppData/...` (unless the path still spells the machine's username)
- Bare `$HOME` and `$HOME/$variable` in shell code
- Explicit angle-bracket or variable placeholders: `<HOME>/...`, `/Users/<user>/...`, `/home/<username>/...`, `/Users/$USER/...`
- Non-human OS/CI system accounts: `/Users/Shared/...`, `/home/linuxbrew/...`, `/home/runner/...`, `/home/ubuntu/...`

The full name is read from `git config user.name` at run time; nothing in the plugin stores it, and no message prints it. It is matched in any case, middle names optional, joined by spaces, dots, dashes, underscores or nothing (the home-directory form). A one-word `user.name` is a handle and guards nothing. `LICENSE` files are exempt.

Full rules: [skills/path-privacy/references/patterns.md](skills/path-privacy/references/patterns.md).

## Install

### 1A. Install in Antigravity CLI (`agy`) & App

Plugins installed under `~/.gemini/config/plugins/` are active in both **Antigravity CLI (`agy`)** and **Antigravity App (`v2.24.0+`)**.

```bash
# Install directly from GitHub (no manual git clone needed)
agy plugin install https://github.com/fblissjr/fb-gemini-plugins/tree/main/skills/path-privacy

# Or install from a local checkout
agy plugin install ./skills/path-privacy

# Validate the plugin manifest, skill, and hooks
agy plugin validate ./skills/path-privacy --strict
```

In the `agy` interactive TUI, you can also run `/plugin`, switch to **Discover**, and select **+ Install from local directory...**.

### 1B. Install in Claude Code

```bash
# From the fb-claude-skills marketplace
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install path-privacy@fb-claude-skills

# Or load directly from a local checkout
claude --plugin-dir ./skills/path-privacy
```

### 2. Install Per-Repo Git Hooks (`pre-commit` & `commit-msg`)

The `PreToolUse` and `SessionStart` hooks run automatically in every git workspace once the plugin is installed in Antigravity or Claude Code. To also gate commits made outside the agent, install the git hooks in your repository (or invoke `/path-privacy:path-privacy` in Claude Code / `/path-privacy` in Antigravity):

```bash
# From inside the repo you want to protect (works from either install root or checkout):
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/install-git-hooks.sh

# Or target another repo with -C:
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/install-git-hooks.sh -C <repo-path>

# To remove them again:
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/install-git-hooks.sh --uninstall
```

The installer writes `.git/hooks/pre-commit` and `.git/hooks/commit-msg` wrappers (`ver=t5`). An existing hook is preserved as `<hook>.local` and runs first.

## Skill & CLI Usage

| Skill | Description |
|-------|-------------|
| `path-privacy` | Scan files, directories, staged changes or strings for external paths; find the full name; scrub with a suggestion config; install, remove and inspect the git hooks; keep Antigravity and Claude Code plugin copies aligned |

Trigger phrases in Antigravity App or CLI: *"scan for path leaks"*, *"check for leaked paths"*, *"are we leaking my home path"*, *"is my name in this repo"*, *"scrub external paths"*, *"install path-privacy hooks"*, *"find absolute paths in this repo"*, *"remove $HOME references"*, *"block path leaks"*.

Direct script examples:

```bash
# Sweep the working tree for external paths
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/find-external-paths.sh -d .

# Scan only staged files
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/find-external-paths.sh --staged

# List tracked lines carrying the full name, as file:line (never prints the name itself)
git grep -n -i -E "$(bash -c '. ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/_name_guard.sh; pp_name_regex .')" | cut -d: -f1,2

# Check which repos under a root have the git commit gate and verify harness alignment
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/install-git-hooks.sh --doctor <root>

# Verify or synchronize peer checkouts and installed ~/.gemini + ~/.claude caches
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/sync-peer.sh --check
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/sync-peer.sh --apply --peer <peer-plugin-dir>
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/sync-peer.sh --install

# Preview working-tree replacements from .path-privacy.local.json (add --apply to write)
bash ~/.gemini/config/plugins/path-privacy/skills/path-privacy/scripts/scrub-paths.sh -d .
```

## Which repos are actually protected?

Git hooks live in `.git/`, so they are per repo, uncommittable and installed by hand. `--doctor` is the inventory: per repo and per hook it reports the version stamp (`t5`), `fail-closed` vs `FAILS OPEN`, whether the frozen scanner path still resolves, and `not installed`, as well as whether installed Antigravity (`~/.gemini/...`) and Claude Code (`~/.claude/plugins/cache/...`) copies on the machine are aligned. Exit 1 if anything needs attention. It is read-only and needs an explicit root to sweep more than the current repo.

`FAILS OPEN` means a pre-0.6.0 wrapper, which exits 0 when the scanner is missing. Re-run the installer in that repo.

## A global `core.hooksPath`

A global `core.hooksPath` replaces `.git/hooks` in every repo. The installer refuses to write into it, since that would gate every repo on the machine. One kind of global hooks directory is the exception: a dispatcher whose hooks each run the repo's own `<git-common-dir>/hooks/<name>`. Such a dispatcher declares itself with a file named `.chains-to-repo-hooks`, and needs executable `pre-commit` and `commit-msg` hooks. When both are present, the installer, `--doctor` and the `SessionStart` check use the repo's own hooks directory.

## Keeping installed hooks and dual harnesses aligned

The plugin directory is a **unified dual-manifest bundle**: it carries both Antigravity's root `plugin.json` + `hooks.json` and Claude Code's `.claude-plugin/plugin.json` + `hooks/hooks.json`, while sharing 100% of `hooks/*.sh`, `skills/path-privacy/scripts/*`, and `skills/path-privacy/references/*`.

- **At commit time (`ver=t5`)**: The wrapper in `.git/hooks/` scores all readable candidate scripts across both `~/.gemini/...` and `~/.claude/plugins/cache/...` by `(wrapper_template_version, plugin_semver, is_frozen)` and executes the newest installed copy on the machine.
- **At session start**: When the wrapper template changes, `SessionStart` refreshes `.git/hooks/` in place. If one harness's installed plugin is older than the repo's hooks, `SessionStart` identifies which harness is lagging and instructs you to run `sync-peer.sh --install`.
- **Across repositories and caches (`sync-peer.sh`)**: Run `sync-peer.sh --apply --peer <dir>` to make a peer repository's `path-privacy` directory 100% byte-identical, and `sync-peer.sh --install` to update both `~/.gemini/` and `~/.claude/` installed caches simultaneously.

## How to remove a leak

A block prints `<file>:<lineno>: <match>` (or `<file>:<lineno>` for the name). Replace the path with a repo-relative reference, `<HOME>/...`, `/Users/<user>/...`, or a generic name, and replace the full name with the GitHub handle or `<author>`. Re-stage and re-commit with a vague message (`docs: minor edits`). Never `--no-verify`.

For leaks already in history, see [skills/path-privacy/references/scrub_workflow.md](skills/path-privacy/references/scrub_workflow.md).

## Dependencies

- `ripgrep` (`brew install ripgrep`)
- `jq`
- `git`
- `bash` (3.2 or later)
