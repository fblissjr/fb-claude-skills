# vibium-tdd

A Claude Code plugin for test-driven development of web applications using Vitest and Vibium.

## Installation

```bash
ln -s /path/to/vibium-tdd ~/.claude/plugins/vibium-tdd
```

Replace `/path/to/vibium-tdd` with the actual path to this plugin directory.

## Features

- **TDD Workflow**: Test-first development patterns adapted for web apps
- **Multi-Framework Support**: React, Vue, Svelte, Next.js, vanilla JS
- **Unit & E2E Testing**: Vitest for unit/component tests, Vibium for E2E
- **AI-Native E2E**: Vibium's MCP integration works seamlessly with Claude Code
- **Zero-Config E2E**: No playwright.config.ts needed - Vibium is zero-config
- **Backend Support**: Node.js (Express/Fastify) and separate backends (FastAPI)
- **Parallel Agents**: Spawn multiple agents to generate tests, analyze coverage, and validate changes simultaneously

## Components

### Skill: vibium-tdd

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

- `skills/vibium-tdd/references/vitest-patterns.md` - Component testing, mocking, fixtures
- `skills/vibium-tdd/references/vibium-e2e.md` - Vibium E2E patterns, browser automation
- `skills/vibium-tdd/references/backend-testing.md` - API testing, database mocking
- `skills/vibium-tdd/references/project-init.md` - Framework setup templates

## Why Vibium over Playwright?

| Aspect | Playwright | Vibium |
|--------|------------|--------|
| Config | `playwright.config.ts` required | Zero-config |
| API | Complex Page Object Model | Simple vibe API |
| AI Integration | Manual | MCP-native |
| Install | `npm init playwright` (interactive) | `npm install vibium` |
| Binary Size | ~100MB+ per browser | ~10MB total |
