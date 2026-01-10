# web-app-tdd

A Claude Code plugin for test-driven development of web applications using Vitest and Playwright.

## Installation

```bash
ln -s /.web-app-tdd ~/.claude/plugins/web-app-tdd
```

## Features

- **TDD Workflow**: Test-first development patterns adapted for web apps
- **Multi-Framework Support**: React, Vue, Svelte, Next.js, vanilla JS
- **Unit & E2E Testing**: Vitest for unit/component tests, Playwright for E2E
- **Backend Support**: Node.js (Express/Fastify) and separate backends (FastAPI)
- **Parallel Agents**: Spawn multiple agents to generate tests, analyze coverage, and validate changes simultaneously

## Components

### Skill: web-app-tdd

Core TDD workflow guidance. Triggers on queries like:
- "Help me add tests to my React app"
- "Set up TDD for my Vite project"
- "How do I test this component?"

### Agents

| Agent | Purpose |
|-------|---------|
| `test-generator` | Generate test files for components (parallelizable) |
| `coverage-analyzer` | Analyze test coverage gaps |
| `setup-helper` | Configure testing infrastructure |
| `test-validator` | Validate code changes have tests (proactive) |

## Reference Files

- `skills/web-app-tdd/references/vitest-patterns.md` - Component testing, mocking, fixtures
- `skills/web-app-tdd/references/playwright-e2e.md` - Page objects, auth, visual testing
- `skills/web-app-tdd/references/backend-testing.md` - API testing, database mocking
- `skills/web-app-tdd/references/project-init.md` - Framework setup templates
