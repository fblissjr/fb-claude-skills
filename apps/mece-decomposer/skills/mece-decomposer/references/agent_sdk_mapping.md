# Agent SDK mapping

last updated: 2026-09-24

How a validated MECE tree maps onto the Claude Agent SDK (`claude-agent-sdk`, imported as `claude_agent_sdk`). The SDK packages the Claude Code harness: each `query()` call runs one agent loop with Claude Code's built-in tools, and returns a stream of messages that ends in a `ResultMessage`. The MCP app's `mece-export-sdk` tool generates this mapping (`mcp-app/sdk-codegen.ts`); keep the two in step.

The tree's shape is known in advance, so the default is code-driven orchestration: plain `asyncio` walks the tree, and each agent atom is one `query()` call. Use model-driven orchestration (subagents, below) only for a branch whose order is itself a judgment call.

## Overview

| Tree element | SDK mapping |
|---|---|
| Atom `agent` | One `ClaudeAgentOptions` plus one `query()` call |
| Atom `human` | A gate in the orchestrator's own code |
| Atom `tool` | A direct call in the orchestrator, or an SDK MCP tool if an agent must call it |
| Atom `external` | Orchestrator code, or an MCP server in `mcp_servers` |
| Branch `sequential` | `await` each child in order, output feeding the next |
| Branch `parallel` | `asyncio.gather()`, at most 7 children |
| Branch `conditional` | A route function: code, or a routing agent with `output_format` |
| Branch `loop` | A bounded `for` loop with a termination check |
| Dependency `data` / `sequencing` / `approval` | Pass the artifact / `asyncio.Event` / a human gate |

## Agent atoms

```python
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

async def run_agent(prompt: str, options: ClaudeAgentOptions) -> str:
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"agent run failed: {message.subtype}")
            return message.result or ""
    raise RuntimeError("query() ended without a ResultMessage")

validate_address_options = ClaudeAgentOptions(
    model="claude-sonnet-5",
    system_prompt="Given a shipping address, verify required fields and ZIP/city agreement. Return corrections.",
    tools=["WebFetch"],
    allowed_tools=["WebFetch"],
    max_turns=5,
)

result = await run_agent(address_text, validate_address_options)
```

| `agent_definition` field | `ClaudeAgentOptions` | Notes |
|---|---|---|
| `name`, `description` | none | Kept as the variable name and a comment |
| `prompt` | `system_prompt` | The atom's input is the `query()` prompt |
| `tools` | `tools` and `allowed_tools` | `tools` limits which built-ins exist (`[]` means none); `allowed_tools` pre-approves them so a headless run does not stop at a permission prompt |
| `model` | `model` | Tier to ID, below |
| `max_turns` | `max_turns` | Omit when unset |

Tool names are Claude Code tool names (`Read`, `Write`, `Bash`, `WebFetch`) or MCP tools as `mcp__<server>__<tool>`. `max_budget_usd` caps spend per atom when the error modes include runaway cost.

## Other atoms

**`human`**: a step the process defines, such as an approval or a physical action, so it lives in the orchestrator: prompt at the terminal, post to a webhook and wait, or read a queue. Do not map it to `AskUserQuestion`. That tool carries questions Claude writes during an agent run; they reach the `can_use_tool` callback, and the SDK gives no way to inject your own. `integration_method: "ask_user_question"` fits only when the adjacent agent atom should be free to ask for clarification: add `AskUserQuestion` to its `tools`, pass a `can_use_tool` callback, and answer with `PermissionResultAllow(updated_input={"questions": ..., "answers": {...}})`.

**`tool`**: a deterministic operation, so call it directly in the orchestrator with no agent. If an agent atom must call it mid-run, expose it in-process:

```python
from claude_agent_sdk import create_sdk_mcp_server, tool

@tool("write_row", "Append one row to the ledger", {"row": dict})
async def write_row(args):
    ledger.append(args["row"])
    return {"content": [{"type": "text", "text": "ok"}]}

ledger_server = create_sdk_mcp_server("ledger", tools=[write_row])
# ClaudeAgentOptions(mcp_servers={"ledger": ledger_server}, allowed_tools=["mcp__ledger__write_row"])
```

**`external`**: a system outside the runtime. Call it from the orchestrator, applying `timeout` and `fallback` from the spec, or give the agent an existing MCP server for it in `mcp_servers`.

## Branches

**Sequential**: `result = await child(result)` for each child in order.

**Parallel**: `await asyncio.gather(*(child(input) for child in children))`. There is a maximum of 7 children, so group extras into sub-branches. Each `query()` starts its own Claude Code process, so wide fan-out costs processes as well as tokens.

**Conditional**: a route function returns the child to run. Make it code when the condition is mechanical. When it needs judgment, use a cheap routing agent with structured output:

```python
router_options = ClaudeAgentOptions(
    model="claude-haiku-4-5",
    system_prompt="Pick the handler for this request.",
    tools=[],
    output_format={"type": "json_schema", "schema": {
        "type": "object",
        "properties": {"child": {"enum": ["1.3.1", "1.3.2"]}},
        "required": ["child"],
    }},
)
# The ResultMessage from query() carries .structured_output == {"child": "1.3.1"}
```

**Loop**: `for _ in range(loop_spec.max_iterations)`, with the children run in order each iteration, then a termination check from `loop_spec.termination`. Never leave a loop unbounded; the generator defaults `max_iterations` to 100.

**Model-driven alternative**: for a branch whose children are specialists that the model should sequence, give one orchestrating `query()` the children as subagents: `agents={"lint": AgentDefinition(description=..., prompt=..., tools=[...], model="haiku")}`. This trades the tree's deterministic order for flexibility. Use it only when the SME said the order depends on the case.

## Cross-branch dependencies

- **Data**: pass the producer's result as the consumer's input. If they sit in different parallel branches, run the producer first, then the rest of the parallel group.
- **Sequencing**: the producer sets an `asyncio.Event` and the consumer awaits it, both inside one `gather`.
- **Approval**: a human gate between the branches; continue only on approval.

## Model tiers

The model ID column must match `MODEL_MAP` in `mcp-app/sdk-codegen.ts`; update both together when a tier moves to a new model.

| Tier | Model ID | Use for |
|---|---|---|
| `haiku` | `claude-haiku-4-5` | Extraction, formatting, classification, routing |
| `sonnet` | `claude-sonnet-5` | Analysis, summarisation, multi-step work: the default |
| `opus` | `claude-opus-5-5` | Judgment under ambiguity, high-stakes outputs that are hard to verify |

Never use `opus` for high-volume repetitive atoms, lookups or formatting.

## Error modes

Map each `error_modes` entry to where it surfaces:

- **Tool failures inside an agent run**: a `PostToolUseFailure` hook sees `tool_name` and `error`.

  ```python
  from claude_agent_sdk import HookMatcher

  async def on_tool_failure(input_data, tool_use_id, context):
      log_failure(input_data["tool_name"], input_data["error"])
      return {}

  ClaudeAgentOptions(hooks={"PostToolUseFailure": [HookMatcher(matcher=None, hooks=[on_tool_failure])]})
  ```

- **The run itself failing** (turn limit, budget, API error): `ResultMessage.is_error` and `subtype`, which `run_agent` raises on. Retry or fall back in the orchestrator.
- **Bad output**: validate the returned text, or use `output_format` so the result arrives as `structured_output` that matches a schema.
