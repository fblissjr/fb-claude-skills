last updated: 2026-02-13

# web-tdd

TDD workflow for web applications with Vitest (unit/component) and Playwright or Vibium (E2E). Supports React+Node, React+Python, and vanilla JS+Python stacks.

## installation

```bash
claude plugin add /path/to/fb-claude-skills/web-tdd
```

Or from the repo URL:

```bash
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin web-tdd
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
