# Agent SDK Mapping

last updated: 2026-02-17

Rules and patterns for mapping a validated MECE decomposition tree to Claude Agent SDK primitives. The output of this mapping is code-ready -- each pattern includes a template that can be directly adapted.

## Mapping Overview

| Tree Element | SDK Primitive | Notes |
|-------------|---------------|-------|
| Atom (`agent`) | `Agent` class | One agent per atom |
| Atom (`human`) | `AskUserQuestion` tool or webhook | Pauses execution for human input |
| Atom (`tool`) | Direct tool invocation | No agent wrapper needed |
| Atom (`external`) | External API call | Via MCP server or custom tool |
| Branch (`sequential`) | Chained `Runner.run()` | Output of step N feeds step N+1 |
| Branch (`parallel`) | `asyncio.gather()` | Max 7 concurrent branches |
| Branch (`conditional`) | Hook-based routing | `PreToolUse` or custom routing agent |
| Branch (`loop`) | While-loop with termination | Check condition after each iteration |
| Cross-branch dependency (data) | Context/session passing | Output artifact passed as input |
| Cross-branch dependency (sequencing) | Explicit await | `asyncio.Event` or similar |
| Cross-branch dependency (approval) | Human-in-the-loop gate | `AskUserQuestion` between branches |

## Atom Mapping

### execution_type: "agent" -> Agent Class

Each agent atom maps to one `Agent` instance.

```python
from agents import Agent, Runner

# From atom_spec.agent_definition
agent = Agent(
    name="validate_shipping_address",
    model="claude-sonnet-4-6",                    # from model tier
    instructions="""                               # from prompt
    Given a shipping address, verify:
    1. All required fields are present
    2. ZIP code matches city/state
    3. Address is deliverable via USPS API

    Return validation result with any corrections.
    """,
    tools=[usps_validate, geocode_lookup],         # from tools list
)

result = await Runner.run(agent, input=address_data)
```

**Field Mapping:**

| AtomSpec Field | Agent SDK Field | Transform |
|---------------|----------------|-----------|
| `agent_definition.name` | `Agent.name` | Direct (snake_case) |
| `agent_definition.description` | Used in orchestrator context | Not a direct Agent field |
| `agent_definition.prompt` | `Agent.instructions` | Direct |
| `agent_definition.tools` | `Agent.tools` | Resolve tool references to tool objects |
| `agent_definition.model` | `Agent.model` | Map tier to model ID (see Model Tier table) |
| `agent_definition.max_turns` | `Runner.run(max_turns=N)` | Passed at run time |

### execution_type: "human" -> AskUserQuestion

```python
# integration_method: "ask_user_question"
# The orchestrating agent uses AskUserQuestion tool to pause for human input

orchestrator = Agent(
    name="approval_orchestrator",
    instructions="""
    Present the draft document to the user for approval.
    Include the decision criteria: {decision_criteria}
    Wait for their response before proceeding.
    """,
    tools=[AskUserQuestion],
)
```

For `integration_method: "webhook"`, the agent calls an external webhook and polls or waits for callback.

### execution_type: "tool" -> Direct Tool Call

```python
# No agent needed -- call the tool directly in the orchestrator
from agents import function_tool

@function_tool
def read_file(path: str) -> str:
    """Read file contents."""
    with open(path) as f:
        return f.read()

# In the orchestrator's flow:
result = read_file(path=file_path)
```

### execution_type: "external" -> External Integration

```python
# Via MCP server or custom tool
from agents import function_tool
import httpx

@function_tool
async def call_external_api(endpoint: str, payload: dict) -> dict:
    """Call external system API."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
```

## Branch Mapping

### Sequential Orchestration

Children execute in order. Each child's output feeds the next child's input.

```python
from agents import Agent, Runner

# Define child agents
step_1 = Agent(name="extract_data", ...)
step_2 = Agent(name="validate_data", ...)
step_3 = Agent(name="transform_data", ...)

async def run_sequential(initial_input: str) -> str:
    """Sequential branch: children run in order."""
    result_1 = await Runner.run(step_1, input=initial_input)
    result_2 = await Runner.run(step_2, input=result_1.final_output)
    result_3 = await Runner.run(step_3, input=result_2.final_output)
    return result_3.final_output
```

### Parallel Orchestration

Children execute concurrently. All must complete before the branch is done.

```python
import asyncio
from agents import Agent, Runner

# Define child agents
branch_a = Agent(name="check_inventory", ...)
branch_b = Agent(name="validate_payment", ...)
branch_c = Agent(name="verify_address", ...)

async def run_parallel(shared_input: str) -> list:
    """Parallel branch: children run concurrently (max 7)."""
    results = await asyncio.gather(
        Runner.run(branch_a, input=shared_input),
        Runner.run(branch_b, input=shared_input),
        Runner.run(branch_c, input=shared_input),
    )
    return [r.final_output for r in results]
```

**Constraint**: Maximum 7 parallel branches. If the tree has more, group them into sub-branches.

### Conditional Orchestration

One child executes based on a routing condition.

```python
from agents import Agent, Runner

# Routing agent decides which child to invoke
router = Agent(
    name="route_request",
    instructions="""
    Evaluate the input and determine which handler to invoke:
    - If {condition_a}: respond with "ROUTE:handler_a"
    - If {condition_b}: respond with "ROUTE:handler_b"
    - If {condition_c}: respond with "ROUTE:handler_c"
    """,
)

handler_a = Agent(name="handler_a", ...)
handler_b = Agent(name="handler_b", ...)
handler_c = Agent(name="handler_c", ...)

HANDLERS = {
    "handler_a": handler_a,
    "handler_b": handler_b,
    "handler_c": handler_c,
}

async def run_conditional(input_data: str) -> str:
    """Conditional branch: route to one child based on condition."""
    route_result = await Runner.run(router, input=input_data)
    route_key = route_result.final_output.split("ROUTE:")[1].strip()
    handler = HANDLERS[route_key]
    result = await Runner.run(handler, input=input_data)
    return result.final_output
```

Alternative: Use `handoffs` for agent-to-agent routing:

```python
from agents import Agent

handler_a = Agent(name="handler_a", ...)
handler_b = Agent(name="handler_b", ...)

router = Agent(
    name="router",
    instructions="Route to the appropriate handler based on input type.",
    handoffs=[handler_a, handler_b],
)
```

### Loop Orchestration

A child executes repeatedly until a termination condition is met.

```python
from agents import Agent, Runner

processor = Agent(name="process_item", ...)
evaluator = Agent(name="check_termination", ...)

async def run_loop(items: list, max_iterations: int = 100) -> list:
    """Loop branch: repeat until termination condition met."""
    results = []
    for i, item in enumerate(items):
        if i >= max_iterations:
            break
        result = await Runner.run(processor, input=item)
        results.append(result.final_output)

        # Check termination
        eval_result = await Runner.run(
            evaluator,
            input=f"Processed {i+1} items. Latest: {result.final_output}"
        )
        if "TERMINATE" in eval_result.final_output:
            break
    return results
```

## Cross-Branch Dependency Patterns

### Data Dependency

The producing atom's output is passed as input to the consuming atom.

```python
# Producer in Branch A
producer_result = await Runner.run(producer_agent, input=input_data)
artifact = producer_result.final_output

# Consumer in Branch B (may be in a different parallel group)
consumer_result = await Runner.run(consumer_agent, input=artifact)
```

When the producer and consumer are in different parallel branches, the parallel orchestration must be restructured: run the producer first, then run the consumer's branch in parallel with remaining branches.

### Sequencing Dependency

Use `asyncio.Event` to signal completion:

```python
import asyncio

completion_signal = asyncio.Event()

async def branch_a():
    result = await Runner.run(agent_a, input=data)
    completion_signal.set()  # Signal that A is done
    return result

async def branch_b():
    await completion_signal.wait()  # Wait for A to finish
    result = await Runner.run(agent_b, input=data)
    return result

# Both branches start concurrently, but B waits for A's signal
await asyncio.gather(branch_a(), branch_b())
```

### Approval Dependency

Insert a human gate between branches:

```python
# After branch A completes
result_a = await Runner.run(branch_a_agent, input=data)

# Human approval gate
approval_agent = Agent(
    name="approval_gate",
    instructions=f"Present this result to the user for approval: {result_a.final_output}",
    tools=[AskUserQuestion],
)
approval = await Runner.run(approval_agent, input=result_a.final_output)

# Continue to branch B only if approved
if "approved" in approval.final_output.lower():
    result_b = await Runner.run(branch_b_agent, input=result_a.final_output)
```

## Model Tier Heuristics

| Tier | Model ID | When to Use | Cost |
|------|----------|-------------|------|
| `haiku` | `claude-haiku-4-5-20251001` | Simple extraction, formatting, classification, routing | Low |
| `sonnet` | `claude-sonnet-4-6` | Analysis, summarization, multi-step reasoning, most tasks | Medium |
| `opus` | `claude-opus-4-6` | Complex judgment, ambiguous inputs, novel situations, critical decisions | High |

### Selection Rules

1. **Default to sonnet** unless there's a clear reason otherwise
2. **Use haiku when**: the atom does one simple thing (classify, extract, format, route) with clear rules and low ambiguity
3. **Use opus when**: the atom requires judgment under uncertainty, handles novel/ambiguous inputs, or produces outputs that are hard to verify and high-stakes
4. **Never use opus for**: high-volume repetitive tasks, simple lookups, or formatting

### Cost Estimation

For a tree with `h` haiku atoms, `s` sonnet atoms, and `o` opus atoms:
- Relative cost ratio is approximately h:3s:15o per invocation
- Optimize by converting sonnet atoms to haiku where the simplicity criteria are met

## Exception Handling via Hooks

Map error modes from atom specs to SDK hooks:

```python
from agents import Agent, RunHooks, RunContextWrapper, ToolCallEvent

class ErrorHandler(RunHooks):
    async def on_tool_error(
        self, context: RunContextWrapper, error: Exception
    ) -> None:
        # Map to error_modes from atom_spec
        if isinstance(error, TimeoutError):
            # Handle timeout error mode
            pass
        elif isinstance(error, ValidationError):
            # Handle validation error mode
            pass

agent = Agent(name="my_agent", ...)
result = await Runner.run(agent, input=data, hooks=ErrorHandler())
```

## Orchestrator Assembly

The top-level orchestrator composes all patterns:

```python
import asyncio
from agents import Agent, Runner

async def execute_tree(tree: dict, input_data: str) -> str:
    """Execute a MECE decomposition tree."""
    node = tree

    if node["node_type"] == "atom":
        return await execute_atom(node, input_data)

    # Branch node -- orchestrate children
    orchestration = node["orchestration"]
    children = node["children"]

    if orchestration == "sequential":
        result = input_data
        for child in children:
            result = await execute_tree(child, result)
        return result

    elif orchestration == "parallel":
        results = await asyncio.gather(
            *[execute_tree(child, input_data) for child in children]
        )
        return combine_results(results)

    elif orchestration == "conditional":
        selected = await route(node["condition"], children, input_data)
        return await execute_tree(selected, input_data)

    elif orchestration == "loop":
        return await loop_execute(
            children[0], node["loop_spec"], input_data
        )
```

This recursive executor mirrors the tree structure directly. Each branch type maps to one orchestration pattern.
