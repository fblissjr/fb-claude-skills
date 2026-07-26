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
for marker in package.json tsconfig.json bun.lock bun.lockb; do
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
      for marker in package.json tsconfig.json bun.lock bun.lockb; do
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

# A repo with no Python or JS marker still gets its own `rules[]` from
# .dev-conventions.json -- the configure skill documents those as generic house
# rules and promises they load next session, and a Go, Rust, or docs-only repo
# would otherwise never see them because this guard runs first.
if [ "$HAS_PYTHON" = false ] && [ "$HAS_JS" = false ]; then
  if [ ! -f "$CWD/.dev-conventions.json" ]; then
    exit 0
  fi
fi

# Assemble context from directive files
# Each file has "# trigger: <signal>" on line 1. Signals: python, javascript, docs, any
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    python)     [ "$HAS_PYTHON" = true ] || continue ;;
    javascript) [ "$HAS_JS" = true ] || continue ;;
    docs)       [ "$HAS_SESSION_LOG" = true ] || continue ;;
    any)        ;;
    *)          continue ;;
  esac
  [ -n "$CONTEXT" ] && CONTEXT+=$'\n'
  CONTEXT+=$(tail -n +2 "$f")
done

[ -z "$CONTEXT" ] && exit 0

# Attribution marker. hook_additional_context records name only the EVENT,
# so without this an injected block cannot be traced back to its plugin.
# Per-repo house rules, appended to the shipped defaults. Always-loaded text,
# so the configure skill pushes back on anything enforceable or already known.
CFG="$CWD/.dev-conventions.json"
if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
  EXTRA=$(jq -r '.rules[]? | "- " + .' "$CFG" 2>/dev/null)
  if [ -n "$EXTRA" ]; then
    CONTEXT="${CONTEXT}
## This repo's own conventions
${EXTRA}
"
  fi
fi

JSON_CONTEXT=$(printf '[plugin:dev-conventions]\n%s' "$CONTEXT" | jq -Rs '.')

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF

exit 0
