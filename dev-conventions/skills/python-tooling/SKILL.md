---
name: python-tooling
description: >-
  Enforce Python tooling conventions: uv over pip, orjson over json. Use when working in Python projects,
  when pip install or pip freeze appears, when json.dumps or json.loads is used, when requirements.txt
  is referenced, or when python/python3 is called directly. Triggers on "pip install", "import json",
  "requirements.txt", "python -m", "python3 -m", "pip freeze", "virtualenv".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-03-03
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
