#!/usr/bin/env bash
# path-privacy: skip-file
# scrub-paths.sh - apply suggested replacements from .path-privacy.local.json
# to files in the working tree. Read-only by default; prints a unified diff
# of proposed changes. Pass --apply to write.
#
# Companion to find-external-paths.sh: the scanner reports leaks with
# "→ use: <substituted form>" hints (when a config is present); this script
# applies those same substitutions.
#
# Usage:
#   scrub-paths.sh [-d <dir>]... [-f <file>]... [--staged]
#                  [--against-root <path>] [--config <path>]
#                  [--apply] [--quiet]
#
# Modes:
#   -f / --file       process a single file (repeatable)
#   -d / --directory  walk a directory; only files containing a configured
#                     `match` substring are touched (repeatable)
#   --staged          process the set returned by `git diff --cached --name-only`
#
# Behavior:
#   Default = dry-run: print `diff -u <orig> <proposed>` per file with
#   changes; exit 0.
#   --apply = write changes in place.
#
# Skipped contexts:
#   - files containing the literal `path-privacy: skip-file` marker in the
#     first 30 lines (same convention as find-external-paths.sh)
#   - files with no match against any configured suggestion
#   - missing config (or jq absent): exit 0 with a notice on stderr
#
# Exit codes:
#   0 = success (no changes proposed, or proposals printed, or --apply
#       wrote successfully)
#   1 = bad usage
#   2 = config / scanner not found
#
# `set -u` only: a per-file error should not abort the rest of the run.

set -u

if ! command -v jq >/dev/null 2>&1; then
  echo "scrub-paths: jq not found. Install via 'brew install jq' or equivalent." >&2
  exit 2
fi

DIRS=()
FILES=()
STAGED=0
ROOT=""
CONFIG_PATH=""
APPLY=0
QUIET=0

usage() { sed -n '2,33p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--directory)    DIRS+=("$2"); shift 2 ;;
    -f|--file)         FILES+=("$2"); shift 2 ;;
    --staged)          STAGED=1; shift ;;
    --against-root)    ROOT="$2"; shift 2 ;;
    --config)          CONFIG_PATH="$2"; shift 2 ;;
    --apply)           APPLY=1; shift ;;
    --quiet)           QUIET=1; shift ;;
    -h|--help)         usage; exit 0 ;;
    *) echo "scrub-paths: unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [ -z "$ROOT" ]; then
  ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
fi
if [ -z "$ROOT" ]; then
  echo "scrub-paths: not inside a git repo and --against-root not given" >&2
  exit 1
fi
ROOT=$(cd "$ROOT" 2>/dev/null && pwd -P)

if [ $STAGED -eq 1 ]; then
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && FILES+=("$f")
  done < <(git -C "$ROOT" diff --cached --name-only --diff-filter=ACM 2>/dev/null)
fi

if [ ${#DIRS[@]} -eq 0 ] && [ ${#FILES[@]} -eq 0 ]; then
  DIRS=("$ROOT")
fi

# --- Load suggestions: parallel arrays of (match-substring, replacement).
# Sorted longest-match-first so specific entries win over more general ones.
SUGGEST_MATCH=()
SUGGEST_TO=()

CFG="${CONFIG_PATH:-$ROOT/.path-privacy.local.json}"
if [ ! -f "$CFG" ]; then
  echo "scrub-paths: no config at $CFG (default: <repo-root>/.path-privacy.local.json). Nothing to do." >&2
  exit 0
fi

while IFS=$'\t' read -r m s; do
  [ -z "$m" ] && continue
  SUGGEST_MATCH+=("$m")
  SUGGEST_TO+=("$s")
done < <(jq -r '
  .suggestions // []
  | sort_by(.match | length) | reverse
  | .[]
  | "\(.match)\t\(.suggest // "")"
' "$CFG" 2>/dev/null || true)

if [ ${#SUGGEST_MATCH[@]} -eq 0 ]; then
  echo "scrub-paths: config $CFG has no usable 'suggestions' entries. Nothing to do." >&2
  exit 0
fi

FILE_SKIP_MARKER='path-privacy: skip-file'

# Pick a sed delimiter that appears in none of the match/replacement strings.
# `|` is unlikely to appear in path patterns; fall back to `~` then `#`.
pick_delim() {
  local cand
  for cand in '|' '~' '#' '%' '@'; do
    local i hit=0
    for (( i=0; i<${#SUGGEST_MATCH[@]}; i++ )); do
      case "${SUGGEST_MATCH[$i]}${SUGGEST_TO[$i]}" in
        *"$cand"*) hit=1; break ;;
      esac
    done
    if [ $hit -eq 0 ]; then echo "$cand"; return 0; fi
  done
  return 1
}

DELIM=$(pick_delim) || {
  echo "scrub-paths: every candidate sed delimiter (| ~ # % @) appears in suggestions. Refusing to scrub." >&2
  exit 2
}

# Escape a literal string for use inside a sed s-command: backslash, the
# chosen delimiter, and ampersand all need a leading backslash. Done in bash
# parameter expansion (not via a nested sed pipeline) so the delimiter
# character does not collide with itself.
escape_for_sed() {
  local s="$1" d="$2"
  s="${s//\\/\\\\}"
  s="${s//&/\\&}"
  s="${s//$d/\\$d}"
  printf '%s' "$s"
}

# Build the sed command once (longest-first order is preserved from the
# array, so specific replacements run before more general ones).
SED_ARGS=()
for (( i=0; i<${#SUGGEST_MATCH[@]}; i++ )); do
  m_esc=$(escape_for_sed "${SUGGEST_MATCH[$i]}" "$DELIM")
  s_esc=$(escape_for_sed "${SUGGEST_TO[$i]}"   "$DELIM")
  SED_ARGS+=( -e "s${DELIM}${m_esc}${DELIM}${s_esc}${DELIM}g" )
done

CHANGED=0
PROCESSED=0

# Should this file be considered? Skip-file marker honored, plus a quick
# substring pre-filter to avoid forking sed on files that obviously won't
# match any suggestion.
file_has_match() {
  local f="$1" m
  for m in "${SUGGEST_MATCH[@]}"; do
    if grep -qF -- "$m" "$f" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

scrub_one() {
  local f="$1"
  [ -f "$f" ] || return 0
  if head -30 "$f" 2>/dev/null | grep -qF "$FILE_SKIP_MARKER"; then
    return 0
  fi
  file_has_match "$f" || return 0

  PROCESSED=$((PROCESSED + 1))

  local tmp
  tmp=$(mktemp) || return 0
  if ! sed "${SED_ARGS[@]}" "$f" > "$tmp" 2>/dev/null; then
    rm -f "$tmp"; return 0
  fi

  if cmp -s "$f" "$tmp"; then
    rm -f "$tmp"
    return 0
  fi

  CHANGED=$((CHANGED + 1))

  if [ $APPLY -eq 1 ]; then
    cat "$tmp" > "$f"
    rm -f "$tmp"
    [ $QUIET -eq 0 ] && echo "scrubbed: $f" >&2
  else
    [ $QUIET -eq 0 ] && diff -u "$f" "$tmp" | sed "1,2s|$tmp|$f (proposed)|"
    rm -f "$tmp"
  fi
}

# Use ripgrep for the substring pre-filter when walking a directory; falls
# back to find+scrub_one when rg is missing.
walk_dir() {
  local d="$1"
  [ -d "$d" ] || return 0
  if command -v rg >/dev/null 2>&1; then
    # Build an alternation of literal substrings via -F -e <pat> (-F = fixed strings).
    local rg_args=( -lF
      --glob '!.git/**' --glob '!.hg/**' --glob '!.svn/**'
      --glob '!node_modules/**' --glob '!__pycache__/**'
      --glob '!.venv/**' --glob '!venv/**'
      --glob '!.mypy_cache/**' --glob '!.ruff_cache/**' --glob '!.pytest_cache/**'
    )
    local m
    for m in "${SUGGEST_MATCH[@]}"; do rg_args+=( -e "$m" ); done
    while IFS= read -r f; do
      [ -n "$f" ] && scrub_one "$f"
    done < <(rg "${rg_args[@]}" "$d" 2>/dev/null || true)
  else
    while IFS= read -r f; do
      [ -n "$f" ] && scrub_one "$f"
    done < <(find "$d" -type f \
      -not -path '*/.git/*' -not -path '*/__pycache__/*' \
      -not -path '*/.venv/*' -not -path '*/node_modules/*' 2>/dev/null)
  fi
}

for f in "${FILES[@]+"${FILES[@]}"}"; do scrub_one "$f"; done
for d in "${DIRS[@]+"${DIRS[@]}"}"; do walk_dir "$d"; done

if [ $QUIET -eq 0 ]; then
  if [ $APPLY -eq 1 ]; then
    printf '\nscrub-paths: %d file(s) changed, %d candidate(s) processed.\n' "$CHANGED" "$PROCESSED" >&2
  else
    printf '\nscrub-paths: %d file(s) would change, %d candidate(s) processed. Re-run with --apply to write.\n' "$CHANGED" "$PROCESSED" >&2
  fi
fi

exit 0
