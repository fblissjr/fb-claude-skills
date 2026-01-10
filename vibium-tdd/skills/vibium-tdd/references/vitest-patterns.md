# Vitest Patterns

Advanced patterns for unit and component testing with Vitest.

## Component Testing

### React with Testing Library

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Counter } from './Counter'

describe('Counter', () => {
  it('starts at zero', () => {
    render(<Counter />)
    expect(screen.getByText('Count: 0')).toBeInTheDocument()
  })

  it('increments on click', async () => {
    const user = userEvent.setup()
    render(<Counter />)

    await user.click(screen.getByRole('button', { name: /increment/i }))

    expect(screen.getByText('Count: 1')).toBeInTheDocument()
  })

  it('calls onChange with new value', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()
    render(<Counter onChange={handleChange} />)

    await user.click(screen.getByRole('button', { name: /increment/i }))

    expect(handleChange).toHaveBeenCalledWith(1)
  })
})
```

### Vue with Vue Test Utils

```typescript
import { mount } from '@vue/test-utils'
import Counter from './Counter.vue'

describe('Counter', () => {
  it('renders initial count', () => {
    const wrapper = mount(Counter, { props: { initialCount: 5 } })
    expect(wrapper.text()).toContain('Count: 5')
  })

  it('increments on click', async () => {
    const wrapper = mount(Counter)
    await wrapper.find('button').trigger('click')
    expect(wrapper.text()).toContain('Count: 1')
  })

  it('emits update event', async () => {
    const wrapper = mount(Counter)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update')).toEqual([[1]])
  })
})
```

### Svelte with Testing Library

```typescript
import { render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import Counter from './Counter.svelte'

describe('Counter', () => {
  it('increments on click', async () => {
    const user = userEvent.setup()
    render(Counter)

    await user.click(screen.getByRole('button'))

    expect(screen.getByText('Count: 1')).toBeInTheDocument()
  })
})
```

## Fixtures and Setup

### beforeEach / afterEach

```typescript
import { beforeEach, afterEach, describe, it } from 'vitest'

describe('UserService', () => {
  let service: UserService
  let mockDb: MockDatabase

  beforeEach(() => {
    mockDb = createMockDatabase()
    service = new UserService(mockDb)
  })

  afterEach(() => {
    mockDb.clear()
  })

  it('creates a user', async () => {
    const user = await service.create({ name: 'John' })
    expect(user.id).toBeDefined()
  })
})
```

### Test Context

```typescript
import { beforeEach, it } from 'vitest'

interface TestContext {
  user: User
  token: string
}

beforeEach<TestContext>(async (context) => {
  context.user = await createTestUser()
  context.token = await generateToken(context.user)
})

it<TestContext>('fetches user profile', async ({ user, token }) => {
  const profile = await api.getProfile(token)
  expect(profile.id).toBe(user.id)
})
```

## Parameterized Tests

### it.each with Array

```typescript
it.each([
  [1, 2, 3],
  [0, 0, 0],
  [-1, 1, 0],
  [100, 200, 300],
])('add(%i, %i) returns %i', (a, b, expected) => {
  expect(add(a, b)).toBe(expected)
})
```

### it.each with Objects

```typescript
it.each([
  { input: 'hello', expected: 'HELLO' },
  { input: 'World', expected: 'WORLD' },
  { input: '', expected: '' },
])('toUpperCase($input) returns $expected', ({ input, expected }) => {
  expect(input.toUpperCase()).toBe(expected)
})
```

### describe.each for Test Suites

```typescript
describe.each([
  { currency: 'USD', symbol: '$' },
  { currency: 'EUR', symbol: '...' },
  { currency: 'GBP', symbol: '...' },
])('formatCurrency with $currency', ({ currency, symbol }) => {
  it('includes currency symbol', () => {
    expect(formatCurrency(100, currency)).toContain(symbol)
  })
})
```

## Mocking

### Mock Modules

```typescript
import { vi } from 'vitest'
import { fetchUser } from './api'

// Mock entire module
vi.mock('./api', () => ({
  fetchUser: vi.fn().mockResolvedValue({ id: 1, name: 'John' }),
  fetchUsers: vi.fn().mockResolvedValue([]),
}))

// In test
it('uses mocked API', async () => {
  const user = await fetchUser(1)
  expect(user.name).toBe('John')
})
```

### Spy on Methods

```typescript
import { vi } from 'vitest'

const spy = vi.spyOn(console, 'log')

it('logs message', () => {
  myFunction()
  expect(spy).toHaveBeenCalledWith('Expected message')
})
```

### Mock Implementations

```typescript
const mockFetch = vi.fn()
  .mockResolvedValueOnce({ id: 1 })  // First call
  .mockResolvedValueOnce({ id: 2 })  // Second call
  .mockRejectedValueOnce(new Error('Network error'))  // Third call
```

### Reset Mocks Between Tests

```typescript
beforeEach(() => {
  vi.clearAllMocks()  // Clear call history
  // or
  vi.resetAllMocks()  // Clear history + reset implementations
})
```

## Snapshot Testing

### Basic Snapshot

```typescript
it('renders correctly', () => {
  const { container } = render(<Header title="Welcome" />)
  expect(container).toMatchSnapshot()
})
```

### Inline Snapshot

```typescript
it('formats date', () => {
  expect(formatDate(new Date('2024-01-15'))).toMatchInlineSnapshot('"Jan 15, 2024"')
})
```

### Update Snapshots

```bash
npx vitest -u  # Update all snapshots
```

## Coverage

### Configuration

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['**/*.test.ts', 'test/**'],
    },
  },
})
```

### Run with Coverage

```bash
npx vitest run --coverage
```

### Coverage Thresholds

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      thresholds: {
        lines: 80,
        branches: 80,
        functions: 80,
        statements: 80,
      },
    },
  },
})
```

## Testing Hooks (React)

```typescript
import { renderHook, act } from '@testing-library/react'
import { useCounter } from './useCounter'

describe('useCounter', () => {
  it('increments counter', () => {
    const { result } = renderHook(() => useCounter())

    act(() => {
      result.current.increment()
    })

    expect(result.current.count).toBe(1)
  })

  it('accepts initial value', () => {
    const { result } = renderHook(() => useCounter(10))
    expect(result.current.count).toBe(10)
  })
})
```

## Testing Stores (Zustand/Pinia)

### Zustand

```typescript
import { useStore } from './store'

beforeEach(() => {
  useStore.setState({ count: 0 })  // Reset between tests
})

it('increments store count', () => {
  const { increment } = useStore.getState()
  increment()
  expect(useStore.getState().count).toBe(1)
})
```

### Pinia

```typescript
import { setActivePinia, createPinia } from 'pinia'
import { useCounterStore } from './counter'

beforeEach(() => {
  setActivePinia(createPinia())
})

it('increments', () => {
  const counter = useCounterStore()
  counter.increment()
  expect(counter.count).toBe(1)
})
```
