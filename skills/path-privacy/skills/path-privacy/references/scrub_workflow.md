# Scrub workflow

<!-- path-privacy: skip-file -->

last updated: 2026-09-24

How to remove leaks discreetly. The privacy guarantee fails the moment the activity is advertised, so all of the following assume "do this quietly".

## Working changes (not yet committed)

The pre-commit hook will block. Steps:

1. Read the hook output: `<file>:<lineno>: <match>`.
2. Open each file, fix the line:
   - If the path points inside the repo, rewrite as a repo-relative reference.
   - If the path points outside the repo, replace with a generic name: "another project", "the upstream repo", "the agent state DB", "SecondRepo".
   - If the line carries the full name, replace it with the GitHub handle or `<author>`.
3. Re-stage with `git add <files>`.
4. Re-commit with a vague message:
   - Good: `docs: minor edits`, `chore: cleanup`, `refactor: simplify`, `docs: refresh`.
   - Bad: anything that names what was removed, or explains that a privacy issue was fixed.
5. Done.

## Newly committed but not yet pushed

You can safely amend or rewrite the local branch.

```
git reset HEAD^                       # uncommit
# fix the files (see above)
git add <files>
git commit -m '<vague message>'
```

Or, if it was the immediately previous commit and the branch is yours alone:

```
# fix the files (see above)
git add <files>
git commit --amend --no-edit          # if message was already vague
git commit --amend -m '<vague>'       # if message also leaked
```

Do not push until clean. Branch name still applies — if the branch itself is named after the leak, rename it: `git branch -m <new-vague-name>`.

## Already pushed (private branch, you control all consumers)

Force-push after rewriting the topic branch:

```
git rebase -i <ancestor-of-bad-commit>
# in the editor, edit the commit, fix the files, continue
git push --force-with-lease
```

Coordinate quietly with anyone who has the branch checked out — give them new instructions in 1:1, not a public message saying "I leaked X".

## Already pushed and shared widely (or in main)

This is a history rewrite. Treat it as a small, focused operation:

1. Use [`git filter-repo`](https://github.com/newren/git-filter-repo) — not `git filter-branch` (deprecated, slow, error-prone).
2. Do it on a topic branch with a vague name (`chore/history-cleanup`).
3. Force-push the rewritten branch. Coordinate consumers privately.
4. Do NOT add a CHANGELOG entry, release note, commit message, or PR description that names the activity. Vague language only.
5. Remember: once committed and pushed, the leaked content has been on a remote and likely in caches and forks. Treat the leaked content (e.g., a leaked private path naming a project you didn't want public) as effectively public. The rewrite limits future visibility, not past.

### `git filter-repo` skeleton

```
# replace exact path
echo 'literal:/Users/jamie/secret-project==>SecondRepo' > replacements.txt
git filter-repo --replace-text replacements.txt

# remove a file entirely
git filter-repo --path internal/leaked.md --invert-paths
```

Run on a clean fresh clone. `git filter-repo` refuses to operate on a repo with uncommitted changes.

## Per-repo suggestion config (optional)

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

A starter template lives at `path-privacy.local.json.example`, beside this file.

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
bash <scripts>/scrub-paths.sh -d .

# Preview a single file
bash <scripts>/scrub-paths.sh -f docs/foo.md

# Preview the staged set (same selection as the pre-commit hook)
bash <scripts>/scrub-paths.sh --staged

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

`<scripts>` is `<plugin-root>/skills/path-privacy/scripts`.

## What never appears anywhere

- The string "leaked" in any commit message, branch name, PR title, changelog entry, or doc.
- The actual leaked path content in any non-gitignored file. Even README example sections.
- A description of the activity in CHANGELOG, release notes, or announcements.

## What is fine

- A short, vague entry in whatever gitignored file this repo keeps local notes in (here, `internal/log/log_YYYY-MM-DD.md`; other repos differ) describing what happened. It stays local because that file is gitignored.
- An internal note to yourself in a personal todo. Not in the repo.
