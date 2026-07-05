# trigger: python
## Python conventions (auto-detected)
- Package manager: ALWAYS use uv, NEVER pip/pip3/`python -m pip`/bare python (`uv add`, `uv run`, `uv sync`).
- Pinning: applications pin exact (`uv add httpx==0.27.2`), libraries use floors (`uv add 'httpx>=0.27'`). When unsure, pin exact.
- Do NOT auto-run linters, formatters, or tests after edits unless asked.
- Lock file: never hand-edit `uv.lock` (machine-generated); update via `uv lock`/`uv sync`, verify with `uv lock --check`.
- Full reference: /dev-conventions:python-tooling.
