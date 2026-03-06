---
description: Generate a new database-backed MCP tool environment from a scenario description
argument-hint: "<description of the platform/domain>"
---

# /env-forge:forge

Interactive environment generation. Walks through the full synthesis pipeline: scenario description -> tasks -> schema -> seed data -> API spec -> server code -> verifiers. Each step produces a file in the output directory.

## Usage

```
/env-forge:forge <description of the platform/domain>
/env-forge:forge
```

Examples:
- `/env-forge:forge a volunteer matching platform where organizations post opportunities and volunteers sign up based on skills and availability`
- `/env-forge:forge pet adoption agency with animal profiles, applications, foster homes, and veterinary records`
- `/env-forge:forge` then describe the domain interactively

## Workflow

### 1. Scenario Definition

If the user provides a description, refine it. If not, ask:
- What domain/platform is this?
- What entities exist (users, products, orders, etc.)?
- What are the main workflows?
- What relationships connect entities?

Write the scenario to `.env-forge/environments/<name>/scenario.json`:
```json
{
  "name": "volunteer_match",
  "description": "A volunteer matching platform where...",
  "tasks": [],
  "created_at": "2026-02-23T12:00:00Z"
}
```

### 2. Reference from Catalog

Before generating from scratch, search the AWM-1K catalog for a structurally similar domain:

```bash
uv run python env-forge/scripts/catalog.py --search "<domain keywords>"
```

If a close match exists, review its structure with `--details`:
- Task list (coverage patterns, complexity mix)
- Table structure (entity relationships, column conventions)
- Endpoint design (REST patterns, operation naming)

Use the closest match as a structural reference -- adapt its patterns to the new domain, don't copy verbatim. If no match is close enough, proceed from scratch.

### 3. Task Generation

Generate 10 realistic, diverse tasks following the task-first methodology from the **env-forge** skill. Each task is a single sentence with all parameters included.

Coverage requirements:
- Mix of CRUD operations
- Search and filtering tasks
- At least one aggregation/reporting task
- At least one multi-step task
- Vary complexity from beginner to advanced

Present tasks to user for review. Allow additions, removals, or modifications. Update `scenario.json` with finalized task list.

### 4. Schema Generation

Design SQLite tables to support ALL tasks. Follow patterns in `references/schema_patterns.md`:
- Proper PKs, FKs, indexes, constraints
- SQLite types (TEXT, INTEGER, REAL)
- Timestamps where appropriate
- No auth fields
- User_id=1 is authenticated user

Write DDL to `.env-forge/environments/<name>/schema.sql`.
Present table list and relationships to user for review.

### 5. Seed Data Generation

Generate INSERT statements that make every task executable. Follow coverage rules in `references/schema_patterns.md`:
- User_id=1 first
- FK dependency order
- Realistic values
- Sufficient volume per task type

Write to `.env-forge/environments/<name>/seed_data.sql`.

### 6. API Specification

Design RESTful endpoints for all tasks. Follow `references/api_design_rules.md`:
- Atomic endpoints (one operation each)
- Full metadata (summary, description, operation_id, tags)
- Typed params and responses
- No auth endpoints

Write to `.env-forge/environments/<name>/api_spec.json`.
Present endpoint list to user for review.

### 7. Server Code Generation

Generate complete, executable FastAPI application. Follow `references/fastapi_mcp_template.md`:
- SQLAlchemy ORM models matching schema
- Pydantic v2 request/response models
- Async endpoint handlers
- fastapi-mcp integration

Write to `.env-forge/environments/<name>/server.py`.

### 8. Verification Functions

Generate verification functions for each task. Follow `references/verification_patterns.md`:
- Modification-based for CRUD tasks
- Query-based for search/list tasks
- Combined for multi-step tasks

Write to `.env-forge/environments/<name>/verifiers.py`.

### 9. Database Creation

Create and seed the SQLite databases:

```bash
mkdir -p .env-forge/environments/<name>/db
sqlite3 .env-forge/environments/<name>/db/current.db < .env-forge/environments/<name>/schema.sql
sqlite3 .env-forge/environments/<name>/db/current.db < .env-forge/environments/<name>/seed_data.sql
cp .env-forge/environments/<name>/db/current.db .env-forge/environments/<name>/db/initial.db
```

### 10. Dependency File

Write `pyproject.toml` for the environment:

```toml
[project]
name = "env-forge-<name>"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "sqlalchemy>=2.0.0",
    "fastapi-mcp>=0.3.0",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 11. Validation

Run structural validation:

```bash
uv run python env-forge/scripts/validate_env.py .env-forge/environments/<name>/
```

### 12. Report

Display:
- Environment path
- Table count and names
- Endpoint count and operation_ids
- Task list
- How to start: `cd .env-forge/environments/<name> && uv run python server.py`
- How to test: run tasks against MCP tools, then verify with `verifiers.py`

## Self-Correction

If any generation step produces errors (syntax, import, schema mismatch):
1. Capture the error/traceback
2. Summarize: what failed, why, what the fix should be
3. Regenerate that step with the error context
4. Maximum 3 retries before asking the user for guidance

## Suitability Check

Before starting, assess whether the domain produces useful synthetic environments. Flag if the domain's core value depends on non-synthesizable data (long-form content, media, AI inference, real-time feeds). See the suitability table in the **env-forge** skill.

## Output

Full environment directory at `.env-forge/environments/<name>/` with all files listed above. The environment is self-contained and runnable.
