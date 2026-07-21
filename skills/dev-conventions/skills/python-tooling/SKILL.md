---
name: python-tooling
description: >-
  Detailed Python/uv conversion reference. Core conventions auto-loaded via SessionStart hook;
  invoke /dev-conventions:python-tooling for full conversion tables.
  Use when you need the complete uv command mapping, version pinning strategy, or lock file workflow.
metadata:
  author: Fred Bliss
  version: 0.7.0
  last_verified: 2026-07-05
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

> JSON library choice (stdlib `json` vs `orjson`, etc.) is a per-project preference, not a universal convention — set it in the project's own `CLAUDE.md` or `.claude/rules/` rather than assuming it here.
