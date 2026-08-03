# trigger: python
# ground: \buv\b|\bpip\b|\bpoetry\b|\bpipenv\b|python package manager
## Python conventions (auto-detected)
- Package manager is uv: `uv add`, `uv run <script>`, `uv sync`. Never bare `python`/`pip` — pip and `uv.lock` edits are hook-blocked, but reaching for `uv run` is on you.
- Pin on the way in: apps exact (`uv add httpx==0.27.2`), libraries floors (`uv add 'httpx>=0.27'`). Unsure → exact.
- Do NOT auto-run linters, formatters, or tests after edits unless asked.
- Depth on any of this, plus Pydantic/Pyright gotchas and pip→uv migration: `/dev-conventions:python-tooling`.
