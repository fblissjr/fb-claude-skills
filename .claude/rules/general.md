# General conventions

These rules load unconditionally in this project.

## Package managers

Python: always `uv`. Never use `pip` or `python` directly.

- Install: `uv add <package>`
- Run: `uv run <script.py>`
- Sync: `uv sync`
- Version pinning: always specify versions. Applications: exact (`uv add pkg==1.2.3`). Libraries: floor (`uv add 'pkg>=1.2'`). When unsure, pin exact.

JavaScript/TypeScript: always `bun`. Never use `npm` or `yarn`.

- Install: `bun add <package>`
- Run: `bun run <script>`
- Init: `bun init`
- Version pinning: always specify versions. Applications: exact (`bun add pkg@1.2.3`). Libraries: caret (`bun add pkg@^1.2.3`). When unsure, pin exact.

## TDD

Write the failing test first, then implement. A new test's claim -- what
breaks if it is deleted -- must be recoverable: a per-test comment, or a
file-level convention (header claim plus per-case rationale) that pins each
case.

A test that pins existing behavior is born green and skips the fallibility
proof red-first gives every other arm -- so prove it once at birth: mutate
the pinned behavior, confirm red, revert. A pin that cannot go red is
decoration (specimen: 2026-08-04, one of eighteen arms).

## After an edit, stop

Do not auto-run linters, formatters, or tests after an edit unless asked. The
reflex is strong, the output is long, and it buries the change the user
actually wants to look at.

## Numbers in prose

Before writing a number into prose, substitute a different plausible value. If
the reader's next action is unchanged, the number is decorative -- delete it.
A number that survives is either normative (a limit being set, which cannot
drift) or descriptive, and a descriptive one needs an observation point -- a
date, a commit, an attribution, past tense -- and belongs only in a dated
record. Binding is not a lesser fix for a decorative number: it makes the claim
permanently true and permanently useless. Delete first; bind only what passed.

## JSON

Use `orjson` for all Python JSON serialization and deserialization.

## Skills standard

Skills here run in Claude Code, so they follow Claude Code's skill schema -- a superset of the cross-vendor [Agent Skills](https://agentskills.io) spec. Validate with `uv run skill-maintain validate` (accepts Claude Code frontmatter fields such as `disable-model-invocation`, `argument-hint`, `model`). Add `--strict` to check cross-vendor portability (flags Claude Code-only fields).

## State in repo

`.skill-maintainer/state/` holds per-repo maintenance state (gitignored). Do not use `<HOME>/.claude/` for project state.

## Non-destructive

Always validate before writing. Create backups when modifying state. Tools
and hooks never commit on their own; Claude committing per the owner's
global rule (fine without asking, never push unasked) is not what this
forbids.

## Logs

Session logs go in `internal/log/log_YYYY-MM-DD.md`. The `internal/` directory is gitignored -- write logs but do not commit them.

## READMEs

Every plugin README includes: last updated date, installation commands, skills table, invocation examples.
