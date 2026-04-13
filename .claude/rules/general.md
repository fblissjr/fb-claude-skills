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

## JSON

Use `orjson` for all Python JSON serialization and deserialization.

## Skills standard

All skills follow the [Agent Skills](https://agentskills.io) spec. Validate with `uv run agentskills validate`.

## State in repo

`.skill-maintainer/state/` holds per-repo maintenance state (gitignored). Do not use `~/.claude/` for project state.

## Non-destructive

Always validate before writing. Create backups when modifying state. Never auto-commit.

## Logs

Session logs go in `internal/log/log_YYYY-MM-DD.md`. The `internal/` directory is gitignored -- write logs but do not commit them.

## READMEs

Every plugin README includes: last updated date, installation commands, skills table, invocation examples.
