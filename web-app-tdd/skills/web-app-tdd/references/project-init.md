# Project Initialization

Framework-specific setup templates for web app testing.

## Vite + React + TypeScript

```bash
npm create vite@latest my-app -- --template react-ts
cd my-app
npm install

# Testing dependencies
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event

# E2E testing (optional)
npm init playwright@latest
```

### Vite Config

```typescript
// vite.config.ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
```

### Test Setup

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom'
```

### Package Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:run": "vitest run",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

## Vite + Vue + TypeScript

```bash
npm create vite@latest my-app -- --template vue-ts
cd my-app
npm install

npm install -D vitest @vitest/ui jsdom
npm install -D @vue/test-utils
```

### Vite Config

```typescript
// vite.config.ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
```

## Vite + Svelte + TypeScript

```bash
npm create vite@latest my-app -- --template svelte-ts
cd my-app
npm install

npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/svelte @testing-library/user-event
```

### Vite Config

```typescript
// vite.config.ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
```

## Next.js

```bash
npx create-next-app@latest my-app --typescript
cd my-app

# Vitest (faster than Jest)
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm install -D @vitejs/plugin-react

# E2E
npm init playwright@latest
```

### Vitest Config for Next.js

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './test/setup.ts',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

### Next.js Test Setup

```typescript
// test/setup.ts
import '@testing-library/jest-dom'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/',
}))
```

## Fullstack Node.js (Express)

```bash
mkdir my-app && cd my-app
npm init -y

# Dependencies
npm install express cors
npm install -D typescript @types/node @types/express @types/cors
npm install -D tsx  # For running TypeScript

# Testing
npm install -D vitest supertest @types/supertest
```

### TypeScript Config

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "**/*.test.ts"]
}
```

### Package Scripts

```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "vitest",
    "test:run": "vitest run"
  }
}
```

### Basic Express App Structure

```typescript
// src/app.ts
import express from 'express'
import cors from 'cors'

export function createApp() {
  const app = express()

  app.use(cors())
  app.use(express.json())

  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok' })
  })

  return app
}
```

```typescript
// src/index.ts
import { createApp } from './app'

const app = createApp()
const PORT = process.env.PORT || 3000

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})
```

## Directory Structure

### Frontend Project

```
my-app/
├── src/
│   ├── components/
│   │   ├── Button.tsx
│   │   └── Button.test.tsx      # Colocated unit test
│   ├── features/
│   │   └── auth/
│   │       ├── LoginForm.tsx
│   │       ├── LoginForm.test.tsx
│   │       └── useAuth.ts
│   ├── utils/
│   │   ├── format.ts
│   │   └── format.test.ts
│   └── test/
│       └── setup.ts             # Test setup/globals
├── e2e/                         # Playwright E2E tests
│   ├── login.spec.ts
│   └── checkout.spec.ts
├── spec.md                      # Project specification
├── vitest.config.ts
├── playwright.config.ts
├── tsconfig.json
└── package.json
```

### Fullstack Node.js

```
my-app/
├── src/
│   ├── routes/
│   │   ├── users.ts
│   │   └── users.test.ts
│   ├── services/
│   │   ├── userService.ts
│   │   └── userService.test.ts
│   ├── middleware/
│   │   └── auth.ts
│   ├── app.ts
│   └── index.ts
├── e2e/
│   └── api.spec.ts
├── spec.md
├── vitest.config.ts
├── tsconfig.json
└── package.json
```

## Playwright Config

### Standard Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

## TypeScript Config for Testing

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src", "e2e"]
}
```

## Initial Test File

Create your first test to verify setup:

```typescript
// src/utils/example.test.ts
import { describe, it, expect } from 'vitest'

describe('test setup', () => {
  it('works', () => {
    expect(1 + 1).toBe(2)
  })
})
```

Run to verify:

```bash
npx vitest run
```

Delete this file after adding real tests.
