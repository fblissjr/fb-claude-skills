last updated: 2026-03-03

# dev-conventions

Development conventions as selective skills. Language-specific tooling fires only when relevant. TDD and documentation conventions are opt-in.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install dev-conventions@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/dev-conventions
```

## skills

| Skill | Invocable | Trigger | What it does |
|-------|-----------|---------|--------------|
| `python-tooling` | no | Python projects, pip usage, json.dumps | Enforces uv over pip, orjson over json |
| `bun-tooling` | no | JS/TS projects, npm/yarn usage | Enforces bun over npm/yarn/pnpm |
| `tdd-workflow` | yes | `/dev-conventions:tdd-workflow` | Red/green TDD: write failing test, implement, refactor |
| `doc-conventions` | yes | `/dev-conventions:doc-conventions` | Last-updated dates, lowercase filenames, session logs, document the "why" |

## invocation

Background skills (`python-tooling`, `bun-tooling`) fire automatically when Claude detects relevant context. No manual invocation needed.

User-invocable skills:

```
/dev-conventions:tdd-workflow
/dev-conventions:doc-conventions
```

