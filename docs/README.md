last updated: 2026-02-18

# documentation

## guides

| Document | Description |
|----------|-------------|
| [mcp-ecosystem.md](mcp-ecosystem.md) | Field guide to the full MCP ecosystem: protocol, tools, resources, apps, connectors, extensions, and how they relate |

See also the root [README.md](../README.md) for plugin installation, surface compatibility, and usage instructions.

## docs for contributors and developers

### skill-maintainer internals

Technical documentation for the automated skill maintenance system.

| Document | Description |
|----------|-------------|
| [api_reference.md](internals/api_reference.md) | Function signatures, parameters, return types for all Python scripts |
| [schema.md](internals/schema.md) | Formal schemas for state.json and config.yaml |
| [duckdb_schema.md](internals/duckdb_schema.md) | DuckDB star schema tables, views, and dimensional model |
| [troubleshooting.md](internals/troubleshooting.md) | Common issues, error messages, and recovery procedures |

### analysis and research

Design documents created during development. Useful for understanding architectural decisions.

| Document | Description |
|----------|-------------|
| [skills_guide_structured.md](analysis/skills_guide_structured.md) | Structured extraction from Anthropic's 30-page skills guide PDF |
| [claude_skills_best_practices_guide_full_report.md](analysis/claude_skills_best_practices_guide_full_report.md) | Best practices guide for building Claude skills |
| [skills_guide_analysis.md](analysis/skills_guide_analysis.md) | Gap analysis: guide recommendations vs this repo's skills |
| [self_updating_system_design.md](analysis/self_updating_system_design.md) | Source materials inventory and change detection strategy |
| [abstraction_analogies.md](analysis/abstraction_analogies.md) | Skills as database constructs (view definitions + stored procedures) |
| [duckdb_dimensional_model_strategy.md](analysis/duckdb_dimensional_model_strategy.md) | DuckDB star schema strategy for agent state |
| [data_centric_agent_state_research.md](analysis/data_centric_agent_state_research.md) | Research on data-centric LLM agent state management |

### captured external documentation

Offline copies of upstream docs for reference and CDC comparison.

| Directory | Description |
|-----------|-------------|
| [claude-docs/](claude-docs/) | Claude official docs (plugins, skills, marketplace, reference) |
| [agentskills/](agentskills/) | Skills specs, reference docs and examples of Skills |
