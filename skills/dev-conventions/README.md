last updated: 2026-03-13

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
| `session-start.sh` | SessionStart | Detects Python/JS markers in cwd, injects uv/orjson/bun/TDD conventions as additionalContext |

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `python-tooling` | `/dev-conventions:python-tooling` | Full uv/orjson conversion tables (detailed reference) |
| `bun-tooling` | `/dev-conventions:bun-tooling` | Full bun conversion tables and lock file migration |
| `tdd-workflow` | `/dev-conventions:tdd-workflow` | Red/green TDD: write failing test, implement, refactor |
| `doc-conventions` | `/dev-conventions:doc-conventions` | Last-updated dates, lowercase filenames, session logs, document the "why" |

## how it works

When a session begins, the hook checks `cwd` for project markers (`pyproject.toml`, `package.json`, etc.). If found, it injects a compact conventions summary into Claude's context as `additionalContext` -- no manual invocation needed. The injected context covers the correct package manager, JSON library, and TDD basics. For full conversion tables or detailed methodology, invoke the skills directly.
