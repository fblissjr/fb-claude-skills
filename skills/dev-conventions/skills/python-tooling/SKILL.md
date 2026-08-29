---
name: python-tooling
description: >-
  House Python conventions plus the type-checking failures that get misdiagnosed:
  the dependency pinning policy (applications exact, libraries floors), the rule
  that linters, formatters and tests are never auto-run after an edit unless asked,
  and the two mechanical mistakes behind most Pydantic/Pyright diagnostic walls. Use
  when adding or pinning a dependency with uv add, when about to run ruff, pytest or
  a formatter after editing Python, when pyright reports a wall of "Arguments missing
  for parameters" or reportCallIssue, when a [tool.pyright] block seems to have no
  effect, when type errors appear on BaseModel subclasses whose fields have
  defaults, or when asked to suppress type errors in a Python project.
---

# Python conventions and type-checking traps

Claude already knows uv. This skill carries only what it cannot derive: the
house pinning policy, and the failures that reliably get misdiagnosed.

## Pinning policy

Applications pin exact (`uv add httpx==0.27.2`); libraries and dev dependencies
use floors (`uv add 'httpx>=0.27'`). Unsure → exact. `uv lock --check` after.

## Before suppressing a wall of type errors

Two mechanical mistakes produce hundreds of diagnostics that read as unfixable
Pydantic/Pyright noise. Measured on one real project: 698 errors → 264, from a
keyword argument and a single annotation. Check both before writing a
suppression: `references/type-checking.md`.

The same file covers Pyright config precedence — `pyrightconfig.json` always
outranks `[tool.pyright]`, which is why a config block can appear to do nothing.

## After an edit, stop

Do not auto-run linters, formatters, or tests after an edit unless asked. This
is the one behavioural default worth overriding here: the reflex is strong, the
output is long, and it buries the change the user actually wants to look at.

## Adjacent, owned elsewhere

- Lint config and ruff findings — `ruff-diagnostics` plugin.
- Pointing Pyright at the project venv — `pyright-autoconfig` plugin.
