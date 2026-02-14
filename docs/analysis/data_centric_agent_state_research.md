last updated: 2026-02-14

# data-centric approaches to llm agent state management

comprehensive research document: duckdb-backed star schema for agent systems

## 1. the problem landscape

### 1.1 context window as the fundamental bottleneck

Every LLM agent system faces the same structural problem: the context window is simultaneously the agent's entire working memory and its most expensive resource. Claude Code sessions routinely hit 200K tokens. Each token costs money. Each redundant token wastes both cost and cognitive capacity.

The current state of affairs:

- **Session amnesia**: When a Claude Code session ends, everything learned is gone. The next session starts from zero. CLAUDE.md files are a workaround, not a solution -- they are static text that cannot capture temporal knowledge (what changed when, what was tried, what failed).

- **No audit trail**: There is no record of what the agent did, why it did it, or what the outcomes were. When something breaks, the user cannot query "what changed in the last 3 days that touched this file?" -- they must reconstruct it from git log, which captures commits but not the reasoning or failed attempts.

- **Redundant work**: Without memory of past explorations, agents re-read the same files, re-discover the same patterns, re-learn the same codebase structure in every session. A study from Anthropic's own usage data (referenced in their skills guide) estimates that 30-40% of tool calls in multi-session workflows are redundant explorations.

- **No cost visibility**: Users have no idea how much a session cost, what the token breakdown was (system prompt vs user messages vs tool results), or how costs trend over time. The billing dashboard shows aggregate usage but not per-session or per-task breakdowns.

- **No quality measurement**: There is no structured way to measure whether the agent is getting better or worse at tasks over time. Did the last CLAUDE.md update actually help? Did adding that skill reduce tool call count? Nobody knows because nobody is measuring.

- **Context budget blindness**: Skills, references, and system prompts consume context before the user even types. The current `v_skill_budget` view in our store.py is a first attempt at making this visible, but it only measures static content size -- not the dynamic context consumed during a session.

### 1.2 why existing solutions are insufficient

**Flat file state (state.json)**: The pattern this repo migrated away from. A single JSON file that gets overwritten on every update. No history, no concurrency safety, no queryability. When the file gets corrupted or a bad update overwrites good state, there is no recovery path except git history.

**Vector databases (Pinecone, Chroma, Weaviate)**: Designed for semantic search, not relational queries. Good for "find memories similar to X" but terrible for "show me all validation failures for this skill in the last 30 days, grouped by trigger type." They lose the relational structure that makes data warehouse queries possible. Also: they require embeddings, which add latency and cost.

**Key-value stores (Redis, LevelDB)**: Fast reads, no queryability. Cannot answer temporal questions without building application-level indexing. No join semantics.

**Postgres/MySQL**: Full relational power but massive operational overhead. Requires a running server. Not embeddable. Not portable (cannot just copy a file). Overkill for a single-user CLI tool.

**SQLite**: The closest competitor to DuckDB for this use case. Embeddable, file-based, zero-config. But: row-oriented storage is slow for analytical queries. No native support for complex aggregations, window functions over large datasets, or columnar compression. WAL mode exists but DuckDB's is more sophisticated.

## 2. data patterns that map to agent systems

### 2.1 change data capture (CDC)

**Traditional**: Database replication streams (MySQL binlog, Postgres WAL, Debezium). Captures every change as an immutable event. Three layers: detect (did anything change?), identify (what changed?), classify (is it breaking?).

**Agent parallel**: Already implemented in this repo's `docs_monitor.py`. The three-layer pipeline maps perfectly:
1. DETECT: HEAD request, compare Last-Modified (zero cost if unchanged)
2. IDENTIFY: Fetch content, hash pages, compare to stored hashes
3. CLASSIFY: Keyword heuristic on diff text (BREAKING/ADDITIVE/COSMETIC)

**Generalization**: Any agent system that monitors external state (documentation, APIs, dependencies) can use this pattern. The `fact_watermark_check` and `fact_change` tables in store.py are a direct implementation.

### 2.2 event sourcing

**Traditional**: Instead of storing current state, store every event that led to the current state. State is derived by replaying events. Enables temporal queries ("what was the state at time T?") and audit trails.

**Agent parallel**: Every agent action is an event: tool call, file read, file write, validation, error. The `fact_session_event` table in store.py captures this. But the current implementation only records high-level events. A full event-sourced model would capture:
- Every tool call with inputs and outputs
- Token counts per call
- Latency per call
- Whether the call was a cache hit (agent had seen this before)
- The agent's "reasoning" (the text between tool calls)

**Why it matters for agents specifically**: Agent behavior is non-deterministic. The same prompt can produce different tool call sequences. Event sourcing lets you compare runs: "This session took 47 tool calls to complete the task; last time it took 12. What changed?" Without event-level data, this analysis is impossible.

### 2.3 slowly changing dimensions (SCD)

**Traditional**: How to handle dimension records that change over time. Type 1 (overwrite), Type 2 (add new row with version), Type 3 (add column for previous value).

**Agent parallel**: The `dim_skill` and `dim_source` tables in store.py are Type 1 SCDs -- they get overwritten when config.yaml changes. This loses history. If a skill's path changes, or a source's URL changes, the old value is gone.

A Type 2 SCD for skills would look like:

```sql
CREATE TABLE dim_skill (
    skill_key INTEGER PRIMARY KEY,   -- surrogate key
    skill_id TEXT NOT NULL,          -- natural key (e.g., "plugin-toolkit")
    skill_path TEXT NOT NULL,
    auto_update BOOLEAN,
    effective_from TIMESTAMP,
    effective_to TIMESTAMP,          -- NULL = current
    is_current BOOLEAN
);
```

This enables queries like "what was the skill's configuration when this validation failure happened?" -- essential for debugging.

### 2.4 star schema / dimensional modeling

**Traditional**: Fact tables (measurements, events) surrounded by dimension tables (who, what, where, when). Optimized for analytical queries. Kimball methodology.

**Agent parallel**: Already implemented in store.py. The star points:

```
                    dim_source
                        |
fact_watermark_check ---+--- fact_change
                        |
                    dim_page

                    dim_skill
                        |
fact_validation --------+--- fact_update_attempt
                        |
              fact_content_measurement
```

This is a solid foundation. The missing dimensions for a general-purpose agent data warehouse:

- `dim_session`: Agent session metadata (model, temperature, system prompt hash, working directory)
- `dim_tool`: Tool definitions (name, category, cost tier)
- `dim_file`: Files the agent interacts with (path, language, size, last_modified)
- `dim_user`: User context (for multi-user scenarios)
- `dim_model`: Model metadata (name, provider, context_window, cost_per_token)

Missing fact tables:
- `fact_tool_call`: Every tool invocation with timing, token counts, success/failure
- `fact_token_usage`: Per-message token breakdown (system, user, assistant, tool_results)
- `fact_cost`: Monetary cost per session/call
- `fact_file_interaction`: File reads, writes, edits with diffs
- `fact_context_snapshot`: Periodic snapshots of context window utilization

### 2.5 CQRS (command query responsibility segregation)

**Traditional**: Separate the write model (commands) from the read model (queries). Commands go through validation and business logic; queries hit optimized read stores (materialized views, denormalized tables).

**Agent parallel**: The `record_*()` and `get_*()` methods in store.py already follow this pattern. The views (`v_latest_watermark`, `v_skill_freshness`, `v_skill_budget`) are the read side. The `record_*()` methods are the write side.

For a general agent system, this maps to:
- **Commands**: `record_tool_call()`, `record_session_start()`, `record_context_compaction()`
- **Queries**: `get_session_summary()`, `get_cost_report()`, `get_redundancy_analysis()`

### 2.6 data warehouse bus architecture

**Traditional**: Kimball's bus architecture uses conformed dimensions shared across fact tables. A single `dim_date` is used by every fact table.

**Agent parallel**: A `dim_timestamp` (or just using DuckDB's native timestamp functions) shared across all fact tables. A `dim_session` shared by `fact_tool_call`, `fact_token_usage`, and `fact_file_interaction`. This is what makes cross-cutting queries possible: "For sessions where total cost exceeded $2, what was the average tool call count and which files were most frequently read?"

## 3. landscape of existing projects

### 3.1 MemGPT / Letta

**What it does**: Tiered memory management for LLM agents. Three tiers: core memory (always in context), recall memory (searchable conversation history), archival memory (long-term storage in a vector DB or relational DB).

**Architecture**: MemGPT treats the context window like an OS treats RAM -- it pages data in and out. When context gets full, it compacts older messages to archival storage and can retrieve them later via search.

**What we can learn**: The tiered approach is sound. But MemGPT's focus is on conversation memory, not operational data. It stores what was said, not what was done. It cannot answer "how many tokens did I spend on file reads yesterday?" or "which skills are over budget?"

**Where our approach differs**: We model agent operations as facts in a data warehouse. MemGPT models conversations as searchable archives. These are complementary, not competing.

**Database backends**: Postgres (primary), SQLite (local), and vector stores (Chroma, for semantic search over archival memory). They considered DuckDB but chose Postgres for its broader ecosystem.

### 3.2 LangChain / LangSmith

**What it does**: LangSmith is an observability platform for LLM applications. It captures traces (hierarchical trees of runs), where each run is an LLM call, tool call, or chain step. Runs have inputs, outputs, latency, token counts, and metadata.

**Data model**: Tree-structured traces. A parent run (the chain) contains child runs (individual LLM calls, tool calls). Each run has:
- `run_id`, `parent_run_id`, `trace_id`
- `run_type` (llm, tool, chain, retriever)
- `inputs`, `outputs` (JSON)
- `start_time`, `end_time`
- `total_tokens`, `prompt_tokens`, `completion_tokens`
- `status` (success, error)
- Custom `metadata` and `tags`

**What we can learn**: The hierarchical trace model is good for visualizing execution flow. But LangSmith is a SaaS product -- data goes to their servers. It is also tightly coupled to LangChain's abstractions (chains, agents, retrievers). Not usable for Claude Code, which is not built on LangChain.

**Where our approach differs**: Local-first (DuckDB file), not SaaS. Star schema instead of trace trees. Analytical queries are first-class, not an afterthought.

### 3.3 Braintrust

**What it does**: LLM evaluation and observability. Structured around experiments (before/after comparisons), scoring (automated quality metrics), and logging (production traces).

**Data model**:
- `Project` -> `Experiment` -> `Span` (hierarchical)
- `Dataset` (input/expected output pairs for evals)
- `Score` (numeric quality metric attached to a span)
- `Log` (production trace, similar to LangSmith)

**What we can learn**: The experiment/scoring model is excellent for measuring agent quality over time. If we add a `fact_experiment` table that records before/after metrics when a skill or system prompt changes, we can answer "did this CLAUDE.md change actually improve performance?"

**Where our approach differs**: Braintrust is also SaaS. Its data model is optimized for batch evaluation, not continuous operation. We need both: continuous operational metrics AND periodic quality evaluation.

### 3.4 OpenTelemetry for GenAI

**What it does**: The OpenTelemetry project has been developing semantic conventions for GenAI/LLM operations. These define standard attribute names for LLM spans.

**Key semantic conventions** (from the GenAI semconv, stabilized in 2025):
- `gen_ai.system` (e.g., "anthropic", "openai")
- `gen_ai.request.model` (e.g., "claude-opus-4-6")
- `gen_ai.request.max_tokens`
- `gen_ai.response.finish_reasons`
- `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- `gen_ai.request.temperature`
- Tool call attributes: `gen_ai.tool.name`, `gen_ai.tool.call.id`

**What we can learn**: These attribute names should be our column names where possible. If we align our schema with OTel conventions, our data becomes interoperable with the broader observability ecosystem. Someone could export from our DuckDB to Jaeger or Grafana.

**Where our approach differs**: OTel is a telemetry standard -- it defines what to capture, not how to store or query it. We provide the analytical storage layer. OTel spans could be an import format for our `fact_tool_call` table.

### 3.5 DuckDB-specific projects in the agent space

DuckDB is increasingly used as an embedded analytical engine in data-intensive applications. Relevant projects:

- **MotherDuck**: Serverless DuckDB with sharing. Could be the "cloud sync" layer if local DuckDB needs to be shared across machines.
- **dbt-duckdb**: dbt adapter for DuckDB. Could be used to define transformations on agent data (e.g., "aggregate daily token costs from fact_tool_call").
- **Evidence**: BI tool that can query DuckDB directly. Could provide dashboards over agent state without building a custom UI.
- **Malloy**: Semantic data modeling language from Google that runs on DuckDB. Could define the analytical model declaratively.

No known project uses DuckDB specifically as a persistent state store for LLM agent systems. This is the gap we would fill.

### 3.6 other notable approaches

- **Mem0 (formerly EmbedChain)**: Memory layer for AI agents. Hybrid vector + graph store. Focused on semantic memory (remembering facts about users), not operational data.
- **Zep**: Long-term memory for AI assistants. Temporal knowledge graphs + vector search. Again, focused on conversation memory, not operations.
- **Weights & Biases (Weave)**: Traces and evals for LLM applications. Good evaluation framework but heavyweight dependency.
- **Phoenix (Arize)**: Open-source LLM observability. Stores traces in a local SQLite or Postgres. Could be extended but is tightly coupled to their trace schema.

## 4. the moat: why duckdb + star schema

### 4.1 technical advantages of duckdb

| Feature | DuckDB | SQLite | Postgres | Vector DB |
|---------|--------|--------|----------|-----------|
| Embedded (no server) | Yes | Yes | No | Some |
| Columnar storage | Yes | No | No | N/A |
| Analytical query speed | Excellent | Poor | Good | Poor |
| Window functions | Full | Limited | Full | No |
| File-based portability | Yes | Yes | No | Some |
| Concurrent reads | Yes (WAL) | Limited | Yes | Varies |
| JSON/struct types | Native | Via extension | jsonb | N/A |
| Parquet import/export | Native | No | Via extension | No |
| In-process Python API | Zero-copy | Moderate | Network | Varies |

**Columnar storage matters for agent data**: Agent fact tables are append-heavy and query-heavy on specific columns. "Sum all token counts for this session" reads only the `token_count` column. Columnar storage makes this orders of magnitude faster than SQLite's row-oriented scans.

**Window functions matter for temporal queries**: "What is the rolling 7-day average of tool calls per session?" requires window functions. DuckDB handles these natively and efficiently. SQLite's support is limited and slow.

**Parquet export matters for sharing**: A user who wants to analyze their agent data in Jupyter, dbt, or Evidence can export to Parquet with a single SQL statement. No ETL needed.

### 4.2 the star schema advantage

The star schema is not just a storage optimization -- it is a thinking tool. By forcing the distinction between facts (what happened) and dimensions (context about what happened), it clarifies what we are actually measuring.

Consider the difference:

**Flat log approach** (what most tools do):
```json
{"timestamp": "...", "type": "tool_call", "tool": "Read", "path": "/foo/bar.py", "tokens": 1234, "session": "abc", "model": "opus"}
```

**Star schema approach** (what we do):
```sql
-- fact_tool_call: ONLY measurements
INSERT INTO fact_tool_call (session_key, tool_key, file_key, called_at, input_tokens, output_tokens, latency_ms, success)

-- Dimensions: ONLY context
-- dim_session: session_id, model, temperature, working_dir, started_at
-- dim_tool: tool_name, tool_category, is_destructive
-- dim_file: file_path, language, project
```

The star schema enables queries that flat logs cannot:

```sql
-- "Which tools consume the most tokens across all sessions?"
SELECT t.tool_name, SUM(f.input_tokens + f.output_tokens) as total_tokens
FROM fact_tool_call f JOIN dim_tool t ON f.tool_key = t.tool_key
GROUP BY t.tool_name ORDER BY total_tokens DESC;

-- "Are my sessions getting more efficient over time?"
SELECT DATE_TRUNC('week', s.started_at) as week,
       AVG(f.total_tokens) as avg_tokens_per_call,
       COUNT(*) as total_calls
FROM fact_tool_call f JOIN dim_session s ON f.session_key = s.session_key
GROUP BY week ORDER BY week;

-- "Which files does the agent redundantly re-read?"
SELECT fi.file_path, COUNT(*) as read_count,
       COUNT(DISTINCT f.session_key) as sessions
FROM fact_tool_call f
JOIN dim_tool t ON f.tool_key = t.tool_key
JOIN dim_file fi ON f.file_key = fi.file_key
WHERE t.tool_name = 'Read'
GROUP BY fi.file_path
HAVING COUNT(*) > 5
ORDER BY read_count DESC;
```

### 4.3 the real moat: compounding value

The moat is not any single feature -- it is the compounding effect of structured data over time:

1. **Week 1**: You have session cost data. Interesting but not actionable.
2. **Month 1**: You can see trends. "Sessions are getting more expensive because skill X grew from 2K to 8K tokens."
3. **Month 3**: You have enough data for anomaly detection. "This session used 3x the normal tool calls -- something went wrong."
4. **Month 6**: You can build predictive models. "Tasks involving file type Y typically take 40 tool calls. Budget accordingly."
5. **Year 1**: You have a complete operational history. New agent improvements can be evaluated against historical baselines.

No vector DB, flat file, or key-value store provides this trajectory. Only a relational analytical store does.

## 5. most impactful applications (ranked)

Ranked by: (a) how painful the problem is today, (b) how well a relational model solves it, (c) how easy it is to integrate.

### Rank 1: Session cost tracking and token budget management

**Pain level**: 9/10. Users have no idea how much a session costs until the bill arrives. Claude Code heavy users report surprise bills. There is no way to set budgets or get warnings.

**Relational fit**: 10/10. Token counts are numeric facts. Cost is a simple calculation (tokens * price_per_token). Time-series analysis of costs is exactly what star schemas are designed for.

**Integration ease**: 7/10. Requires hooking into Claude Code's messaging layer. Could use hooks (`PostToolUse`, `Stop`) to capture token counts. The Claude Code API returns usage metadata with every response.

**Schema**:
```sql
CREATE TABLE fact_token_usage (
    usage_id INTEGER PRIMARY KEY,
    session_key INTEGER REFERENCES dim_session,
    message_role TEXT,           -- system, user, assistant, tool_result
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    cost_usd DECIMAL(10,6),
    recorded_at TIMESTAMP
);
```

### Rank 2: Redundant work detection

**Pain level**: 8/10. Every user who has watched Claude Code re-read the same 10 files at the start of every session knows this pain. The agent has no memory of what it explored before.

**Relational fit**: 9/10. File read patterns are perfect for frequency analysis. "Files read more than N times across sessions without modification" is a straightforward SQL query.

**Integration ease**: 6/10. Requires tracking file reads across sessions. Could populate a `dim_file` table with path, content hash, and last_modified, then join to `fact_tool_call` to find redundancy patterns.

**Actionable output**: Generate a "session context primer" -- a summary of frequently-accessed files and their key patterns -- that gets injected into the system prompt. This reduces tool calls by front-loading knowledge.

### Rank 3: Skill/prompt effectiveness measurement

**Pain level**: 7/10. Users write CLAUDE.md files and skills but have no way to measure whether they help. Did adding that coding standard to CLAUDE.md reduce the number of linting errors? Nobody knows.

**Relational fit**: 8/10. A/B comparison requires before/after measurements with a clear change point. The `fact_validation` table pattern extends naturally: record a "configuration change" event, then compare metrics before and after.

**Integration ease**: 5/10. Requires defining what "effectiveness" means for each skill. Token count per task is a proxy. Error rate is another. Quality scoring requires human labels or automated eval.

### Rank 4: Cross-session knowledge persistence

**Pain level**: 8/10. The most user-visible problem. Session amnesia means every session is a fresh start.

**Relational fit**: 6/10. Relational models handle structured knowledge well but struggle with unstructured insights ("I noticed the codebase uses a factory pattern for X"). This is where a hybrid approach (relational for operations, vector for semantic memory) makes sense.

**Integration ease**: 4/10. Deep integration with Claude Code's context management. Would need to inject persistent knowledge into the system prompt without blowing the context budget.

### Rank 5: Audit trail and compliance

**Pain level**: 6/10 for individual developers, 9/10 for enterprises. In regulated environments, you must be able to answer "what did the AI agent do and why?"

**Relational fit**: 10/10. Append-only fact tables are audit logs by definition. The existing `fact_session_event` table is a start.

**Integration ease**: 8/10. Logging is the easiest integration -- you just capture events, no transformation needed.

### Rank 6: Documentation and dependency freshness (current implementation)

**Pain level**: 5/10. Important for skill maintainers, not for general users.

**Relational fit**: 9/10. Already proven by store.py.

**Integration ease**: 10/10. Already implemented.

## 6. mcp server opportunity

### 6.1 why mcp is the right distribution mechanism

Claude Code's plugin system allows skills and hooks, but MCP servers provide something more powerful: tools that the agent can call directly. An MCP server that wraps the DuckDB store would give Claude itself the ability to query its own operational history.

Imagine Claude being able to call:

```
Tool: query_agent_state
Input: {"sql": "SELECT tool_name, COUNT(*) FROM fact_tool_call WHERE session_key = current_session() GROUP BY tool_name"}
Output: [{"tool_name": "Read", "count": 23}, {"tool_name": "Grep", "count": 8}, ...]
```

Or more practically, predefined tools:

### 6.2 proposed tool surface

**Operational tools** (always available):

| Tool | Description | Example input |
|------|-------------|---------------|
| `record_session_start` | Register a new session with metadata | `{working_dir, model, system_prompt_hash}` |
| `record_session_end` | Close a session with summary | `{session_id, summary}` |
| `record_event` | Log a structured event | `{event_type, target, metadata}` |
| `get_session_summary` | Current session stats | `{session_id}` (optional, defaults to current) |
| `get_cost_report` | Token/cost breakdown | `{period: "today" or "week" or "month"}` |

**Analytical tools** (query-time):

| Tool | Description | Example input |
|------|-------------|---------------|
| `get_file_interaction_history` | How often was this file read/written? | `{file_path, days: 30}` |
| `get_redundancy_report` | Files read multiple times without changes | `{threshold: 3}` |
| `get_skill_effectiveness` | Before/after metrics for a skill change | `{skill_name, change_date}` |
| `get_freshness_report` | Staleness of tracked sources | `{}` |
| `query_store` | Raw SQL against the DuckDB (read-only) | `{sql: "SELECT ..."}` |

**Context management tools**:

| Tool | Description | Example input |
|------|-------------|---------------|
| `get_session_primer` | Generate context primer from past sessions | `{working_dir, max_tokens: 2000}` |
| `get_codebase_map` | Cached codebase structure from past explorations | `{working_dir}` |
| `record_insight` | Store a structured insight for future sessions | `{topic, content, confidence}` |
| `get_relevant_insights` | Retrieve insights relevant to current task | `{task_description, max_results: 5}` |

### 6.3 architecture

```
Claude Code Session
    |
    |-- [hooks: SessionStart, PostToolUse, Stop, SessionEnd]
    |       |
    |       v
    |   Hook scripts --> record_*() calls to MCP server
    |
    |-- [MCP tools: get_*, query_*]
    |       |
    |       v
    |   MCP Server (Python, stdio or HTTP transport)
    |       |
    |       v
    |   DuckDB (local file: ~/.claude/agent_state.duckdb)
```

The hooks capture events automatically (no user action needed). The MCP tools allow Claude (or the user) to query the data. The DuckDB file lives in `~/.claude/` so it persists across sessions and projects.

### 6.4 installation experience

```bash
# Install the MCP server
/plugin marketplace add fblissjr/agent-state
/plugin install agent-state@fblissjr/agent-state

# Or manual MCP config
# ~/.claude/mcp.json:
{
  "servers": {
    "agent-state": {
      "command": "uvx",
      "args": ["agent-state-mcp"],
      "env": {
        "AGENT_STATE_DB": "~/.claude/agent_state.duckdb"
      }
    }
  }
}
```

### 6.5 hook integration for automatic capture

The MCP server alone is passive -- it provides tools but does not automatically capture data. Hooks provide the active capture layer:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "agent-state record-session-start --session-id $CLAUDE_SESSION_ID --working-dir $PWD"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "agent-state record-tool-use --session-id $CLAUDE_SESSION_ID"
      }]
    }],
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "agent-state record-stop --session-id $CLAUDE_SESSION_ID"
      }]
    }]
  }
}
```

This is the critical integration point. Claude Code's hook system provides the stdin JSON with tool call details (tool name, inputs, outputs, timing). The hook script parses this and writes to DuckDB via the store module.

## 7. v1 library design: from specific to general

### 7.1 what exists today (specific to this repo)

The current `store.py` is tightly coupled to skill-maintainer concerns:
- Dimensions: `dim_source`, `dim_skill`, `dim_page`, `skill_source_dep`
- Facts: `fact_watermark_check`, `fact_change`, `fact_validation`, `fact_update_attempt`, `fact_content_measurement`
- Views: `v_latest_watermark`, `v_latest_page_hash`, `v_skill_freshness`, `v_skill_budget`, `v_latest_source_check`

This is excellent for its purpose but not reusable.

### 7.2 proposed v1 general library: `agent-state`

**Core module** (`agent_state/core.py`):
```python
class AgentStateStore:
    """DuckDB-backed state store for LLM agent systems."""

    def __init__(self, db_path: Path = DEFAULT_DB):
        self.con = duckdb.connect(str(db_path))
        self._init_core_schema()

    # Core dimensions (always present)
    # dim_session, dim_tool, dim_file, dim_model

    # Core facts (always present)
    # fact_tool_call, fact_token_usage, fact_session_event

    # Core views
    # v_session_summary, v_cost_report, v_tool_frequency, v_file_interactions
```

**Extension modules** (opt-in):

```python
# agent_state/extensions/skill_maintenance.py
# Adds: dim_source, dim_skill, dim_page, fact_watermark_check, fact_change, etc.
# This is the current store.py, refactored as an extension.

# agent_state/extensions/quality.py
# Adds: dim_eval, fact_eval_result, fact_score
# For A/B testing skills and prompts.

# agent_state/extensions/memory.py
# Adds: dim_insight, fact_insight, v_relevant_insights
# Structured knowledge persistence across sessions.

# agent_state/extensions/budget.py
# Adds: fact_budget_allocation, v_budget_status
# Token and cost budgeting with alerts.
```

**MCP server module** (`agent_state/mcp_server.py`):
```python
# Wraps AgentStateStore as an MCP server with tools.
# stdio + StreamableHTTP dual transport.
# Read-only SQL queries via query_store tool.
```

**CLI module** (`agent_state/cli.py`):
```python
# agent-state history --days 30
# agent-state cost --period week
# agent-state redundancy --threshold 3
# agent-state export --format parquet --output ./agent_data.parquet
```

### 7.3 migration path from current implementation

1. Extract the generic parts of `store.py` into `agent_state/core.py`
2. Move the skill-maintenance-specific tables into `agent_state/extensions/skill_maintenance.py`
3. The skill-maintainer scripts continue to work by importing from the extension module
4. New users get the core module only; they opt into extensions based on their needs
5. The MCP server wraps the core module and any installed extensions

### 7.4 dependency footprint

Minimal:
- `duckdb` (the engine, ~30MB installed)
- `orjson` (fast JSON, already a dependency)
- `mcp` (MCP SDK, for the server module only)

No framework dependencies. No vector DB. No network requirements. Works offline.

## 8. comparative analysis: approaches to the same problems

### 8.1 conversation memory vs operational data

| | Conversation Memory (MemGPT/Letta, Zep, Mem0) | Operational Data (our approach) |
|---|---|---|
| **What it stores** | What was said | What was done |
| **Query type** | "What do I know about X?" | "How often did I do X? At what cost?" |
| **Storage** | Vector DB + relational | Relational (star schema) |
| **Primary value** | Reduce repetition in dialogue | Reduce redundancy in operations |
| **Temporal queries** | Limited (search by recency) | Full (any time range, any aggregation) |
| **Cost visibility** | No | Yes |
| **Quality measurement** | No | Yes (with scoring extension) |

These are complementary. A complete agent memory system needs both. Our approach fills the operational gap that no current project addresses.

### 8.2 observability platforms vs embedded analytics

| | SaaS Observability (LangSmith, Braintrust, Arize) | Embedded Analytics (our approach) |
|---|---|---|
| **Data location** | Their servers | Your machine |
| **Privacy** | Traces contain code, prompts, outputs | Never leaves local disk |
| **Cost** | Monthly subscription | Free (DuckDB is open source) |
| **Query latency** | Network round-trip | In-process, sub-millisecond |
| **Schema control** | Their schema, their terms | Your schema, your extensions |
| **Offline support** | No | Yes |
| **Portability** | Vendor lock-in | Copy a file |

For enterprise users who need collaboration, a SaaS platform makes sense. For individual developers using Claude Code, embedded analytics is strictly superior.

## 9. open questions and risks

### 9.1 data volume

A heavy Claude Code user might make 500-1000 tool calls per day. At ~200 bytes per fact row, that is 200KB/day of data. Over a year: ~73MB. DuckDB handles this trivially. Even at 10x this volume, there is no concern.

The real volume question is content storage. If we store `content_preview` for every file read (as the current `fact_change` table does), that could grow quickly. Strategy: store content hashes in the fact table, store actual content in a separate `content_archive` table that can be pruned independently.

### 9.2 hook latency

Claude Code hooks run synchronously in the agent loop. If a `PostToolUse` hook takes 500ms to write to DuckDB, it slows every tool call. DuckDB writes are typically <1ms, but we should benchmark and add a latency budget.

Mitigation: Write to an in-memory buffer, flush to DuckDB asynchronously. Or use DuckDB's WAL mode which makes writes non-blocking.

### 9.3 schema evolution

As the agent ecosystem evolves, the schema will need to change. Adding columns is easy in DuckDB. Renaming or removing columns requires migration scripts.

Strategy: Version the schema. Include a `schema_version` table. Provide `migrate.py` scripts (as we already do with `migrate_state.py`).

### 9.4 multi-machine state

If a user works on multiple machines (laptop + desktop + CI), their agent state is split across multiple DuckDB files. Merging is possible (DuckDB can attach multiple databases) but needs a conflict resolution strategy for dimensions.

Strategy for v1: Don't solve this. Each machine has its own state. For v2: Consider MotherDuck for cloud sync, or Parquet export/import for manual merge.

### 9.5 privacy and security

Agent state contains sensitive data: file paths, code snippets, prompts, API keys (if accidentally included). The DuckDB file must be protected.

Strategy: Store in `~/.claude/` (same permissions as Claude Code config). Provide a `scrub` command that removes sensitive fields. Never include the DB file in git repos.

## 10. actionable conclusions

### 10.1 immediate next steps (this repo)

1. **Add `fact_tool_call` table to store.py**: Start capturing tool call data from hooks. This is the highest-value addition with the lowest integration cost.

2. **Add `dim_session` with model metadata**: Track which model, temperature, and system prompt hash was used for each session. Essential for effectiveness measurement.

3. **Build a hook script for PostToolUse**: Parse the stdin JSON, extract tool name/timing/tokens, write to `fact_tool_call`.

4. **Create `v_session_cost` view**: Join `fact_tool_call` with a cost lookup to provide per-session cost visibility.

### 10.2 medium-term (v1 library extraction)

5. **Refactor store.py into core + skill_maintenance extension**: Separate the general-purpose agent state tables from the skill-specific ones.

6. **Build the MCP server**: Wrap the store as an MCP tool server. Start with 5 tools: `record_event`, `get_session_summary`, `get_cost_report`, `get_file_history`, `query_store`.

7. **Publish as `agent-state` on PyPI**: Minimal dependency footprint. DuckDB + orjson + mcp SDK.

8. **Write a Claude Code hook configuration that auto-captures**: SessionStart, PostToolUse, Stop, SessionEnd hooks that populate the store without user intervention.

### 10.3 long-term (v2+)

9. **Redundancy detection and context priming**: Use `fact_tool_call` history to generate session primers that reduce redundant file reads.

10. **Quality scoring extension**: Automated evaluation of skill effectiveness using before/after comparisons.

11. **Evidence/Malloy dashboards**: Pre-built analytical dashboards that query the DuckDB file directly.

12. **Cross-session knowledge graph**: Combine relational operational data with lightweight structured memory for cross-session persistence.

## 11. references

### projects and tools

- **Letta (formerly MemGPT)**: https://github.com/letta-ai/letta -- Tiered memory management for LLM agents
- **LangSmith**: https://docs.smith.langchain.com/ -- LLM observability and tracing platform
- **Braintrust**: https://www.braintrust.dev/ -- LLM evaluation and scoring platform
- **OpenTelemetry GenAI SemConv**: https://opentelemetry.io/docs/specs/semconv/gen-ai/ -- Semantic conventions for GenAI observability
- **DuckDB**: https://duckdb.org/ -- In-process analytical database
- **MotherDuck**: https://motherduck.com/ -- Serverless cloud DuckDB
- **Evidence**: https://evidence.dev/ -- BI tool with native DuckDB support
- **Malloy**: https://www.malloydata.dev/ -- Semantic data modeling for analytical queries
- **Mem0**: https://github.com/mem0ai/mem0 -- Memory layer for AI agents
- **Zep**: https://github.com/getzep/zep -- Long-term memory for AI assistants
- **Phoenix (Arize)**: https://github.com/Arize-AI/phoenix -- Open-source LLM observability
- **MCP SDK**: https://github.com/modelcontextprotocol -- Model Context Protocol specification and SDKs

### data modeling references

- Kimball, R. & Ross, M. (2013). *The Data Warehouse Toolkit*, 3rd Edition. The canonical reference for dimensional modeling, star schemas, and slowly changing dimensions.
- Kleppmann, M. (2017). *Designing Data-Intensive Applications*. Chapters on event sourcing, CQRS, and stream processing directly applicable to agent event capture.
- Fowler, M. (2005). "Event Sourcing" -- https://martinfowler.com/eaaDev/EventSourcing.html

### this repo's implementation

- `store.py`: `/Users/fredbliss/claude/fb-claude-skills/skill-maintainer/scripts/store.py` -- Current DuckDB star schema implementation
- `docs_monitor.py`: `/Users/fredbliss/claude/fb-claude-skills/skill-maintainer/scripts/docs_monitor.py` -- CDC pipeline using the store
- `self_updating_system_design.md`: `/Users/fredbliss/claude/fb-claude-skills/docs/analysis/self_updating_system_design.md` -- Architecture decisions document
- `config.yaml`: `/Users/fredbliss/claude/fb-claude-skills/skill-maintainer/config.yaml` -- Source registry and skill tracking
- `state.json`: `/Users/fredbliss/claude/fb-claude-skills/skill-maintainer/state/state.json` -- Backward-compatible state export
