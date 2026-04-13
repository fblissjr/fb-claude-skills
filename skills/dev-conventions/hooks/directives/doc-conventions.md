# trigger: docs
## Documentation conventions (auto-loaded)
- Last updated date (YYYY-MM-DD) at top of every doc/README you create or modify.
- Lowercase filenames with underscores. No spaces, no camelCase.
- Document the "why": decisions, alternatives considered, not just what was built.
- Internal docs in ./internal/ (gitignored). Session logs in ./internal/log/log_YYYY-MM-DD.md.
- ALWAYS update session log before finishing a session or iteration of work.
- If packages were added, removed, or version-bumped during the session, include a "Dependency changes" section in the session log (package, old version, new version, action). Source from `git diff pyproject.toml` / `git diff package.json`. Never create a separate dependency manifest file.
- For full doc conventions, invoke /dev-conventions:doc-conventions.
