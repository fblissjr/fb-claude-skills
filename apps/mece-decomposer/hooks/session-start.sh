#!/usr/bin/env bash

# Detect MECE/Agent SDK usage and inject decomposition principles.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if markers found, silent exit 0 otherwise.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

HAS_MECE=false

# Cheap checks first: known files/directories
if [ -f "$CWD/decomposition.json" ] || [ -d "$CWD/.mece" ]; then
  HAS_MECE=true
fi

# Check for Agent SDK imports (expensive -- last)
if [ "$HAS_MECE" = false ]; then
  if grep -rqE "from claude_agent_sdk|import claude_agent_sdk|from agents import|from agents\." "$CWD" --include="*.py" \
    $(printf " --exclude-dir=%s" node_modules .venv venv .git __pycache__ dist build) 2>/dev/null; then
    HAS_MECE=true
  fi
fi

if [ "$HAS_MECE" = false ]; then
  exit 0
fi

# Assemble context from directive files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    mece) [ "$HAS_MECE" = true ] || continue ;;
    any)  ;;
    *)    continue ;;
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
