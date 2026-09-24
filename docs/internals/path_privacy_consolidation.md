last updated: 2026-09-24

# Path-privacy consolidation: a shelved design

**Status: shelved, 2026-09-24. Not built, not installed.** The external-push
gate this design depends on was built and tested in temporary space: 80 tests
passing, and 37 of 38 deliberate code mutations caught by the tests. The owner
then declined to maintain a machine-wide system, and the code was deleted.

**What protects instead**, all settings with no upkeep:
- git uses the GitHub noreply address everywhere;
- GitHub keeps email private and blocks pushes that expose it;
- Claude Code attribution is off in user settings;
- the path-privacy plugin guards home paths and the full name;
- the user-level personal-data hook stays as last patched, frozen.

**Known gap:** GitHub checks only the newest commit in a push, so older
unpushed commits authored with a private address are fixed per repo, by hand,
when that repo is next pushed.

**Trigger to reopen:** a real leak those settings didn't stop. The design and
its measurements below stay as the starting point.

## How this came up

Two systems do the same job, keeping personal identifiers out of repos:

- **path-privacy** (this repo's plugin), whose protection has three parts:
  - a PreToolUse hook that rewrites in-repo absolute paths on Edit and Write,
    blocks external paths and the full name, and scans git and gh command text;
  - per-repo pre-commit and commit-msg git hooks, put in place by an installer
    and nagged about by a SessionStart check;
  - the "a routine correction is never mentioned" rule, carried in its block
    messages.
- **The owner's user-level `~/.claude/hooks/block-personal-data.sh`**, which
  reads a PreToolUse command to guess the repo, then scans the staged diff, the
  diff against HEAD and unpushed commits for private IPs, home paths and
  hostnames.

On 2026-09-24, review and live-fire found that guessing the repo from command
text can't be made complete: newlines, heredocs, `sh -c`, `--git-dir=`,
`GIT_DIR=`, cd chains, and scripts that commit. So the owner approved a
git-level design instead:
- a global `core.hooksPath` dispatcher that chains to each repo's own hooks;
- pre-push as the only blocking gate, enforced only on remotes outside an
  explicit list of the owner's hosts;
- pre-commit and commit-msg warn only;
- a slim PreToolUse guard for bypass flags and gh text arguments.

mrskill is building that in its own session.

## The design, once that gate has proven itself

Merge the two systems into one: path-privacy becomes the git-level gate.

**It drops:**
- its per-repo git hooks, the installer, the SessionStart "no commit gate"
  notice, and the self-refresh machinery, all replaced by the global
  dispatcher;
- scanning commit messages and branch names in Bash command text, the source of
  the full-name false positives fixed in 0.18.2 and 0.18.3. commit-msg and
  pre-push see the real messages and refs.

**It keeps:**
- rewriting in-repo absolute paths to repo-relative ones on Edit and Write. It
  is cheap, never blocks, and fixes the problem at its source;
- scanning `gh pr`/`gh issue` text, which goes to GitHub without passing
  through git;
- the never-mention-the-correction rule in its messages.

**It may change:** blocking external paths and the name in Edit and Write
content could become a notice, since the push gate is authoritative (AGENTS.md
invariant 1c: tier by what is detectable where).

**It absorbs** `block-personal-data.sh`. Its patterns (private IP ranges,
hostnames, mount points, the RFC 1918 block constants to exclude) join the
home-path and full-name patterns in one settings file under `~/.claude/`, and
the separate user-level hook retires.

## The catch: path-privacy is published

Other people who install the plugin don't have the owner's global hooks, so its
checks can't simply be deleted. The merged plugin needs two modes:

- **Machine-wide:** an opt-in install that sets `core.hooksPath` to the
  plugin's dispatcher. The owner's mode.
- **Per-repo:** today's behaviour, for anyone who does not opt in.

The plugin detects which mode is active by a marker in the dispatcher, the same
marker the 2026-09-24 plan already needs so path-privacy recognises a chaining
dispatcher instead of reporting "no commit gate".

## Open questions for when it reopens

- Whether the per-repo mode should simply install the same dispatcher locally,
  giving one code path in two install scopes, rather than keep the current
  hooks.
- Where the owner's host list and patterns live once the plugin owns them, and
  how a published plugin ships an empty, documented default.
- Whether any user-level hook remains once the plugin carries the
  bypass-flag guard.
