# Scrub workflow

<!-- path-privacy: skip-file -->

last updated: 2026-04-25

How to remove leaks discreetly. The privacy guarantee fails the moment the activity is advertised, so all of the following assume "do this quietly".

## Working changes (not yet committed)

The pre-commit hook will block. Steps:

1. Read the hook output: `<file>:<lineno>: <match>`.
2. Open each file, fix the line:
   - If the path points inside the repo, rewrite as a repo-relative reference.
   - If the path points outside the repo, replace with a generic name: "another project", "the upstream repo", "the agent state DB", "SecondRepo".
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

## What never appears anywhere

- The string "leaked" in any commit message, branch name, PR title, changelog entry, or doc.
- The actual leaked path content in any non-gitignored file. Even README example sections.
- A description of the activity in CHANGELOG, release notes, or announcements.

## What is fine

- A short, vague entry in a gitignored file like `internal/log/log_YYYY-MM-DD.md` describing what happened. The directory is gitignored — it stays local.
- An internal note to yourself in a personal todo. Not in the repo.
