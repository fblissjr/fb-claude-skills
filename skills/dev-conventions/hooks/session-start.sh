#!/usr/bin/env bash

# Detect Python/JS project markers in cwd and inject relevant conventions.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if dev markers found, silent exit 0 otherwise.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

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

# Fallback: check up to 2 levels deep for monorepo layouts
# (e.g., frontend/package.json, web/app/pyproject.toml)
SKIP_DIRS="node_modules|.venv|venv|.git|__pycache__|dist|build|.next|.output"
if [ "$HAS_PYTHON" = false ] || [ "$HAS_JS" = false ]; then
  while IFS= read -r subdir; do
    dirname=$(basename "$subdir")
    echo "$dirname" | grep -qE "^($SKIP_DIRS)$" && continue
    if [ "$HAS_PYTHON" = false ]; then
      for marker in pyproject.toml setup.py setup.cfg Pipfile; do
        if [ -f "$subdir/$marker" ]; then
          HAS_PYTHON=true
          break
        fi
      done
    fi
    if [ "$HAS_JS" = false ]; then
      for marker in package.json tsconfig.json bun.lockb; do
        if [ -f "$subdir/$marker" ]; then
          HAS_JS=true
          break
        fi
      done
    fi
    [ "$HAS_PYTHON" = true ] && [ "$HAS_JS" = true ] && break
  done < <(find "$CWD" -mindepth 1 -maxdepth 2 -type d 2>/dev/null)
fi

HAS_SESSION_LOG=false
if [ -d "$CWD/internal/log" ] || [ -d "$CWD/internal" ]; then
  HAS_SESSION_LOG=true
fi

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
PARTS+=("- TDD: ALWAYS write a failing test first, then implement, then refactor. No exceptions for behavioral changes.")
PARTS+=("- Run tests after every change. Never skip the red step.")
PARTS+=("- For full TDD methodology, invoke /dev-conventions:tdd-workflow.")

if [ "$HAS_SESSION_LOG" = true ]; then
  PARTS+=("")
  PARTS+=("## Session logging (auto-loaded)")
  PARTS+=("- ALWAYS update internal/log/log_YYYY-MM-DD.md before finishing a session or iteration of work.")
  PARTS+=("- Capture: what was done, decisions made, open questions.")
  PARTS+=("- For full doc conventions, invoke /dev-conventions:doc-conventions.")
fi

# Join array with real newlines, then JSON-escape for output
CONTEXT=$(printf '%s\n' "${PARTS[@]}")

JSON_CONTEXT=$(printf '%s' "$CONTEXT" | jq -Rs '.')

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF

exit 0
