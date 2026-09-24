---
name: export
description: Generate Claude Agent SDK Python code scaffolding from a validated MECE decomposition. Use when user says "export to Agent SDK", "generate agent code", "create SDK scaffolding", or wants to turn a decomposition tree into runnable Python code.
---

# /export

Generate Claude Agent SDK Python code from a validated MECE decomposition tree.

## Usage

```
/export <decomposition JSON or file path>
```

Examples:
- `/export` after a `/decompose` session (exports the last output)
- `/export output.json`
- `/export` then paste decomposition JSON

## Workflow

### 1. Verify Validation

The decomposition must pass validation first (overall score >= 0.70), because code generated from an overlapping or gapped tree duplicates or drops work. If it has not been validated, run `/validate` first and show its issues.

### 2. Generate Code

Using the mapping rules from `references/agent_sdk_mapping.md`:
- One `ClaudeAgentOptions` per agent atom (model tier, system prompt, tools), run through `query()`
- Orchestration functions per branch type (sequential, parallel, conditional, loop)
- Cross-branch dependency wiring
- Error handling from atom error modes
- Stubs that raise `NotImplementedError` for human, tool and external atoms, routing conditions and loop termination

### 3. Output

```python
# Claude Agent SDK scaffolding for: [Decomposition Scope]
# Dimension: [temporal/functional/etc.]

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query


async def run_agent(prompt: str, options: ClaudeAgentOptions) -> str:
    ...  # runs query() and returns the ResultMessage text


# Node 1.1.1: Step Name (step_name)
n1_1_1_step_name_options = ClaudeAgentOptions(
    model="claude-sonnet-5",
    system_prompt="...",
    tools=["Read", "Write"],
    allowed_tools=["Read", "Write"],
    max_turns=5,
)


async def execute_n1_1_phase_1(input_data: str) -> str:
    "Phase 1 (sequential)"
    result = input_data
    result = await execute_n1_1_1_step_name(result)
    result = await execute_n1_1_2_next_step(result)
    return result


async def main(input_data: str) -> str:
    return await execute_n1_root(input_data)
```

### Export Preview (when MCP server connected)

The `mece-export-sdk` MCP tool renders a preview panel with the generated code and a copy button.

## What You Get

- Options for every agent atom in the tree
- Orchestration functions matching the tree structure
- Comments linking each section to its tree node ID
- A `main()` entry point that executes the full tree
- `NotImplementedError` stubs, named by node ID, for each step left to write, so an unfinished step fails loudly instead of passing its input through

## Next Steps

- "Can we refine the prompts for each agent?" -> edit the generated code
- "I need to adjust the decomposition first" -> `/decompose` or `/interview`
