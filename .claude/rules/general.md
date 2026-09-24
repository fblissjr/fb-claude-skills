# General conventions

## Pinning

Always pin a version. Applications pin exact (`uv add pkg==1.2.3`,
`bun add pkg@1.2.3`); libraries use a floor (`uv add 'pkg>=1.2'`) or a caret
(`bun add pkg@^1.2.3`). Unsure: exact.

## TDD

Write the failing test first, then implement. A new test's claim -- what
breaks if it is deleted -- must be recoverable: a per-test comment, or a
file-level convention (header claim plus per-case rationale) that pins each
case.

A test that pins existing behavior is born green and skips the fallibility
proof red-first gives every other arm -- so prove it once at birth: mutate
the pinned behavior, confirm red, revert. A pin that cannot go red is
decoration.

## After an edit, don't run linters or tests unasked

Leave linters, formatters, and tests alone after an edit unless asked. The
reflex is strong, the output is long, and it buries the change the user
actually wants to look at.

## JSON

Use `orjson` for all Python JSON serialization and deserialization.

## State in repo

`.skill-maintainer/state/` holds per-repo maintenance state (gitignored). Keep
project state out of `<HOME>/.claude/`.

## Non-destructive

Validate before writing. Back up state before modifying it. Tools and hooks
never commit on their own; Claude committing per the owner's global rule
(fine without asking, never push unasked) is not what this forbids.

## READMEs

Every plugin README includes: last updated date, installation commands, skills table, invocation examples.
