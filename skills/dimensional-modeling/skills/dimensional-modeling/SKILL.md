---
name: dimensional-modeling
description: Design and implement Kimball-style star schemas in DuckDB for LLM agent state persistence. Use when user needs to track agent execution, model operational data, design fact/dimension tables, implement SCD Type 2, generate surrogate keys, or build analytical views. Also triggers on "star schema", "dimensional model", "DuckDB schema", "fact table", "dimension table", "SCD Type 2", "surrogate keys", "data warehouse for agents", "design a schema for", "help me track agent state", "store execution data in DuckDB", "I need to persist agent history", or "how do I model".
allowed-tools: "Read"
---

# Dimensional modeling for agent systems

Design Kimball-style star schemas in DuckDB for agent state, execution and operational data. Kimball's method (business process, grain, dimensions, facts) is assumed; this skill carries the house conventions layered on it, which differ from textbook defaults in ways that matter.

The principle behind the choice: abstract the data, not the behavior. Frameworks that abstract interaction patterns break when practice moves faster than the abstraction; facts (what happened) in dimensions (what context) stay model-agnostic.

<scope>
For: a new DuckDB schema for agent or tool state, adding facts or dimensions to an existing star schema, SCD Type 2, surrogate keys, analytical views, and modeling agent execution as a DAG. Not for transactional application schemas, where normalization and FK integrity are the right default; not for ad-hoc querying of a JSON file (json-query owns that).
</scope>

<conventions>
Every design follows all of these. Each overrides a common default, for the reason given.

- **Grain is a sentence, written before any table.** "One row in fact_tool_call is one tool invocation by one agent in one session." Between two candidate grains, take the finer: aggregation recovers the coarse one, nothing recovers the fine one.
- **Surrogate keys are MD5 hex of the natural key components**, not sequences. Deterministic keys let a rebuilt database and parallel writers agree without coordination. Use these two functions verbatim, because keys only join across stores when every store hashes identically:

  ```python
  import hashlib

  def dimension_key(*natural_keys) -> str:
      parts = [str(k) if k is not None else "-1" for k in natural_keys]
      return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()

  def hash_diff(**attributes) -> str:
      parts = [f"{k}={v}" for k, v in sorted(attributes.items()) if v is not None]
      return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
  ```

- **Dimensions are SCD Type 2 and carry no PRIMARY KEY**, because `hash_key` repeats across an entity's versions. Columns: `effective_from`, `effective_to` (NULL means current), `is_current`, and `hash_diff` over the mutable non-key attributes. On a change: close the old row (`effective_to = now`, `is_current = FALSE`) and insert the new one.
- **Facts are append-only with no PRIMARY KEY, no sequence and no FK constraint.** The grain is the dimension keys plus the event timestamp. A DuckDB foreign key must reference a PRIMARY KEY or UNIQUE column, and a dimension's `hash_key` can be neither, so the application layer enforces integrity.
- **Every row carries lineage:** `inserted_at` (`created_at` on dimensions), `record_source`, `session_id`.
- **Full dimension or degenerate:** a full dimension table when attributes change, history matters, or several facts share the entity; otherwise carry the natural key in the fact row (`session_id`, `model`, `project_dir`).
- **Facts never join to facts row to row.** To relate two facts, aggregate each to the grain of a conformed dimension and join the aggregates (drill-across). A direct join on a shared key fans rows out and double-counts measures.
- **Views join dimensions with `is_current = TRUE`**, except point-in-time queries, which bound `effective_from` / `effective_to` instead.
- **Every database has `meta_schema_version` and `meta_load_log`.**
- **DuckDB is columnar:** batch inserts over single-row writes, and treat the `.duckdb` file as a rebuildable cache, not the source of truth.
</conventions>

<agent_dag>
The primary use case models agent execution as a pipeline DAG: goal, task, branch or attempt, session, agent, tool chain, tool call. Each phase becomes one fact table at its own grain:

| Phase | Fact table | Captures |
|-------|-----------|----------|
| Decompose | fact_task_decomposition | goal to tasks |
| Route | fact_routing_decision | task to agent or tool |
| Execute | fact_execution_step | one tool call: timing, tokens, status |
| Prune | fact_pruning_event | what was abandoned and why |
| Synthesize | fact_synthesis_result | merged output with a quality signal |
| Verify | fact_verification | checks on the final output |

Schemas, hook-based capture and views: [references/dag_execution.md](references/dag_execution.md).
</agent_dag>

<references>
- [schema_patterns.md](references/schema_patterns.md): dimension, fact, bridge, meta and session-event table templates
- [key_generation.md](references/key_generation.md): natural keys, composite keys, NULL handling, what goes in `hash_diff`
- [anti_patterns.md](references/anti_patterns.md): the mistakes these conventions exist to prevent, each with its failure (PK on an SCD2 dimension, sequences, FK constraints, normalized facts, one fact table for everything, over-wide dimensions)
- [query_patterns.md](references/query_patterns.md): DuckDB query recipes over this schema shape (latest-per-entity, point-in-time, drill-across, FILTER aggregates)
- [dag_execution.md](references/dag_execution.md): agent execution as a DAG
</references>
