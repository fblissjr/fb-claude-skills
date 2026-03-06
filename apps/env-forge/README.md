last updated: 2026-02-23

# env-forge

A Claude Code interface for the [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) synthesis pipeline from Snowflake Labs. Browse and materialize 1000 pre-generated tool environments, or forge new ones interactively using AWM's task-first methodology.

## What this is (and isn't)

**AWM** is the research project. It defines a 7-step synthesis pipeline (scenario -> tasks -> schema -> seed data -> API spec -> server code -> verifiers), runs it at scale to produce 1000 environments, and publishes the result as [Snowflake/AgentWorldModel-1K](https://huggingface.co/datasets/Snowflake/AgentWorldModel-1K) on Hugging Face.

**env-forge** is a Claude Code plugin that wraps AWM in two ways:

1. **Browse mode** -- search, preview, and materialize environments from the AWM-1K catalog into runnable directories (catalog.py, materialize.py, validate_env.py)
2. **Forge mode** -- walk through AWM's synthesis pipeline interactively in Claude Code, using AWM's methodology and patterns to generate new environments on demand

The brings together methodology, output format (FastAPI + SQLAlchemy + fastapi-mcp + SQLite), task-first design principle (vs. outcome based ones, while preferrable, are often harder to get started with), and verification patterns all come from AWM. env-forge adds: catalog search, materialization to disk, compile-checking, structural validation, slash commands, and the catalog-as-exemplar step.

## Installation

```bash
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install env-forge@fb-claude-skills
```

To remove: `claude plugin uninstall env-forge@fb-claude-skills`

## Quick Start

```bash
# 1. Search the catalog for a domain
uv run python env-forge/scripts/catalog.py --search "e-commerce"

# 2. Materialize an environment from the catalog
uv run python env-forge/scripts/materialize.py --scenario e_commerce_33

# 3. Validate it
uv run python env-forge/scripts/validate_env.py .env-forge/environments/e_commerce_33/

# 4. Run the server
cd .env-forge/environments/e_commerce_33 && uv run python server.py
```

Or use the slash commands:
```
/env-forge:browse e-commerce     # search + materialize interactively
/env-forge:forge a pet adoption agency with animal profiles and applications
```

The server exposes all endpoints as MCP tools at `http://127.0.0.1:8000/mcp`. Point any MCP client at that URL and the agent has typed, documented tools backed by real state.

## Skills

| Skill | Description |
|-------|-------------|
| env-forge | AWM synthesis methodology adapted for interactive use: task-first schema synthesis, API generation, verification patterns |

## Commands

| Command | Description |
|---------|-------------|
| `/env-forge:browse` | Browse AWM-1K catalog by category or keyword, materialize selected environment |
| `/env-forge:forge` | Interactive environment generation using AWM's synthesis pipeline |
| `/env-forge:launch` | Materialize and start a generated environment (not yet implemented) |
| `/env-forge:verify` | Run verification against current DB state for a task (not yet implemented) |

## Status

**Phase 1** (current): browse, forge, catalog scripts, materialize, validate. Working.

**Phase 2** (planned): launch command (auto-start server after materialize), verify command (run verifier functions against live DB), MCP tool wrapping for agent-in-the-loop testing.

## How it works

### Browse mode

Searches the AWM-1K dataset (1000 environments, 28 categories) on Hugging Face. Data is fetched on first use and cached locally in `.env-forge/cache/`. Select a scenario and it materializes into a runnable environment.

### Forge mode

Walks through AWM's synthesis pipeline interactively:

1. **Scenario definition** -- describe the domain, entities, workflows
2. **Catalog reference** -- search AWM-1K for a structurally similar domain to use as exemplar
3. **Task generation** -- 10 diverse tasks covering CRUD, search, aggregation, multi-step
4. **Schema** -- SQLite tables derived from tasks (not the reverse)
5. **Seed data** -- realistic INSERT statements that make every task executable
6. **API spec** -- RESTful endpoints with full metadata
7. **Server code** -- FastAPI + fastapi-mcp + SQLAlchemy (runnable)
8. **Verifiers** -- DB state comparison functions for task completion
9. **Database creation** -- schema applied, data seeded, backup snapshot taken
10. **Validation** -- structural checks on all generated artifacts

Steps 3-8 follow AWM's methodology. Steps 2, 9, 10 are env-forge additions.

### Scripts

All scripts live in `env-forge/scripts/` and share constants and utilities via `shared.py`:

```bash
# Catalog browsing
uv run python env-forge/scripts/catalog.py --list-categories
uv run python env-forge/scripts/catalog.py --search "e-commerce"
uv run python env-forge/scripts/catalog.py --category "booking"
uv run python env-forge/scripts/catalog.py --details marketplace_1

# Materialization
uv run python env-forge/scripts/materialize.py --scenario e_commerce_33

# Validation
uv run python env-forge/scripts/validate_env.py .env-forge/environments/e_commerce_33/
```

Materialize performs compile-checks on generated `server.py` and `verifiers.py` before writing (WARNING on syntax errors, never blocks output).

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

This matches AWM's output format, unpacked from JSONL into individual files. `initial.db` is a pristine snapshot for resetting state between test runs.

Run with: `cd .env-forge/environments/<name> && uv run python server.py`

## Dependencies

Plugin scripts require:
- `orjson`
- `huggingface_hub` -- fetches AWM-1K data from `Snowflake/AgentWorldModel-1K` on demand

Generated environments need (declared in their own pyproject.toml):
- `fastapi`, `uvicorn`, `sqlalchemy`, `fastapi-mcp`, `pydantic`

## What env-forge adds over raw AWM

| Capability | AWM | env-forge |
|-----------|-----|-----------|
| 7-step synthesis pipeline | yes (batch, LLM-heavy) | yes (interactive, Claude-guided) |
| 1000 pre-built environments | yes (JSONL on HF) | browse + materialize to disk |
| Catalog search | no | yes (keyword, category, details) |
| Compile-checking | minimal | syntax validation before write |
| Structural validation | no | validate_env.py (6 checks) |
| Catalog-as-exemplar | no | search for similar domain before forging |
| Claude Code integration | no | slash commands, plugin packaging |
| DB reset | no | initial.db snapshot |

## Patterns

### catalog-as-exemplar

When generating new environments, first search the AWM-1K catalog for a structurally similar domain. Use the closest match as a few-shot reference -- adapt its patterns rather than generating from scratch. See `commands/forge.md` step 2.

### shared.py

Common constants and utilities (cache paths, download helpers, JSONL loaders) extracted into a shared module. Scripts use `sys.path.insert` to ensure the sibling import resolves regardless of working directory.

## Credits

- **Synthesis methodology, output format, and task-first design**: [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) by Snowflake Labs
- **AWM-1K dataset**: [Snowflake/AgentWorldModel-1K](https://huggingface.co/datasets/Snowflake/AgentWorldModel-1K) on Hugging Face
