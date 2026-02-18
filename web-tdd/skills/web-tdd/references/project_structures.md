# project structures and common patterns

last updated: 2026-02-17

## directory structure

### react + node

```
my-project/
├── spec.md
├── README.md
├── .gitignore
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Button.tsx
│   │   │   └── Button.test.tsx
│   │   └── test/
│   │       └── setup.ts
│   ├── vitest.config.ts
│   └── package.json
├── backend/
│   ├── src/
│   │   └── routes/
│   │       └── users.ts
│   └── package.json
└── e2e/
    └── login.spec.ts
```

### react + python

```
my-project/
├── spec.md
├── README.md
├── .gitignore
├── frontend/
│   ├── src/
│   │   └── components/
│   ├── vitest.config.ts
│   └── package.json
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── tests/
│   │   └── test_api.py
│   └── pyproject.toml
└── e2e/
    └── login.spec.ts
```

## mocking external services

### AI/API calls (frontend)

```typescript
// Mock Gemini/OpenAI calls
vi.mock('../services/ai', () => ({
  generateResponse: vi.fn().mockResolvedValue({ text: 'Mocked response' })
}))
```

### database (python backend)

```python
# Use test database or mock
@pytest.fixture
async def test_db():
    # Setup test database
    yield db
    # Teardown
```

## common patterns

### testing loading states

```typescript
it('shows loading spinner while fetching', async () => {
  // Mock slow response
  vi.mocked(fetchData).mockImplementation(
    () => new Promise(resolve => setTimeout(resolve, 1000))
  )

  render(<DataList />)
  expect(screen.getByRole('progressbar')).toBeInTheDocument()
})
```

### testing error states

```typescript
it('shows error message on failure', async () => {
  vi.mocked(fetchData).mockRejectedValue(new Error('Network error'))

  render(<DataList />)
  await waitFor(() => {
    expect(screen.getByText(/error/i)).toBeInTheDocument()
  })
})
```

### testing mobile responsive

```typescript
// Playwright
test('sidebar collapses on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto('/')

  await expect(page.locator('[data-testid=sidebar]')).not.toBeVisible()
  await expect(page.locator('[data-testid=mobile-menu]')).toBeVisible()
})
```
