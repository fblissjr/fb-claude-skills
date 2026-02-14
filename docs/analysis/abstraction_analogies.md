last updated: 2026-02-14

# abstraction analogies: selection under constraint

canonical version: `~/workspace/star-schema-llm-context/docs/abstraction_analogies.md`

this file is a summary. the full treatment lives in the star-schema-llm-context repo, which is the shared library that this repo's skill-maintainer consumes.

---

## the unifying insight

three repos converge on one observation: **the same DAG structure -- decompose, route, prune, synthesize, verify -- appears in database query planning, distributed search, sparse MoE transformers, Gemini Deep Think, and agent hierarchies**. the universal primitive is routing: given limited compute, which subset of the search space to activate.

## the corrected mental model

### what breaks: the vertical compilation analogy

the initial analogy mapped tokens to bytecode and skills to Python bindings in a vertical compilation stack. this breaks because:

- **skills are data, not code.** a skill gets loaded into the context window (a mutable data structure). it doesn't get compiled. model weights are the compiled binary -- they don't change per session.
- **the context window is a temporary table**, not a program counter. it has a fixed capacity (`[1, seq_len, hidden_dim]`), and loading a skill is an `INSERT INTO context_buffer`.
- **attention is a query operation**, not instruction execution. QK^T computes similarity scores (join condition), softmax normalizes them (WHERE clause), and multiplication by V aggregates results.

### what works: the database analogy

| LLM/Agent Concept | Database Analog | Why |
|-------------------|----------------|-----|
| Tokens | Rows in a temporary table | Context window = `[1, seq_len, hidden_dim]` table in RAM |
| Model weights | Compiled binary / storage engine | Don't change per session. Define capabilities. |
| Inference + tokenization | Query executor | Scan context, compute attention (fuzzy self-join), produce output |
| Skills | View definitions + stored procedures | Define projections (what to show) and control execution graphs |
| References | Materialized subqueries | Pre-computed knowledge loaded on demand |
| SKILL.md frontmatter | Routing metadata / index entries | Controls WHEN skill loads (not loaded = not scanned) |
| Context window | Working memory / temp table | Fixed capacity, must be managed explicitly |
| Skill loading | INSERT INTO context_buffer | Adds rows to the working set |
| Progressive disclosure | Lazy materialization | Load detail only when needed (layers 0-5) |
| The architecture | External query planner | Optimizes LLM I/O by selecting what context to load |

## the routing spine: five invariant operations

every system that processes more possibilities than it can evaluate implements these five operations:

| Phase | DB Query Planning | Sparse MoE | Agent Hierarchy | CDC Pipeline |
|-------|------------------|------------|----------------|-------------|
| **Decompose** | Parse SQL into logical plan | Tokenize input | Break request into subtasks | Split pages by delimiter |
| **Route** | Optimizer selects indexes | Router picks top-k experts | Spawn subagents per subtask | Hash pages, match to skills |
| **Prune** | Predicate pushdown | Gate zeros non-selected | Kill unproductive agents | Skip unchanged (hash match) |
| **Synthesize** | Join/aggregate results | Weighted sum of outputs | Merge subagent results | Collect into unified report |
| **Verify** | Check constraints, return | Output guardrails | Quality check merged answer | Classify severity, validate |

### concrete examples from this codebase

**CDC pipeline (docs_monitor.py)**:
1. **Decompose**: split `llms-full.txt` into per-page sections by `Source:` delimiter
2. **Route**: hash each page, compare to stored hashes, identify which pages changed
3. **Prune**: skip unchanged pages (hash match = predicate pushdown)
4. **Synthesize**: collect all changes into a classified report
5. **Verify**: run keyword heuristic (BREAKING/ADDITIVE/COSMETIC), validate skill

**Skill loading (progressive disclosure)**:
1. **Decompose**: skill split into layers (frontmatter, body, references, cross-refs, CLAUDE.md, coderef)
2. **Route**: frontmatter description determines whether skill loads at all
3. **Prune**: only load layers needed for current prompt (don't load all references)
4. **Synthesize**: compose skill content + loaded references into working context
5. **Verify**: validation against Agent Skills spec

## three repos as database components

| Role | Repo | Database analog |
|------|------|----------------|
| Storage Engine / Kernel | `star-schema-llm-context/` | Handles I/O, memory management, locking. No business logic. |
| Stored Procedures / System Catalog | `fb-claude-skills/` | Business logic. Loading a skill = `CREATE OR REPLACE PROCEDURE`. |
| Client Application | `ccutils/` and consumers | Orchestration layer that initiates sessions and calls procedures. |

## the DAG hierarchy

```
Goal / Objective     (why -- spans days, sessions)
  Task               (what -- decomposed unit)
    Branch / Attempt (how -- specific approach, may be pruned)
      Session        (where -- execution boundary)
        Agent        (delegation -- routed sub-problem)
          Tool chain (sequence -- ordered operations)
            Tool call(atomic -- read/write/search/execute)
```

`fact_tool_call` is the **EXPLAIN ANALYZE output**: without logging routing decisions, you can't optimize the agent.

## selection under constraint: the unified framework

given more possibilities than you can evaluate, select the subset that matters, process it, combine results.

- **Token level**: attention selects which context tokens influence the output
- **Skill level**: frontmatter routing selects which skills load
- **Reference level**: progressive disclosure selects which references load
- **Agent level**: task decomposition selects which subagents to spawn
- **CDC level**: hash comparison selects which pages to fetch and classify
- **Schema level**: views select which dimension rows are current (`is_current = TRUE`)

the star schema is the persistent record of these selections. fact tables capture what was selected. dimension tables capture the entities being selected from. views compose the two to answer analytical questions.

---

## source attribution

- Claude agent analysis: fb-claude-skills session af5bb1d (2026-02-14)
- Gemini Deep Think analysis: internal/research/20260214-gemini-analysis-analogies.md
- Data-centric agent state research: fb-claude-skills/docs/analysis/data_centric_agent_state_research.md
- Full canonical treatment: ~/workspace/star-schema-llm-context/docs/abstraction_analogies.md
