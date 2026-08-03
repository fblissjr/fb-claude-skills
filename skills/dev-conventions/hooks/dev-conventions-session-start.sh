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

# Per-repo directive gating. A repo whose own rules supersede a shipped block
# turns it off by filename in .dev-conventions.json:
#   { "directives": { "tdd": false, "doc-conventions": false } }
# Same has() guard as the PreToolUse hook's enforced(): jq's `//` treats a
# stored `false` as absent, so the key is tested explicitly.
CFG="$CWD/.dev-conventions.json"
directive_enabled() {
  [ -f "$CFG" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  local v
  v=$(jq -r --arg k "$1" \
      'if (.directives? | type) == "object" and (.directives | has($k))
       then (.directives[$k] | tostring) else "" end' "$CFG" 2>/dev/null)
  [ "$v" != "false" ]
}

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  directive_enabled "$(basename "$f" .md)" || continue
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

# Per-repo house rules, appended to the shipped defaults. Always-loaded text,
# so the configure skill pushes back on anything enforceable or already known.
# Appended BEFORE the empty-context exit: a repo that mutes every shipped
# directive still gets its own rules[] — muting trims the defaults, never the
# repo's own conventions.
if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
  EXTRA=$(jq -r '.rules[]? | "- " + .' "$CFG" 2>/dev/null)
  if [ -n "$EXTRA" ]; then
    [ -n "$CONTEXT" ] && CONTEXT+=$'\n'
    CONTEXT+="## This repo's own conventions
${EXTRA}
"
  fi
fi

[ -z "$CONTEXT" ] && exit 0

# Attribution marker. hook_additional_context records only the EVENT name,
# so without this an injected block cannot be traced back to its plugin.

# The supersession line exists because generic defaults shadowing a sharper
# repo-local rule cost reconciliation on every use — the friction is recorded,
# so the escape is stated once here instead of argued per block.
JSON_CONTEXT=$(printf '[plugin:dev-conventions]\nA repo-local rule (CLAUDE.md, .claude/rules/) covering the same ground supersedes any block below; repos can also mute blocks via .dev-conventions.json.\n%s' "$CONTEXT" | jq -Rs '.')

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF

exit 0
