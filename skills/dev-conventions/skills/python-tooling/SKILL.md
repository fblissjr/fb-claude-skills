---
name: python-tooling
description: >-
  Python type-checking failures that look like unfixable Pydantic/Pyright noise but
  are two mechanical mistakes, plus this repo's dependency-pinning policy. Use when
  pyright reports a wall of "Arguments missing for parameters" or reportCallIssue,
  when a [tool.pyright] block seems to have no effect, when deciding how to pin a
  dependency, or when asked to suppress type errors in a Python project.
metadata:
  last_verified: "2026-07-26"
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

## Adjacent, owned elsewhere

- Lint config and ruff findings — `ruff-diagnostics` plugin.
- Pointing Pyright at the project venv — `pyright-autoconfig` plugin.
- `pip` and `uv.lock` edits are blocked by this plugin's PreToolUse hook, so the
  package-manager preference is enforced rather than explained.
