# Model delegation

For data-processing, routine coding, and similar well-specified tasks, use your judgment to pick an appropriate lower-power model and run the work in a subagent. Route to the cheapest model capable of the task.

## Delegate down-tier when a task is all of:

- **Well-specified**: inputs, outputs, and success criteria are clear before starting. No judgment calls expected mid-flight.
- **Mechanical or pattern-bound**: renames, moves, reformatting, applying a known pattern across files, data transformation, boilerplate, well-scoped test writing, straightforward implementation against a spec you provide.
- **Verifiable**: the result can be checked cheaply on return (tests, diff review, schema validation, spot checks).

## Keep in the main loop (strongest model):

- Design decisions and architecture.
- Anything ambiguous enough that the task spec would need revision partway through.
- User interaction and anything that depends on conversation context.
- Verification of delegated results — always check what comes back before building on it.

## How to delegate

- If this project has pre-shaped delegation agents in `.claude/agents/` (`fast-executor` for mechanical work, `task-coder` for standard coding and data tasks), delegate to those. Otherwise spawn a generic subagent with a `model` override. Illustrative tiers as of mid-2026: haiku for mechanical work, sonnet for standard coding and data tasks. Tier names change; the principle is fixed — pick the cheapest model you judge capable of the slice.
- Give the subagent a complete, self-contained task spec: exact files, expected output, constraints, and how the result will be verified. A subagent sees none of the conversation.
- Independent delegable tasks go to parallel subagents.

When unsure whether a task is delegable, keep it in the main loop.
