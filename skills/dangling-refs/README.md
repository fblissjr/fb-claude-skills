last updated: 2026-08-02

# dangling-refs

References outlive the things they reference. This plugin is about closing that
gap.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install dangling-refs@fb-claude-skills
```

## Skills

| Skill | Purpose | Invoke |
|---|---|---|
| `retire` | Remove a unit — plugin, package, module, directory, dependency — without leaving references behind | Say "retire this plugin", "remove this package", "is anything still referencing X", or ask before deleting a tracked directory |

## Why this exists

Deleting a unit is the easy half. The hard half is that **the breakage is
non-local**: removing `apps/foo/` leaves references broken in files nobody
edited, so nothing fires. Not a language server, which sees only open files. Not
a `PostToolUse` hook, which sees only edited files. Not a pre-commit diff check,
which sees only the diff. Every one of them is scoped to what changed, and what
changed is not where the damage is.

The origin was a real removal that left five references behind in shipped
content, found by a manual sweep run *after* the deletion had already been
committed. A link check had passed cleanly the whole time, because four of the
five were prose naming the deleted unit rather than links pointing at it.

## What it does and does not do

It is a **procedure**, not a linter, because most of the value is in judgment a
linter cannot exercise. Of those five references, exactly one was mechanically
detectable as a path that no longer resolved. The rest were sentences mentioning
a concept, and no path checker catches those.

The judgment is the sorting: every reference falls into one of four buckets, and
two of them must be left alone. Changelogs and design records describe what was
true when written, and rewriting them destroys the record of what was tried.
Instructions about what may still be sitting in someone else's repo stay correct
after your removal and strand their audience if deleted.

## Relationship to other checks

Complementary to a whole-tree consistency check rather than a replacement. A
check can answer "does any tracked file name a path that does not resolve"; it
cannot answer "should this sentence still exist". Run the skill when removing
something, and let a check catch what leaks through later.

Distinct from `path-privacy`, which enforces that paths resolve *inside the repo
root*. Adjacent rule, opposite failure: that one is about a path resolving
somewhere it should not, this one about a reference resolving nowhere at all.
