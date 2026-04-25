# Pattern reference

<!-- path-privacy: skip-file -->

last updated: 2026-04-25

The scanner uses one PCRE2 pattern with a named capture group. A token is a candidate if it matches; whether it is actually a leak is decided by resolving it against the repo root.

## Candidate-path PCRE

The scanner uses two patterns. Both share a named capture group (`path`) that ripgrep extracts via `-or '$path'`.

**Strict (default; used for files and dirs)**

```
(?:^|[^A-Za-z0-9_/])(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))[^[:space:]"'`<>()\[\]\\]*)
```

The left boundary `(?:^|[^A-Za-z0-9_/])` prevents partial matches inside identifiers like `myUsers/...` and avoids false-flagging code where `Users` is part of a longer word.

**Lax (used for `--text` mode with `--lax-boundary`; commit messages and branch names)**

```
(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))[^[:space:]"'`<>()\[\]\\]*)
```

No left boundary. This is what catches branch names like `fix/Users/jamie/path` where the leading `/` of `/Users/` is preceded by a word char (the last letter of the branch prefix). Risk: identifiers like `myfunction/Users/foo` would also match, but in commit-message and branch-name contexts that pattern is exotic.

Both patterns share the same right-side character class: everything that can plausibly be in a filesystem path, excluding shell delimiters and quoting characters. This errs on the side of capturing too much rather than too little; the resolver step trims false positives.

## Resolution

For each candidate `c`:

1. Expand `${HOME}` and `$HOME` to the running user's home.
2. Expand a leading `~/` or bare `~` likewise.
3. If the result is still not absolute (defensive — shouldn't happen given the pattern), anchor against repo root.
4. Normalize: collapse `.` and `..` segments textually. No symlink resolution — content scans must not require the path to exist.
5. If the resolved absolute path equals the repo root or starts with `<repo root>/`, it is repo-internal and skipped. Otherwise, it is a leak.

## Placeholder allowlist

If the path is `/Users/<seg>/...` or `/home/<seg>/...` and `<seg>` is one of the following, it is treated as documentation and skipped:

```
USERNAME, username, USER, user, <USERNAME>, <USER>, <user>, <username>,
me, you, name, NAME, <name>, somebody, $USER, ${USER}, $$USER
```

Tilde paths (`~/...`) and `$HOME`-rooted paths are not subject to placeholder allowlist — they always resolve against the running user's home and almost always end up external. If you genuinely need to document such a path as an example, use the per-line opt-out.

## Per-line opt-out

A line containing the literal token `path-privacy: ignore` is skipped entirely. Examples:

```
# Example: see ~/.claude/agent_state.duckdb (path-privacy: ignore)
```

```python
SAMPLE_PATH = "/Users/jamie/data"  # path-privacy: ignore
```

Use sparingly. Each opt-out is a deliberate decision that this line legitimately needs to mention a path the rule would otherwise reject.

## Skip globs

Mirror of the scan-for-secrets skip set. The scanner ignores the following directories:

```
.git, .hg, .svn, node_modules, __pycache__, .venv, venv,
.mypy_cache, .ruff_cache, .pytest_cache
```

Add your own via the standard ripgrep `.ignore` / `.gitignore` mechanism if needed — the scanner respects them.

## Known false positives

- **URLs that happen to look like paths.** `http://example.com/Users/foo` would match the `/Users/` shape. Mitigation: the pattern requires a non-word, non-slash boundary on the left; `/Users/` inside `://` is preceded by `/`, so it gets pruned. Verified.
- **Regex source itself.** Files documenting regexes for `/Users/` etc. would match themselves. Mitigation: per-line `path-privacy: ignore`, or the scanner's plugin-internal source files use it where required.
- **`$HOMEDIR`, `$HOMEPAGE`, etc.** The pattern requires `\$HOME` followed by `/`, `\b`, or end-of-string, so longer variable names are not matched.

## Edge cases that are NOT handled

- Paths inside base64-encoded content, gzip blobs, or other encoded data. Not in scope; use the literal pass of `scan-for-secrets` if you know the exact string.
- Paths inside binary files. ripgrep skips binaries by default.
- Paths in non-text files that the scanner can't read. Same.
