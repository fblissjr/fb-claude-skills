# Playwright E2E Patterns

Advanced patterns for end-to-end testing with Playwright.

## Page Object Model

Encapsulate page interactions in reusable classes.

### Define Page Object

```typescript
// pages/LoginPage.ts
import { Page, Locator } from '@playwright/test'

export class LoginPage {
  private readonly emailInput: Locator
  private readonly passwordInput: Locator
  private readonly submitButton: Locator

  constructor(private page: Page) {
    this.emailInput = page.locator('[name=email]')
    this.passwordInput = page.locator('[name=password]')
    this.submitButton = page.locator('button[type=submit]')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }

  async getErrorMessage() {
    return this.page.locator('[data-testid=error]').textContent()
  }
}
```

### Use in Tests

```typescript
// tests/login.spec.ts
import { test, expect } from '@playwright/test'
import { LoginPage } from '../pages/LoginPage'

test('successful login redirects to dashboard', async ({ page }) => {
  const loginPage = new LoginPage(page)

  await loginPage.goto()
  await loginPage.login('user@example.com', 'password123')

  await expect(page).toHaveURL('/dashboard')
})

test('invalid credentials show error', async ({ page }) => {
  const loginPage = new LoginPage(page)

  await loginPage.goto()
  await loginPage.login('user@example.com', 'wrongpassword')

  expect(await loginPage.getErrorMessage()).toBe('Invalid credentials')
})
```

## Custom Fixtures

### Extend Test with Fixtures

```typescript
// fixtures.ts
import { test as base } from '@playwright/test'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'

type Fixtures = {
  loginPage: LoginPage
  dashboardPage: DashboardPage
  authenticatedPage: Page
}

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page))
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page))
  },

  authenticatedPage: async ({ page }, use) => {
    // Login before test
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login('test@example.com', 'password123')
    await page.waitForURL('/dashboard')
    await use(page)
  },
})

export { expect } from '@playwright/test'
```

### Use Custom Fixtures

```typescript
import { test, expect } from '../fixtures'

test('view profile when authenticated', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/profile')
  await expect(authenticatedPage.locator('h1')).toContainText('Profile')
})
```

## Authentication State

### Save Auth State (Global Setup)

```typescript
// global-setup.ts
import { chromium } from '@playwright/test'

async function globalSetup() {
  const browser = await chromium.launch()
  const page = await browser.newPage()

  // Perform login
  await page.goto('http://localhost:5173/login')
  await page.fill('[name=email]', 'admin@test.com')
  await page.fill('[name=password]', 'adminpassword')
  await page.click('button[type=submit]')
  await page.waitForURL('/dashboard')

  // Save storage state
  await page.context().storageState({ path: './auth.json' })
  await browser.close()
}

export default globalSetup
```

### Use Saved State

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  globalSetup: './global-setup.ts',
  projects: [
    {
      name: 'authenticated',
      use: { storageState: './auth.json' },
    },
    {
      name: 'unauthenticated',
      use: { storageState: undefined },
    },
  ],
})
```

## API Testing

### Direct API Calls

```typescript
import { test, expect } from '@playwright/test'

test('API returns users', async ({ request }) => {
  const response = await request.get('/api/users')

  expect(response.ok()).toBeTruthy()

  const users = await response.json()
  expect(users.length).toBeGreaterThan(0)
  expect(users[0]).toHaveProperty('email')
})

test('API creates user', async ({ request }) => {
  const response = await request.post('/api/users', {
    data: { name: 'John', email: 'john@test.com' },
  })

  expect(response.status()).toBe(201)

  const user = await response.json()
  expect(user.name).toBe('John')
})
```

### API + UI Combined

```typescript
test('user created via API appears in UI', async ({ page, request }) => {
  // Create via API
  await request.post('/api/users', {
    data: { name: 'Jane', email: 'jane@test.com' },
  })

  // Verify in UI
  await page.goto('/users')
  await expect(page.locator('text=jane@test.com')).toBeVisible()
})
```

## Visual Comparison

### Screenshot Comparison

```typescript
test('homepage matches snapshot', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveScreenshot('homepage.png')
})

test('button hover state', async ({ page }) => {
  await page.goto('/')
  await page.hover('button.primary')
  await expect(page.locator('button.primary')).toHaveScreenshot('button-hover.png')
})
```

### Update Screenshots

```bash
npx playwright test --update-snapshots
```

### Screenshot Options

```typescript
await expect(page).toHaveScreenshot('full-page.png', {
  fullPage: true,
  maxDiffPixels: 100,
})
```

## Debugging

### Debug Mode

```bash
npx playwright test --debug  # Step through with inspector
```

### Headed Mode

```bash
npx playwright test --headed  # See the browser
```

### Trace Viewer

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    trace: 'on-first-retry',  // Capture trace on failure
  },
})
```

```bash
npx playwright show-trace trace.zip
```

### Pause in Test

```typescript
test('debug this', async ({ page }) => {
  await page.goto('/')
  await page.pause()  // Opens inspector
  await page.click('button')
})
```

## Configuration

### Full Config Example

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'] } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

## Common Patterns

### Wait for Network Idle

```typescript
await page.goto('/', { waitUntil: 'networkidle' })
```

### Wait for Element

```typescript
await page.waitForSelector('[data-testid=loaded]')
await expect(page.locator('[data-testid=loaded]')).toBeVisible()
```

### Handle Dialogs

```typescript
page.on('dialog', async (dialog) => {
  expect(dialog.message()).toBe('Are you sure?')
  await dialog.accept()
})

await page.click('button.delete')
```

### File Upload

```typescript
await page.setInputFiles('input[type=file]', 'path/to/file.pdf')
```

### Keyboard/Mouse

```typescript
await page.keyboard.press('Enter')
await page.keyboard.type('Hello')
await page.mouse.click(100, 200)
```
