---
name: web-tdd
description: TDD workflow for web applications with Vitest (unit/component) and Playwright or Vibium (E2E). Supports React+Node, React+Python, and vanilla JS+Python stacks. Use when building web apps, adding tests to existing projects, or implementing features with test-driven development.
metadata:
  author: Fred Bliss
  version: 0.1.0
---

# web-tdd skill

Test-driven development for web applications. Write test → watch fail → implement → watch pass → document → commit.

## Quick Start

Determine your stack:

```
Stack?
│
├── React + Node backend
│   └── Vitest everywhere (frontend + backend with supertest)
│
├── React + Python backend
│   └── Vitest (frontend) + pytest (backend)
│
└── Vanilla JS/HTML + Python
    └── Vitest or Jest (frontend) + pytest (backend)
```

For E2E testing:
- **Playwright** - Full-featured, mature, requires config
- **Vibium** - Zero-config, AI-native, simpler API

Default: Start with Playwright. Switch to Vibium if you need simpler setup or MCP integration.

## Project Setup

### New Project

```bash
mkdir my-project && cd my-project
git init

# Create spec and README
echo "# my-project\n\nBrief description." > README.md
touch spec.md

# Initialize frontend
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install

# Add testing
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event

# Add E2E (choose one)
npm install -D @playwright/test  # Playwright
# OR
npm install vibium               # Vibium (zero-config)

cd ..

# Initialize backend (if Python)
mkdir backend && cd backend
uv init
uv add fastapi uvicorn
uv add pytest httpx --dev
cd ..
```

### Existing Project

```bash
# Check current test setup
grep -E "vitest|jest|playwright|vibium|pytest" package.json pyproject.toml 2>/dev/null

# Add what's missing (see setup commands above)
```

### Gitignore Setup

Always ensure these are ignored before first commit:

```bash
cat >> .gitignore << 'EOF'
# Test artifacts
coverage/
playwright-report/
test-results/
*.png
*.webm

# Environment
.env
.env.local
.env.*.local

# Build
dist/
build/
node_modules/
__pycache__/
*.pyc
.pytest_cache/
.venv/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF
```

## The Workflow

### 1. Start with spec.md

Every project has a `spec.md` at the root with:
- Overview of what you're building
- TODO lists for features (checked off as completed)
- Architecture decisions
- Testing strategy

```markdown
# Project Name

## Overview
What this does in 1-2 sentences.

## Features
- [ ] User authentication
- [ ] Dashboard with metrics
- [x] Landing page (completed)

## Architecture
Key decisions: React frontend, FastAPI backend, PostgreSQL.

## Testing
- Unit: `npm test` (frontend), `uv run pytest` (backend)
- E2E: `npx playwright test`
```

Update spec.md as you go. Check off completed items. Add new TODOs as discovered.

### 2. Write a Failing Test First

```bash
# Frontend component test
touch frontend/src/components/LoginForm.test.tsx

# Write the test describing expected behavior
# Run it - should fail
cd frontend && npx vitest run src/components/LoginForm.test.tsx
```

### 3. Implement to Pass

Write minimal code to make the test pass. No more.

```bash
# Run again - should pass
npx vitest run src/components/LoginForm.test.tsx
```

### 4. Refactor if Needed

Clean up while tests stay green.

### 5. Document and Commit

```bash
# Update spec.md TODOs
# Update README if user-facing change

# Commit implementation + tests + docs together
git add -A
git commit -m "feat(auth): add login form with validation

- Add LoginForm component
- Add validation tests
- Update spec.md checklist"
```

### 6. Push (Manual, Always)

**Never auto-push.** Review your commits, then:

```bash
git push origin main  # or your branch
```

If opening a PR, do that manually too. You stay in control.

## Test Types

### Unit Tests (Vitest)

For pure functions, utilities, hooks:

```typescript
// utils/format.test.ts
import { describe, it, expect } from 'vitest'
import { formatCurrency } from './format'

describe('formatCurrency', () => {
  it('formats USD correctly', () => {
    expect(formatCurrency(1234.5, 'USD')).toBe('$1,234.50')
  })
})
```

### Component Tests (Vitest + Testing Library)

For React/Vue/Svelte components:

```typescript
// components/Button.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './Button'

describe('Button', () => {
  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    await userEvent.click(screen.getByRole('button'))
    
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

### API Tests (Python with pytest)

```python
# backend/tests/test_api.py
import pytest
from httpx import AsyncClient
from app import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/users", json={"name": "John"})
    
    assert response.status_code == 201
    assert response.json()["name"] == "John"
```

### E2E Tests (Playwright)

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test'

test('user can log in', async ({ page }) => {
  await page.goto('/login')
  await page.fill('[name=email]', 'test@example.com')
  await page.fill('[name=password]', 'password123')
  await page.click('button[type=submit]')
  
  await expect(page.locator('h1')).toContainText('Dashboard')
})
```

### E2E Tests (Vibium Alternative)

```typescript
// e2e/login.test.ts
import { browser } from 'vibium'
import { describe, it, expect, afterEach } from 'vitest'

describe('Login Flow', () => {
  let vibe: Awaited<ReturnType<typeof browser.launch>>

  afterEach(async () => {
    if (vibe) await vibe.quit()
  })

  it('user can log in', async () => {
    vibe = await browser.launch()
    await vibe.go('http://localhost:5173/login')
    
    await (await vibe.find('[name=email]')).type('test@example.com')
    await (await vibe.find('[name=password]')).type('password123')
    await (await vibe.find('button[type=submit]')).click()
    
    const heading = await vibe.find('h1')
    expect(await heading.text()).toContain('Dashboard')
  })
})
```

## Configuration

### Vitest Config (Frontend)

```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
  },
})
```

### Playwright Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

### pytest Config (Backend)

```toml
# backend/pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Package Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "test": "vitest",
    "test:run": "vitest run",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

## Commit Strategy

Each commit includes:
1. **Implementation** - The feature/fix code
2. **Tests** - Tests for that implementation  
3. **Documentation** - Updated spec.md, README if needed

Commit after each green test cycle. Push manually when ready.

**Commit message format:**
```
type(scope): short description

- Detail 1
- Detail 2
- Update spec.md checklist
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

## When to Use What

| Testing What | Tool | Why |
|--------------|------|-----|
| Pure functions | Vitest | Fast, isolated |
| React components | Vitest + Testing Library | JSDOM is enough |
| React hooks | Vitest + renderHook | No real DOM needed |
| Python API | pytest + httpx | Native async support |
| Full user flows | Playwright | Real browser |
| Quick E2E + MCP | Vibium | Zero config, AI-native |
| Visual regression | Playwright | Screenshot comparison |

## Directory Structure, Mocking, and Common Patterns

See `references/project_structures.md` for full directory layouts (React+Node, React+Python), mocking strategies (AI/API, database), and common test patterns (loading states, error states, mobile responsive).

## Remember

1. **Test first** - Write the test before the implementation
2. **Minimal to pass** - Don't over-engineer
3. **Spec is source of truth** - Keep spec.md updated
4. **You control pushes** - Review before pushing, no auto-push
5. **Commit atomic units** - Feature + tests + docs together
