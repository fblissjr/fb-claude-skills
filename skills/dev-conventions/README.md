last updated: 2026-03-30

# dev-conventions

Development conventions with automatic project detection. A SessionStart hook detects Python/JS project markers and injects the relevant conventions into Claude's context. Skills provide detailed reference tables on demand.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install dev-conventions@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/skills/dev-conventions
```

## hooks

| Hook | Event | What it does |
|------|-------|--------------|
| `session-start.sh` | SessionStart | Detects Python/JS markers in cwd (root + 2 levels deep for monorepos), injects uv/orjson/bun/TDD directives as additionalContext. Detects `internal/` directory and injects session logging directive. |

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `python-tooling` | `/dev-conventions:python-tooling` | Full uv/orjson conversion tables (detailed reference) |
| `bun-tooling` | `/dev-conventions:bun-tooling` | Full bun conversion tables and lock file migration |
| `tdd-workflow` | `/dev-conventions:tdd-workflow` | Red/green TDD: write failing test, implement, refactor |
| `doc-conventions` | `/dev-conventions:doc-conventions` | Last-updated dates, lowercase filenames, session logs, document the "why" |

## how it works

When a session begins, the hook checks `cwd` for project markers (`pyproject.toml`, `package.json`, etc.). It first checks the project root, then falls back to scanning up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, `dist`, `build`, `.next`, `.output`. If markers are found, it injects conventions and behavioral directives as `additionalContext` -- no manual invocation needed. The injected context covers the correct package manager, JSON library, and TDD as a directive (not a suggestion). If an `internal/` or `internal/log/` directory exists, it also injects a session logging directive. For full conversion tables or detailed methodology, invoke the skills directly.
