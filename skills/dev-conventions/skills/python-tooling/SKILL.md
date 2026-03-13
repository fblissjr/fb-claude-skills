---
name: python-tooling
description: >-
  Detailed Python/uv/orjson conversion reference. Core conventions auto-loaded via SessionStart hook;
  invoke /dev-conventions:python-tooling for full conversion tables.
  Use when you need the complete uv command mapping or orjson migration patterns.
metadata:
  author: Fred Bliss
  version: 0.2.0
  last_verified: 2026-03-13
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

## JSON: orjson

Always use `orjson` instead of the stdlib `json` module.

| Instead of | Use |
|------------|-----|
| `import json` | `import orjson` |
| `json.dumps(data)` | `orjson.dumps(data).decode()` |
| `json.loads(text)` | `orjson.loads(text)` |
| `json.dump(data, f)` | `f.write(orjson.dumps(data))` |
