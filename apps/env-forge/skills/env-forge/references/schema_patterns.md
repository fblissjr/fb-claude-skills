# Schema Patterns for Environment Forge

SQLite schema design patterns extracted from the AWM synthesis pipeline. Use these when generating database schemas for new environments.

## Table Design Rules

### Primary Keys
- Every table has an explicit INTEGER PRIMARY KEY (usually `id`)
- Use AUTOINCREMENT only when gap-free sequences matter (rare)
- Composite keys for junction/association tables

### Foreign Keys
- Always declare FK constraints: `REFERENCES table_name(column_name)`
- Enable enforcement: `PRAGMA foreign_keys = ON;` at connection time
- Insert data in dependency order (parent tables first)

### Column Types
SQLite is loosely typed but use these for clarity:
- `INTEGER` -- IDs, counts, booleans (0/1), timestamps (epoch)
- `TEXT` -- strings, dates (ISO 8601), JSON blobs
- `REAL` -- prices, ratings, coordinates, percentages
- `BLOB` -- binary data (rare in tool environments)

### Timestamps
- Add `created_at TEXT DEFAULT (datetime('now'))` to all tables
- Add `updated_at TEXT` to tables with mutable records
- ISO 8601 format: `YYYY-MM-DD HH:MM:SS`

### Indexes
- Index all foreign keys
- Index columns used in WHERE/ORDER BY for common queries
- Composite index for multi-column filters: `CREATE INDEX idx_name ON table(col1, col2);`

## Authentication Exclusion

Environments assume a pre-authenticated user. Exclude from all schemas:
- `password_hash`, `password_salt`, `password`
- `auth_token`, `session_token`, `refresh_token`
- `session` tables, `oauth_*` tables
- `login_attempts`, `password_resets`

If a `users` table is needed, include only profile fields:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    bio TEXT,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
```

User with `id=1` is always the authenticated user. Create this user first in seed data.

## Common Schema Templates

### E-commerce Core

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    category TEXT,
    stock_quantity INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    image_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_amount REAL NOT NULL,
    shipping_address TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL
);

CREATE TABLE cart_items (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
```

### Booking/Reservation

```sql
CREATE TABLE venues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    city TEXT,
    capacity INTEGER,
    hourly_rate REAL,
    is_available INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    total_cost REAL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_venue_id ON bookings(venue_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_start_time ON bookings(start_time);
```

### Task/Project Management

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'archived', 'completed')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    description TEXT,
    assignee_id INTEGER REFERENCES users(id),
    status TEXT DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'review', 'done')),
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
    due_date TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_assignee_id ON tasks(assignee_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_comments_task_id ON comments(task_id);
```

## Seed Data Rules

### Insertion Order
Always insert in FK dependency order:
1. Independent tables (users, categories, tags)
2. First-level dependents (products, venues, projects)
3. Second-level dependents (orders, bookings, tasks)
4. Junction tables (order_items, tag_assignments)

### Coverage by Task Type

| Task Type | Data Strategy |
|-----------|--------------|
| SEARCH/FILTER | Diverse data: some matching, some not matching criteria |
| LIST/GET | 5-10+ records for meaningful results |
| CREATE/POST | All referenced FK entities must exist |
| UPDATE/PATCH | Existing records in modifiable state |
| DELETE | Expendable records (not referenced by FK) |
| AGGREGATION | Sufficient volume (20+) for meaningful stats |

### Data Quality

- Real product names, proper email formats, realistic prices
- Temporal diversity: records spread across dates
- Status variations: mix of active/inactive, pending/completed
- Numeric ranges: low/medium/high prices, quantities, ratings
- Text variations: short and long descriptions, different categories
- Timestamps in ISO 8601: `2024-01-15 09:30:00`
- User_id=1 owns most data; other users provide contrast

### Example Seed Data (E-commerce)

```sql
-- Users (id=1 is authenticated user)
INSERT INTO users (id, username, email, full_name) VALUES (1, 'current_user', 'user@example.com', 'Alex Johnson');
INSERT INTO users (id, username, email, full_name) VALUES (2, 'seller_jane', 'jane@shop.com', 'Jane Smith');
INSERT INTO users (id, username, email, full_name) VALUES (3, 'seller_bob', 'bob@store.com', 'Bob Wilson');

-- Products (diverse categories and price ranges)
INSERT INTO products (id, name, description, price, category, stock_quantity, rating) VALUES (1, 'MacBook Pro 14"', 'Apple M3 Pro chip, 18GB RAM', 1999.99, 'Electronics', 15, 4.8);
INSERT INTO products (id, name, description, price, category, stock_quantity, rating) VALUES (2, 'Ergonomic Office Chair', 'Lumbar support, adjustable height', 349.99, 'Furniture', 42, 4.5);
INSERT INTO products (id, name, description, price, category, stock_quantity, rating) VALUES (3, 'Running Shoes Nike Air', 'Lightweight, breathable mesh', 129.99, 'Sports', 88, 4.3);
```
