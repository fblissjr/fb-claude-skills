#!/usr/bin/env bash

# Detect Python/JS project markers in cwd and inject relevant conventions.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if dev markers found, silent exit 0 otherwise.

CWD=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

HAS_PYTHON=false
HAS_JS=false

# Python markers
for marker in pyproject.toml setup.py setup.cfg Pipfile; do
  if [ -f "$CWD/$marker" ]; then
    HAS_PYTHON=true
    break
  fi
done
if [ "$HAS_PYTHON" = false ]; then
  # Check for top-level .py files
  for f in "$CWD"/*.py; do
    if [ -f "$f" ]; then
      HAS_PYTHON=true
      break
    fi
  done
fi

# JS/TS markers
for marker in package.json tsconfig.json bun.lockb; do
  if [ -f "$CWD/$marker" ]; then
    HAS_JS=true
    break
  fi
done

if [ "$HAS_PYTHON" = false ] && [ "$HAS_JS" = false ]; then
  exit 0
fi

# Build context parts in an array, then join with real newlines for proper JSON escaping
PARTS=()

if [ "$HAS_PYTHON" = true ]; then
  PARTS+=("## Python conventions (auto-detected)")
  PARTS+=("- Package manager: ALWAYS use uv. NEVER use pip, pip3, python -m pip, or bare python/python3.")
  PARTS+=("  - Install packages: uv add <pkg>")
  PARTS+=("  - Run scripts: uv run <script.py>")
  PARTS+=("  - Run tools: uv run pytest, uv run ruff, etc.")
  PARTS+=("  - Sync deps: uv sync")
  PARTS+=("  - Create venv: uv venv")
  PARTS+=("  - Lock: uv lock (use pyproject.toml + uv.lock, not requirements.txt)")
  PARTS+=("- JSON: ALWAYS use orjson, NEVER stdlib json.")
  PARTS+=("  - import orjson (not import json)")
  PARTS+=("  - orjson.dumps(data).decode() / orjson.loads(text)")
  PARTS+=("")
fi

if [ "$HAS_JS" = true ]; then
  PARTS+=("## JavaScript/TypeScript conventions (auto-detected)")
  PARTS+=("- Package manager: ALWAYS use bun. NEVER use npm, yarn, pnpm, or npx.")
  PARTS+=("  - Install: bun install / bun add <pkg>")
  PARTS+=("  - Dev deps: bun add -d <pkg>")
  PARTS+=("  - Run scripts: bun run <script>")
  PARTS+=("  - Execute: bunx <tool> (not npx)")
  PARTS+=("  - Init: bun init")
  PARTS+=("  - Lock file: bun.lockb (not package-lock.json or yarn.lock)")
  PARTS+=("")
fi

PARTS+=("## TDD workflow (auto-loaded)")
PARTS+=("- Red/green cycle: write a failing test first, then implement until it passes, then refactor.")
PARTS+=("- Run tests after every change. Keep tests focused and fast.")
PARTS+=("- For full TDD methodology, invoke /dev-conventions:tdd-workflow.")

# Join array with real newlines, then let python json.dumps produce proper \n escapes
CONTEXT=$(printf '%s\n' "${PARTS[@]}")

JSON_CONTEXT=$(python3 -c "
import json, sys
print(json.dumps(sys.stdin.read().rstrip('\n')))
" <<< "$CONTEXT")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF

exit 0
