#!/usr/bin/env bash

# Detect env-forge/FastAPI+MCP usage and inject environment design principles.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if markers found, silent exit 0 otherwise.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

HAS_ENVFORGE=false

# Check for env-forge output directory
if [ -d "$CWD/.env-forge" ]; then
  HAS_ENVFORGE=true
fi

# Check for fastapi-mcp usage
if [ "$HAS_ENVFORGE" = false ]; then
  if grep -rqE "from fastapi_mcp|import fastapi_mcp|fastapi-mcp" "$CWD" --include="*.py" --include="pyproject.toml" \
    $(printf " --exclude-dir=%s" node_modules .venv venv .git __pycache__ dist build) 2>/dev/null; then
    HAS_ENVFORGE=true
  fi
fi

if [ "$HAS_ENVFORGE" = false ]; then
  exit 0
fi

# Assemble context from directive files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    envforge) [ "$HAS_ENVFORGE" = true ] || continue ;;
    any)      ;;
    *)        continue ;;
  esac
  [ -n "$CONTEXT" ] && CONTEXT+=$'\n'
  CONTEXT+=$(tail -n +2 "$f")
done

[ -z "$CONTEXT" ] && exit 0

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
