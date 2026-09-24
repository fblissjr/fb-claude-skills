# Pattern reference

<!-- path-privacy: skip-file -->

last updated: 2026-09-24

The scanner (`scripts/find-external-paths.sh`) finds candidate paths with one
PCRE2 pattern, then decides per candidate whether it is a leak. The name guard
(`scripts/_name_guard.sh`) is separate and builds its pattern from
`git config user.name` at run time.

## Candidate-path PCRE

Both patterns share a named capture group (`path`) that ripgrep extracts via
`-or '$path'`. `MANGLED` is `-(?:Users|home)-<user>(?=-|\b)`, where `<user>` is
the running user's home-directory name with every non-alphanumeric turned into
`-`; it is left out when that name is a placeholder or shorter than two
characters.

**Strict (default; files and directories)**

```
(?:^|[^A-Za-z0-9_/]|/(?=-(?:Users|home)-))(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b)|MANGLED)(?:[^[:space:]"'`<>()\[\]\\]|<[A-Za-z0-9._-]+>)*)
```

The left boundary prevents partial matches inside identifiers like
`myUsers/...`. The `/` alternative admits the dash-joined form inside a longer
path (`/tmp/claude-501/-Users-<user>-...`).

**Lax (`--text --lax-boundary`; commit messages and branch names)**

The same without the left boundary, so `fix/Users/jamie/path` is caught.

## Deciding a candidate

In order; the first rule that applies decides.

1. A bare prefix (`/Users/`, `/home/`, `~/`) is not a leak.
2. A candidate containing a `<placeholder>` segment is documentation, not a leak.
3. A candidate matching an `allow` prefix in `.path-privacy.local.json` is not a leak.
4. The dash-joined home form is a leak (it matched only because it spells the username).
5. Home-relative forms (`~/`, `$HOME`, `${HOME}`):
   - bare home, or home followed by anything but `/` (`"$HOME"`, `$HOME,`): not a leak
   - home followed by a variable segment (`$HOME/$dir`, `~/$1`): not a leak
   - home followed by a dot-directory, `Library` or `AppData`: not a leak,
     unless the candidate spells the username as a whole token
   - anything else continues to resolution
6. `/Users/<seg>` or `/home/<seg>` where `<seg>` is a placeholder (below): not a leak.
7. Resolve: expand `~` and `$HOME`, collapse `.` and `..` textually (no
   symlinks; content scans must not need the path to exist). Inside the repo
   root: not a leak. Outside: a leak.

## Placeholder users

Compared case-insensitively. Kept in step with the whole-tree audit's list in
`tools/skill-maintainer/src/skill_maintainer/tests.py`:

```
username user <username> <user> me you name <name> somebody $user ${user} $$user
someone someuser foo bar baz test tester example alice bob carol jane john jamie
dev developer youruser yourname shared linuxbrew travis runner vagrant ubuntu ec2-user
```

## Full-name pattern

Built from `user.name` with two or more words (generational suffixes such as
Jr and III dropped first; first and last word at least two characters). For
"Jane Q. Example":

```
(^|[^[:alpha:]])jane[[:space:]._-]*(q\.?[[:space:]._-]*)?example([^[:alpha:]]|$)
```

Applied to lowercased text. Matches "Jane Example", "jane.example",
"JANE-Q-EXAMPLE", "janeexample". Does not match "Janet Example", "Jane
Examples", the handle or the email. Lines starting `Signed-off-by:` are skipped;
files named LICENSE, LICENCE or COPYING (any extension) are skipped.

## Per-line opt-out

A line containing the literal token `path-privacy: ignore` is skipped by the
path scanner. It does not exempt the full name.

```python
SAMPLE_PATH = "/Users/jamie/data"  # path-privacy: ignore
```

## File-level opt-out

A file is skipped by the path scanner, the scrub and both hooks' path checks
when one of its first 30 lines has `path-privacy: skip-file` as its leading
content: at most three spaces of indent, then an optional `#`, `//`, `--`, `;`
or `<!--`, then the token. Free text may follow (`# path-privacy: skip-file --
regex source`). One definition, `scripts/_skip_marker.sh`, serves every shell
consumer; the Python audit keeps a copy, and a test asserts the two agree.

Not a marker, each because it was once a working bypass:

- a mention inside a sentence, or backticked
- `## ...` (a markdown heading) or `* ...` (a bullet)
- four or more spaces of indent (a markdown code block)
- anything inside a fenced code block; a fence closes only with the same
  character in a run at least as long, with nothing after it

`skill-maintain test` additionally asserts that changelogs, skill docs and
plugin READMEs are never exempt, whatever the pattern allows.

## Skip globs

The directory sweep ignores `.git`, `.hg`, `.svn`, `node_modules`,
`__pycache__`, `.venv`, `venv`, `.mypy_cache`, `.ruff_cache` and
`.pytest_cache`, and respects `.gitignore`. It includes dotfiles.

## Known limits

- URLs: `http://example.com/Users/foo` is not matched, because `/Users/` there
  is preceded by `/`.
- `$HOMEDIR`, `$HOMEPAGE`: not matched; `$HOME` must be followed by `/` or a
  word boundary.
- Encoded or binary content: not scanned. Binary files that match are listed
  as unscanned.
