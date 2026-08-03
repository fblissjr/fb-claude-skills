#!/usr/bin/env bash

# Detect Python/JS project markers in cwd and inject relevant conventions.
# Reads hook input JSON from stdin, extracts cwd.
# Outputs JSON with additionalContext if dev markers found, silent exit 0 otherwise.

# --explain [dir]: diagnostic mode, run by hand. In normal operation three
# causes of silence (trigger never fired, muted, ground covered) emit
# byte-identical output — nothing — and the first consumer field report took
# `bash -x` to tell them apart. Explain prints, per directive, which gate
# stopped it and which line matched. It is also the instrument that makes
# pattern-limit specimens cheap to accumulate: without it every specimen
# costs the same manual dig, so any "tune after N specimens" trigger stays
# out of reach by construction.
EXPLAIN=0
if [ "${1:-}" = "--explain" ]; then
  EXPLAIN=1
  CWD="${2:-$PWD}"
else
  CWD=$(jq -r '.cwd // ""' 2>/dev/null)
fi

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
# would otherwise never see them because this guard runs first. Explain mode
# bypasses the guard: a no-marker repo asked to explain should say so per
# directive, not exit wordlessly.
if [ "$EXPLAIN" = 0 ] && [ "$HAS_PYTHON" = false ] && [ "$HAS_JS" = false ]; then
  if [ ! -f "$CWD/.dev-conventions.json" ]; then
    exit 0
  fi
fi

# Assemble context from directive files
# Each file has "# trigger: <signal>" on line 1. Signals: python, javascript, docs, any
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

# Per-repo directive gating via .dev-conventions.json. Three states per
# directive filename: absent/"" (trigger, then ground coverage decide),
# false (muted, never loads), true (FORCE-load: overrides BOTH the trigger
# match and coverage). Explicit true exists because a block gets wrongly
# silenced two ways — an over-matching ground pattern, or a trigger whose
# markers sit in gitignored fixtures or below the scan depth — and a force
# that only skipped coverage recovered just one of them (consumer-verified,
# 2026-08-03: trigger short-circuited before state was ever read).
#   { "directives": { "tdd": false, "python": true } }
# Same has() guard as the PreToolUse hook's enforced(): jq's `//` treats a
# stored `false` as absent, so the key is tested explicitly.
CFG="$CWD/.dev-conventions.json"
directive_state() {
  [ -f "$CFG" ] || { echo ""; return; }
  command -v jq >/dev/null 2>&1 || { echo ""; return; }
  jq -r --arg k "$1" \
     'if (.directives? | type) == "object" and (.directives | has($k))
      then (.directives[$k] | tostring) else "" end' "$CFG" 2>/dev/null
}

# Ground coverage: a block whose GROUND the repo's own always-loaded files
# already cover stays silent — per block, not per file. A repo whose CLAUDE.md
# only describes its module layout still gets every block; a repo that states
# its own package-manager rule silences exactly that block and no other. Each
# directive declares its ground as an ERE in its leading metadata block
# ("# ground: ...", line 2 by convention); no ground line means the block
# always loads (fail-open to broadcast, so a custom directive without one
# keeps pre-0.15.0 behavior). The patterns demand rule-shaped context, not
# bare token mentions — "never use npm" covers the ground, "distributed via
# npm" does not (reviewed specimens are pinned in the test suite). The
# surfaces checked are the repo's conventions carriers: root CLAUDE.md,
# .claude/rules/*.md, and rules[] in .dev-conventions.json. Silencing gates
# PROSE only — the PreToolUse enforcement hook never consults this.
# Ground is grepped over PROSE only: fenced code blocks are documentation-of-
# a-command, not stated rules, and the rule-vs-command discriminator is
# positional, not lexical — no alternation tuning finds that boundary
# (consumer-measured, 2026-08-03: a fenced `bun run ...` parity command
# silenced the javascript block in a repo with no npm prohibition and no
# pinning policy). Fenced lines are BLANKED, not deleted, so reported line
# numbers stay true. Inline code spans stay: "use `bun add`, never `npm
# install`" is a rule with code in it. Properties that make this safe: the
# strip can only REMOVE coverage, so it errs toward under-silencing — the
# recoverable direction (mute exists); a naive open/close toggle mis-tracking
# an exotic fence also errs the same way. The one regression class — a repo
# stating conventions inside a fenced block — fails toward the block loading.
prose_of() {
  awk '/^[[:space:]]*(```|~~~)/ { f = !f; print ""; next }
       f { print ""; next }
       { print }' "$1"
}

# The single coverage implementation. ground_covered is a quiet wrapper so
# the hook path and --explain cannot drift apart.
ground_match() {  # prints "path:line:text" of the first prose match
  local pat="$1" r m
  [ -n "$pat" ] || return 1
  for r in "$CWD/CLAUDE.md" "$CWD"/.claude/rules/*.md; do
    [ -f "$r" ] || continue
    if m=$(prose_of "$r" | grep -inm1 -E "$pat" 2>/dev/null); then
      printf '%s:%s\n' "$r" "$m"
      return 0
    fi
  done
  if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
    if m=$(jq -r '.rules[]?' "$CFG" 2>/dev/null | grep -im1 -E "$pat"); then
      printf '%s rules[]: %s\n' "$CFG" "$m"
      return 0
    fi
  fi
  return 1
}
ground_covered() { ground_match "$1" >/dev/null; }

# Explain-only: total matching lines across all surfaces. First-match display
# under-represents robustness — the consumer's tdd coverage showed a
# meta-sentence ABOUT coverage as the match while the load-bearing rule sat
# 135 lines down, and only a hand-run counterfactual proved the gate was not
# silencing off its own epitaph. The count makes that legible: "+N more"
# means deleting the shown line does not open the gate.
# WHAT THE COUNT DOES NOT MEASURE (consumer-measured, same day): independence.
# It counts matching lines, and a rule and a sentence about the rule count
# alike — "+1 more" can be two rules or one rule plus its epitaph. No
# positional discriminator separates those the way fences separated commands
# from rules, and chasing it lexically is whack-a-mole; the explain output
# states the limit instead.
ground_match_total() {
  local pat="$1" r c n=0
  [ -n "$pat" ] || { echo 0; return; }
  for r in "$CWD/CLAUDE.md" "$CWD"/.claude/rules/*.md; do
    [ -f "$r" ] || continue
    c=$(prose_of "$r" | grep -icE "$pat" 2>/dev/null) || c=0
    n=$((n + c))
  done
  if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
    c=$(jq -r '.rules[]?' "$CFG" 2>/dev/null | grep -icE "$pat") || c=0
    n=$((n + c))
  fi
  echo "$n"
}

# ground_of / directive_body: the leading run of "# key: value" lines is
# metadata as a CLASS — honored only at the head, stripped only at the head.
# A body line that happens to start with "# ground: " (a directive
# documenting the syntax) survives into the output, and a future metadata
# key neither leaks into sessions nor gets silently eaten from bodies.
ground_of() {
  awk '/^# [a-z-]+: /{ if (sub(/^# ground: /, "")) { print; exit } next } { exit }' "$1"
}
directive_body() {
  awk 'body { print; next } /^# [a-z-]+: /{ next } { body = 1; print }' "$1"
}

# --explain: the same gates, narrated. Byte-identical silence has three
# causes (trigger never fired, muted, ground covered); this prints which
# gate stopped each directive and the exact line that matched. It shares
# directive_state/ground_match with the silent path below, so the
# explanation cannot drift from the behavior.
if [ "$EXPLAIN" = 1 ]; then
  printf 'dev-conventions --explain  cwd=%s\n' "$CWD"
  printf 'markers: python=%s js=%s session-log=%s\n\n' "$HAS_PYTHON" "$HAS_JS" "$HAS_SESSION_LOG"
  for f in "$SCRIPT_DIR"/directives/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .md)
    trigger=$(head -1 "$f" | sed 's/^# trigger: //')
    fired=yes
    case "$trigger" in
      python)     [ "$HAS_PYTHON" = true ] || fired=no ;;
      javascript) [ "$HAS_JS" = true ] || fired=no ;;
      docs)       [ "$HAS_SESSION_LOG" = true ] || fired=no ;;
      any)        ;;
      *)          fired=no ;;
    esac
    state=$(directive_state "$name")
    if [ "$state" = "true" ]; then
      printf '%-16s LOADS   force-loaded (overrides trigger and coverage)\n' "$name"
    elif [ "$state" = "false" ]; then
      printf '%-16s silent  muted in .dev-conventions.json\n' "$name"
    elif [ "$fired" = "no" ]; then
      printf '%-16s silent  trigger "%s" did not fire\n' "$name" "$trigger"
    elif g=$(ground_of "$f") && m=$(ground_match "$g"); then
      extra=""
      n=$(ground_match_total "$g")
      [ "$n" -gt 1 ] && extra=" (+$((n-1)) more matching line(s) — deleting the shown line does not open the gate)"
      printf '%-16s silent  ground covered by %s%s\n' "$name" "$m" "$extra"
    else
      printf '%-16s LOADS   trigger fired, ground not covered\n' "$name"
    fi
  done
  printf '\nnote: coverage counts are matching lines, not independent rules — a rule and a sentence about the rule count alike.\n'
  exit 0
fi

for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  # State first so force can override a trigger miss; directive_state is a
  # pure-bash no-op for the common no-config repo, so the default path still
  # pays nothing before the trigger match.
  state=$(directive_state "$(basename "$f" .md)")
  [ "$state" = "false" ] && continue
  if [ "$state" != "true" ]; then
    trigger=$(head -1 "$f" | sed 's/^# trigger: //')
    case "$trigger" in
      python)     [ "$HAS_PYTHON" = true ] || continue ;;
      javascript) [ "$HAS_JS" = true ] || continue ;;
      docs)       [ "$HAS_SESSION_LOG" = true ] || continue ;;
      any)        ;;
      *)          continue ;;
    esac
    ground_covered "$(ground_of "$f")" && continue
  fi
  [ -n "$CONTEXT" ] && CONTEXT+=$'\n'
  CONTEXT+=$(directive_body "$f")
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
