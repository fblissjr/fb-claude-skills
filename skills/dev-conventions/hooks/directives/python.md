# trigger: python
## Python conventions (auto-detected)
- Package manager: ALWAYS use uv. NEVER use pip, pip3, python -m pip, or bare python/python3.
  - Install packages: uv add <pkg>
  - Run scripts: uv run <script.py>
  - Run tools: uv run pytest, uv run ruff, etc. (on-demand only -- do NOT auto-run linters or formatters after edits unless explicitly asked)
  - Sync deps: uv sync
  - Create venv: uv venv
  - Lock: uv lock (use pyproject.toml + uv.lock, not requirements.txt)
- JSON: ALWAYS use orjson, NEVER stdlib json.
  - import orjson (not import json)
  - orjson.dumps(data).decode() / orjson.loads(text)
