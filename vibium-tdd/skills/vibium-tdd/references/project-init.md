# Project Initialization

Framework-specific setup templates for web app testing with Vitest and Vibium.

## Vite + React + TypeScript

```bash
npm create vite@latest my-app -- --template react-ts
cd my-app
npm install

# Testing dependencies
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event

# E2E testing with Vibium
npm install vibium
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
    "test:e2e": "vitest run e2e/"
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

# E2E
npm install vibium
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

# E2E
npm install vibium
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

# E2E with Vibium
npm install vibium
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

# E2E
npm install vibium
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
    "test:run": "vitest run",
    "test:e2e": "vitest run e2e/"
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
+-- src/
|   +-- components/
|   |   +-- Button.tsx
|   |   +-- Button.test.tsx      # Colocated unit test
|   +-- features/
|   |   +-- auth/
|   |       +-- LoginForm.tsx
|   |       +-- LoginForm.test.tsx
|   |       +-- useAuth.ts
|   +-- utils/
|   |   +-- format.ts
|   |   +-- format.test.ts
|   +-- test/
|       +-- setup.ts             # Test setup/globals
+-- e2e/                         # Vibium E2E tests
|   +-- login.test.ts
|   +-- checkout.test.ts
+-- spec.md                      # Project specification
+-- vitest.config.ts
+-- tsconfig.json
+-- package.json
```

### Fullstack Node.js

```
my-app/
+-- src/
|   +-- routes/
|   |   +-- users.ts
|   |   +-- users.test.ts
|   +-- services/
|   |   +-- userService.ts
|   |   +-- userService.test.ts
|   +-- middleware/
|   |   +-- auth.ts
|   +-- app.ts
|   +-- index.ts
+-- e2e/
|   +-- api.test.ts
+-- spec.md
+-- vitest.config.ts
+-- tsconfig.json
+-- package.json
```

## E2E Test Setup with Vibium

Unlike Playwright, Vibium requires no config file. Just install and use.

### Basic E2E Test File

```typescript
// e2e/login.test.ts
import { browser } from 'vibium'
import { describe, it, expect, afterEach } from 'vitest'

describe('Login', () => {
  let vibe: Awaited<ReturnType<typeof browser.launch>>

  afterEach(async () => {
    if (vibe) await vibe.quit()
  })

  it('user can login', async () => {
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

### Running with Dev Server

Start your dev server in one terminal:

```bash
npm run dev
```

Run E2E tests in another:

```bash
npm run test:e2e
```

Or use a script to manage the server:

```typescript
// e2e/helpers.ts
import { spawn, ChildProcess } from 'child_process'

let server: ChildProcess | null = null

export async function startDevServer(port = 5173) {
  return new Promise<void>((resolve) => {
    server = spawn('npm', ['run', 'dev'], { stdio: 'pipe' })
    server.stdout?.on('data', (data) => {
      if (data.toString().includes('localhost')) {
        resolve()
      }
    })
    // Fallback timeout
    setTimeout(resolve, 5000)
  })
}

export function stopDevServer() {
  if (server) {
    server.kill()
    server = null
  }
}
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

## Initial Test Files

### Unit Test Verification

```typescript
// src/utils/example.test.ts
import { describe, it, expect } from 'vitest'

describe('test setup', () => {
  it('works', () => {
    expect(1 + 1).toBe(2)
  })
})
```

### E2E Test Verification

```typescript
// e2e/smoke.test.ts
import { browser } from 'vibium'
import { describe, it, expect, afterEach } from 'vitest'

describe('smoke test', () => {
  let vibe: Awaited<ReturnType<typeof browser.launch>>

  afterEach(async () => {
    if (vibe) await vibe.quit()
  })

  it('browser launches', async () => {
    vibe = await browser.launch()
    await vibe.go('https://example.com')

    const heading = await vibe.find('h1')
    expect(await heading.text()).toBeTruthy()
  })
})
```

Run to verify:

```bash
# Unit tests
npx vitest run src/

# E2E tests (after starting dev server)
npx vitest run e2e/
```

Delete verification tests after confirming setup works.
