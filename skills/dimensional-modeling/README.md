last updated: 2026-02-14

# dimensional-modeling

Kimball-style dimensional modeling patterns for DuckDB star schemas in agent systems.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install dimensional-modeling@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/dimensional-modeling
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `dimensional-modeling` | "star schema", "dimensional model", "DuckDB schema", "fact table", "SCD Type 2" | Design and implement Kimball-style star schemas for agent state persistence |

## invocation

```
/dimensional-modeling
```

Or describe what you need:

```
"I need to track how my agent decomposes tasks and routes to subagents"
"Design a star schema for tracking skill quality over time"
"Help me model CDC change detection data in DuckDB"
```

## what it teaches

- How to identify business processes and declare fact table grain
- Dimension table design with SCD Type 2 for change tracking
- Hash-based surrogate key generation (no sequences, deterministic)
- Fact table patterns (append-only, no PKs, metadata on every row)
- Analytical view recipes for star schema queries
- Agent execution modeled as a data pipeline DAG
- Common anti-patterns and how to avoid them

## references

| Reference | Purpose |
|-----------|---------|
| schema_patterns.md | Dimension and fact table templates with examples |
| query_patterns.md | Star schema query cookbook (joins, trends, SCD lookups) |
| key_generation.md | Hash keys, natural keys, degenerate dimensions |
| anti_patterns.md | Common mistakes and how to avoid them |
| dag_execution.md | Agent execution as data pipeline DAG with schema and capture |

## related

- [star-schema-llm-context](https://github.com/fblissjr/star-schema-llm-context) -- pattern library and conceptual framework
- [fb-claude-skills/skill-maintainer/scripts/store.py](../skill-maintainer/scripts/store.py) -- working reference implementation (v0.6.0)
