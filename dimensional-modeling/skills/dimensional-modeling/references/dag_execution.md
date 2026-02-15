last updated: 2026-02-14

# agent execution as data pipeline DAG

How to model agent task execution using dimensional modeling. The core insight: agents ARE data pipelines. A Claude Code session executing a complex task IS a DAG.

## the hierarchy

```
Goal / Objective     (why -- spans days, sessions)
  Task               (what -- decomposed unit)
    Branch / Attempt (how -- specific approach, may be pruned)
      Session        (where -- execution boundary)
        Agent        (delegation -- routed sub-problem)
          Tool chain (sequence -- ordered operations)
            Tool call(atomic -- read/write/search/execute)
```

## mapping to the five invariant operations

Every agent execution follows the same five phases that appear in database query planning, sparse MoE transformers, and CDC pipelines:

| Phase | Agent Execution | Fact Table |
|-------|----------------|-----------|
| Decompose | Break goal into tasks | fact_task_decomposition |
| Route | Assign tasks to agents/tools | fact_routing_decision |
| Execute | Run tool calls | fact_execution_step |
| Prune | Kill unproductive branches | fact_pruning_event |
| Synthesize | Merge subagent outputs | fact_synthesis_result |
| Verify | Quality check final output | fact_verification |

## schema

### fact_task_decomposition

Tracks the decompose phase: what was broken down and how.

```sql
CREATE TABLE IF NOT EXISTS fact_task_decomposition (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,            -- links related decompositions
    model            TEXT,

    -- measures
    parent_task      TEXT,            -- NULL for top-level goals
    child_task       TEXT NOT NULL,
    decomposition_depth INTEGER DEFAULT 0,
    subtask_count    INTEGER DEFAULT 1,
    strategy         TEXT,            -- 'sequential', 'parallel', 'conditional'

    -- event
    decomposed_at    TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

### fact_routing_decision

Tracks the route phase: what was assigned where.

```sql
CREATE TABLE IF NOT EXISTS fact_routing_decision (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,
    task_id          TEXT NOT NULL,
    model            TEXT,

    -- measures
    agent_name       TEXT,            -- 'main', 'Explore', 'Plan', 'Bash', etc.
    tool_name        TEXT,            -- specific tool selected
    routing_reason   TEXT,            -- why this agent/tool was chosen
    alternatives_considered INTEGER DEFAULT 0,

    -- event
    routed_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

### fact_execution_step

Tracks individual tool calls. This is the EXPLAIN ANALYZE output for agents.

```sql
CREATE TABLE IF NOT EXISTS fact_execution_step (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,
    task_id          TEXT,
    agent_name       TEXT,
    model            TEXT,

    -- measures
    tool_name        TEXT NOT NULL,
    duration_ms      INTEGER,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    status           TEXT NOT NULL,   -- 'success', 'error', 'timeout'
    target_path      TEXT,            -- file path for read/write/edit operations
    error_message    TEXT,

    -- event
    called_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

### fact_pruning_event

Tracks what was killed or abandoned.

```sql
CREATE TABLE IF NOT EXISTS fact_pruning_event (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,
    task_id          TEXT,
    agent_name       TEXT,

    -- measures
    pruning_reason   TEXT NOT NULL,   -- 'timeout', 'error_threshold', 'user_cancel', 'redundant'
    steps_completed  INTEGER DEFAULT 0,
    tokens_spent     INTEGER DEFAULT 0,

    -- event
    pruned_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

### fact_synthesis_result

Tracks the merge/synthesis of outputs.

```sql
CREATE TABLE IF NOT EXISTS fact_synthesis_result (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,
    model            TEXT,

    -- measures
    input_count      INTEGER NOT NULL, -- how many subresults were merged
    output_tokens    INTEGER,
    quality_signal   TEXT,            -- 'high', 'medium', 'low', or numeric score
    synthesis_strategy TEXT,          -- 'sequential_merge', 'parallel_merge', 'select_best'

    -- event
    synthesized_at   TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

### fact_verification

Tracks quality checks on output.

```sql
CREATE TABLE IF NOT EXISTS fact_verification (
    -- degenerate dimensions
    session_id       TEXT NOT NULL,
    goal_id          TEXT,

    -- measures
    verification_type TEXT NOT NULL,  -- 'test_run', 'lint', 'type_check', 'manual_review'
    passed           BOOLEAN NOT NULL,
    error_count      INTEGER DEFAULT 0,
    warning_count    INTEGER DEFAULT 0,
    details          TEXT,            -- JSON for specifics

    -- event
    verified_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL
);
```

## capture mechanism

### Claude Code hooks

Use Claude Code hooks to capture events as they happen:

| Hook | Events Captured |
|------|----------------|
| PostToolUse | fact_execution_step (every tool call) |
| SubagentStart | fact_routing_decision (subagent spawned) |
| SubagentStop | fact_synthesis_result (subagent returned) |
| Stop | fact_session_event (session end) |
| TaskCompleted | fact_verification (task completion status) |

### journal.py pattern (from fb-claude-skills)

Two-phase capture for performance:

1. **Append phase** (hook execution, <50ms): Write JSONL to a buffer file. No DuckDB access.
2. **Ingest phase** (batch, periodic): Read JSONL buffer, batch-insert into DuckDB.

```python
# Hook script (fast path)
import orjson
from pathlib import Path

def on_post_tool_use(event):
    entry = {
        "type": "execution_step",
        "session_id": event["session_id"],
        "tool_name": event["tool_name"],
        "duration_ms": event["duration_ms"],
        "status": event["status"],
        "called_at": event["timestamp"],
    }
    Path("state/journal.jsonl").open("a").write(
        orjson.dumps(entry).decode() + "\n"
    )
```

```python
# Batch ingest (slow path)
def ingest_journal(store, journal_path):
    entries = []
    for line in Path(journal_path).read_text().splitlines():
        entries.append(orjson.loads(line))

    for entry in entries:
        if entry["type"] == "execution_step":
            store.con.execute("""
                INSERT INTO fact_execution_step (...)
                VALUES (?, ?, ?, ...)
            """, [...])

    # Truncate journal after successful ingest
    Path(journal_path).write_text("")
```

## analytical views

### routing pattern success rates

Which routing decisions lead to successful outcomes?

```sql
CREATE VIEW v_routing_success AS
SELECT
    r.agent_name,
    r.tool_name,
    COUNT(*) AS total_routings,
    COUNT(*) FILTER (WHERE e.status = 'success') AS successes,
    ROUND(COUNT(*) FILTER (WHERE e.status = 'success') * 100.0 / COUNT(*), 1) AS success_rate,
    AVG(e.duration_ms) AS avg_duration_ms,
    AVG(e.input_tokens + e.output_tokens) AS avg_total_tokens
FROM fact_routing_decision r
LEFT JOIN fact_execution_step e
    ON e.session_id = r.session_id
    AND e.task_id = r.task_id
    AND e.agent_name = r.agent_name
GROUP BY r.agent_name, r.tool_name
ORDER BY total_routings DESC;
```

### decomposition depth vs quality

Does deeper decomposition lead to better outcomes?

```sql
CREATE VIEW v_decomposition_quality AS
SELECT
    td.decomposition_depth,
    COUNT(DISTINCT td.goal_id) AS goal_count,
    AVG(CASE WHEN v.passed THEN 1.0 ELSE 0.0 END) AS verification_pass_rate,
    AVG(sr.output_tokens) AS avg_synthesis_tokens
FROM fact_task_decomposition td
LEFT JOIN fact_verification v ON v.goal_id = td.goal_id
LEFT JOIN fact_synthesis_result sr ON sr.goal_id = td.goal_id
GROUP BY td.decomposition_depth
ORDER BY td.decomposition_depth;
```

### cost per routing pattern

Which patterns are most expensive?

```sql
SELECT
    r.agent_name,
    r.tool_name,
    SUM(e.input_tokens + e.output_tokens) AS total_tokens,
    SUM(e.duration_ms) AS total_duration_ms,
    COUNT(*) AS call_count
FROM fact_routing_decision r
JOIN fact_execution_step e
    ON e.session_id = r.session_id
    AND e.task_id = r.task_id
GROUP BY r.agent_name, r.tool_name
ORDER BY total_tokens DESC
LIMIT 20;
```

## what this enables

Not just "how much did it cost" but "what routing decisions did the agent make, and which patterns succeed?"

- "This decomposition pattern succeeds 80% of the time; that one fails 60%"
- "When the agent spawns >3 subagents, synthesis quality drops -- prune earlier"
- "Read-first-then-write routing outperforms write-then-fix by 2x in tool calls"
- "This 5-step sequence appears in every code review -- make it a skill"

The data engineering parallel: the same patterns that govern Airflow DAGs (decompose, route, prune, synthesize, verify) govern agent execution.
