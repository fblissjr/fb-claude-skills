last updated: 2026-02-14

# web-tdd

TDD workflow for web applications with Vitest (unit/component) and Playwright or Vibium (E2E). Supports React+Node, React+Python, and vanilla JS+Python stacks.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install web-tdd@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/web-tdd
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `web-tdd` | "set up TDD", "add tests to my React app", "create tests for the login flow" | Guides TDD workflow: test setup, failing test, implementation, pass, document, commit |

## invocation

```
/web-tdd
```

Or describe what you want naturally -- the skill triggers on test-related keywords.

## what this covers

- **React + Node backend** -- Vitest everywhere (frontend + backend with supertest)
- **React + Python backend** -- Vitest (frontend) + pytest (backend)
- **Vanilla JS/HTML + Python** -- Vitest or Jest (frontend) + pytest (backend)
- **E2E** -- Playwright (full-featured) or Vibium (zero-config, AI-native)

## key philosophy

1. Single source of truth (SKILL.md)
2. spec.md as living documentation
3. TDD cycle: test first, fail, implement, pass, document, commit
4. You control all remote operations (no auto-push)

## credits

Evolved from earlier `vibium-tdd` and `web-app-tdd` skills into a unified, simplified version.
