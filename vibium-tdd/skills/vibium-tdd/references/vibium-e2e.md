# Vibium E2E Patterns

Advanced patterns for end-to-end browser testing with Vibium.

## Core API

Vibium provides both async and sync APIs. Use async for tests, sync for quick scripts.

### Async API (Recommended for Tests)

```typescript
import { browser } from 'vibium'

const vibe = await browser.launch()
await vibe.go('https://example.com')

const link = await vibe.find('a')
await link.click()

const png = await vibe.screenshot()
await vibe.quit()
```

### Sync API (Good for Scripts/REPL)

```typescript
import { browserSync } from 'vibium'

const vibe = browserSync.launch()
vibe.go('https://example.com')

const link = vibe.find('a')
link.click()

const png = vibe.screenshot()
vibe.quit()
```

## Element Interaction

### Finding Elements

```typescript
// CSS selectors
const button = await vibe.find('button.primary')
const input = await vibe.find('[name=email]')
const heading = await vibe.find('h1')
const testId = await vibe.find('[data-testid=submit]')
```

### Clicking

```typescript
const button = await vibe.find('button')
await button.click()
```

### Typing Text

```typescript
const input = await vibe.find('input[type=text]')
await input.type('Hello, world!')
```

### Getting Text Content

```typescript
const heading = await vibe.find('h1')
const text = await heading.text()
console.log(text)  // "Welcome"
```

## Navigation

### Go to URL

```typescript
await vibe.go('https://example.com')
await vibe.go('http://localhost:5173/login')
```

### Wait for Navigation

Vibium auto-waits for elements, but you can add explicit waits:

```typescript
await vibe.go('http://localhost:5173/login')

// Type credentials
await vibe.find('[name=email]').then(el => el.type('user@test.com'))
await vibe.find('[name=password]').then(el => el.type('password123'))
await vibe.find('button[type=submit]').then(el => el.click())

// The find() will auto-wait for element to appear
const dashboard = await vibe.find('[data-testid=dashboard]')
```

## Screenshots

### Capture Viewport

```typescript
const png = await vibe.screenshot()

// Save to file
import { writeFile } from 'fs/promises'
await writeFile('screenshot.png', png)
```

### Screenshot for Debugging

```typescript
import { browserSync } from 'vibium'
import { writeFileSync } from 'fs'

const vibe = browserSync.launch()
vibe.go('http://localhost:5173')

// Do some actions...
vibe.find('button').click()

// Screenshot to see current state
writeFileSync('debug.png', vibe.screenshot())

vibe.quit()
```

## Test Organization

### With Vitest

```typescript
// e2e/login.test.ts
import { browser } from 'vibium'
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'

describe('Login Flow', () => {
  let vibe: Awaited<ReturnType<typeof browser.launch>>

  beforeAll(async () => {
    vibe = await browser.launch()
  })

  afterAll(async () => {
    await vibe.quit()
  })

  afterEach(async () => {
    // Navigate away to reset state between tests
    await vibe.go('about:blank')
  })

  it('shows login form', async () => {
    await vibe.go('http://localhost:5173/login')

    const emailInput = await vibe.find('[name=email]')
    expect(emailInput).toBeDefined()
  })

  it('logs in with valid credentials', async () => {
    await vibe.go('http://localhost:5173/login')

    await (await vibe.find('[name=email]')).type('test@example.com')
    await (await vibe.find('[name=password]')).type('password123')
    await (await vibe.find('button[type=submit]')).click()

    const heading = await vibe.find('h1')
    const text = await heading.text()
    expect(text).toContain('Dashboard')
  })

  it('shows error for invalid credentials', async () => {
    await vibe.go('http://localhost:5173/login')

    await (await vibe.find('[name=email]')).type('wrong@example.com')
    await (await vibe.find('[name=password]')).type('wrongpass')
    await (await vibe.find('button[type=submit]')).click()

    const error = await vibe.find('[data-testid=error]')
    const text = await error.text()
    expect(text).toContain('Invalid')
  })
})
```

### Standalone Test Script

```typescript
// e2e/checkout.ts
import { browserSync } from 'vibium'
import { writeFileSync } from 'fs'

const vibe = browserSync.launch()

try {
  // Navigate to shop
  vibe.go('http://localhost:5173/shop')

  // Add item to cart
  vibe.find('[data-testid=add-to-cart]').click()

  // Go to checkout
  vibe.find('[data-testid=cart-icon]').click()
  vibe.find('[data-testid=checkout-btn]').click()

  // Fill checkout form
  vibe.find('[name=name]').type('John Doe')
  vibe.find('[name=email]').type('john@test.com')
  vibe.find('[name=card]').type('4242424242424242')

  // Screenshot before submit
  writeFileSync('before-submit.png', vibe.screenshot())

  // Submit
  vibe.find('button[type=submit]').click()

  // Verify success
  const confirmation = vibe.find('[data-testid=confirmation]')
  console.log('Success:', confirmation.text())

  // Screenshot after
  writeFileSync('after-submit.png', vibe.screenshot())

} catch (error) {
  // Screenshot on failure for debugging
  writeFileSync('error.png', vibe.screenshot())
  throw error
} finally {
  vibe.quit()
}
```

## Form Testing

### Fill Multiple Fields

```typescript
async function fillLoginForm(vibe: any, email: string, password: string) {
  await (await vibe.find('[name=email]')).type(email)
  await (await vibe.find('[name=password]')).type(password)
}

// Usage
await fillLoginForm(vibe, 'user@test.com', 'password123')
await (await vibe.find('button[type=submit]')).click()
```

### Form with Dropdowns

```typescript
// For native selects, click and find option
const select = await vibe.find('select[name=country]')
await select.click()
const option = await vibe.find('option[value=US]')
await option.click()
```

### Checkboxes and Radio Buttons

```typescript
// Click to toggle
const checkbox = await vibe.find('input[type=checkbox]')
await checkbox.click()

// Radio button
const radio = await vibe.find('input[value=express]')
await radio.click()
```

## Multi-Page Flows

### Shopping Cart Flow

```typescript
import { browser } from 'vibium'

async function testCheckoutFlow() {
  const vibe = await browser.launch()

  try {
    // 1. Browse products
    await vibe.go('http://localhost:5173/products')

    // 2. Add to cart
    const addBtn = await vibe.find('[data-testid=add-to-cart]')
    await addBtn.click()

    // 3. Go to cart
    const cartIcon = await vibe.find('[data-testid=cart]')
    await cartIcon.click()

    // 4. Proceed to checkout
    const checkoutBtn = await vibe.find('[data-testid=checkout]')
    await checkoutBtn.click()

    // 5. Fill shipping info
    await (await vibe.find('[name=address]')).type('123 Main St')
    await (await vibe.find('[name=city]')).type('New York')
    await (await vibe.find('[name=zip]')).type('10001')

    // 6. Submit order
    const submitBtn = await vibe.find('button[type=submit]')
    await submitBtn.click()

    // 7. Verify confirmation
    const confirmation = await vibe.find('[data-testid=order-number]')
    const orderNumber = await confirmation.text()
    console.log('Order placed:', orderNumber)

  } finally {
    await vibe.quit()
  }
}
```

## Error Handling

### Graceful Failure with Screenshots

```typescript
import { browser } from 'vibium'
import { writeFile } from 'fs/promises'

async function runTest() {
  const vibe = await browser.launch()

  try {
    await vibe.go('http://localhost:5173')
    // ... test steps ...
  } catch (error) {
    // Capture screenshot on failure
    const png = await vibe.screenshot()
    await writeFile(`failure-${Date.now()}.png`, png)
    throw error
  } finally {
    await vibe.quit()
  }
}
```

### Retry Pattern

```typescript
async function findWithRetry(vibe: any, selector: string, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await vibe.find(selector)
    } catch (e) {
      if (i === maxRetries - 1) throw e
      await new Promise(r => setTimeout(r, 1000))
    }
  }
}
```

## Python E2E Tests

### Basic Pattern

```python
from vibium import browser
import pytest

@pytest.fixture
async def vibe():
    v = await browser.launch()
    yield v
    await v.quit()

async def test_login(vibe):
    await vibe.go("http://localhost:5173/login")

    email = await vibe.find("[name=email]")
    await email.type("test@example.com")

    password = await vibe.find("[name=password]")
    await password.type("password123")

    submit = await vibe.find("button[type=submit]")
    await submit.click()

    heading = await vibe.find("h1")
    text = await heading.text()
    assert "Dashboard" in text
```

### Sync API with pytest

```python
from vibium import browser_sync as browser
import pytest

@pytest.fixture
def vibe():
    v = browser.launch()
    yield v
    v.quit()

def test_homepage(vibe):
    vibe.go("http://localhost:5173")
    heading = vibe.find("h1")
    assert "Welcome" in heading.text()
```

## MCP Integration

Vibium works seamlessly with Claude Code via MCP. Once configured:

```bash
claude mcp add vibium -- npx -y vibium
```

Claude can use browser tools directly:
- `browser_launch` - Start browser
- `browser_navigate` - Go to URL
- `browser_find` - Find element
- `browser_click` - Click element
- `browser_type` - Type text
- `browser_screenshot` - Capture viewport
- `browser_quit` - Close browser

This enables Claude to write and debug E2E tests interactively.

## Best Practices

### 1. Use Data-Testid Attributes

```html
<!-- In your components -->
<button data-testid="submit-btn">Submit</button>
```

```typescript
// In tests - stable selectors
const btn = await vibe.find('[data-testid=submit-btn]')
```

### 2. Keep Tests Independent

Each test should work in isolation. Don't rely on state from previous tests.

### 3. Screenshot on Failure

Always capture screenshots when tests fail - invaluable for debugging.

### 4. Start Fresh

Close and reopen the browser between test files, or navigate to `about:blank` between tests.

### 5. Wait for Elements

Vibium auto-waits, but be explicit when needed for reliability.

### 6. Use Descriptive Test Names

```typescript
it('shows error message when submitting empty form', async () => {
  // ...
})
```
