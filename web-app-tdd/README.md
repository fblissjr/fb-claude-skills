# web-app-tdd

A Claude Code plugin for test-driven development of web applications using Vitest and Playwright.

## Features

- **TDD Workflow**: Test-first development patterns adapted for web apps
- **Multi-Framework Support**: React, Vue, Svelte, Next.js, vanilla JS
- **Unit & E2E Testing**: Vitest for unit/component tests, Playwright for E2E
- **Backend Support**: Node.js (Express/Fastify) and separate backends (FastAPI)
- **Parallel Agents**: Spawn multiple agents to generate tests, analyze coverage, and validate changes simultaneously

## Installation

### Option 1: Symlink to plugins directory

```bash
ln -s /path/to/web-app-tdd ~/.claude/plugins/web-app-tdd
```

### Option 2: Copy to plugins directory

```bash
cp -r /path/to/web-app-tdd ~/.claude/plugins/
```

### Option 3: Use with --plugin-dir flag

```bash
claude --plugin-dir /path/to/web-app-tdd
```

## Components

### Skill: web-app-tdd

Core TDD workflow guidance. Triggers on queries like:
- "Help me add tests to my React app"
- "Set up TDD for my Vite project"
- "How do I test this component?"

### Agents

Spawn these agents for parallel task execution:

| Agent | Purpose | Example Use |
|-------|---------|-------------|
| `test-generator` | Generate test files for components | "Generate tests for Button, Modal, and Form components" |
| `coverage-analyzer` | Analyze test coverage gaps | "What parts of my codebase don't have tests?" |
| `setup-helper` | Configure testing infrastructure | "Set up Vitest and Playwright for my project" |
| `test-validator` | Validate code changes have tests | "Check if my new feature has proper test coverage" |

**Parallel execution example:**
```
User: "Generate tests for the auth module components"
Claude: "I'll spawn test-generator agents for LoginForm, SignupForm, and useAuth in parallel."
```

## Skill Reference Files

The skill includes detailed reference documentation:

- `references/vitest-patterns.md` - Component testing, mocking, fixtures, coverage
- `references/playwright-e2e.md` - Page objects, auth, visual testing, config
- `references/backend-testing.md` - API testing, database mocking, MSW
- `references/project-init.md` - Framework-specific setup templates

## TDD Workflow

The plugin teaches this workflow:

1. **Write a failing test first**
2. **Run test, watch it fail**
3. **Implement minimal code to pass**
4. **Run test, watch it pass**
5. **Refactor if needed**
6. **Document and commit together**

## Supported Frameworks

- **Frontend**: React, Vue, Svelte, vanilla JS/TS
- **Meta-frameworks**: Next.js, Nuxt, SvelteKit
- **Bundlers**: Vite, webpack
- **Test runners**: Vitest (recommended), Jest
- **E2E**: Playwright
- **Backends**: Express, Fastify, FastAPI (via uv-tdd skill)

## License

Apache 2.0
