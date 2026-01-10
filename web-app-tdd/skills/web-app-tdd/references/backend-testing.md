# Backend Testing

Patterns for testing Node.js backends and integrating with separate backend servers.

## Node.js with Supertest

### Basic Express Testing

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import request from 'supertest'
import { createApp } from './app'

let app: Express

beforeAll(async () => {
  app = await createApp()
})

describe('Users API', () => {
  describe('GET /api/users', () => {
    it('returns list of users', async () => {
      const res = await request(app).get('/api/users')

      expect(res.status).toBe(200)
      expect(res.body).toBeInstanceOf(Array)
    })

    it('supports pagination', async () => {
      const res = await request(app)
        .get('/api/users')
        .query({ page: 1, limit: 10 })

      expect(res.status).toBe(200)
      expect(res.body.length).toBeLessThanOrEqual(10)
    })
  })

  describe('POST /api/users', () => {
    it('creates a new user', async () => {
      const res = await request(app)
        .post('/api/users')
        .send({ name: 'John', email: 'john@test.com' })

      expect(res.status).toBe(201)
      expect(res.body.name).toBe('John')
      expect(res.body.id).toBeDefined()
    })

    it('validates required fields', async () => {
      const res = await request(app)
        .post('/api/users')
        .send({ name: 'John' })  // Missing email

      expect(res.status).toBe(400)
      expect(res.body.error).toContain('email')
    })
  })

  describe('GET /api/users/:id', () => {
    it('returns user by id', async () => {
      const res = await request(app).get('/api/users/1')

      expect(res.status).toBe(200)
      expect(res.body.id).toBe(1)
    })

    it('returns 404 for unknown user', async () => {
      const res = await request(app).get('/api/users/99999')

      expect(res.status).toBe(404)
    })
  })
})
```

### Testing Authentication

```typescript
describe('Protected routes', () => {
  let authToken: string

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: 'admin@test.com', password: 'password' })

    authToken = res.body.token
  })

  it('allows access with valid token', async () => {
    const res = await request(app)
      .get('/api/admin/users')
      .set('Authorization', `Bearer ${authToken}`)

    expect(res.status).toBe(200)
  })

  it('denies access without token', async () => {
    const res = await request(app).get('/api/admin/users')

    expect(res.status).toBe(401)
  })
})
```

## Database Testing

### Test Database Strategy

Use a separate test database or in-memory database.

```typescript
// test/setup.ts
import { db } from '../src/database'

beforeAll(async () => {
  // Use test database
  process.env.DATABASE_URL = 'postgres://localhost/myapp_test'
  await db.connect()
})

beforeEach(async () => {
  // Reset to known state
  await db.migrate.rollback()
  await db.migrate.latest()
  await db.seed.run()
})

afterAll(async () => {
  await db.destroy()
})
```

### In-Memory SQLite

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    env: {
      DATABASE_URL: ':memory:',
    },
  },
})
```

### Mocking the Database Layer

```typescript
import { vi } from 'vitest'

vi.mock('../src/database', () => ({
  users: {
    findAll: vi.fn().mockResolvedValue([
      { id: 1, name: 'Test User', email: 'test@example.com' },
    ]),
    findById: vi.fn().mockImplementation((id) =>
      id === 1
        ? { id: 1, name: 'Test User' }
        : null
    ),
    create: vi.fn().mockImplementation((data) => ({
      id: 2,
      ...data,
    })),
  },
}))
```

## Integration Testing

### Full Stack Test

```typescript
describe('User registration flow', () => {
  it('creates user and sends welcome email', async () => {
    // Mock email service
    const sendEmail = vi.fn()
    vi.spyOn(emailService, 'send').mockImplementation(sendEmail)

    // Hit the API
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'new@test.com',
        password: 'secure123',
        name: 'New User',
      })

    expect(res.status).toBe(201)

    // Verify in database
    const user = await db.users.findByEmail('new@test.com')
    expect(user).toBeDefined()
    expect(user.name).toBe('New User')

    // Verify email sent
    expect(sendEmail).toHaveBeenCalledWith(
      expect.objectContaining({
        to: 'new@test.com',
        subject: expect.stringContaining('Welcome'),
      })
    )
  })
})
```

### Testing with External Services

```typescript
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Mock external API
const server = setupServer(
  http.get('https://api.stripe.com/v1/customers', () => {
    return HttpResponse.json({ data: [{ id: 'cus_123' }] })
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

it('fetches stripe customers', async () => {
  const res = await request(app).get('/api/billing/customers')
  expect(res.body[0].id).toBe('cus_123')
})
```

## FastAPI (Python)

For Python backends, use pytest. See the **uv-tdd** skill for full patterns.

### Basic Pattern

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_read_users():
    response = client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_user():
    response = client.post("/api/users", json={
        "name": "John",
        "email": "john@test.com"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "John"

@pytest.fixture
def auth_token():
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password"
    })
    return response.json()["token"]

def test_protected_route(auth_token):
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
```

## Frontend Mocking Backend

When testing frontend with a separate backend:

### MSW (Mock Service Worker)

```typescript
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: 1, name: 'John' },
      { id: 2, name: 'Jane' },
    ])
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ id: 3, ...body }, { status: 201 })
  }),
]
```

```typescript
// src/mocks/server.ts (for Vitest)
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```typescript
// vitest.setup.ts
import { server } from './src/mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### Override Handlers in Tests

```typescript
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

it('handles API error', async () => {
  server.use(
    http.get('/api/users', () => {
      return HttpResponse.json({ error: 'Server error' }, { status: 500 })
    })
  )

  render(<UserList />)
  await expect(screen.findByText('Error loading users')).resolves.toBeVisible()
})
```
