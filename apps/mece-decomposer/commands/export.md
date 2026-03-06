---
description: Generate Claude Agent SDK Python code scaffolding from a validated MECE decomposition
argument-hint: "<decomposition JSON or file path>"
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

The decomposition must pass validation first (overall score >= 0.70). If not validated, I'll run `/validate` first and show any issues.

### 2. Generate Code

Using the mapping rules from `references/agent_sdk_mapping.md`:
- One `Agent` definition per agent atom
- Orchestration functions per branch type (sequential, parallel, conditional, loop)
- Cross-branch dependency wiring
- Hook-based error handling from atom error modes
- Model tier assignments

### 3. Output

```python
"""
Agent SDK scaffolding for: [Decomposition Scope]
Dimension: [temporal/functional/etc.]
"""

import asyncio
from agents import Agent, Runner, function_tool

# Node 1.1.1: Step Name
step_name_agent = Agent(
    name="step-name",
    model="claude-sonnet-4-6",
    instructions="""...""",
    tools=[...],
)

# Orchestration
async def execute_phase_1(input_data: str) -> str:
    """Phase 1 (sequential orchestration)"""
    result = input_data
    result = await execute_step_1(result)
    result = await execute_step_2(result)
    return result

async def main(input_data: str) -> str:
    return await execute_root(input_data)

if __name__ == "__main__":
    result = asyncio.run(main("initial input"))
    print(result)
```

### Export Preview (when MCP server connected)

The `mece-export-sdk` MCP tool renders a preview panel with the generated code and a copy button.

## What You Get

- Agent definitions for every agent atom in the tree
- Orchestration functions matching the tree structure
- Comments linking each section to its tree node ID
- A `main()` entry point that executes the full tree
- TODO markers for human, tool, and external atoms that need implementation

## Next Steps

- "Can we refine the prompts for each agent?" -> edit the generated code
- "I need to adjust the decomposition first" -> `/decompose` or `/interview`
