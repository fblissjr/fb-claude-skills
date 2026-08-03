---
name: init
description: >-
  Scaffold dev conventions into a repo's own files, once, instead of broadcasting
  them every session -- detects the stack, skips ground the repo already covers,
  writes tailored convention lines into CLAUDE.md or .claude/rules/, then the
  plugin's ambient blocks go silent for this repo automatically. Use when the user
  says "set up dev conventions", "scaffold conventions", "init conventions",
  "write the conventions into this repo", "make the conventions local", or
  "/dev-conventions:init". Also the answer when the SessionStart blocks keep
  loading and the user wants them owned locally instead.
argument-hint: "[target file, optional]"
metadata:
  last_verified: "2026-08-03"
---

# Scaffold dev conventions into this repo

Broadcast prose is generic, paid every session, unownable by the repo, and
coupled to plugin updates. Scaffolded prose is tailored once, owned by the
repo, versioned in git, and reaches every collaborator's Claude through normal
context loading -- including people who never installed this plugin. This
skill converts the first into the second, then gets out of the way: the
SessionStart hook checks per-block ground coverage, so the moment a block's
ground exists in the repo's own files, that block stops loading here.

## Procedure

### 1. Detect the stack

Same evidence the hooks use: `pyproject.toml`/`setup.py`/`*.py` for Python;
`package.json`/`tsconfig.json`/`bun.lock`/`bun.lockb` for JS/TS; check the
root, then two levels deep for monorepos. An `internal/` directory signals the
session-log convention is in use.

### 2. Inventory existing coverage, per block

The candidate blocks are the templates in
`${CLAUDE_PLUGIN_ROOT}/hooks/directives/*.md`. Line 2 of each carries its
ground as an ERE (`# ground: ...`). For each candidate, grep that pattern
(case-insensitive) across the repo's conventions surfaces: root `CLAUDE.md`,
`.claude/rules/*.md`, and `rules[]` in `.dev-conventions.json`. Covered ground
is skipped -- never write a second copy of a rule the repo already states.
Report what was skipped and where its existing copy lives.

### 3. Tailor to reality, not ideology

Write what is true of this repo and wanted by its owner. A bun repo gets the
bun lines; a repo genuinely on npm gets *offered* the migration, not a rule
contradicting its lockfile -- writing "use bun" into an npm repo relocates the
friction, it does not remove it. If the detected state and the plugin's
defaults disagree, ask.

### 4. Apply the exclusion test to every line

Before writing a line, ask whether the model would already do it without
being told: anything inferable from code, standard conventions, or detailed
API docs does not get written. Every scaffolded line is future context rent
for this repo -- the scaffold should land at roughly the size of the shipped
directives (a handful of lines per block), or smaller.

### 5. Write to the repo's own structure

- If `$1` names a target file, use it.
- Else if `.claude/rules/` exists and is in use, add or extend a file there.
- Else append a conventions section to the repo's root `CLAUDE.md` (create it
  if the repo has none).

Strip the `# trigger:` and `# ground:` metadata lines from anything taken
from the templates. Show the full proposed diff before writing. Validate,
never auto-commit -- the owner reviews and commits.

### 6. Migrate and clean up

- Fold any `rules[]` from `.dev-conventions.json` into the scaffolded file
  (they are repo-owned prose already; this just moves them where every
  collaborator's session loads them). Remove them from the JSON after.
- Note any `directives` mute entries that are now moot because the scaffold
  covers their ground -- coverage silencing supersedes them.

### 7. Report

State per block: scaffolded (where), skipped as covered (where the existing
copy lives), or excluded by the test in step 4. A report that does not say
what it skipped cannot be told from one that checked nothing.

## What this skill does not do

- It does not touch the PreToolUse enforcement hook or `enforce.*` config --
  mechanical blocks are the plugin's job permanently, and they update
  centrally on purpose.
- It does not rewrite conventions the repo already states, even when they
  disagree with the plugin's defaults. Report the disagreement; the owner
  decides.
- It does not need re-running when the plugin updates. Scaffolded text is the
  repo's prose now, maintained like the rest of the repo's prose.
