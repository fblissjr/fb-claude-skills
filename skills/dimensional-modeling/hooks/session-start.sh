#!/usr/bin/env bash

# Detect DuckDB/star schema usage and inject dimensional modeling principles.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if markers found, silent exit 0 otherwise.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

HAS_DUCKDB=false

# Cheap checks first: .duckdb files (bounded find, no grep)
if find "$CWD" -maxdepth 3 -name "*.duckdb" -not -path "*/.git/*" -print -quit 2>/dev/null | grep -q .; then
  HAS_DUCKDB=true
fi

# Check for SQL files with fact_/dim_ table patterns
if [ "$HAS_DUCKDB" = false ]; then
  if grep -rqE "CREATE TABLE.*(fact_|dim_)" "$CWD" --include="*.sql" \
    $(printf " --exclude-dir=%s" node_modules .venv venv .git __pycache__ dist build) 2>/dev/null; then
    HAS_DUCKDB=true
  fi
fi

# Check for duckdb imports in Python files (most expensive -- last)
if [ "$HAS_DUCKDB" = false ]; then
  if grep -rqE "import duckdb|from duckdb" "$CWD" --include="*.py" \
    $(printf " --exclude-dir=%s" node_modules .venv venv .git __pycache__ dist build) 2>/dev/null; then
    HAS_DUCKDB=true
  fi
fi

if [ "$HAS_DUCKDB" = false ]; then
  exit 0
fi

# Assemble context from directive files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    duckdb) [ "$HAS_DUCKDB" = true ] || continue ;;
    any)    ;;
    *)      continue ;;
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
