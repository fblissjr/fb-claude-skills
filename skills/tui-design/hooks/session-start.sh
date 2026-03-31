#!/usr/bin/env bash

# Detect TUI library usage and inject design principles.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if TUI markers found, silent exit 0 otherwise.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

HAS_TUI=false

# Check for Rich/Textual/Questionary/Click imports in Python files
SKIP_DIRS="node_modules|.venv|venv|.git|__pycache__|dist|build"
TUI_PATTERN="from (rich|textual|questionary|click)|import (rich|textual|questionary|click)"

if grep -rqE "$TUI_PATTERN" "$CWD" --include="*.py" \
  $(printf " --exclude-dir=%s" node_modules .venv venv .git __pycache__ dist build) 2>/dev/null; then
  HAS_TUI=true
fi

if [ "$HAS_TUI" = false ]; then
  exit 0
fi

# Assemble context from directive files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    tui) [ "$HAS_TUI" = true ] || continue ;;
    any) ;;
    *)   continue ;;
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
