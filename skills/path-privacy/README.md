# path-privacy

<!-- path-privacy: skip-file -->

last updated: 2026-07-26

Stops absolute and home-relative filesystem paths from leaking into committed artifacts. One rule: every path written into the repo must be relative to the repo root.


## Which repos are actually protected?

Hooks live in `.git/`, so they are per-repo, uncommittable, and installed by
hand. Nothing tracks where they are. `--doctor` is that inventory:

```bash
# this repo
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh" --doctor

# every git repo under a root you name
bash "${CLAUDE_PLUGIN_ROOT}/skills/path-privacy/scripts/install-git-hooks.sh" --doctor <root>
```

Per repo and per hook it reports the version stamp, `fail-closed` vs
`FAILS OPEN`, whether the frozen scanner path still resolves, and `not
installed` when a hook is missing. Exit 1 if anything needs attention. It is
read-only and requires an explicit root — it will not sweep your home
directory on its own.

`FAILS OPEN` means a pre-0.6.0 wrapper: those exit 0 when the scanner is
missing, so the gate reports success on every commit while doing nothing.
Re-run the installer in those repos.

## Keeping installed hooks current

A plugin update refreshes the **scanner** your hooks call, but never the
**wrapper** itself. That is structural, not an oversight: the wrapper is the
thing that *locates* the plugin, so the plugin cannot rewrite it. Its logic is
baked in when you run `install-git-hooks.sh` and stays frozen until you run it
again, which means a repo can carry a wrapper whose bugs were fixed several
releases ago.

Three things narrow that window:

- Since 0.6.0 the generated wrapper carries a `# path-privacy:wrapper-version`
  stamp, and the SessionStart hook compares it against the installed plugin —
  one notice, in the repo where it matters. Pre-0.6.0 wrappers have no stamp
  and are reported as `pre-0.6.0`.
- Since 0.7.0 the wrapper also says so itself, on stderr at commit time. That
  reaches you when you commit from a plain terminal with no session open.
- Since 0.7.3 all three staleness checks — the SessionStart notice, the
  wrapper's own self-report, and `--doctor` — establish which side is behind
  before advising anything, from one shared comparison in
  `scripts/_version_compare.sh`. A wrapper can be *newer* than the plugin
  (install the hooks from a source checkout, then run against a lagging
  installed copy), and in that state re-running the installer regenerates the
  wrapper from the older plugin and downgrades a working gate. The ahead case
  gets its own message saying the gate is fine and not to reinstall, and
  `--doctor` annotates it rather than exiting non-zero. "Newer" has to be
  positively verified: a stamp that is not plainly numeric — including the
  `unknown` written when `plugin.json` was unreadable at install time — is
  never treated as newer, so it gets the refresh advice, which is idempotent.
- Since 0.7.0 a marketplace-installed wrapper re-resolves to the **newest**
  cached version of the plugin on every run, rather than only when its frozen
  path has been deleted. Before that it kept running the superseded scanner
  for the whole ~14-day cache-retention window after an update.

```bash
# in any repo the notice fires for
<plugin-dir>/skills/path-privacy/scripts/install-git-hooks.sh
```

It deliberately does **not** rewrite the hook for you. Silently editing a file
in someone's `.git/hooks` is the kind of surprise a privacy gate should never
spring — and the 0.6.0 release fixed four ways that installer could damage a
repo. Detection is safe; an unattended rewrite of a security gate is not.

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

After expanding `~`, `$HOME`, and `${HOME}`, if the absolute path does NOT live under the current repo root, it is a leak. Repo-relative paths and generic placeholders (`/Users/USERNAME/foo`, `<HOME>/.claude/...`) are not flagged. Per-line `path-privacy: ignore` opts a specific line out. The file-level form, `path-privacy: skip-file`, opts a whole file out when it is the **leading content** of one of the first 30 lines — up to three spaces of indent and a comment introducer (`#`, `//`, `--`, `;`, `<!--`) are allowed before it, and a rationale after it. A mention buried in a sentence, a markdown heading or bullet, or a four-space-indented example is not an opt-out; that is what stops a file from exempting itself just by documenting the escape hatch. Formats without comment syntax (JSON, CSV) have no file-level form — use the per-line marker or gitignore the file. Commit messages and branch names honour only the per-line form — a message cannot exempt itself by quoting one token.

Full pattern reference: `skills/path-privacy/references/patterns.md`.

## How to remove a leak

Pre-commit hook fires, prints `<file>:<lineno>: <match>`, exits 1. Open the file, replace the absolute portion with a repo-relative reference or a generic name. Re-stage, re-commit with a vague message ("docs: minor edits"). Do not announce that a leak was fixed.

For paths already in git history, see `skills/path-privacy/references/scrub_workflow.md`.

## Dependencies

- `ripgrep` (`brew install ripgrep`)
- `jq` (for the SessionStart hook)
- `git`
