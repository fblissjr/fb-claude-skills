last updated: 2026-02-23

# env-forge

Generate and launch database-backed MCP tool environments from scenario descriptions or the AWM-1K catalog. Two modes: browse 1000 pre-generated environments across 28 domains, or forge new ones from scratch using a task-first design methodology.

## Installation

```bash
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install env-forge@fb-claude-skills
```

To remove: `claude plugin uninstall env-forge@fb-claude-skills`

## Skills

| Skill | Description |
|-------|-------------|
| env-forge | Environment design methodology: task-first schema synthesis, API generation, verification patterns |

## Commands

| Command | Description |
|---------|-------------|
| `/env-forge:browse` | Browse AWM-1K catalog by category or keyword, materialize selected environment |
| `/env-forge:forge` | Interactive environment generation from a scenario description |
| `/env-forge:launch` | Materialize and start a generated environment (Phase 2) |
| `/env-forge:verify` | Run verification against current DB state for a task (Phase 2) |

## Usage

### Browse the catalog

```
/env-forge:browse e-commerce
/env-forge:browse booking
```

Searches the AWM-1K dataset (1000 environments, 28 categories). Select a scenario and it materializes: SQLite database, FastAPI+MCP server, seed data, verification functions.

### Forge a new environment

```
/env-forge:forge a volunteer matching platform where organizations post opportunities and volunteers sign up
```

Walks through the full synthesis pipeline: scenario -> tasks -> schema -> data -> API spec -> server code -> verifiers.

### Scripts

```bash
# Search the catalog
uv run python env-forge/scripts/catalog.py --search "e-commerce"
uv run python env-forge/scripts/catalog.py --category "Healthcare/Medical"
uv run python env-forge/scripts/catalog.py --list-categories

# Materialize a scenario from the catalog
uv run python env-forge/scripts/materialize.py --scenario e_commerce_33

# Validate a generated environment
uv run python env-forge/scripts/validate_env.py .env-forge/environments/e_commerce_33/
```

## Generated environment structure

```
.env-forge/environments/<name>/
  scenario.json          # Scenario metadata + task list
  schema.sql             # SQLite DDL
  seed_data.sql          # INSERT statements
  api_spec.json          # RESTful API specification
  server.py              # FastAPI + fastapi-mcp server
  verifiers.py           # Task completion verification functions
  db/
    initial.db           # Seeded database (backup for reset)
    current.db           # Working database
  pyproject.toml         # Dependencies for this environment
```

Run with: `cd .env-forge/environments/<name> && uv run python server.py`

## Dependencies

Plugin scripts require:
- `orjson`
- `huggingface_hub` -- fetches AWM-1K data from `Snowflake/AgentWorldModel-1K` on demand

Generated environments need (declared in their own pyproject.toml):
- `fastapi`, `uvicorn`, `sqlalchemy`, `fastapi-mcp`, `pydantic`

## Methodology

Based on the Agent World Model (AWM) synthesis pipeline from Snowflake Labs. Key insight: **task-first design** -- start with what users do, derive schema and API from tasks, not the reverse. See `skills/env-forge/SKILL.md` for the full methodology and `references/` for detailed patterns.
