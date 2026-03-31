last updated: 2026-03-31

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
| `session-start.sh` | SessionStart | Detects Python/JS markers in cwd (root + 2 levels deep for monorepos), injects matching directives as additionalContext. |

### detection markers

| Marker | Directive injected |
|--------|--------------------|
| `pyproject.toml`, `*.py` (root or 2 levels deep) | `python.md` -- uv, orjson, Python conventions |
| `package.json`, `bun.lockb` (root or 2 levels deep) | `javascript.md` -- bun, JS/TS conventions |
| Any Python or JS marker | `tdd.md` -- red/green TDD as a directive |
| `internal/` or `internal/log/` directory | `doc-conventions.md` -- session logging, last-updated dates |

### composable directives

All injected content lives in `hooks/directives/` as standalone `.md` files. The hook concatenates whichever directives match and returns them as a single `additionalContext` block.

To add a new directive: drop a `.md` file in `hooks/directives/` and add a detection condition to `hooks/session-start.sh`.

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `python-tooling` | `/dev-conventions:python-tooling` | Full uv/orjson conversion tables (detailed reference) |
| `bun-tooling` | `/dev-conventions:bun-tooling` | Full bun conversion tables and lock file migration |
| `tdd-workflow` | `/dev-conventions:tdd-workflow` | Red/green TDD: write failing test, implement, refactor |
| `doc-conventions` | `/dev-conventions:doc-conventions` | Last-updated dates, lowercase filenames, session logs, document the "why" |

## how it works

When a session begins, the hook checks `cwd` for project markers (`pyproject.toml`, `package.json`, `*.py`, `bun.lockb`). It first checks the project root, then falls back to scanning up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, `dist`, `build`, `.next`, `.output`. For each detected marker, the hook reads the corresponding directive file from `hooks/directives/` and concatenates the results into a single `additionalContext` block -- no manual invocation needed. For full conversion tables or detailed methodology, invoke the skills directly.
