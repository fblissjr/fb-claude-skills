last updated: 2026-02-14

# duckdb-backed dimensional modeling for llm agent systems

strategic analysis of using DuckDB star schema / dimensional models as the foundation for data-driven LLM agent architectures, with specific focus on Claude Agent loops and Claude Code workflows.

## executive summary

**Core insight**: LLM interactions are not ephemeral conversations — they generate structured temporal data (tool calls, file edits, validations, session events, token usage) that can be modeled dimensionally for queryability, audit trails, and cross-session intelligence.

**Current state**: fb-claude-skills has implemented a dimensional model for CDC pipelines tracking skill/plugin maintenance (sources, pages, changes, validations, updates). This is a narrow vertical slice.

**Strategic question**: What is the general-purpose pattern? How do we build a reusable "agent state store" that works across domains?

**Key dimensions**:
1. Agent memory and continuity
2. Token budget optimization
3. Quality tracking over time
4. Multi-agent coordination
5. Development workflow analytics
6. Change data capture (CDC) beyond docs
7. Retrieval-augmented generation (RAG)
8. Prompt/response audit trails
9. Cost optimization
10. Self-improving agents

## foundational architecture

### why duckdb?

1. **Embedded**: No server process, single file database, zero-ops deployment
2. **Analytical**: Columnar storage optimized for OLAP queries (aggregations, time-series)
3. **SQL interface**: Familiar query language, rich ecosystem of tools
4. **Performant**: Vectorized execution, efficient compression, fast scans
5. **Portable**: Single .duckdb file, commit to git or distribute
6. **Integration**: Python, R, Node.js bindings; Parquet/CSV/JSON export
7. **WAL mode**: Concurrent reads, safe writes, ACID guarantees
8. **Temporal queries**: Window functions, temporal JOINs, native date/time types

### dimensional model primer

**Star schema** = fact tables (measures/events) + dimension tables (attributes/entities)

- **Fact tables**: append-only, immutable, timestamped events (tool calls, file edits, validations)
- **Dimension tables**: slowly-changing entities (skills, sources, files, sessions, agents)
- **Bridge tables**: many-to-many relationships (skill-source dependencies, agent-tool access)

**Why dimensional?**
- **Temporal queryability**: "Show me validation pass rates over the last 30 days"
- **Audit trails**: Complete history, never delete, always append
- **Cross-cutting queries**: Join facts across dimensions ("which agent made the most edits to Python files?")
- **Aggregation efficiency**: Pre-computed aggregates in views, fast rollups

### current implementation (skill-maintainer)

Located in `/Users/fredbliss/claude/fb-claude-skills/skill-maintainer/scripts/store.py`

**Dimensions**:
- `dim_source` (source_id, source_name, source_type, url)
- `dim_skill` (skill_id, skill_name, skill_path, auto_update)
- `dim_page` (page_id, source_id, url)
- `skill_source_dep` (bridge table)

**Facts**:
- `fact_watermark_check` (check_id, source_id, checked_at, last_modified, etag, changed)
- `fact_change` (change_id, source_id, page_id, detected_at, classification, old_hash, new_hash, summary)
- `fact_validation` (validation_id, skill_id, validated_at, is_valid, error_count, warnings)
- `fact_update_attempt` (attempt_id, skill_id, mode, status, changes_applied, backup_path)
- `fact_content_measurement` (measurement_id, skill_id, file_path, line_count, estimated_tokens)
- `fact_session` (session_id, started_at, ended_at, working_dir)
- `fact_session_event` (event_id, session_id, event_type, target_path, metadata)

**Views** (aggregations):
- `v_latest_watermark` -- most recent watermark per source
- `v_latest_page_hash` -- most recent hash per page
- `v_skill_freshness` -- last change detected, last validated, breaking/additive counts
- `v_skill_budget` -- token counts by file type, over_budget flag
- `v_latest_source_check` -- most recent git check per source

**Pattern**: CDC detect -> identify -> classify -> record facts -> query views for reporting

## strategic use cases

### 1. agent memory and continuity

**Problem**: Agents are stateless across sessions. When you resume a task, the agent has no memory of previous attempts, decisions, or failures.

**Solution**: Dimensional model of agent actions, decisions, and outcomes.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_agent (
    agent_id INTEGER PRIMARY KEY,
    agent_name TEXT UNIQUE NOT NULL,
    agent_type TEXT,  -- 'main', 'subagent', 'team_member'
    system_prompt_hash TEXT,
    created_at TIMESTAMP
);

CREATE TABLE dim_task (
    task_id INTEGER PRIMARY KEY,
    task_description TEXT,
    task_type TEXT,  -- 'debug', 'refactor', 'implement', 'analyze'
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT  -- 'pending', 'in_progress', 'completed', 'abandoned'
);

CREATE TABLE dim_decision_point (
    decision_id INTEGER PRIMARY KEY,
    decision_type TEXT,  -- 'tool_choice', 'approach_selection', 'file_modification'
    context_hash TEXT,
    created_at TIMESTAMP
);
```

**Facts**:
```sql
CREATE TABLE fact_agent_action (
    action_id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES dim_agent,
    task_id INTEGER REFERENCES dim_task,
    session_id TEXT,
    action_at TIMESTAMP,
    action_type TEXT,  -- 'tool_call', 'decision', 'response'
    tool_name TEXT,
    target_path TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    metadata TEXT  -- JSON: tool args, decision rationale, error info
);

CREATE TABLE fact_decision (
    decision_id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES dim_agent,
    task_id INTEGER REFERENCES dim_task,
    decision_point_id INTEGER REFERENCES dim_decision_point,
    decided_at TIMESTAMP,
    option_chosen TEXT,
    alternatives_considered TEXT,  -- JSON array
    rationale TEXT,
    outcome TEXT,  -- 'success', 'failure', 'unknown'
    retried BOOLEAN
);

CREATE TABLE fact_task_outcome (
    outcome_id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES dim_task,
    agent_id INTEGER REFERENCES dim_agent,
    completed_at TIMESTAMP,
    success BOOLEAN,
    test_pass_rate REAL,
    files_modified INTEGER,
    total_tokens INTEGER,
    time_elapsed_seconds INTEGER,
    final_status TEXT
);
```

#### queries that unlock value

**Agent memory retrieval**:
```sql
-- What did I try last time I worked on this file?
SELECT action_type, tool_name, metadata, action_at
FROM fact_agent_action a
JOIN dim_task t ON t.task_id = a.task_id
WHERE target_path = '/path/to/file.py'
ORDER BY action_at DESC
LIMIT 10;

-- What approaches have I tried for this type of task?
SELECT t.task_description, d.option_chosen, d.outcome, d.rationale
FROM fact_decision d
JOIN dim_task t ON t.task_id = d.task_id
WHERE t.task_type = 'refactor'
  AND d.outcome = 'success'
ORDER BY d.decided_at DESC;

-- Which agent is best at this task type?
SELECT a.agent_name, 
       AVG(o.success::INTEGER) AS success_rate,
       AVG(o.test_pass_rate) AS avg_test_pass,
       COUNT(*) AS tasks_completed
FROM fact_task_outcome o
JOIN dim_agent a ON a.agent_id = o.agent_id
JOIN dim_task t ON t.task_id = o.task_id
WHERE t.task_type = 'debug'
GROUP BY a.agent_name
ORDER BY success_rate DESC;
```

**Continuity on resume**:
```sql
-- Resume context: what was I doing in the last session?
SELECT a.action_type, a.tool_name, a.target_path, a.metadata, a.action_at
FROM fact_agent_action a
JOIN dim_task t ON t.task_id = a.task_id
WHERE t.status = 'in_progress'
  AND a.session_id = (
    SELECT session_id FROM fact_agent_action 
    ORDER BY action_at DESC LIMIT 1
  )
ORDER BY a.action_at DESC
LIMIT 20;
```

#### integration with claude code

**Hook points**:
- `SessionStart` hook: query last session's actions, inject into system prompt
- `Stop` hook: record agent actions from current turn
- `TaskCompleted` hook: record task outcome
- `PreToolUse` hook: check if this tool/file combo failed recently, warn user

**MCP server**: Expose memory queries as MCP tools:
- `recall_previous_attempts(file_path, task_type)`
- `get_successful_approaches(task_type, limit=5)`
- `check_decision_history(decision_type, context_hash)`

**Implementation complexity**: Medium
- Schema: 3 dimensions, 3 facts (straightforward)
- Data capture: Requires parsing Claude Code's internal event stream or JSON logs
- Retrieval: Simple SQL queries wrapped in Python functions
- Context injection: Hook integration (already supported)

**Value**: High
- Eliminates "I've tried this before and it didn't work" frustration
- Enables learning from past failures without re-running tests
- Provides cross-session continuity that mimics human memory

---

### 2. token budget optimization

**Problem**: Skills/tools/agents consume context window unpredictably. No visibility into what's eating tokens until you hit the limit.

**Solution**: Measure token usage per invocation, track over time, optimize high-cost components.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_component (
    component_id INTEGER PRIMARY KEY,
    component_name TEXT UNIQUE NOT NULL,
    component_type TEXT,  -- 'skill', 'tool', 'reference_file', 'system_prompt'
    file_path TEXT,
    created_at TIMESTAMP
);

CREATE TABLE dim_context_window (
    window_id INTEGER PRIMARY KEY,
    model_name TEXT,
    max_tokens INTEGER,
    effective_date DATE
);
```

**Facts**:
```sql
CREATE TABLE fact_token_usage (
    usage_id INTEGER PRIMARY KEY,
    session_id TEXT,
    agent_id INTEGER REFERENCES dim_agent,
    measured_at TIMESTAMP,
    component_id INTEGER REFERENCES dim_component,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    invocation_context TEXT  -- 'skill_load', 'tool_call', 'reference_inject'
);

CREATE TABLE fact_context_overflow (
    overflow_id INTEGER PRIMARY KEY,
    session_id TEXT,
    overflowed_at TIMESTAMP,
    window_id INTEGER REFERENCES dim_context_window,
    tokens_at_overflow INTEGER,
    dropped_components TEXT,  -- JSON: list of component_ids that were dropped
    compact_triggered BOOLEAN
);

CREATE TABLE fact_component_measurement (
    measurement_id INTEGER PRIMARY KEY,
    component_id INTEGER REFERENCES dim_component,
    measured_at TIMESTAMP,
    file_type TEXT,
    line_count INTEGER,
    word_count INTEGER,
    char_count INTEGER,
    estimated_tokens INTEGER,
    content_hash TEXT
);
```

#### queries that unlock value

**Budget analysis**:
```sql
-- What's eating my context window?
SELECT c.component_name, c.component_type,
       AVG(u.input_tokens) AS avg_tokens,
       COUNT(*) AS invocations,
       SUM(u.input_tokens) AS total_tokens
FROM fact_token_usage u
JOIN dim_component c ON c.component_id = u.component_id
WHERE u.measured_at > current_timestamp - INTERVAL '7 days'
GROUP BY c.component_name, c.component_type
ORDER BY total_tokens DESC;

-- Which skills are over-budget?
SELECT c.component_name, 
       MAX(m.estimated_tokens) AS tokens,
       MAX(m.estimated_tokens) > 4000 AS over_budget
FROM fact_component_measurement m
JOIN dim_component c ON c.component_id = m.component_id
WHERE c.component_type = 'skill'
  AND m.measured_at = (
    SELECT MAX(measured_at) FROM fact_component_measurement 
    WHERE component_id = m.component_id
  )
GROUP BY c.component_name
ORDER BY tokens DESC;

-- Token efficiency: output per input
SELECT a.agent_name,
       SUM(u.output_tokens)::REAL / SUM(u.input_tokens) AS output_per_input,
       SUM(u.total_tokens) AS total,
       SUM(u.cost_usd) AS total_cost
FROM fact_token_usage u
JOIN dim_agent a ON a.agent_id = u.agent_id
WHERE u.measured_at > current_timestamp - INTERVAL '30 days'
GROUP BY a.agent_name
ORDER BY output_per_input DESC;
```

**Overflow prevention**:
```sql
-- How often do I hit context limit?
SELECT DATE_TRUNC('day', overflowed_at) AS day,
       COUNT(*) AS overflow_count,
       AVG(tokens_at_overflow) AS avg_tokens_at_overflow
FROM fact_context_overflow
WHERE overflowed_at > current_timestamp - INTERVAL '30 days'
GROUP BY day
ORDER BY day;

-- What gets dropped most often during compact?
SELECT c.component_name,
       COUNT(*) AS times_dropped
FROM fact_context_overflow o,
     LATERAL (SELECT UNNEST(JSON_EXTRACT_STRING(o.dropped_components, '$[*]')) AS cid) AS dropped
JOIN dim_component c ON c.component_id = dropped.cid::INTEGER
GROUP BY c.component_name
ORDER BY times_dropped DESC;
```

#### integration with claude code

**Hook points**:
- `Stop` hook: record token usage from current turn (parse from API response)
- `PreCompact` hook: record what's about to be dropped
- Skill load: measure token count before injecting into context

**MCP server**: Budget monitoring tools:
- `check_token_budget(component_name)` -> current usage vs limit
- `suggest_token_optimizations()` -> components to trim/refactor
- `predict_context_overflow(planned_actions)` -> will this fit?

**Implementation complexity**: Low-Medium
- Schema: 2 dimensions, 3 facts
- Data capture: Parse Claude API response JSON (token counts are standard fields)
- Measurement: `fact_component_measurement` already implemented in current store.py
- Queries: Straightforward aggregations

**Value**: Medium-High
- Prevents "ran out of context" mid-task failures
- Identifies bloated skills/references for refactoring
- Cost tracking for budget-sensitive users

---

### 3. quality tracking over time

**Problem**: How do you know if your skills/agents are getting better or worse? No historical trend data.

**Solution**: Track quality metrics (validation results, test pass rates, user satisfaction) over time.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_quality_metric (
    metric_id INTEGER PRIMARY KEY,
    metric_name TEXT UNIQUE NOT NULL,
    metric_type TEXT,  -- 'validation', 'test', 'lint', 'user_feedback'
    threshold_pass REAL,
    created_at TIMESTAMP
);

CREATE TABLE dim_artifact (
    artifact_id INTEGER PRIMARY KEY,
    artifact_type TEXT,  -- 'skill', 'generated_code', 'documentation'
    artifact_path TEXT,
    component_id INTEGER REFERENCES dim_component,
    created_at TIMESTAMP
);
```

**Facts**:
```sql
CREATE TABLE fact_quality_measurement (
    measurement_id INTEGER PRIMARY KEY,
    artifact_id INTEGER REFERENCES dim_artifact,
    metric_id INTEGER REFERENCES dim_quality_metric,
    measured_at TIMESTAMP,
    measured_by TEXT,  -- 'skills-ref', 'pytest', 'ruff', 'user'
    score REAL,
    passed BOOLEAN,
    error_count INTEGER,
    warning_count INTEGER,
    details TEXT  -- JSON: full error/warning messages
);

CREATE TABLE fact_validation (
    validation_id INTEGER PRIMARY KEY,
    component_id INTEGER REFERENCES dim_component,
    validated_at TIMESTAMP,
    validator_name TEXT,
    validator_version TEXT,
    is_valid BOOLEAN,
    error_count INTEGER,
    warning_count INTEGER,
    errors TEXT,  -- JSON array
    warnings TEXT,  -- JSON array
    trigger_type TEXT  -- 'manual', 'post_update', 'pre_commit', 'ci'
);

CREATE TABLE fact_test_run (
    run_id INTEGER PRIMARY KEY,
    artifact_id INTEGER REFERENCES dim_artifact,
    ran_at TIMESTAMP,
    framework TEXT,  -- 'pytest', 'jest', 'manual'
    total_tests INTEGER,
    passed INTEGER,
    failed INTEGER,
    skipped INTEGER,
    duration_seconds REAL,
    exit_code INTEGER,
    log_path TEXT
);
```

#### queries that unlock value

**Quality trends**:
```sql
-- Is this skill getting better or worse over time?
SELECT DATE_TRUNC('week', validated_at) AS week,
       AVG(is_valid::INTEGER) AS pass_rate,
       AVG(error_count) AS avg_errors,
       COUNT(*) AS validations
FROM fact_validation
WHERE component_id = (SELECT component_id FROM dim_component WHERE component_name = 'plugin-toolkit')
GROUP BY week
ORDER BY week;

-- Test pass rate over time
SELECT DATE_TRUNC('day', ran_at) AS day,
       SUM(passed)::REAL / SUM(total_tests) AS pass_rate,
       AVG(duration_seconds) AS avg_duration
FROM fact_test_run
WHERE ran_at > current_timestamp - INTERVAL '90 days'
GROUP BY day
ORDER BY day;

-- Which artifacts have never been validated?
SELECT a.artifact_path, a.created_at
FROM dim_artifact a
LEFT JOIN fact_validation v ON v.component_id = a.component_id
WHERE v.validation_id IS NULL
  AND a.created_at < current_timestamp - INTERVAL '7 days';
```

**Regression detection**:
```sql
-- Did quality regress after the last update?
WITH recent_validations AS (
  SELECT component_id, validated_at, is_valid,
         LAG(is_valid) OVER (PARTITION BY component_id ORDER BY validated_at) AS prev_valid
  FROM fact_validation
)
SELECT c.component_name,
       rv.validated_at,
       rv.prev_valid AS was_valid,
       rv.is_valid AS now_valid
FROM recent_validations rv
JOIN dim_component c ON c.component_id = rv.component_id
WHERE rv.prev_valid = TRUE AND rv.is_valid = FALSE;
```

#### integration with claude code

**Hook points**:
- `PostToolUse` hook (Write/Edit): trigger validation, record result
- `TaskCompleted` hook: run tests, record pass rate
- Skill update pipeline: validate before/after, compare

**MCP server**: Quality monitoring:
- `get_quality_trend(component_name, days=30)` -> time-series data
- `check_for_regressions(since_date)` -> list of quality drops
- `suggest_tests_for_artifact(artifact_path)` -> coverage gaps

**Implementation complexity**: Medium
- Schema: 2 dimensions, 3 facts
- Data capture: Hook into existing validation (already have `fact_validation` in store.py)
- Test integration: Parse pytest/jest output
- Queries: Time-series aggregations (DuckDB window functions)

**Value**: High
- Prevents shipping broken updates
- Builds confidence in auto-update systems
- Enables data-driven refactoring (focus on low-quality components)

---

### 4. multi-agent coordination

**Problem**: Multiple agents (main + subagents, or agent teams) working on the same task. No shared state, duplicate work, conflicting edits.

**Solution**: Shared fact store for work assignments, handoffs, and coordination.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_work_item (
    work_id INTEGER PRIMARY KEY,
    work_type TEXT,  -- 'file_edit', 'research', 'test_creation', 'review'
    target_path TEXT,
    description TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT  -- 'pending', 'assigned', 'in_progress', 'completed', 'blocked'
);

CREATE TABLE dim_agent_capability (
    capability_id INTEGER PRIMARY KEY,
    capability_name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE agent_capability_map (
    agent_id INTEGER REFERENCES dim_agent,
    capability_id INTEGER REFERENCES dim_agent_capability,
    proficiency REAL,  -- 0.0 to 1.0
    PRIMARY KEY (agent_id, capability_id)
);
```

**Facts**:
```sql
CREATE TABLE fact_work_assignment (
    assignment_id INTEGER PRIMARY KEY,
    work_id INTEGER REFERENCES dim_work_item,
    agent_id INTEGER REFERENCES dim_agent,
    assigned_at TIMESTAMP,
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,  -- 'offered', 'accepted', 'rejected', 'completed', 'abandoned'
    reason TEXT
);

CREATE TABLE fact_agent_handoff (
    handoff_id INTEGER PRIMARY KEY,
    from_agent_id INTEGER REFERENCES dim_agent,
    to_agent_id INTEGER REFERENCES dim_agent,
    work_id INTEGER REFERENCES dim_work_item,
    handed_off_at TIMESTAMP,
    handoff_reason TEXT,  -- 'capability_mismatch', 'timeout', 'blocked', 'delegation'
    context_snapshot TEXT  -- JSON: relevant state for the receiving agent
);

CREATE TABLE fact_conflict (
    conflict_id INTEGER PRIMARY KEY,
    work_id INTEGER REFERENCES dim_work_item,
    agent1_id INTEGER REFERENCES dim_agent,
    agent2_id INTEGER REFERENCES dim_agent,
    detected_at TIMESTAMP,
    conflict_type TEXT,  -- 'file_edit', 'duplicate_work', 'incompatible_approach'
    resolution TEXT,  -- 'agent1_wins', 'agent2_wins', 'merge', 'abort'
    resolved_at TIMESTAMP
);
```

#### queries that unlock value

**Work coordination**:
```sql
-- What work is currently in progress?
SELECT w.work_type, w.target_path, a.agent_name, wa.assigned_at
FROM fact_work_assignment wa
JOIN dim_work_item w ON w.work_id = wa.work_id
JOIN dim_agent a ON a.agent_id = wa.agent_id
WHERE wa.status = 'accepted'
  AND w.status = 'in_progress';

-- Which agent should I assign this work to?
SELECT a.agent_name, 
       acm.proficiency,
       COUNT(DISTINCT wa.work_id) AS current_workload
FROM dim_agent a
JOIN agent_capability_map acm ON acm.agent_id = a.agent_id
JOIN dim_agent_capability ac ON ac.capability_id = acm.capability_id
LEFT JOIN fact_work_assignment wa ON wa.agent_id = a.agent_id 
    AND wa.status = 'accepted'
WHERE ac.capability_name = 'python_refactoring'
GROUP BY a.agent_name, acm.proficiency
ORDER BY acm.proficiency DESC, current_workload ASC;

-- Handoff patterns: who hands off to whom?
SELECT a1.agent_name AS from_agent,
       a2.agent_name AS to_agent,
       h.handoff_reason,
       COUNT(*) AS handoff_count
FROM fact_agent_handoff h
JOIN dim_agent a1 ON a1.agent_id = h.from_agent_id
JOIN dim_agent a2 ON a2.agent_id = h.to_agent_id
GROUP BY a1.agent_name, a2.agent_name, h.handoff_reason
ORDER BY handoff_count DESC;
```

**Conflict detection**:
```sql
-- Are two agents about to conflict on the same file?
SELECT w1.work_id AS work1, w2.work_id AS work2,
       a1.agent_name AS agent1, a2.agent_name AS agent2,
       w1.target_path
FROM fact_work_assignment wa1
JOIN fact_work_assignment wa2 ON wa2.work_id != wa1.work_id
JOIN dim_work_item w1 ON w1.work_id = wa1.work_id
JOIN dim_work_item w2 ON w2.work_id = wa2.work_id
JOIN dim_agent a1 ON a1.agent_id = wa1.agent_id
JOIN dim_agent a2 ON a2.agent_id = wa2.agent_id
WHERE w1.target_path = w2.target_path
  AND w1.status = 'in_progress'
  AND w2.status = 'in_progress'
  AND wa1.status = 'accepted'
  AND wa2.status = 'accepted';
```

#### integration with claude code

**Hook points**:
- `SubagentStart` hook: assign work item, record assignment
- `SubagentStop` hook: mark work completed or handed off
- `TeammateIdle` hook: query pending work, offer to idle agent

**MCP server**: Coordination primitives:
- `claim_work(work_id, agent_id)` -> attempt to claim work item
- `handoff_work(work_id, to_agent_id, reason, context)` -> delegate
- `check_conflicts(target_path)` -> list of agents working on same target
- `suggest_work_for_agent(agent_id)` -> match work to capability

**Implementation complexity**: High
- Schema: 3 dimensions + capability map, 3 facts
- Data capture: Requires agent team protocol changes (not built into Claude Code)
- Coordination logic: Conflict detection, capability matching, load balancing
- Queries: Graph-like (handoff chains), requires careful indexing

**Value**: Very High (for agent teams)
- Eliminates duplicate work
- Prevents merge conflicts
- Enables true parallelism (multiple agents on disjoint work items)
- Capability-based routing (send work to the best agent)

**Note**: Most valuable for agent teams (currently experimental in Claude Code). Lower priority for single-agent workflows.

---

### 5. development workflow analytics

**Problem**: "Which tools do I actually use? Which skills get invoked? What patterns emerge?" No visibility.

**Solution**: Track tool/skill invocations, measure usage patterns, identify optimization opportunities.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_tool (
    tool_id INTEGER PRIMARY KEY,
    tool_name TEXT UNIQUE NOT NULL,
    tool_type TEXT,  -- 'builtin', 'mcp', 'custom'
    description TEXT
);

CREATE TABLE dim_file (
    file_id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_type TEXT,  -- from extension: 'py', 'md', 'json', etc.
    initial_size_bytes INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE dim_user_intent (
    intent_id INTEGER PRIMARY KEY,
    intent_text TEXT,  -- user's original prompt
    intent_hash TEXT,  -- for deduplication
    categorized_as TEXT,  -- 'refactor', 'debug', 'implement', etc.
    created_at TIMESTAMP
);
```

**Facts**:
```sql
CREATE TABLE fact_tool_invocation (
    invocation_id INTEGER PRIMARY KEY,
    session_id TEXT,
    agent_id INTEGER REFERENCES dim_agent,
    tool_id INTEGER REFERENCES dim_tool,
    invoked_at TIMESTAMP,
    duration_ms INTEGER,
    success BOOLEAN,
    error_type TEXT,
    input_size_bytes INTEGER,
    output_size_bytes INTEGER,
    metadata TEXT  -- JSON: tool-specific args/results
);

CREATE TABLE fact_skill_invocation (
    invocation_id INTEGER PRIMARY KEY,
    session_id TEXT,
    component_id INTEGER REFERENCES dim_component,
    invoked_at TIMESTAMP,
    invoked_by TEXT,  -- 'user', 'agent'
    completed_at TIMESTAMP,
    success BOOLEAN,
    actions_taken INTEGER,  -- tool calls during skill execution
    metadata TEXT
);

CREATE TABLE fact_file_modification (
    modification_id INTEGER PRIMARY KEY,
    session_id TEXT,
    file_id INTEGER REFERENCES dim_file,
    modified_at TIMESTAMP,
    modification_type TEXT,  -- 'create', 'edit', 'delete', 'rename'
    agent_id INTEGER REFERENCES dim_agent,
    tool_id INTEGER REFERENCES dim_tool,
    lines_added INTEGER,
    lines_deleted INTEGER,
    chars_added INTEGER,
    chars_deleted INTEGER,
    diff_snippet TEXT  -- first 1000 chars of diff
);

CREATE TABLE fact_session_intent (
    intent_id INTEGER REFERENCES dim_user_intent,
    session_id TEXT,
    stated_at TIMESTAMP,
    achieved BOOLEAN,
    achieved_at TIMESTAMP
);
```

#### queries that unlock value

**Usage patterns**:
```sql
-- Most-used tools
SELECT t.tool_name, 
       COUNT(*) AS invocations,
       AVG(ti.duration_ms) AS avg_duration_ms,
       AVG(ti.success::INTEGER) AS success_rate
FROM fact_tool_invocation ti
JOIN dim_tool t ON t.tool_id = ti.tool_id
WHERE ti.invoked_at > current_timestamp - INTERVAL '30 days'
GROUP BY t.tool_name
ORDER BY invocations DESC;

-- Most-invoked skills
SELECT c.component_name,
       COUNT(*) AS invocations,
       SUM(CASE WHEN si.invoked_by = 'user' THEN 1 ELSE 0 END) AS user_invoked,
       SUM(CASE WHEN si.invoked_by = 'agent' THEN 1 ELSE 0 END) AS agent_invoked
FROM fact_skill_invocation si
JOIN dim_component c ON c.component_id = si.component_id
WHERE si.invoked_at > current_timestamp - INTERVAL '30 days'
GROUP BY c.component_name
ORDER BY invocations DESC;

-- Which files get edited most?
SELECT f.file_path, f.file_type,
       COUNT(*) AS edits,
       SUM(fm.lines_added) AS total_lines_added,
       SUM(fm.lines_deleted) AS total_lines_deleted
FROM fact_file_modification fm
JOIN dim_file f ON f.file_id = fm.file_id
WHERE fm.modified_at > current_timestamp - INTERVAL '90 days'
GROUP BY f.file_path, f.file_type
ORDER BY edits DESC;
```

**Workflow optimization**:
```sql
-- What tasks take the longest?
SELECT ui.categorized_as AS task_type,
       AVG(EXTRACT(EPOCH FROM (si.achieved_at - si.stated_at))) AS avg_seconds,
       COUNT(*) AS tasks
FROM fact_session_intent si
JOIN dim_user_intent ui ON ui.intent_id = si.intent_id
WHERE si.achieved = TRUE
GROUP BY ui.categorized_as
ORDER BY avg_seconds DESC;

-- Tool failure patterns
SELECT t.tool_name, ti.error_type,
       COUNT(*) AS failures
FROM fact_tool_invocation ti
JOIN dim_tool t ON t.tool_id = ti.tool_id
WHERE ti.success = FALSE
  AND ti.invoked_at > current_timestamp - INTERVAL '30 days'
GROUP BY t.tool_name, ti.error_type
ORDER BY failures DESC;
```

#### integration with claude code

**Hook points**:
- `PreToolUse` / `PostToolUse`: record tool invocations
- Skill invocation: record when skill is loaded/executed
- `PostToolUse(Write/Edit)`: record file modifications with diff stats
- `UserPromptSubmit`: capture user intent, categorize

**MCP server**: Analytics tools:
- `get_usage_stats(days=30)` -> top tools, skills, files
- `analyze_workflow(task_type)` -> typical tool sequence, duration
- `suggest_optimizations()` -> underused skills, slow tools

**Implementation complexity**: Medium
- Schema: 3 dimensions, 4 facts
- Data capture: Hook integration (straightforward), diff parsing (moderate)
- Categorization: Intent classification (could use LLM or keyword matching)
- Queries: Aggregations + time-series

**Value**: Medium
- Identifies unused skills (candidates for removal)
- Highlights slow tools (candidates for optimization)
- Reveals common patterns (candidates for automation/macros)

---

### 6. change data capture (cdc) beyond docs

**Problem**: Skill-maintainer monitors docs/git repos. What about API contracts, database schemas, config files, external service dependencies?

**Solution**: Generalize CDC pipeline to any external dependency with a versioned state.

#### schema (extends current CDC model)

**Dimensions**:
```sql
-- Extend dim_source with more types
CREATE TABLE dim_source (
    source_id INTEGER PRIMARY KEY,
    source_name TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL,  -- 'docs', 'git', 'api', 'schema', 'config', 'service'
    url TEXT,
    created_at TIMESTAMP
);

CREATE TABLE dim_dependency (
    dependency_id INTEGER PRIMARY KEY,
    dependency_name TEXT UNIQUE NOT NULL,
    dependency_type TEXT,  -- 'api_endpoint', 'db_schema', 'env_var', 'external_service'
    spec_url TEXT,
    owner TEXT,
    created_at TIMESTAMP
);

CREATE TABLE component_dependency_map (
    component_id INTEGER REFERENCES dim_component,
    dependency_id INTEGER REFERENCES dim_dependency,
    relationship_type TEXT,  -- 'consumes', 'provides', 'depends_on'
    PRIMARY KEY (component_id, dependency_id)
);
```

**Facts**:
```sql
CREATE TABLE fact_dependency_check (
    check_id INTEGER PRIMARY KEY,
    dependency_id INTEGER REFERENCES dim_dependency,
    checked_at TIMESTAMP,
    check_type TEXT,  -- 'api_call', 'schema_diff', 'config_parse', 'health_check'
    available BOOLEAN,
    version_detected TEXT,
    response_time_ms INTEGER,
    metadata TEXT  -- JSON: check-specific details
);

CREATE TABLE fact_schema_change (
    change_id INTEGER PRIMARY KEY,
    dependency_id INTEGER REFERENCES dim_dependency,
    detected_at TIMESTAMP,
    change_type TEXT,  -- 'field_added', 'field_removed', 'type_changed', 'constraint_changed'
    old_schema TEXT,  -- JSON schema snapshot
    new_schema TEXT,
    classification TEXT,  -- 'BREAKING', 'ADDITIVE', 'COSMETIC'
    affected_components TEXT  -- JSON: list of component_ids
);

CREATE TABLE fact_api_contract_change (
    change_id INTEGER PRIMARY KEY,
    dependency_id INTEGER REFERENCES dim_dependency,
    detected_at TIMESTAMP,
    endpoint TEXT,
    method TEXT,  -- 'GET', 'POST', etc.
    change_type TEXT,  -- 'endpoint_removed', 'param_required', 'response_changed'
    old_contract TEXT,  -- OpenAPI/JSON schema
    new_contract TEXT,
    classification TEXT
);
```

#### queries that unlock value

**Dependency monitoring**:
```sql
-- Which APIs are down?
SELECT d.dependency_name, d.dependency_type,
       dc.checked_at, dc.available, dc.response_time_ms
FROM fact_dependency_check dc
JOIN dim_dependency d ON d.dependency_id = dc.dependency_id
WHERE dc.checked_at > current_timestamp - INTERVAL '1 hour'
  AND dc.available = FALSE;

-- Breaking changes in dependencies
SELECT d.dependency_name, sc.detected_at, sc.change_type, sc.affected_components
FROM fact_schema_change sc
JOIN dim_dependency d ON d.dependency_id = sc.dependency_id
WHERE sc.classification = 'BREAKING'
  AND sc.detected_at > current_timestamp - INTERVAL '7 days';

-- Which components are affected by this API change?
SELECT c.component_name, c.component_type
FROM component_dependency_map cdm
JOIN dim_component c ON c.component_id = cdm.component_id
WHERE cdm.dependency_id = (
  SELECT dependency_id FROM dim_dependency WHERE dependency_name = 'anthropic_api'
);
```

**Impact analysis**:
```sql
-- Cascade analysis: what breaks if this dependency fails?
WITH RECURSIVE impact AS (
  -- Base: direct dependents
  SELECT c.component_id, c.component_name, 1 AS depth
  FROM component_dependency_map cdm
  JOIN dim_component c ON c.component_id = cdm.component_id
  WHERE cdm.dependency_id = ? 
  
  UNION
  
  -- Recursive: components that depend on dependents
  SELECT c2.component_id, c2.component_name, impact.depth + 1
  FROM impact
  JOIN component_dependency_map cdm2 ON cdm2.dependency_id = impact.component_id
  JOIN dim_component c2 ON c2.component_id = cdm2.component_id
  WHERE impact.depth < 5  -- max depth
)
SELECT component_name, depth FROM impact ORDER BY depth, component_name;
```

#### integration with claude code

**Hook points**:
- `SessionStart`: check all dependencies, warn if any are unavailable
- Periodic background task: poll APIs, check schemas, compare to stored state

**MCP server**: Dependency monitoring:
- `check_dependency_health(dependency_name)` -> availability, version, latency
- `get_breaking_changes(since_date)` -> list of breaking changes
- `analyze_impact(dependency_name)` -> cascade of affected components

**Implementation complexity**: High
- Schema: 2 dimensions + map, 3 facts
- Data capture: API polling, schema parsing (OpenAPI, JSON Schema, SQL DDL)
- Diffing logic: Structural diff for schemas/contracts (complex)
- Integration: Requires external API keys, credentials, network access

**Value**: Very High (for production systems)
- Prevents breakage from upstream API changes
- Enables proactive migration (deprecation warnings)
- Dependency graph visualization (what depends on what)

**Note**: Most relevant for production use cases (agents managing real services). Lower priority for skill development.

---

### 7. retrieval-augmented generation (rag)

**Problem**: Vector search is great for semantic similarity, but terrible for structured queries ("show me all edits to Python files last Tuesday").

**Solution**: Use DuckDB as a structured retrieval layer alongside (or instead of) vector search.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_document (
    document_id INTEGER PRIMARY KEY,
    document_path TEXT UNIQUE NOT NULL,
    document_type TEXT,  -- 'code', 'documentation', 'log', 'config'
    language TEXT,
    created_at TIMESTAMP,
    last_modified_at TIMESTAMP
);

CREATE TABLE dim_chunk (
    chunk_id INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES dim_document,
    chunk_index INTEGER,
    chunk_text TEXT,
    chunk_hash TEXT,
    line_start INTEGER,
    line_end INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    embedding FLOAT[],  -- optional: for hybrid search
    created_at TIMESTAMP
);

CREATE TABLE dim_entity (
    entity_id INTEGER PRIMARY KEY,
    entity_name TEXT UNIQUE NOT NULL,
    entity_type TEXT,  -- 'function', 'class', 'variable', 'endpoint', 'table'
    definition_chunk_id INTEGER REFERENCES dim_chunk,
    created_at TIMESTAMP
);
```

**Facts**:
```sql
CREATE TABLE fact_chunk_retrieval (
    retrieval_id INTEGER PRIMARY KEY,
    chunk_id INTEGER REFERENCES dim_chunk,
    session_id TEXT,
    retrieved_at TIMESTAMP,
    query_text TEXT,
    relevance_score REAL,
    retrieval_method TEXT,  -- 'vector', 'keyword', 'sql', 'hybrid'
    used_in_response BOOLEAN
);

CREATE TABLE fact_entity_reference (
    reference_id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES dim_entity,
    chunk_id INTEGER REFERENCES dim_chunk,
    reference_type TEXT,  -- 'definition', 'usage', 'import', 'call'
    line_number INTEGER
);

CREATE TABLE fact_document_update (
    update_id INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES dim_document,
    updated_at TIMESTAMP,
    update_type TEXT,  -- 'created', 'modified', 'deleted'
    chunks_affected INTEGER,
    reindex_required BOOLEAN
);
```

#### queries that unlock value

**Structured retrieval**:
```sql
-- Find all code chunks that use a specific function
SELECT d.document_path, c.chunk_text, er.line_number
FROM fact_entity_reference er
JOIN dim_entity e ON e.entity_id = er.entity_id
JOIN dim_chunk c ON c.chunk_id = er.chunk_id
JOIN dim_document d ON d.document_id = c.document_id
WHERE e.entity_name = 'record_validation'
  AND er.reference_type IN ('usage', 'call');

-- Temporal retrieval: what changed in the last hour?
SELECT d.document_path, c.chunk_text
FROM fact_document_update du
JOIN dim_document d ON d.document_id = du.document_id
JOIN dim_chunk c ON c.document_id = d.document_id
WHERE du.updated_at > current_timestamp - INTERVAL '1 hour'
  AND du.update_type = 'modified';

-- Hybrid search: SQL filter + vector similarity
SELECT c.chunk_text, c.embedding <=> ?::FLOAT[] AS similarity
FROM dim_chunk c
JOIN dim_document d ON d.document_id = c.document_id
WHERE d.document_type = 'code'
  AND d.language = 'python'
  AND c.chunk_text LIKE '%validation%'
ORDER BY similarity
LIMIT 10;
```

**Retrieval analytics**:
```sql
-- Which chunks are most commonly retrieved?
SELECT d.document_path, c.chunk_index,
       COUNT(*) AS retrieval_count,
       AVG(cr.relevance_score) AS avg_score
FROM fact_chunk_retrieval cr
JOIN dim_chunk c ON c.chunk_id = cr.chunk_id
JOIN dim_document d ON d.document_id = c.document_id
WHERE cr.retrieved_at > current_timestamp - INTERVAL '30 days'
GROUP BY d.document_path, c.chunk_index
ORDER BY retrieval_count DESC
LIMIT 20;

-- Dead chunks: never retrieved
SELECT d.document_path, c.chunk_index
FROM dim_chunk c
JOIN dim_document d ON d.document_id = c.document_id
LEFT JOIN fact_chunk_retrieval cr ON cr.chunk_id = c.chunk_id
WHERE cr.retrieval_id IS NULL
  AND c.created_at < current_timestamp - INTERVAL '30 days';
```

#### integration with claude code

**Hook points**:
- `PostToolUse(Read)`: record chunk retrieval
- `PostToolUse(Write/Edit)`: mark document as needing reindex
- Query interface: MCP server or direct SQL

**MCP server**: Structured RAG:
- `search_code(query, filters)` -> structured search (function name, file type, date range)
- `get_entity_references(entity_name)` -> all usages
- `get_recent_changes(since, file_type)` -> temporal retrieval

**Implementation complexity**: Very High
- Schema: 3 dimensions, 3 facts
- Chunking strategy: Language-aware splitting (AST-based for code)
- Entity extraction: AST parsing, symbol resolution
- Embedding generation: Optional (requires model inference)
- Indexing: Triggers to keep chunks in sync with file edits

**Value**: Very High (for large codebases)
- Structured queries that vector search can't handle
- Temporal retrieval (recent changes)
- Entity-centric navigation (find all usages)
- Hybrid search (combine SQL filters + semantic similarity)

**Note**: Competes with purpose-built vector DBs (Chroma, Pinecone). DuckDB wins on structured queries, loses on pure semantic search. Best for hybrid use cases.

---

### 8. prompt/response audit trails

**Problem**: Compliance, debugging, and prompt engineering require audit trails of what was asked and what was generated.

**Solution**: Store every prompt and response with metadata for compliance and analysis.

#### schema

**Dimensions**:
```sql
CREATE TABLE dim_prompt_template (
    template_id INTEGER PRIMARY KEY,
    template_name TEXT UNIQUE NOT NULL,
    template_text TEXT,
    template_hash TEXT,
    created_at TIMESTAMP
);

CREATE TABLE dim_model (
    model_id INTEGER PRIMARY KEY,
    model_name TEXT UNIQUE NOT NULL,
    provider TEXT,  -- 'anthropic', 'openai', 'google'
    model_version TEXT,
    context_window INTEGER,
    cost_per_1k_input REAL,
    cost_per_1k_output REAL
);
```

**Facts**:
```sql
CREATE TABLE fact_prompt (
    prompt_id INTEGER PRIMARY KEY,
    session_id TEXT,
    prompted_at TIMESTAMP,
    template_id INTEGER REFERENCES dim_prompt_template,
    model_id INTEGER REFERENCES dim_model,
    prompt_text TEXT,
    prompt_hash TEXT,
    system_prompt TEXT,
    user_id TEXT,
    input_tokens INTEGER,
    estimated_cost_usd REAL
);

CREATE TABLE fact_response (
    response_id INTEGER PRIMARY KEY,
    prompt_id INTEGER REFERENCES fact_prompt,
    responded_at TIMESTAMP,
    response_text TEXT,
    response_hash TEXT,
    finish_reason TEXT,  -- 'stop', 'length', 'tool_use', 'error'
    output_tokens INTEGER,
    cached_tokens INTEGER,
    latency_ms INTEGER,
    estimated_cost_usd REAL,
    safety_flags TEXT  -- JSON: moderation/safety results
);

CREATE TABLE fact_prompt_feedback (
    feedback_id INTEGER PRIMARY KEY,
    prompt_id INTEGER REFERENCES fact_prompt,
    response_id INTEGER REFERENCES fact_response,
    feedback_at TIMESTAMP,
    feedback_type TEXT,  -- 'thumbs_up', 'thumbs_down', 'report'
    feedback_text TEXT,
    user_id TEXT
);
```

#### queries that unlock value

**Audit compliance**:
```sql
-- All prompts by a specific user in a date range
SELECT p.prompted_at, p.prompt_text, r.response_text
FROM fact_prompt p
LEFT JOIN fact_response r ON r.prompt_id = p.prompt_id
WHERE p.user_id = 'alice@example.com'
  AND p.prompted_at BETWEEN '2026-02-01' AND '2026-02-14'
ORDER BY p.prompted_at;

-- Prompts that triggered safety flags
SELECT p.prompted_at, p.prompt_text, r.safety_flags
FROM fact_response r
JOIN fact_prompt p ON p.prompt_id = r.prompt_id
WHERE r.safety_flags IS NOT NULL
  AND r.safety_flags != '';
```

**Prompt engineering**:
```sql
-- Which templates produce the best responses?
SELECT pt.template_name,
       COUNT(*) AS uses,
       AVG(LENGTH(r.response_text)) AS avg_response_length,
       AVG(r.latency_ms) AS avg_latency,
       SUM(CASE WHEN pf.feedback_type = 'thumbs_up' THEN 1 ELSE 0 END)::REAL / COUNT(*) AS satisfaction
FROM fact_prompt p
JOIN dim_prompt_template pt ON pt.template_id = p.template_id
LEFT JOIN fact_response r ON r.prompt_id = p.prompt_id
LEFT JOIN fact_prompt_feedback pf ON pf.prompt_id = p.prompt_id
GROUP BY pt.template_name
ORDER BY satisfaction DESC;

-- Expensive prompts
SELECT p.prompt_text, m.model_name,
       p.input_tokens, r.output_tokens,
       (p.estimated_cost_usd + r.estimated_cost_usd) AS total_cost
FROM fact_prompt p
JOIN fact_response r ON r.prompt_id = p.prompt_id
JOIN dim_model m ON m.model_id = p.model_id
WHERE p.prompted_at > current_timestamp - INTERVAL '7 days'
ORDER BY total_cost DESC
LIMIT 20;
```

#### integration with claude code

**Hook points**:
- `UserPromptSubmit`: record prompt
- `Stop`: record response
- Custom feedback mechanism: thumbs up/down after response

**MCP server**: Audit/analysis:
- `search_prompts(query, date_range, user_id)` -> audit trail
- `analyze_template_performance(template_id)` -> metrics
- `export_audit_log(start_date, end_date)` -> compliance report

**Implementation complexity**: Low
- Schema: 2 dimensions, 3 facts
- Data capture: Hook integration (straightforward)
- Privacy: PII handling (may need redaction/encryption)
- Queries: Simple SELECTs with filters

**Value**: High (for compliance-sensitive domains)
- Regulatory compliance (GDPR, HIPAA audit trails)
- Debugging ("what did the agent see?")
- Prompt optimization (A/B testing templates)

---

### 9. cost optimization

**Problem**: No visibility into which tasks/agents/tools consume the most API credits. Can't optimize spend.

**Solution**: Track cost per dimension (agent, task, tool, session) and identify optimization opportunities.

#### schema (extends token budget schema)

**Facts**:
```sql
CREATE TABLE fact_api_call (
    call_id INTEGER PRIMARY KEY,
    session_id TEXT,
    agent_id INTEGER REFERENCES dim_agent,
    model_id INTEGER REFERENCES dim_model,
    called_at TIMESTAMP,
    call_type TEXT,  -- 'completion', 'embedding', 'tool_use'
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_tokens INTEGER,
    cost_usd REAL,
    latency_ms INTEGER,
    success BOOLEAN,
    error_type TEXT
);

CREATE TABLE fact_cost_allocation (
    allocation_id INTEGER PRIMARY KEY,
    session_id TEXT,
    component_id INTEGER REFERENCES dim_component,
    allocated_at TIMESTAMP,
    cost_usd REAL,
    allocation_method TEXT  -- 'direct', 'proportional', 'estimated'
);
```

#### queries that unlock value

**Cost analysis**:
```sql
-- Cost per agent
SELECT a.agent_name, 
       SUM(ac.cost_usd) AS total_cost,
       AVG(ac.cost_usd) AS avg_cost_per_call,
       COUNT(*) AS calls
FROM fact_api_call ac
JOIN dim_agent a ON a.agent_id = ac.agent_id
WHERE ac.called_at > current_timestamp - INTERVAL '30 days'
GROUP BY a.agent_name
ORDER BY total_cost DESC;

-- Cost per task type
SELECT t.task_type,
       SUM(ca.cost_usd) AS total_cost,
       COUNT(DISTINCT ca.session_id) AS sessions,
       SUM(ca.cost_usd) / COUNT(DISTINCT ca.session_id) AS cost_per_session
FROM fact_cost_allocation ca
JOIN dim_component c ON c.component_id = ca.component_id
JOIN dim_task t ON t.task_id = ca.component_id  -- assuming component maps to task
WHERE ca.allocated_at > current_timestamp - INTERVAL '30 days'
GROUP BY t.task_type
ORDER BY total_cost DESC;

-- Cache hit rate (cost savings)
SELECT DATE_TRUNC('day', called_at) AS day,
       SUM(input_tokens) AS total_input,
       SUM(cached_tokens) AS total_cached,
       SUM(cached_tokens)::REAL / SUM(input_tokens) AS cache_hit_rate
FROM fact_api_call
WHERE called_at > current_timestamp - INTERVAL '30 days'
GROUP BY day
ORDER BY day;
```

**Optimization opportunities**:
```sql
-- Which components are most expensive relative to value?
SELECT c.component_name,
       SUM(ca.cost_usd) AS total_cost,
       COUNT(DISTINCT ca.session_id) AS uses,
       AVG(t.success::INTEGER) AS success_rate,
       SUM(ca.cost_usd) / NULLIF(AVG(t.success::INTEGER), 0) AS cost_per_success
FROM fact_cost_allocation ca
JOIN dim_component c ON c.component_id = ca.component_id
LEFT JOIN fact_task_outcome t ON t.task_id = ca.component_id
GROUP BY c.component_name
HAVING COUNT(DISTINCT ca.session_id) > 5
ORDER BY cost_per_success DESC;
```

#### integration with claude code

**Hook points**:
- Every API call: record cost from response headers
- `TaskCompleted`: allocate costs to task/skill

**MCP server**: Cost monitoring:
- `get_cost_report(period, breakdown_by)` -> cost summary
- `suggest_cost_optimizations()` -> use cheaper models, reduce tokens
- `set_cost_alert(threshold_usd)` -> notify when exceeded

**Implementation complexity**: Low
- Schema: 0 new dimensions, 2 facts
- Data capture: Parse API response metadata (standard fields)
- Allocation: May require heuristics (distribute session cost across components)
- Queries: Aggregations

**Value**: High (for heavy users)
- Identify expensive tasks/agents
- Justify model downgrades (Opus -> Sonnet -> Haiku)
- Budget alerts (stop when limit reached)

---

### 10. self-improving agents

**Problem**: Agents repeat the same mistakes. No mechanism to learn from past failures and adjust strategies.

**Solution**: Query historical performance, detect patterns, adjust behavior based on data.

#### schema (extends agent memory + quality tracking)

**Facts**:
```sql
CREATE TABLE fact_strategy_attempt (
    attempt_id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES dim_agent,
    task_id INTEGER REFERENCES dim_task,
    strategy_name TEXT,
    attempted_at TIMESTAMP,
    success BOOLEAN,
    duration_seconds INTEGER,
    outcome_metrics TEXT,  -- JSON: task-specific success metrics
    failure_reason TEXT
);

CREATE TABLE fact_strategy_adjustment (
    adjustment_id INTEGER PRIMARY KEY,
    agent_id INTEGER REFERENCES dim_agent,
    adjusted_at TIMESTAMP,
    old_strategy TEXT,
    new_strategy TEXT,
    reason TEXT,  -- why the adjustment was made
    confidence REAL,  -- 0.0 to 1.0
    based_on_attempts INTEGER  -- how many attempts informed this decision
);
```

#### queries that unlock value

**Strategy optimization**:
```sql
-- Which strategies work best for this task type?
SELECT sa.strategy_name,
       AVG(sa.success::INTEGER) AS success_rate,
       AVG(sa.duration_seconds) AS avg_duration,
       COUNT(*) AS attempts
FROM fact_strategy_attempt sa
JOIN dim_task t ON t.task_id = sa.task_id
WHERE t.task_type = 'refactor'
GROUP BY sa.strategy_name
HAVING COUNT(*) >= 3
ORDER BY success_rate DESC, avg_duration ASC;

-- When should I switch strategies?
WITH strategy_windows AS (
  SELECT strategy_name,
         success,
         ROW_NUMBER() OVER (PARTITION BY strategy_name ORDER BY attempted_at DESC) AS recency
  FROM fact_strategy_attempt
  WHERE agent_id = ?
    AND attempted_at > current_timestamp - INTERVAL '7 days'
)
SELECT strategy_name,
       AVG(success::INTEGER) AS recent_success_rate
FROM strategy_windows
WHERE recency <= 5  -- last 5 attempts
GROUP BY strategy_name
HAVING AVG(success::INTEGER) < 0.5;  -- flag strategies with <50% recent success
```

**Learning from failures**:
```sql
-- What are the most common failure reasons?
SELECT failure_reason,
       COUNT(*) AS occurrences,
       COUNT(DISTINCT task_id) AS tasks_affected
FROM fact_strategy_attempt
WHERE success = FALSE
  AND attempted_at > current_timestamp - INTERVAL '30 days'
GROUP BY failure_reason
ORDER BY occurrences DESC;

-- Has this strategy improved over time?
SELECT DATE_TRUNC('week', attempted_at) AS week,
       AVG(success::INTEGER) AS success_rate
FROM fact_strategy_attempt
WHERE strategy_name = 'ast_refactor'
  AND attempted_at > current_timestamp - INTERVAL '90 days'
GROUP BY week
ORDER BY week;
```

#### integration with claude code

**Hook points**:
- Before task: query best strategy for this task type
- After task: record strategy outcome
- Periodic: analyze performance, suggest adjustments

**MCP server**: Self-improvement:
- `suggest_strategy(task_type, context)` -> best strategy based on history
- `record_outcome(strategy_name, success, metrics)` -> append to history
- `analyze_performance(agent_id, days=30)` -> performance report with suggestions

**Implementation complexity**: High
- Schema: 0 new dimensions, 2 facts
- Strategy definition: Requires agents to be strategy-aware (not automatic)
- Decision logic: Threshold tuning (when to switch strategies)
- Queries: Statistical analysis (confidence intervals, trend detection)

**Value**: Very High (long-term)
- Agents get better over time
- Automated A/B testing of strategies
- Failure pattern detection (avoid repeated mistakes)

**Note**: Requires significant cultural shift (agents must be designed to record and query strategies). Not a drop-in feature.

---

## general-purpose "agent state store" design

Based on the use cases above, here's a proposed architecture for a reusable library/framework.

### core schema (minimal)

**Dimensions**:
- `dim_agent` (agent_id, agent_name, agent_type, system_prompt_hash)
- `dim_session` (session_id, started_at, ended_at, working_dir)
- `dim_component` (component_id, component_name, component_type, file_path)
- `dim_task` (task_id, task_description, task_type, status)
- `dim_model` (model_id, model_name, provider, context_window, cost_per_1k_input)

**Facts**:
- `fact_agent_action` (action_id, agent_id, session_id, task_id, action_at, action_type, tool_name, target_path, metadata)
- `fact_api_call` (call_id, session_id, agent_id, model_id, called_at, input_tokens, output_tokens, cost_usd)
- `fact_quality_measurement` (measurement_id, component_id, measured_at, metric_name, score, passed)

**Extensions** (opt-in):
- Token budget tracking: `fact_token_usage`, `fact_context_overflow`
- Multi-agent: `dim_work_item`, `fact_work_assignment`, `fact_agent_handoff`
- Dependency CDC: `dim_dependency`, `fact_dependency_check`, `fact_schema_change`
- RAG: `dim_document`, `dim_chunk`, `fact_chunk_retrieval`
- Audit: `fact_prompt`, `fact_response`, `fact_prompt_feedback`
- Self-improvement: `fact_strategy_attempt`, `fact_strategy_adjustment`

### library interface

```python
from agent_store import AgentStore

# Initialize
store = AgentStore(db_path="agent_state.duckdb", schema_modules=["core", "token_budget", "quality"])

# Record events
store.record_session_start(session_id="abc123", working_dir="/path/to/project")
store.record_agent_action(
    agent_id=1,
    session_id="abc123",
    action_type="tool_call",
    tool_name="Edit",
    target_path="/path/to/file.py",
    metadata={"lines_added": 10, "lines_deleted": 5}
)
store.record_api_call(
    session_id="abc123",
    model_id=1,
    input_tokens=1200,
    output_tokens=350,
    cost_usd=0.018
)

# Query state
actions = store.get_recent_actions(session_id="abc123", limit=20)
memory = store.recall_previous_attempts(file_path="/path/to/file.py", limit=5)
budget = store.get_token_budget(component_name="my-skill")

# Export for analysis
store.export_parquet("agent_actions.parquet", table="fact_agent_action", since="2026-02-01")

# Cleanup
store.close()
```

### integration strategies

#### 1. hook-based (non-invasive)
Install hooks in `~/.claude/hooks/hooks.json` that call Python scripts:
```json
{
  "Stop": [{"type": "command", "command": "uv run record_agent_turn.py"}]
}
```

#### 2. mcp server (query interface)
Expose the store as an MCP server with tools:
- `recall_memory(file_path, limit)` -> previous attempts
- `get_token_budget(component_name)` -> current usage
- `check_quality_trend(component_name, days)` -> time-series data

#### 3. sdk wrapper (invasive but powerful)
Wrap the Claude SDK to intercept API calls and record them automatically:
```python
from agent_store import InstrumentedClient

client = InstrumentedClient(api_key=..., store_path="agent_state.duckdb")
response = client.messages.create(...)  # automatically recorded
```

### deployment models

1. **Local development**: Single-user, embedded DuckDB file in project directory
2. **Team shared state**: DuckDB file on shared network drive or git LFS
3. **Cloud analytics**: Export Parquet to S3/GCS, query with BigQuery/Athena
4. **Real-time dashboard**: DuckDB + Grafana connector for live metrics

### performance considerations

**Write throughput**:
- DuckDB WAL mode: ~10k inserts/sec on SSD
- Batch inserts: Use transactions (`BEGIN; INSERT ...; INSERT ...; COMMIT;`)
- Async writes: Background thread for recording (don't block agent loop)

**Query latency**:
- Indexes: Add indexes on foreign keys and common filter columns
- Materialized views: Pre-compute expensive aggregations
- Partition by date: `PARTITION BY DATE_TRUNC('month', action_at)` for time-series

**Storage**:
- Compression: DuckDB auto-compresses (typically 5-10x vs JSON)
- Retention policy: Archive/delete old facts after N days (configure per fact table)
- Parquet export: For long-term cold storage (S3 + Athena)

### privacy and security

**PII handling**:
- Redact user prompts: Hash or encrypt before storing
- Anonymize user_id: Use hashed IDs, not email addresses
- Right to deletion: Implement `delete_user_data(user_id)` for GDPR compliance

**Access control**:
- File permissions: DuckDB file should be readable only by owner
- Encryption at rest: Use filesystem encryption (LUKS, FileVault)
- Audit logging: Record who queries what (metadata in `fact_query_log`)

---

## implementation roadmap

### phase 1: foundation (week 1)
- [ ] Core schema (5 dimensions, 3 facts)
- [ ] Python library with `record_*()` and `get_*()` methods
- [ ] Hook integration (record session events)
- [ ] Basic queries (recent actions, token usage)

### phase 2: integration (week 2)
- [ ] MCP server (expose queries as tools)
- [ ] Claude Code hook templates (copy-paste installation)
- [ ] Export utilities (Parquet, CSV, JSON)
- [ ] Example dashboard (DuckDB + SQL queries in notebook)

### phase 3: advanced features (week 3-4)
- [ ] Multi-agent coordination (work items, handoffs)
- [ ] Dependency CDC (API monitoring, schema diff)
- [ ] Self-improvement (strategy tracking, performance analysis)
- [ ] RAG integration (structured retrieval, entity extraction)

### phase 4: production hardening (week 5+)
- [ ] Performance optimization (indexes, materialized views)
- [ ] Retention policies (auto-archive old data)
- [ ] Privacy compliance (PII redaction, deletion)
- [ ] Documentation and examples

---

## comparison to existing solutions

| Solution | Strength | Weakness | When to Use |
|---|---|---|---|
| **DuckDB star schema** | Structured queries, temporal analysis, ACID | Requires schema design, SQL knowledge | Production agents, analytics, compliance |
| **Vector DB (Chroma, Pinecone)** | Semantic search, RAG | Poor for structured queries, no temporal | Pure RAG use cases |
| **JSON logs** | Simple, human-readable | No querying, no aggregations | Debugging, small-scale |
| **Redis** | Fast, real-time | In-memory (data loss risk), no analytics | Session state, caching |
| **PostgreSQL** | OLTP, transactions | Slower for analytics than DuckDB | Multi-user, transactional |
| **Parquet + Athena** | Scalable, cheap storage | High query latency, no real-time | Archived data, warehouse |

**DuckDB sweet spot**: Embedded analytics for single-user or small-team agents with structured temporal queries.

---

## strategic recommendations

### high priority (implement first)

1. **Agent memory and continuity** (use case 1)
   - Value: Immediate productivity boost
   - Complexity: Medium
   - Integration: Hook-based

2. **Token budget optimization** (use case 2)
   - Value: Prevents context overflow failures
   - Complexity: Low
   - Integration: Hook-based + views

3. **Quality tracking over time** (use case 3)
   - Value: Confidence in auto-update systems
   - Complexity: Medium
   - Integration: Validation pipeline

### medium priority (evaluate need)

4. **Development workflow analytics** (use case 5)
   - Value: Identify optimization opportunities
   - Complexity: Medium
   - Integration: Hook-based

5. **Prompt/response audit trails** (use case 8)
   - Value: Compliance, debugging
   - Complexity: Low
   - Integration: Hook-based

6. **Cost optimization** (use case 9)
   - Value: Budget control
   - Complexity: Low
   - Integration: API response parsing

### low priority (niche use cases)

7. **Multi-agent coordination** (use case 4)
   - Value: Very high for agent teams
   - Complexity: High
   - Requires: Agent team protocol (experimental)

8. **CDC beyond docs** (use case 6)
   - Value: High for production systems
   - Complexity: Very high
   - Requires: External integrations

9. **RAG** (use case 7)
   - Value: High for large codebases
   - Complexity: Very high
   - Competes with: Purpose-built vector DBs

10. **Self-improving agents** (use case 10)
    - Value: Very high long-term
    - Complexity: Very high
    - Requires: Cultural shift (strategy-aware agents)

---

## conclusion

**Core insight validated**: LLM agent interactions generate rich structured data that dimensional modeling unlocks.

**Current implementation**: fb-claude-skills demonstrates the pattern for CDC pipelines (docs/source monitoring, validation, updates). This is a narrow vertical slice.

**General-purpose pattern**: "Agent State Store" = DuckDB + star schema + Python library + MCP server + hooks integration. Supports 10+ use cases across memory, budget, quality, coordination, analytics, CDC, RAG, audit, cost, and self-improvement.

**Next steps**:
1. Refactor current `store.py` into a reusable library (extract skill-specific logic)
2. Implement core schema (5 dims, 3 facts) as "agent_store" package
3. Build MCP server wrapper (expose queries as tools)
4. Create hook templates for easy installation
5. Document with examples (Jupyter notebooks, SQL queries)

**Long-term vision**: Every Claude Code session automatically populates a queryable dimensional model. Agents recall previous attempts, optimize token budgets, track quality trends, and learn from failures—all through SQL queries over a single .duckdb file.

This is not a database—it's an agent memory system.
