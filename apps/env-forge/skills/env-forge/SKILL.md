---
name: env-forge
description: Generate database-backed MCP tool environments from scenario descriptions or browse 1000 pre-built environments. Use when user says "generate a tool environment", "create an MCP backend", "scaffold database tools", "build a sandbox", "synthesize an environment", "launch an environment", "browse environments", "AWM catalog", "create API tools", "generate test tools", "tool environment for", "database-backed tools", "sandbox for agent testing", or "create tools for".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-02-25
allowed-tools: "Bash(uv run *), Bash(mkdir *), Bash(sqlite3 *), Read, Write, Glob, Grep, Edit"
---

# env-forge -- Environment Design Methodology

Claude Code interface for the [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) synthesis pipeline from Snowflake Labs. Generates self-contained, database-backed tool environments exposed via MCP. Each environment is a complete FastAPI + SQLite stack with typed endpoints, seed data, and task verification functions. The synthesis methodology, output format, and task-first design principle are from AWM.

Two modes:
- **Browse**: Pick from 1000 pre-generated environments across 28 domains (AWM-1K catalog)
- **Forge**: Generate a new environment from a scenario description

## Core Insight: Task-First Design

The key methodology: **tasks drive schema, not the reverse.**

Traditional approach: design tables -> build API -> hope tasks work.
Task-first approach: define user tasks -> derive schema from tasks -> design API to support tasks -> generate verification from tasks.

This produces environments where every table column and every API endpoint exists because a task needs it. No dead schema, no unused endpoints.

## Environment Anatomy

Every environment has three layers:

| Layer | Implementation | Purpose |
|-------|---------------|---------|
| State | SQLite database | Persistent, queryable, diffable |
| Interface | FastAPI + fastapi-mcp | Typed tools with OpenAPI metadata |
| Verification | Python functions | DB state comparison for task completion |

The state layer is the source of truth. Tools read and write state. Verification compares state snapshots (before vs after tool execution).

## Synthesis Pipeline

When forging a new environment, follow these steps in order. Each step produces a file in the output directory.

### Step 1: Define Scenario

Write a clear description of the platform/domain. Include:
- What entities exist (users, products, orders, etc.)
- What relationships connect them
- What workflows users perform

### Step 2: Generate Tasks (10 per scenario)

Generate 10 realistic, diverse user tasks that cover:
- CRUD operations (create, read, update, delete)
- Search and filtering
- Aggregation and reporting
- Multi-step workflows
- Edge cases

Each task is a single sentence with all parameters included. Example: "Search for laptops under $500 and add the cheapest one to the cart."

Tasks must NOT include authentication (assume user is logged in as user_id=1), file downloads, or page navigation.

### Step 3: Generate Schema

Design SQLite tables to support ALL tasks. Rules:
- Proper primary keys, foreign keys, indexes, constraints
- Use SQLite types: TEXT, INTEGER, REAL, BLOB
- Add timestamps (created_at, updated_at) where appropriate
- Exclude authentication fields (password_hash, salt, token, session)
- Users table has essential profile fields only (id, username, email)
- All operations as authenticated user_id=1

Full patterns: `references/schema_patterns.md`

### Step 4: Generate Seed Data

Write INSERT statements that make every task executable. Coverage rules:
- SEARCH tasks: diverse data matching AND not matching criteria
- LIST tasks: 5-10+ records for meaningful results
- CREATE tasks: all referenced entities exist
- UPDATE tasks: existing records to modify
- DELETE tasks: expendable records
- AGGREGATION tasks: sufficient volume for meaningful stats

Data uses realistic values: real product names, proper formats, temporal diversity, status variations.

Full patterns: `references/schema_patterns.md`

### Step 5: Generate API Specification

Design RESTful endpoints for all tasks. Rules:
- Atomic endpoints: each does ONE operation
- Maximize reusability: base CRUD that composes
- Follow exact schema names (tables, columns)
- RESTful conventions (GET/POST/PUT/DELETE/PATCH)
- Group by resource type
- No auth endpoints
- User-specific data filters by user_id=1 automatically

Every endpoint requires: summary (80 chars max), description (200 chars max, single line), operation_id (snake_case), tags, typed request_params, typed response schema.

Full patterns: `references/api_design_rules.md`

### Step 6: Generate Server Code

Produce a complete, executable FastAPI application. Stack:
- FastAPI + fastapi-mcp for MCP tool exposure
- SQLAlchemy ORM (no raw SQL)
- Pydantic v2 for request/response models
- SQLite via DATABASE_PATH env var

All endpoint handlers are async and self-contained. Session lifecycle: create -> work -> commit (for writes) -> close.

Full template: `references/fastapi_mcp_template.md`

### Step 7: Generate Verification Functions

For each task, write a Python function that determines completion by comparing DB state:

```python
def verify_task(initial_db_path: str, final_db_path: str) -> dict:
    # Connect to both databases
    # Query relevant tables
    # Compare state
    # Return diagnostic dict
```

Two verification strategies:
- **Modification tasks** (add, update, delete): compare initial vs final DB
- **Query tasks** (find, list, get): check final_answer content against DB

Full patterns: `references/verification_patterns.md`

## Self-Correction Pattern

When generation fails (syntax errors, import errors, schema mismatches):

1. Capture the full traceback
2. Summarize the error: what failed, why, what the fix should be
3. Retry generation with the error summary appended to the prompt
4. Maximum 3 retries before escalating to the user

This applies to schema generation, server code generation, and data insertion.

## Suitability Assessment

Not every domain produces useful synthetic environments. Data must be realistically fakeable:

| Synthesizable | NOT Synthesizable |
|--------------|-------------------|
| Numeric values (prices, ratings, coordinates) | Long-form content (articles, blogs) |
| Structured entities (users, products, orders) | Media content (actual video/audio/images) |
| Status/state values | AI inference results |
| Short text (names, titles, descriptions) | Search ranking algorithms |
| Dates, timestamps | Real-time external feeds |
| Geographic data (cities, coordinates) | |

If a scenario requires non-synthesizable data as its core (e.g., "a blog platform" where posts ARE the product), flag it. The environment will have placeholder text that cannot meaningfully exercise search or recommendation tasks.

## Domain Categories (28)

The AWM-1K catalog covers: E-commerce/Marketplace, Booking/Reservation, Social/Community, Task/Project Management, Finance/Banking, Subscription/Membership, Inventory/Catalog, Messaging/Communication, Lists/Collections, Scheduling/Calendar, Forms/Surveys, Settings/Configuration, Healthcare/Medical, Education/Learning, Real Estate/Property, HR/Recruiting, Legal/Compliance, Logistics/Shipping, Food/Restaurant, Entertainment/Gaming, Fitness/Wellness, Travel/Hospitality, Automotive, IoT/Smart Devices, Developer Tools, CRM/Sales, Content Management, Analytics/Reporting.

Full index: `references/catalog_index.md`

## Output Structure

```
.env-forge/environments/<name>/
  scenario.json     # Metadata + task list
  schema.sql        # SQLite DDL
  seed_data.sql     # INSERT statements
  api_spec.json     # API specification
  server.py         # FastAPI + fastapi-mcp (runnable)
  verifiers.py      # Task verification functions
  db/
    initial.db      # Seeded (backup)
    current.db      # Working (mutated by tools)
  pyproject.toml    # Environment dependencies
```

## Scripts

```bash
# Browse catalog
uv run python env-forge/scripts/catalog.py --search "e-commerce"

# Materialize from catalog
uv run python env-forge/scripts/materialize.py --scenario e_commerce_33

# Validate environment structure
uv run python env-forge/scripts/validate_env.py .env-forge/environments/e_commerce_33/
```

## References

| Reference | Purpose |
|-----------|---------|
| `references/schema_patterns.md` | SQLite schema patterns with examples |
| `references/api_design_rules.md` | RESTful API spec patterns and rules |
| `references/verification_patterns.md` | DB state comparison verification |
| `references/fastapi_mcp_template.md` | Server code template (FastAPI + fastapi-mcp + SQLAlchemy) |
| `references/catalog_index.md` | AWM-1K scenario index by category |
