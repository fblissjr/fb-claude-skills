---
name: retire
description: Remove a unit from a repo without leaving references behind - a plugin, package, module, directory, dependency, or feature. Sweeps tracked content for every mention BEFORE the delete, sorts the hits into what must change, what must stay as history, and what reaches users, then names the cascade the removal actually triggers. Use when the user says "retire this plugin", "delete this package", "remove this module", "drop this dependency", "deprecate X", "clean up after removing Y", "is anything still referencing Z", or is about to delete a tracked directory. Deletion-induced breakage is non-local - the files that break are ones nobody touched - so no edit-time check or language server catches it.
metadata:
  last_verified: "2026-08-02"
  review_interval_days: "365"
---

Deleting a unit is the easy half. The references outlive it, and they break in
files nobody opened.

That is the whole reason this needs a procedure rather than care: **the breakage
is non-local.** Removing `apps/foo/` leaves five files broken that were never
edited, so nothing fires — not a language server, not a PostToolUse hook, not a
pre-commit diff check. They only see files that changed.

## Sweep before you delete, not after

Run this first. The output is your work list, and it is much harder to assemble
once the thing is gone and you are grepping from memory.

```bash
git grep -lF -- 'the-name' :/
```

Search the **name**, not the path. Paths appear in links and manifests; the name
appears in prose, commands, and examples, which is where most references hide.
For a unit with a distinct directory, sweep both.

**The `:/` is load-bearing and the `-F` nearly so.** Without `:/` the search is
scoped to your working directory, and the single most likely place to run this is
inside the unit you are about to delete — where it reports a tidy handful of
self-references while every external reference stays invisible. Measured in one
repo: sweeping for a plugin's name from inside its own directory found 12 hits;
from the root, 26. The 14 it missed are the entire point of sweeping.

`-F` matches the name literally. A unit called `foo.js` or `c++-utils` is a
regex that quietly matches things it should not, and a name beginning with `-`
is parsed as an option. `git grep` is used rather than `git ls-files | xargs
grep` because the latter splits on whitespace (a tracked path containing a space
is silently skipped), and on GNU systems runs `grep` with no file operands when
nothing matches, which blocks on stdin instead of reporting clean.

Do not trust a link check for this. "No broken markdown links" is a strictly
weaker property than "nothing names a thing that no longer exists" — a repo can
pass the first cleanly while a dozen sentences still describe the deleted unit as
though it were alive.

## Sort every hit into one of four buckets

The sorting is the skill. Most of the cost of getting this wrong is either
editing something that should have been left alone, or leaving something that
should have been edited.

**Structural — must change.** Manifests, registries, workspace or build config,
dependency lists, indexes and tables of contents, any file whose job is to
enumerate what exists. These are wrong the moment the unit is gone.

**Historical — must NOT change.** Changelogs, design records, postmortems,
"removed in 0.5.0" notes. These describe what was true when written. Rewriting
them destroys the record of what was tried, which is usually the most valuable
thing about them. Add a status header if the staleness would mislead; never edit
the body to pretend the history was different.

**Illustrative — usually change.** Examples that happen to use the unit's name to
teach something unrelated ("name external dependencies generically, like *the
foo DB*"). The lesson does not depend on the name, and a reader who goes looking
for `foo` and finds nothing loses trust in the docs. Swap in a neutral example.

**Third-party — leave.** Instructions about what may exist in *someone else's*
repo: "if your installed config still contains X, delete it." Unaffected by what
you ship, and still correct after the removal. Deleting these strands the people
the instructions were written for.

## Shipped content is a separate, higher bar

Anything inside a published unit's distribution boundary reaches other people. In
a plugin repo that is whatever the marketplace `source` points at; elsewhere it is
whatever the package manifest includes.

Sweep it explicitly and separately. A stale reference in an internal design note
is untidy; the same reference in a shipped skill or README is a defect someone
else has to work around. Check this even when the root sweep looks clean, because
distribution boundaries rarely match directory intuition.

## Name the cascade before you start

A removal is never one delete. Expect all of these, and confirm each:

- the unit's own files
- workspace / build / dependency configuration that names it
- the registry or marketplace entry, **plus a deprecation or rename mapping** so
  installed copies get cleaned up rather than silently orphaned
- every index, table, or list that enumerated it
- documentation that cites it, sorted by the four buckets above
- code that imports it — check this with a language-aware search, not grep alone
- the changelog
- lockfiles, if the unit was a dependency

## Removing something published is a breaking change

If anyone could have installed or depended on it, the version bump is major.
The deprecation mapping exists precisely because that breakage has to be handled
rather than absorbed. Numbering it as a minor release understates what happened
to anyone downstream.

## Verify

```bash
# every remaining hit should be one you deliberately kept
git grep -nF -- 'the-name' :/

# no link, inline or reference-style, points at the removed path
git grep -nE -- '\]\(<path>|\]:[[:space:]]*<path>|href="[^"]*<path>' :/

# nothing still imports it -- extensions, not a hand-listed glob
git grep -nE -- '(import|require|from)[^\n]*the-name' :/
```

Replace `<path>` with the removed path **regex-escaped** — a literal `.` in a
filename otherwise matches any character. The link check deliberately covers
reference-style definitions and `href=` as well as inline links, and searches
every tracked file rather than only `*.md`, because a manifest or registry entry
naming a path is exactly what a removal breaks.

Do not hand-list source extensions in the import check. A glob of
`'*.py' '*.ts' '*.js'` looks complete and silently skips `.tsx`, `.mjs`, `.jsx`,
`.pyi` and `.cjs` — in one repo, 21 tracked files the check never opened.

Then run the repo's own test or lint suite. A removal is done when the suite is
green and every remaining sweep hit falls in the historical or third-party
bucket. **The sweep will not go silent, and should not:** the cascade above
requires a changelog entry naming the retired unit, so a permanently empty result
would mean that entry is missing.

## Report what you deliberately left

Close by listing the references you chose **not** to change and why — the
historical ones, the third-party ones. That list is the difference between "I
missed these" and "I decided these", and without it the next sweep re-litigates
every one of them.
