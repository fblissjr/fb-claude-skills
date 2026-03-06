---
name: dimensional-modeling
description: Design and implement Kimball-style star schemas in DuckDB for LLM agent state persistence. Use when user needs to track agent execution, model operational data, design fact/dimension tables, implement SCD Type 2, generate surrogate keys, or build analytical views. Also triggers on "star schema", "dimensional model", "DuckDB schema", "fact table", "dimension table", "SCD Type 2", "surrogate keys", "data warehouse for agents", "design a schema for", "help me track agent state", "store execution data in DuckDB", "I need to persist agent history", or "how do I model".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-02-25
allowed-tools: "Read"
---

# Dimensional Modeling for Agent Systems

Design and implement Kimball-style star schemas in DuckDB for tracking agent state, execution, and operational data.

## When to Use

- Designing a new DuckDB schema for agent/tool state tracking
- Adding fact or dimension tables to an existing star schema
- Implementing SCD Type 2 for slowly changing dimensions
- Choosing between degenerate dimensions and full dimension tables
- Designing surrogate key generation strategies
- Building analytical views over star schema data
- Modeling agent execution as a data pipeline DAG

## Core Principle

**Abstract the data, not the behavior.** Frameworks that abstract interaction patterns (chains, agents, retrievers) break when research moves faster than the abstraction. Dimensional modeling abstracts what happened (facts) in what context (dimensions) -- patterns that are 30+ years old and model-agnostic.

## Process

### Step 1: Identify the Business Process

What are you tracking? Every schema starts by naming the business process:

| Business Process | Example Grain | Example Facts |
|-----------------|---------------|---------------|
| Agent task execution | One tool call | duration_ms, input_tokens, output_tokens, status |
| Skill quality tracking | One validation run | error_count, warning_count, is_valid |
| CDC change detection | One page check | content_hash, change_type, severity |
| Session cost tracking | One session | total_tokens, cost_usd, tool_call_count |
| Task decomposition | One routing decision | subtask_count, agent_assigned, success |

### Step 2: Declare the Grain

The grain is the most atomic level of data captured in the fact table. State it as a sentence:

> "One row in fact_tool_call represents a single tool invocation by a single agent in a single session."

**Rules:**
- Too coarse = you lose detail you can't recover
- Too fine = you waste storage on noise
- When in doubt, go finer -- you can always aggregate up

When choosing between grain levels, use ultrathink to reason through the trade-offs before committing.

### Step 3: Identify the Dimensions

Dimensions answer who/what/where/when/why/how about each fact row.

**Full dimension table** when:
- The entity has mutable attributes (name changes, status changes)
- You need to track history (SCD Type 2)
- Multiple fact tables reference the same entity

**Degenerate dimension** (carried in fact rows) when:
- The natural key IS the only interesting attribute
- High cardinality (session_id, transaction_id)
- No mutable attributes to track

See [references/schema_patterns.md](references/schema_patterns.md) for dimension table templates.

### Step 4: Design the Facts

Fact tables are append-only event logs. Every fact table follows these rules:

1. **No primary keys.** Grain = composite dimension keys + event timestamp.
2. **No sequences.** Deterministic surrogate keys via MD5 hash.
3. **No FK constraints.** Join by convention, validate at application layer.
4. **Metadata on every row:** `inserted_at`, `record_source`, `session_id`.

See [references/schema_patterns.md](references/schema_patterns.md) for fact table templates.

### Step 5: Generate Keys

All surrogate keys use MD5 hash of natural key components:

```python
import hashlib

def dimension_key(*natural_keys) -> str:
    """MD5 surrogate from natural key components."""
    parts = [str(k) if k is not None else "-1" for k in natural_keys]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()

def hash_diff(**attributes) -> str:
    """MD5 of non-key attributes for SCD Type 2 change detection."""
    parts = [f"{k}={v}" for k, v in sorted(attributes.items()) if v is not None]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
```

See [references/key_generation.md](references/key_generation.md) for details on key design.

### Step 6: Implement SCD Type 2

When a dimension attribute changes:
1. Set `effective_to = NOW()` and `is_current = FALSE` on the old row
2. Insert new row with updated attributes, `effective_from = NOW()`, `is_current = TRUE`
3. Compute new `hash_diff` from non-key attributes

This requires **no PRIMARY KEY** on dimension tables (hash_key appears in multiple rows).

### Step 7: Build Views

Views compose dimensions and facts to answer analytical questions. Always filter `is_current = TRUE` when joining dimensions unless doing point-in-time analysis.

See [references/query_patterns.md](references/query_patterns.md) for view recipes.

### Step 8: Add Meta Tables

Every database needs:
- `meta_schema_version` -- tracks schema evolution
- `meta_load_log` -- tracks script execution for operational visibility

## Agent Execution as a DAG

The primary use case: model agent execution as a data pipeline DAG.

```
Goal / Objective     (why -- spans days, sessions)
  Task               (what -- decomposed unit)
    Branch / Attempt (how -- specific approach, may be pruned)
      Session        (where -- execution boundary)
        Agent        (delegation -- routed sub-problem)
          Tool chain (sequence -- ordered operations)
            Tool call(atomic -- read/write/search/execute)
```

The five invariant operations (decompose, route, prune, synthesize, verify) become fact table grains:

| Phase | Fact Table | What It Captures |
|-------|-----------|-----------------|
| Decompose | fact_task_decomposition | goal -> tasks (what was broken down and how) |
| Route | fact_routing_decision | task -> agent/tool (what was assigned where) |
| Execute | fact_execution_step | atomic tool call with timing, tokens, status |
| Prune | fact_pruning_event | what was killed/abandoned and why |
| Synthesize | fact_synthesis_result | merged output with quality signal |
| Verify | fact_verification | quality checks on final output |

See [references/dag_execution.md](references/dag_execution.md) for full schema and capture mechanisms.

## Common Anti-Patterns

See [references/anti_patterns.md](references/anti_patterns.md) for mistakes to avoid:
- Adding PRIMARY KEY to SCD Type 2 dimension tables
- Using auto-increment sequences instead of hash keys
- Normalizing fact tables (they should be denormalized)
- Making dimension tables too wide (split into outriggers)
- Forgetting metadata columns (record_source, session_id)

## Reference Implementation

Working proof: `skill-maintainer/scripts/store.py` -- the full Kimball schema (v0.6.0) with 3 dimensions, 6 fact tables, analytical views, and automatic schema migration.

## References

- [schema_patterns.md](references/schema_patterns.md) -- dimension and fact table templates
- [query_patterns.md](references/query_patterns.md) -- star schema query cookbook
- [key_generation.md](references/key_generation.md) -- hash keys, natural keys, degenerate dimensions
- [anti_patterns.md](references/anti_patterns.md) -- common mistakes and how to avoid them
- [dag_execution.md](references/dag_execution.md) -- agent execution as data pipeline DAG
