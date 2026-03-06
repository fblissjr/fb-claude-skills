---
description: Browse AWM-1K catalog of 1000 pre-built tool environments by category or keyword
argument-hint: "<category or search keyword>"
---

# /env-forge:browse

Browse and materialize pre-built tool environments from the AWM-1K catalog. 1000 environments across 28 domains, ready to launch with no generation needed.

## Usage

```
/env-forge:browse <category or keyword>
/env-forge:browse
```

Examples:
- `/env-forge:browse e-commerce` -- search for e-commerce environments
- `/env-forge:browse Healthcare/Medical` -- browse a specific category
- `/env-forge:browse booking hotel` -- keyword search
- `/env-forge:browse` -- list all categories

## Workflow

### 1. Search or Browse

If the user provides a keyword or category, search the catalog:

```bash
uv run python env-forge/scripts/catalog.py --search "<keyword>"
```

Or list categories:

```bash
uv run python env-forge/scripts/catalog.py --list-categories
```

Present results as a numbered list with scenario name and description excerpt.

### 2. User Selects a Scenario

The user picks a scenario by name or number. Show details:

```bash
uv run python env-forge/scripts/catalog.py --details <scenario_name>
```

Display:
- Full description
- Task list (10 tasks)
- Table count
- Endpoint count

### 3. Materialize

Once confirmed, materialize the environment:

```bash
uv run python env-forge/scripts/materialize.py --scenario <scenario_name>
```

This creates the full environment directory at `.env-forge/environments/<scenario_name>/`:
- `scenario.json` -- metadata and tasks
- `schema.sql` -- SQLite DDL
- `seed_data.sql` -- INSERT statements
- `api_spec.json` -- API specification
- `server.py` -- FastAPI + MCP server
- `verifiers.py` -- task verification functions
- `db/initial.db` + `db/current.db` -- seeded SQLite databases
- `pyproject.toml` -- environment dependencies

### 4. Report

After materialization, display:
- Environment path
- Number of tables and endpoints
- How to start the server: `cd .env-forge/environments/<name> && uv run python server.py`
- How to connect via MCP: `http://127.0.0.1:8000/mcp`
- List of available tasks for testing

## Categories

E-commerce/Marketplace, Booking/Reservation, Social/Community, Task/Project Management, Finance/Banking, Subscription/Membership, Inventory/Catalog, Messaging/Communication, Lists/Collections, Scheduling/Calendar, Forms/Surveys, Settings/Configuration, Healthcare/Medical, Education/Learning, Real Estate/Property, HR/Recruiting, Legal/Compliance, Logistics/Shipping, Food/Restaurant, Entertainment/Gaming, Fitness/Wellness, Travel/Hospitality, Automotive, IoT/Smart Devices, Developer Tools, CRM/Sales, Content Management, Analytics/Reporting.

## Notes

- First run downloads JSONL files from Hugging Face (cached for subsequent runs)
- Requires `huggingface_hub` package: `uv add huggingface_hub`
- No HF authentication needed -- the dataset is public
