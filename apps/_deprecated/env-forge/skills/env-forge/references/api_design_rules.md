# API Design Rules for Environment Forge

RESTful API specification patterns for generating agent-friendly tool endpoints. Every API endpoint becomes an MCP tool -- design for machine consumption, not human browsing.

## Core Principles

### Atomic Endpoints
Each endpoint does ONE specific, well-defined operation. Prefer multiple small composable endpoints over fewer complex ones. For complex tasks, design individual atomic operations that can be chained by the agent.

### Schema Alignment
API MUST follow the database schema exactly:
- Use exact table names and column names
- Respect all relationships and constraints
- Map endpoints to tables (one CRUD set per entity)

### RESTful Conventions

| Operation | Method | Path Pattern | Example |
|-----------|--------|-------------|---------|
| List | GET | `/api/{resource}` | `GET /api/products` |
| Get one | GET | `/api/{resource}/{id}` | `GET /api/products/42` |
| Create | POST | `/api/{resource}` | `POST /api/products` |
| Full update | PUT | `/api/{resource}/{id}` | `PUT /api/products/42` |
| Partial update | PATCH | `/api/{resource}/{id}` | `PATCH /api/products/42` |
| Delete | DELETE | `/api/{resource}/{id}` | `DELETE /api/products/42` |
| Search | GET | `/api/{resource}/search` | `GET /api/products/search?q=laptop` |

### Authentication Handling
- No auth endpoints (login, logout, register, token refresh)
- All user-specific operations implicitly filter by `user_id=1`
- Endpoints that create user-owned resources automatically set `user_id=1`

## Endpoint Specification Format

Every endpoint requires these metadata fields for agent discoverability:

```json
{
  "path": "/api/products/search",
  "method": "GET",
  "summary": "Search products by name or category",
  "description": "Search for products matching a query string. Returns matching products sorted by relevance. Use when agent needs to find specific products.",
  "operation_id": "search_products",
  "tags": ["products"],
  "request_params": {
    "q": {
      "type": "string",
      "param_type": "query",
      "required": true,
      "description": "Search query to match against product names and descriptions",
      "example": "laptop"
    },
    "category": {
      "type": "string",
      "param_type": "query",
      "required": false,
      "description": "Filter by product category",
      "example": "Electronics"
    },
    "min_price": {
      "type": "number",
      "param_type": "query",
      "required": false,
      "description": "Minimum price filter",
      "example": 100.0
    },
    "max_price": {
      "type": "number",
      "param_type": "query",
      "required": false,
      "description": "Maximum price filter",
      "example": 500.0
    },
    "limit": {
      "type": "integer",
      "param_type": "query",
      "required": false,
      "description": "Maximum number of results to return",
      "example": 10
    }
  },
  "response": {
    "products": {
      "type": "array",
      "description": "List of matching products",
      "items": {
        "id": {"type": "integer", "description": "Product ID", "example": 1},
        "name": {"type": "string", "description": "Product name", "example": "MacBook Pro"},
        "price": {"type": "number", "description": "Price in USD", "example": 1999.99},
        "category": {"type": "string", "description": "Product category", "example": "Electronics"},
        "rating": {"type": "number", "description": "Average rating", "example": 4.5}
      }
    },
    "total_count": {
      "type": "integer",
      "description": "Total number of matching products",
      "example": 15
    }
  },
  "required_tables": ["products"],
  "required_fields": {
    "products": ["id", "name", "price", "category", "description", "rating"]
  }
}
```

## Metadata Field Rules

### summary (required)
- Maximum 80 characters
- One-line purpose statement
- Clear and actionable for AI agents
- Examples: "Search products by name or category", "Add item to user's cart", "Get order details by ID"

### description (required)
- Maximum 200 characters, SINGLE LINE (no line breaks)
- Explains what the endpoint does AND when to use it
- Include the agent's perspective: "Use when agent needs to..."

### operation_id (required)
- Unique across all endpoints
- snake_case format
- Pattern: `{verb}_{resource}` or `{verb}_{resource}_by_{field}`
- Examples: `list_products`, `create_order`, `search_products_by_category`, `get_user_cart`

### tags (required)
- Logical grouping array
- Usually the resource name: `["products"]`, `["orders"]`
- Enables agents to discover related endpoints

### request_params (required when params exist)
Each parameter specifies:
- `type`: string, integer, number, boolean, array, object
- `param_type`: "query", "path", or "body"
- `required`: boolean
- `description`: what the parameter controls
- `example`: realistic example value

### response (required)
- Complete response structure with ALL returned fields
- Each field: type, description, example
- For arrays: include `items` with full field definitions
- Consistent naming across all endpoints

## API Group Organization

Group endpoints by resource/domain area:

```json
{
  "api_groups": [
    {
      "group_name": "Products",
      "endpoints": [
        {"path": "/api/products", "method": "GET", "operation_id": "list_products"},
        {"path": "/api/products/{product_id}", "method": "GET", "operation_id": "get_product"},
        {"path": "/api/products", "method": "POST", "operation_id": "create_product"},
        {"path": "/api/products/{product_id}", "method": "PUT", "operation_id": "update_product"},
        {"path": "/api/products/{product_id}", "method": "DELETE", "operation_id": "delete_product"},
        {"path": "/api/products/search", "method": "GET", "operation_id": "search_products"}
      ]
    },
    {
      "group_name": "Cart",
      "endpoints": [
        {"path": "/api/cart", "method": "GET", "operation_id": "get_cart"},
        {"path": "/api/cart/items", "method": "POST", "operation_id": "add_to_cart"},
        {"path": "/api/cart/items/{item_id}", "method": "DELETE", "operation_id": "remove_from_cart"},
        {"path": "/api/cart/items/{item_id}", "method": "PATCH", "operation_id": "update_cart_item_quantity"}
      ]
    }
  ]
}
```

## Design Patterns for Task Coverage

### Search Tasks
Provide search endpoints with flexible parameters:
- Text search (name, description)
- Category/type filter
- Numeric range filters (price, rating)
- Date range filters
- Sort and limit parameters

### Multi-Step Tasks
Break into composable atomic calls. Example for "Find cheapest laptop and add to cart":
1. `GET /api/products/search?q=laptop&sort=price_asc&limit=1`
2. `POST /api/cart/items` with `{"product_id": <result_id>, "quantity": 1}`

### Aggregation Tasks
Provide summary/stats endpoints:
- `GET /api/products/stats` -- count, avg price by category
- `GET /api/orders/summary` -- total orders, revenue by status
- `GET /api/users/{id}/activity` -- user engagement metrics

### State Transition Tasks
Use PATCH for status updates with validation:
- `PATCH /api/orders/{id}` with `{"status": "shipped"}`
- Status transitions should be validated in server code
