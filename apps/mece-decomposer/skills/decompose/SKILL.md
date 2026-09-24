---
name: decompose
description: Break down a goal, process, or workflow into MECE components with Agent SDK mapping. Use when user says "decompose", "break down this process", "MECE analysis", "create a decomposition tree", or pastes a JSON/YAML/CSV workflow export to analyze.
---

# /decompose

Decompose a process, goal or workflow into MECE components, producing a human-readable tree and JSON that maps to agent primitives. The method, limits and scoring are in the **mece-decomposer** skill and its references; this skill adds the input rules and the output shape.

Usage: `/decompose <what to decompose>`, or `/decompose` followed by a pasted JSON, YAML or CSV export from a workflow tool.

<input_rules>
- **Structured input gets its schema confirmed before any cut.** For JSON, XML, YAML, CSV or any tool export, ask what the data represents, what the key fields mean and how the entities relate; state your interpretation and let the user correct it until they agree. Field names in exports are routinely misleading, and a tree built on a misread schema is wrong at every level. Free text skips this.
- **Scope is asked, not guessed.** When the trigger, completion criteria or exclusions are ambiguous, ask; an assumed boundary makes the exhaustiveness score meaningless. If scope cannot be established from the conversation, switch to `/interview`.
</input_rules>

<done>
Done is a tree that passes the structural validator and carries ME/CE scores for every level the depth-adaptive schedule tests, with dimension rationale, atom classifications, model tiers and cross-branch dependencies filled in.
</done>

<output>
1. The human-readable tree. One line per node: label, execution type in brackets, estimated duration, and model tier or integration method:

   ```
   Process Name (orchestration type)
   +-- Phase 1 (parallel)
   |   +-- [agent] Step A (~5m, sonnet)
   |   +-- [human] Step B (~2h, webhook)
   +-- Phase 2 (sequential)
       +-- [tool] Step C (~10s, tool_name)
       +-- [agent] Step D (~1m, haiku)
   ```

2. The JSON, conforming to `references/output_schema.md` in the mece-decomposer skill, checked with:

   ```bash
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/mece-decomposer/scripts/validate_mece.py <output.json>
   ```

3. When the `mece-decompose` MCP tool is available, call it with the full JSON string to render the interactive tree.
</output>

Adjacent skills: `/validate` scores an existing decomposition, `/interview` extracts one from an SME, `/export` turns a validated one into code.
