# trigger: git
<!-- path-privacy: skip-file -->
## Path privacy (auto-loaded in git repos)

Every path you write into this repo must be relative to the repo root. A path leaks if, after expanding `~` or `$HOME`, it resolves outside that root. Use `./scripts/foo.sh`, or a generic name (`another project`, `<HOME>/.claude/...`).

This is enforced, not advised. A PreToolUse hook blocks leaks in file edits, commit messages, and branch names before they land; pre-commit and commit-msg hooks hard-block at commit time. The block names the offending path and lists the escapes, so none of that needs memorising here. Never bypass with `--no-verify`.

The one rule no hook can catch: **if you fix a leak, do not say so.** Keep it out of commit titles, messages, branch names, and the changelog — vague language only ("docs: minor edits"). Never name what was scrubbed. The guarantee fails the moment the activity is advertised.
