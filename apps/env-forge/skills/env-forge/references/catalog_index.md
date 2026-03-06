# AWM-1K Catalog Index

The AWM-1K dataset contains 1000 pre-generated tool environments across 28 domain categories. Each environment includes: scenario description, 10 user tasks, SQLite schema, seed data, API specification, FastAPI server code, and verification functions.

Source: [Snowflake/AgentWorldModel-1K](https://huggingface.co/datasets/Snowflake/AgentWorldModel-1K) on Hugging Face.

## Categories

| # | Category | Description |
|---|----------|-------------|
| 1 | E-commerce/Marketplace | Online stores, product catalogs, shopping carts, order management |
| 2 | Booking/Reservation | Venue booking, appointment scheduling, resource reservation |
| 3 | Social/Community | Forums, social networks, user profiles, content sharing |
| 4 | Task/Project Management | Task boards, project tracking, team collaboration, sprints |
| 5 | Finance/Banking | Accounts, transactions, budgets, investment portfolios |
| 6 | Subscription/Membership | Plans, billing cycles, member benefits, renewals |
| 7 | Inventory/Catalog | Stock management, warehousing, product catalogs, SKUs |
| 8 | Messaging/Communication | Chat, notifications, email threads, message queues |
| 9 | Lists/Collections | Wishlists, playlists, reading lists, curated collections |
| 10 | Scheduling/Calendar | Events, meetings, availability, recurring schedules |
| 11 | Forms/Surveys | Form builders, survey responses, questionnaires, polls |
| 12 | Settings/Configuration | User preferences, system config, feature flags, profiles |
| 13 | Healthcare/Medical | Patient records, appointments, prescriptions, vitals |
| 14 | Education/Learning | Courses, enrollments, grades, assignments, quizzes |
| 15 | Real Estate/Property | Listings, tours, leases, property management |
| 16 | HR/Recruiting | Job postings, applications, interviews, employee records |
| 17 | Legal/Compliance | Contracts, cases, compliance checks, document management |
| 18 | Logistics/Shipping | Shipments, tracking, warehouses, delivery routes |
| 19 | Food/Restaurant | Menus, orders, reservations, delivery, recipes |
| 20 | Entertainment/Gaming | Games, scores, achievements, media libraries |
| 21 | Fitness/Wellness | Workouts, meal plans, health tracking, goals |
| 22 | Travel/Hospitality | Hotels, flights, itineraries, reviews, travel plans |
| 23 | Automotive | Vehicles, maintenance, parts, dealers, service records |
| 24 | IoT/Smart Devices | Devices, sensors, automation rules, telemetry |
| 25 | Developer Tools | Repositories, CI/CD, issue tracking, deployments |
| 26 | CRM/Sales | Contacts, deals, pipelines, sales activities |
| 27 | Content Management | Articles, pages, media, publishing workflows |
| 28 | Analytics/Reporting | Dashboards, metrics, reports, data exports |

## Dataset Files

The AWM-1K dataset is stored as JSONL files on Hugging Face:

| File | Content | Fields |
|------|---------|--------|
| `gen_scenario.jsonl` | Scenario descriptions | name, description |
| `gen_tasks.jsonl` | User tasks (10 per scenario) | scenario, tasks[] |
| `gen_db.jsonl` | Database schemas | scenario, db_schema.tables[].name/ddl/indexes |
| `gen_sample.jsonl` | Seed data | scenario, sample_data.tables[].table_name/insert_statements[] |
| `gen_spec.jsonl` | API specifications | scenario, api_spec.api_groups[].endpoints[] |
| `gen_envs.jsonl` | Server code | scenario, environment.code/port |
| `gen_verifier.jsonl` | Verification (LLM judge) | scenario, task_idx, verification.code/reasoning |
| `gen_verifier.pure_code.jsonl` | Verification (code judge) | scenario, task_idx, verification.code/strategy |

## Browsing the Catalog

Use `catalog.py` to search and browse:

```bash
# List all categories
uv run python env-forge/scripts/catalog.py --list-categories

# Search by keyword
uv run python env-forge/scripts/catalog.py --search "e-commerce"
uv run python env-forge/scripts/catalog.py --search "booking hotel"

# Filter by category
uv run python env-forge/scripts/catalog.py --category "Healthcare/Medical"

# Show details for a specific scenario
uv run python env-forge/scripts/catalog.py --details marketplace_1
```

## Scenario Naming Convention

Scenario names in the dataset follow the pattern: `{domain}_{number}` (e.g., `e_commerce_33`, `booking_marketplace_1`, `healthcare_5`). The number is an index within the domain, not globally unique.

## Materializing a Scenario

```bash
uv run python env-forge/scripts/materialize.py --scenario e_commerce_33
```

This fetches the scenario's data from all JSONL files, writes the environment files to `.env-forge/environments/e_commerce_33/`, creates and seeds the SQLite database, and generates the pyproject.toml.

## Data Path

Data is fetched from Hugging Face at runtime, not stored in the git repo. The `huggingface_hub` library downloads JSONL files on first access and caches them in `.env-forge/cache/`. Subsequent runs use the cache. To force refresh:

```bash
uv run python env-forge/scripts/catalog.py --refresh
```

## Example Scenarios

These are representative examples from the dataset:

**E-commerce**: Online marketplace with products, categories, cart, orders, reviews, wishlists. Tasks like "Search for laptops under $500", "Add cheapest result to cart", "Get order history for last month".

**Healthcare**: Patient portal with appointments, prescriptions, medical records, lab results. Tasks like "Schedule appointment with Dr. Smith next Tuesday", "View active prescriptions", "Get lab results from last visit".

**Project Management**: Team workspace with projects, tasks, sprints, time tracking. Tasks like "Create a new task in the Backend sprint", "Assign task to team member", "Get burndown chart data for current sprint".

**Finance**: Banking platform with accounts, transactions, budgets, transfers. Tasks like "Transfer $200 from checking to savings", "Get spending by category for this month", "Set up recurring payment".
