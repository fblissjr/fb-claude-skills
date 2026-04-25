# trigger: git
<!-- path-privacy: skip-file -->
## Path privacy (auto-loaded in git repos)

Single rule: every path you write into the repo must be relative to the repo root.

A path "leaks" if, after expanding `~`, `$HOME`, or `${HOME}`, it resolves to an absolute path that does NOT live under the current repo root. This applies to ALL of the following: code, comments, markdown, docs, commit titles, commit messages, branch names, changelog entries, and any other text that ends up in the repo.

Examples that leak: `~/development/SomeRepo/foo`, `~/.claude/plans/<plan-name>.md`, `/Users/<your-name>/code/x`, `/home/<your-name>/code/x`, `$HOME/...`. Replace these with one of:
- A repo-relative reference (`./scripts/foo.sh`).
- A generic name (`another project`, `SecondRepo`, `the agent-state DB`, `<HOME>/.claude/...`).

Discretion when fixing leaks: if you find yourself removing or working around a leak, the activity itself stays out of branch names, commit titles, commit messages, the changelog, and repo content. Vague language only ("docs: minor edits", "chore: cleanup"). Do NOT write that you fixed a leak. Do NOT name what was scrubbed. The privacy guarantee fails the moment the activity is advertised.

The pre-commit and commit-msg git hooks will hard-block leaks. Do not bypass with `--no-verify`. Fix the path, re-stage, re-commit.

For a one-off line that legitimately needs to mention an external-looking path (regex source, doc example), append the literal token `path-privacy: ignore` to that line. Use sparingly.
