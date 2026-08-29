---
name: path-privacy
description: >-
  Enforces a single rule: every path in repo content must be relative to the repo root.
  Anything resolving outside the repo is a leak: other repos on disk, absolute
  home-directory paths under /Users or /home, tilde paths, and $HOME-based paths.
  Ships a SessionStart directive plus
  pre-commit and commit-msg git hooks that hard-block. Use when user says
  "scan for path leaks", "check for leaked paths", "are we leaking my home path",
  "scrub external paths", "install path-privacy hooks", "find absolute paths in this repo",
  "remove $HOME references", "block path leaks", "audit before commit", "privacy scan paths".
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
- `<HOME>/.claude/...`, `the shared state DB` (generic reference)

For external dependencies, name them generically: "another project", "SecondRepo", "the shared state DB", `<HOME>/.claude/...`. Never paste an actual absolute path.

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
| Check this repo's gate | `... install-git-hooks.sh --doctor` | Read-only. Reports version, fail-open/fail-closed, and whether the gate is installed at all |
| Check many repos | `... install-git-hooks.sh --doctor <root>` | Same, for every git repo under `<root>`. Requires an explicit root — it never sweeps your home directory on its own |

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}` when the plugin is installed via the marketplace, or `skills/path-privacy` when running from a checkout of fb-claude-skills.

## How findings look

Each finding is one line: `<file>:<lineno>: <matched-token>`. After all findings, a one-line remediation hint. Exit code is 1 on any finding, 0 when clean.

## Per-line opt-out

A line containing the literal token `path-privacy: ignore` is skipped by the scanner. Use sparingly — only on lines that are themselves examples or placeholders that legitimately need to mention an external-looking path (e.g., the regex source, a doc snippet showing what the rule catches).

## File-level opt-out

A file is skipped entirely — by the scanner, the scrub, and both hooks — when one of its **first 30 lines** has the opt-out marker as that line's **leading content**: at most three spaces of indent, an optional comment introducer, then the token. Anything after the marker on that line is free text, so prefer stating why — write it as `# path-privacy: skip-file -- regex source, every pattern here looks like a leak`, at the start of a line.

Accepted introducers are `#`, `//`, `--`, `;`, and `<!--`. This is for files that are *about* the rule: the scanner's own regex source, this skill, the pattern catalogs.

**A file that merely mentions the marker is not exempt**, and the restrictions are narrower than they first look because each one was reached by a real bypass. `##` is excluded because it is an ordinary markdown heading; `*` because it is a bullet; four spaces of indent because that is markdown's own boundary for a code block, i.e. a document *demonstrating* the marker. All three were working opt-outs at one point, verified by landing a real commit carrying a home path through the installed pre-commit hook.

One definition, `scripts/_skip_marker.sh`, is shared by all four shell consumers — scanner, scrub, and both hooks — so it cannot be fixed in one and left broken in the others. The Python audit keeps a deliberate copy, because it must run in repos where this plugin is not installed; a test asserts the two accept the same strings, which is the only thing that makes a copy safe.

**A marker inside a fenced code block does not count either.** That one cannot be expressed as a pattern — an example line inside ``` is byte-identical to a real marker — so the check carries fence state across the window instead of testing each line alone. Documentation can therefore show the marker in a fence, which is how documentation should show it. Fences follow markdown's own rules: a fence closes only with a run of the same character, at least as long as the one that opened it, with nothing but blanks after — so a `~~~` line inside a ``` block, or a shorter run inside a longer one, is content, not a way out of the block. (An earlier release claimed fence tracking was impossible; a later one tracked fences but let either character close either block, which reopened the same hole.)

**None of that is the last line of defence, and it should not be treated as one.** `skill-maintain test` asserts that changelogs, skill docs, and plugin READMEs are never file-level exempt *by any route* — including routes nobody has thought of yet. Those are the file classes this keeps happening to, and the assertion holds whatever the pattern does. Quoting the marker inline with backticks, as this paragraph does, is inert regardless.

Three limits worth knowing:

- **Commit messages and branch names cannot use it.** They are scanned as a string with the marker check off, so quoting one token cannot exempt a message from the gate. Use `path-privacy: ignore` on the offending line instead.
- **Formats with no comment syntax have no file-level opt-out.** JSON and CSV cannot put the marker at the head of a line, and widening the rule to admit a JSON key prefix would reopen it to every YAML value and config string. Use per-line `path-privacy: ignore`, or gitignore the file — which is the right answer for a data file genuinely full of real paths.
- **The marker must already be on disk to cover an Edit.** An Edit sends only the replacement fragment, so a marker at the top of the file is not in the payload; the write blocker reads it from the target file instead. A brand-new file has no disk copy, so there the marker is read from the content being written — which means it has to be in that content's first 30 lines.

## Checking that the gate is actually there

Hooks live in `.git/`, so they are per-repo, uncommittable, and installed by hand. Nothing tracks which repos have them. `--doctor` is that inventory:

```bash
bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh --doctor
bash <plugin-root>/skills/path-privacy/scripts/install-git-hooks.sh --doctor <root>
```

It reports, per repo and per hook: the version stamp (`<unstamped, pre-0.6.0>` if absent), `fail-closed` vs `FAILS OPEN`, whether the frozen scanner path still resolves, and `not installed` when the hook is missing. Exit 1 if anything needs attention, so it is scriptable.

Read `FAILS OPEN` as urgent: those wrappers exit 0 when the scanner is missing, so the gate reports success on every commit while doing nothing. Re-run the installer in that repo to replace it.

**A wrapper is never updated by a plugin update.** It is the thing that *locates* the plugin, so the plugin cannot rewrite it. A plugin update refreshes the scanner the wrapper calls; the wrapper's own logic stays frozen at install time until you re-run `install-git-hooks.sh`. Both the SessionStart hook and the wrapper itself say so when they notice a mismatch.

## Per-repo suggestions (optional)

Drop a `.path-privacy.local.json` at the repo root to enrich
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

**Gitignore it first, then create it.** In that order. The file is by
definition a list of your absolute paths, so until it is ignored the PreToolUse
hook blocks every write to it — including the first one. Append the filename to
`.gitignore`, then copy the template.

Each entry's `match` is a literal substring (not a regex); `suggest` is the
text that replaces it. Entries are auto-sorted longest-match-first so the
most specific entry wins regardless of how you order them. Requires `jq`;
silently no-ops if `jq` is missing or the file is malformed.

**Start with an empty `suggest` mapped to your repo's own absolute prefix.** An
empty `suggest` deletes the matched text outright, rewriting an absolute in-repo
path into a genuinely repo-relative one — which is exactly what the rule asks
for, and the single highest-value entry in most configs. It is supported
deliberately; only an empty `match` is skipped.

That entry affects `scrub-paths.sh` only, never the scanner: a path inside the
repo is not a leak and never appears as a finding in the first place. The two
consumers share one config but match different sets — the scanner uses it to
annotate leaks, the scrub uses it to rewrite text.

To use a config file at a non-default path, pass `--config <path>` to the
scanner.

A starter template lives at `references/path-privacy.local.json.example`.

### `allow`: exempting a path instead of rewriting it

A suggestion rewrites the text. That is right for prose and comments and wrong
for anything runnable, because the rewritten form has to still work. The case
that forces the distinction: a hook command containing `D="$HOME/.impeccable"`.
The path names no user and reveals no machine layout, but substituting a
placeholder into it makes the hook create a directory literally called
`<HOME>`.

For that shape, list the path under `allow` and it is exempted untouched:

```json
{
  "allow": [
    "$HOME/.impeccable",
    {"prefix": "~/.cursor/agents/", "_why": "generic, names no user"}
  ]
}
```

Entries are matched as a **prefix, anchored at the start** of the candidate,
never as a substring anywhere on the line. Anchoring is the whole safety
property: a substring rule would let an allowed path appearing later in a line
exempt a real leak earlier in it, which is the class the gate exists to catch.
Prefix matching also widens usefully on its own — allowing `$HOME/.impeccable`
covers everything beneath it and nothing else under `$HOME`.

Entries are literal matched text rather than resolved paths, so `~/.cursor/`
and `$HOME/.cursor/` are separate and both need listing if both appear.

**Reach for `allow` only when a rewrite would break something.** It is for
generic tool-config dot-directories. A path that names a *project* — another
checkout on your disk — is the thing being guarded against; rewrite that by
hand.

Both consumers honour the list. `scrub-paths.sh` refuses to load any
suggestion whose `match` overlaps an allow prefix in either direction, and
says which two entries collided. Otherwise the config would hold two
contradictory claims about one path and the scrubber, the consumer that
actually rewrites files, would act on the wrong one.

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

**Do not configure a match for the shell HOME variable in a repo containing
shell scripts.** Substring replacement has no idea it is inside code: a live
variable reference becomes a literal placeholder and the script breaks. The
scanner still flags those; fix them by hand. The shipped template omits these
forms on purpose.

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
