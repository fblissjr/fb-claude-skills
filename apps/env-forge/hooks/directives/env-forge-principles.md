# trigger: envforge
## Environment design principles (auto-loaded)
- Task-first: tasks drive schema, not the reverse. Every table column and API endpoint exists because a task needs it.
- Three layers: state (SQLite), interface (FastAPI + fastapi-mcp), verification (DB state comparison).
- 10 tasks per scenario covering CRUD, search, aggregation, multi-step workflows, and edge cases.
- Seed data must make every task executable. Realistic values, temporal diversity, status variations.
- Atomic endpoints: each does ONE operation. Maximize reusability via base CRUD that composes.
- For full synthesis pipeline and patterns, invoke /env-forge:env-forge.
