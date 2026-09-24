---
name: retire
description: Remove a unit from a repo without leaving references behind - a plugin, package, module, directory, dependency, or feature. Sweeps tracked content for every mention BEFORE the delete, sorts the hits into what must change, what must stay as history, and what reaches users, then names the cascade the removal actually triggers. Use when the user says "retire this plugin", "delete this package", "remove this module", "drop this dependency", "deprecate X", "clean up after removing Y", "is anything still referencing Z", or is about to delete a tracked directory. Deletion-induced breakage is non-local - the files that break are ones nobody touched - so no edit-time check or language server catches it.
---

Deleting a unit is the easy half. The references outlive it, and they break in
files nobody opened: removing `apps/foo/` leaves files broken that were never
edited, so nothing fires — not a language server, not a PostToolUse hook, not a
pre-commit diff check. They only see files that changed.

<sweep>
Sweep before the delete. The output is the work list, and it is much harder to
assemble once the thing is gone and you are grepping from memory.

```bash
git grep -lF -- 'the-name' :/
```

Search the name, not only the path. Paths appear in links and manifests; the
name appears in prose, commands, and examples, which is where most references
hide. For a unit with a distinct directory, sweep both.

`:/` roots the search at the repo top. Without it the search is scoped to the
working directory, and the most likely place to run this is inside the unit
being deleted, where it reports a tidy handful of self-references while every
external reference stays invisible.

`-F` matches the name literally. A unit called `foo.js` or `c++-utils` is a
regex that quietly matches things it should not, and a name beginning with `-`
is parsed as an option. `git grep` beats `git ls-files | xargs grep`, which
splits on whitespace (a tracked path containing a space is silently skipped)
and on GNU systems runs `grep` with no file operands when nothing matches,
blocking on stdin instead of reporting clean.

A link check is no substitute. "No broken markdown links" is a strictly weaker
property than "nothing names a thing that no longer exists": a repo can pass
the first while a dozen sentences still describe the deleted unit as though it
were alive.
</sweep>

<buckets>
Sort every hit into one of four buckets. The sorting is the skill: the cost of
getting this wrong is editing what should have been left alone, or leaving what
should have been edited.

- **Structural — must change.** Manifests, registries, workspace or build
  config, dependency lists, indexes and tables of contents, any file whose job
  is to enumerate what exists. These are wrong the moment the unit is gone.
- **Historical — must not change.** Changelogs, design records, postmortems,
  "removed in 0.5.0" notes. They describe what was true when written, and
  rewriting them destroys the record of what was tried. Add a status header if
  the staleness would mislead; leave the body as written.
- **Illustrative — usually change.** Examples that use the unit's name to teach
  something unrelated ("name external dependencies generically, like *the foo
  DB*"). The lesson does not depend on the name, and a reader who goes looking
  for `foo` and finds nothing loses trust in the docs. Swap in a neutral example.
- **Third-party — leave.** Instructions about what may exist in someone else's
  repo: "if your installed config still contains X, delete it." Still correct
  after the removal; deleting them strands the people they were written for.

Shipped content is a higher bar. Anything inside a published unit's
distribution boundary (in a plugin repo, whatever the marketplace `source`
points at; elsewhere, whatever the package manifest includes) reaches other
people. Sweep it separately, even when the root sweep looks clean, because
distribution boundaries rarely match directory intuition: a stale reference in
an internal note is untidy, the same reference in a shipped skill or README is
a defect someone else has to work around.
</buckets>

<cascade>
A removal is never one delete. Name the cascade before starting, and confirm
each item:

- the unit's own files
- workspace, build and dependency configuration that names it
- the registry or marketplace entry, plus a deprecation or rename mapping so
  installed copies get cleaned up rather than silently orphaned
- every index, table, or list that enumerated it
- documentation that cites it, sorted by the buckets above
- code that imports it, checked with a language-aware search, not grep alone
- the changelog
- lockfiles, if the unit was a dependency

If anyone could have installed or depended on the unit, the removal is a
breaking change and the version bump is major. The deprecation mapping exists
because that breakage has to be handled rather than absorbed.
</cascade>

<verify>
```bash
# every remaining hit should be one you deliberately kept
git grep -nF -- 'the-name' :/

# no link, inline or reference-style, points at the removed path
git grep -nE -- '\]\(<path>|\]:[[:space:]]*<path>|href="[^"]*<path>' :/

# nothing still imports it -- extensions, not a hand-listed glob
git grep -nE -- '(import|require|from)[^\n]*the-name' :/
```

Replace `<path>` with the removed path regex-escaped, since a literal `.` in a
filename otherwise matches any character. The link check covers
reference-style definitions and `href=` as well as inline links, and searches
every tracked file rather than only `*.md`, because a manifest or registry
entry naming a path is exactly what a removal breaks.

Leave source extensions out of the import check. A glob of `'*.py' '*.ts'
'*.js'` looks complete and silently skips `.tsx`, `.mjs`, `.jsx`, `.pyi` and
`.cjs`.

Then run the repo's own test or lint suite. The removal is done when the suite
is green and every remaining sweep hit falls in the historical or third-party
bucket. The sweep will not go silent, and should not: the cascade requires a
changelog entry naming the retired unit, so an empty result means that entry
is missing.
</verify>

<report>
Close by listing the references deliberately left unchanged and why: the
historical ones, the third-party ones. That list is the difference between "I
missed these" and "I decided these", and without it the next sweep
re-litigates every one of them.
</report>
