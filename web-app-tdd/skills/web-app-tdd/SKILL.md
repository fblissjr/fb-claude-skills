---
name: web-app-tdd
description: TDD workflow for web applications using Vitest for unit/component tests and Playwright for E2E tests. Use when building or testing web apps (React, Vue, Svelte, vanilla JS), adding tests to existing frontend projects, implementing features with test-driven development, or setting up testing infrastructure for frontend and fullstack applications.
---

# Web App TDD

Test-driven development workflow for web applications: write test first, watch fail, implement, watch pass.

## Quick Start

Determine your situation:

```
Project state?
|
+-- New project
|   +-- Frontend-only --> npm create vite@latest (Vitest built-in)
|   +-- Fullstack Node --> See references/project-init.md
|   +-- Separate backend --> Frontend setup + backend independently
|
+-- Existing project
    +-- Has test runner (vitest/jest) --> Use existing runner
    +-- No tests --> Add Vitest (see Adding Tests below)
```

**Default choices** (opinionated, override if project requires):
- Unit/Component tests: **Vitest** (fast, Vite-native, Jest-compatible API)
- E2E tests: **Playwright** (reliable, fast, good DX)
- Test location: Colocated (`Button.test.tsx` next to `Button.tsx`)

## Core TDD Workflow

For every feature or fix:

### 1. Write a failing test first

```bash
# Create test file next to source
touch src/features/auth/login.test.ts

# Write test describing expected behavior
# Run it - should fail
npx vitest run src/features/auth/login.test.ts
```

### 2. Implement minimal code to pass

```bash
# Write just enough implementation to pass
npx vitest run src/features/auth/login.test.ts  # Should pass now
```

### 3. Refactor if needed

Keep tests passing. Clean up implementation.

### 4. Document and commit together

- Update spec.md TODOs
- Update README if user-facing change
- Commit: implementation + tests + docs as single unit

### Watch Mode

Run tests continuously during development:

```bash
npx vitest              # Unit tests in watch mode
npx playwright test --ui  # E2E with interactive UI
```

## Test Strategy

Use the testing pyramid - more unit tests, fewer E2E:

```
       /\
      /E2E\       Few, slow, high-confidence
     /------\
    / Integr \    Some, medium speed
   /----------\
  / Unit Tests \  Many, fast, focused
 /--------------\
```

**Use Vitest for:**
- Pure functions, utilities, helpers
- Component rendering and behavior
- State management logic
- API client logic (with mocks)

**Use Playwright for:**
- Critical user journeys (login, checkout, signup)
- Cross-page flows
- Features requiring real browser behavior
- Visual regression (optional)

**Rule**: If it can be tested with Vitest, prefer Vitest. Use Playwright for what requires a real browser.

## Vitest Quick Reference

### Install

```bash
npm install -D vitest @vitest/ui
```

### Config

Create or update `vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',  // For DOM/component testing
  },
})
```

### Basic Test

```typescript
import { describe, it, expect } from 'vitest'
import { formatCurrency } from './format'

describe('formatCurrency', () => {
  it('formats USD correctly', () => {
    expect(formatCurrency(1234.5, 'USD')).toBe('$1,234.50')
  })

  it('handles zero', () => {
    expect(formatCurrency(0, 'USD')).toBe('$0.00')
  })
})
```

### Run Tests

```bash
npx vitest              # Watch mode
npx vitest run          # Single run
npx vitest run login    # Tests matching "login"
npx vitest --ui         # Browser UI
```

For component testing, fixtures, mocking: see **[references/vitest-patterns.md](references/vitest-patterns.md)**

## Playwright Quick Reference

### Install

```bash
npm init playwright@latest
```

### Basic E2E Test

```typescript
import { test, expect } from '@playwright/test'

test('user can log in', async ({ page }) => {
  await page.goto('/login')
  await page.fill('[name=email]', 'test@example.com')
  await page.fill('[name=password]', 'password123')
  await page.click('button[type=submit]')
  await expect(page.locator('h1')).toContainText('Dashboard')
})
```

### Run Tests

```bash
npx playwright test           # All tests
npx playwright test login     # Tests matching "login"
npx playwright test --headed  # See the browser
npx playwright show-report    # View HTML report
```

For page objects, auth persistence, fixtures: see **[references/playwright-e2e.md](references/playwright-e2e.md)**

## Backend Testing

### Node.js API (Express/Fastify)

Use Vitest with supertest:

```typescript
import { describe, it, expect } from 'vitest'
import request from 'supertest'
import { app } from './app'

describe('GET /api/users', () => {
  it('returns users list', async () => {
    const res = await request(app).get('/api/users')
    expect(res.status).toBe(200)
    expect(res.body).toBeInstanceOf(Array)
  })
})
```

### Separate Python Backend

Use pytest with the uv-tdd skill patterns. The frontend tests can mock API responses or run against a test server.

For database testing, integration patterns: see **[references/backend-testing.md](references/backend-testing.md)**

## Project Setup

### New Vite Project

```bash
npm create vite@latest my-app -- --template react-ts
cd my-app
npm install

# Add testing
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom
```

Update `package.json`:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:run": "vitest run"
  }
}
```

### Adding Tests to Existing Project

1. Check for existing test setup:
   ```bash
   grep -E "vitest|jest|mocha" package.json
   ```

2. If no test runner, add Vitest:
   ```bash
   npm install -D vitest
   ```

3. Create first test next to existing code:
   ```bash
   # If you have src/utils/format.ts
   touch src/utils/format.test.ts
   ```

4. Write test, run, implement TDD cycle.

For framework-specific setup (Vue, Svelte, Next.js): see **[references/project-init.md](references/project-init.md)**

## Documentation Pattern

Create `spec.md` at project root:

```markdown
# Project Name

## Overview
Brief description of what this project does.

## Features
- [ ] User authentication
- [ ] Dashboard with metrics
- [x] Landing page (completed)

## Architecture
Key decisions and component structure.

## Testing
- Unit: `npm test`
- E2E: `npm run test:e2e`
```

Update as you progress:
- Check off completed features
- Add discovered requirements
- Document architectural decisions

## Commit Strategy

Each commit includes:
1. **Implementation** - The feature/fix code
2. **Tests** - Tests for that implementation
3. **Documentation** - Updated spec.md, README if needed

Example:
```
feat(auth): add login form validation

- Add email format validation
- Add password strength check
- Update spec.md checklist
```

Commit after each green test cycle. Push if remote is configured.

## Common Patterns

### Testing Async Code

```typescript
it('fetches user data', async () => {
  const user = await fetchUser(1)
  expect(user.name).toBe('John')
})
```

### Mocking

```typescript
import { vi } from 'vitest'

// Mock a module
vi.mock('./api', () => ({
  fetchUser: vi.fn().mockResolvedValue({ id: 1, name: 'John' })
}))

// Spy on a method
const spy = vi.spyOn(console, 'log')
```

### Component Testing (React)

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './Button'

it('calls onClick when clicked', async () => {
  const handleClick = vi.fn()
  render(<Button onClick={handleClick}>Click me</Button>)

  await userEvent.click(screen.getByRole('button'))

  expect(handleClick).toHaveBeenCalledOnce()
})
```

### Testing with Server Running

For E2E tests that need a dev server, configure `playwright.config.ts`:

```typescript
export default defineConfig({
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

## Reference Files

- **[references/vitest-patterns.md](references/vitest-patterns.md)** - Component testing, fixtures, mocking, coverage
- **[references/playwright-e2e.md](references/playwright-e2e.md)** - Page objects, auth, visual testing, config
- **[references/backend-testing.md](references/backend-testing.md)** - API testing, database mocking, integration
- **[references/project-init.md](references/project-init.md)** - Framework-specific setup templates
