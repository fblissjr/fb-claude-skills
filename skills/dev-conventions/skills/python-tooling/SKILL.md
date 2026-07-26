---
name: python-tooling
description: >-
  Detailed Python/uv conversion reference. Core conventions auto-loaded via SessionStart hook;
  invoke /dev-conventions:python-tooling for full conversion tables.
  Use when you need the complete uv command mapping, version pinning strategy, or lock file workflow.
metadata:
  last_verified: "2026-07-05"
---

# Python Tooling Conventions

## Package management: uv

Always use `uv` for Python package and environment management. Never use `pip`, `pip3`, `python -m pip`, or bare `python`/`python3`.

| Instead of | Use |
|------------|-----|
| `pip install X` | `uv add X` |
| `pip install -r requirements.txt` | `uv sync` (with pyproject.toml) |
| `python script.py` | `uv run script.py` |
| `python -m pytest` | `uv run pytest` |
| `python -m venv .venv` | `uv venv` |
| `pip freeze > requirements.txt` | `uv lock` (use pyproject.toml + uv.lock) |

## Version pinning

| Project type | Strategy | Example |
|-------------|----------|---------|
| Application (deployed service, CLI, script) | Exact pin | `uv add httpx==0.27.2` |
| Library (published package, workspace member) | Floor pin | `uv add 'httpx>=0.27'` |
| Dev/test dependency | Floor pin | `uv add --group dev 'pytest>=7.0'` |

When in doubt, pin exact. After adding any dependency, run `uv lock --check` to verify the lock file is consistent.

## Lock file

`uv.lock` is machine-generated. Never hand-edit it. Update it only through `uv lock` or `uv sync`, and commit it alongside `pyproject.toml`. Use `pyproject.toml` + `uv.lock`, not `requirements.txt`.

## Pydantic `str` enums

Assign enum members, never the bare string they coerce from:

```python
status = SkillStatus.ACTIVE   # not status = "active"
```

Pydantic accepts `"active"` at runtime and coerces it, so both spellings work and the difference never shows up in tests. But the coercion is invisible to Pyright, which sees `str` where the field is typed `SkillStatus`. Using the member is what puts the value under static analysis, so a typo like `"actve"` fails at check time instead of becoming a validation error in whatever code path happens to run first.

## Linting: ruff

Use `extend-select`, not `select`.

```toml
[tool.ruff.lint]
extend-select = ["SIM", "PTH"]   # keeps ruff's defaults, adds to them
# select     = ["E", "F", "I"]   # REPLACES the defaults with just these
```

Ruff 0.16 (2026-07-23) raised the default rule set from 59 rules to 413, on the grounds that many rules catching syntax errors and immediate runtime errors were not previously on by default. Because `select` replaces that set rather than extending it, a curated `select` list written before 0.16 now enables *fewer* checks than having no ruff config at all — and nothing warns you. A project can report `All checks passed!` while the defaults find real bugs in the same tree.

If a project already has a `select` list, converting it to `extend-select` is usually the right move, but it is the owner's call. Raise it; don't rewrite their lint config unprompted.

Invoke ruff in this order, preferring the project's pinned version:

| Order | Form | When |
|---|---|---|
| 1 | `uv run ruff ...` | ruff is a project dependency. Matches CI. |
| 2 | `uvx ruff ...` | ruff is not a project dependency. |
| 3 | `ruff ...` | only if installed globally. |

Two restraints, both from Astral's own guidance:

- **Don't format a project that isn't ruff-formatted.** If `ruff format --diff` shows changes throughout a file, the project doesn't use ruff for formatting; reformatting buries the actual change in noise.
- **Scope fixes to the code being edited.** Use `ruff check --diff` to see what applies to your change. Fixing the whole tree is a separate task, and needs asking first.

Ruff is a linter, not a type checker — it pairs with Pyright rather than replacing it, and the two barely overlap in practice. The `ruff-diagnostics` plugin wires ruff findings into Claude's context after each Python edit; where it is installed, there is no need to shell out to `ruff check` after every edit.

> JSON library choice (stdlib `json` vs `orjson`, etc.) is a per-project preference, not a universal convention — set it in the project's own `CLAUDE.md` or `.claude/rules/` rather than assuming it here.
