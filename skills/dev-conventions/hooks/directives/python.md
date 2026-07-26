# trigger: python
## Python conventions (auto-detected)
- Package manager is uv: `uv add`, `uv run <script>`, `uv sync`. (pip and hand-edits to `uv.lock` are hook-blocked in uv projects, so this line is only a reminder to reach for `uv run` rather than bare `python`.)
- Pinning: applications pin exact (`uv add httpx==0.27.2`), libraries use floors (`uv add 'httpx>=0.27'`). When unsure, pin exact.
- Do NOT auto-run linters, formatters, or tests after edits unless asked.
- Pydantic `str` enums: use enum members (`SkillStatus.ACTIVE`), never bare strings (`"active"`) — Pyright cannot see Pydantic's runtime coercion, so members catch typos at static-analysis time.
- Full reference: /dev-conventions:python-tooling.
