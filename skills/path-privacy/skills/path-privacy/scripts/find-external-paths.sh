#!/usr/bin/env bash
# path-privacy: skip-file
# find-external-paths.sh - find filesystem paths that resolve outside the current repo root.
#
# Rule: any /Users/<x>/..., /home/<x>/..., ~/..., or $HOME-based path whose resolved
# absolute form does NOT live under the repo root is a leak. Relative paths are fine.
# Generic placeholders (USERNAME, $USER, <user>) are not leaks.
#
# Usage:
#   find-external-paths.sh [-d <dir>]... [-f <file>]... [--staged] [--text <string>]
#                          [--lax-boundary] [--against-root <path>] [--quiet]
#
# Exit 0 = clean, 1 = at least one leak, 2 = bad usage.
#
# `set -u` only (not `set -eu`): per-file errors (unreadable file, malformed
# content) should not abort the rest of the scan.

set -u

if ! command -v rg >/dev/null 2>&1; then
  echo "find-external-paths: ripgrep (rg) not found. Install via 'brew install ripgrep' or equivalent." >&2
  exit 127
fi

DIRS=()
FILES=()
STAGED=0
TEXT=""
ROOT=""
QUIET=0
LAX=0

usage() { sed -n '2,15p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--directory)    DIRS+=("$2"); shift 2 ;;
    -f|--file)         FILES+=("$2"); shift 2 ;;
    --staged)          STAGED=1; shift ;;
    --text)            TEXT="$2"; shift 2 ;;
    --lax-boundary)    LAX=1; shift ;;
    --against-root)    ROOT="$2"; shift 2 ;;
    --quiet)           QUIET=1; shift ;;
    -h|--help)         usage; exit 0 ;;
    *) echo "find-external-paths: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [ -z "$ROOT" ]; then
  ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
fi
if [ -z "$ROOT" ]; then
  echo "find-external-paths: not inside a git repo and --against-root not given" >&2
  exit 2
fi
ROOT=$(cd "$ROOT" 2>/dev/null && pwd -P)
if [ -z "$ROOT" ]; then
  echo "find-external-paths: could not resolve repo root" >&2
  exit 2
fi

if [ $STAGED -eq 1 ]; then
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && FILES+=("$f")
  done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
fi

if [ ${#DIRS[@]} -eq 0 ] && [ ${#FILES[@]} -eq 0 ] && [ -z "$TEXT" ]; then
  DIRS=(".")
fi

# Skip globs (mirror scan-for-secrets/scripts/regex-scan.sh)
SKIPS=(
  --glob '!.git/**'
  --glob '!.hg/**'
  --glob '!.svn/**'
  --glob '!node_modules/**'
  --glob '!__pycache__/**'
  --glob '!.venv/**'
  --glob '!venv/**'
  --glob '!.mypy_cache/**'
  --glob '!.ruff_cache/**'
  --glob '!.pytest_cache/**'
)

# Strict pattern: requires non-word-non-slash on the left so identifiers like
# `myUsers/...` don't match. Used for file content.
PATTERN_STRICT='(?:^|[^A-Za-z0-9_/])(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))[^[:space:]"'"'"'`<>()\[\]\\]*)'
# Lax pattern: no left boundary. Used for commit messages and branch names where
# the embedding context (e.g., `fix/Users/jamie`) puts a word char immediately
# before the path segment.
PATTERN_LAX='(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))[^[:space:]"'"'"'`<>()\[\]\\]*)'

IGNORE_MARKER='path-privacy: ignore'
FILE_SKIP_MARKER='path-privacy: skip-file'

# Generic placeholder usernames -- skipping these prevents documentation false positives.
PLACEHOLDER_USERS=(
  USERNAME username USER user '<USERNAME>' '<USER>' '<user>' '<username>'
  me you name NAME '<name>' somebody '$USER' '${USER}' '$$USER'
)

is_placeholder_user() {
  local u="$1" p
  for p in "${PLACEHOLDER_USERS[@]}"; do
    [ "$u" = "$p" ] && return 0
  done
  return 1
}

inside_root() {
  case "$1" in
    "$ROOT"|"$ROOT"/*) return 0 ;;
  esac
  return 1
}

resolve_path() {
  local p="$1"
  p="${p//\$\{HOME\}/$HOME}"
  p="${p//\$HOME/$HOME}"
  case "$p" in
    '~/'*)  p="$HOME/${p#~/}" ;;
    '~')    p="$HOME" ;;
  esac
  case "$p" in
    /*) ;;
    *)  p="$ROOT/$p" ;;
  esac
  local IFS=/
  # shellcheck disable=SC2206
  local parts=($p)
  local out=() seg
  for seg in "${parts[@]}"; do
    case "$seg" in
      ''|'.') ;;
      '..')   [ ${#out[@]} -gt 0 ] && unset 'out[${#out[@]}-1]' ;;
      *)      out+=("$seg") ;;
    esac
  done
  printf '/%s' "${out[@]}"
}

emit_finding() {
  [ $QUIET -eq 0 ] && printf '%s:%s: %s\n' "$1" "$2" "$3"
}

FOUND=0

# Decide whether a candidate path is a leak; emit + flag if so.
check_candidate() {
  local label="$1" lineno="$2" cand="$3"
  local user_seg=""
  case "$cand" in
    /Users/*) user_seg="${cand#/Users/}"; user_seg="${user_seg%%/*}" ;;
    /home/*)  user_seg="${cand#/home/}";  user_seg="${user_seg%%/*}" ;;
  esac
  if [ -n "$user_seg" ] && is_placeholder_user "$user_seg"; then
    return 0
  fi
  local abs
  abs=$(resolve_path "$cand")
  if ! inside_root "$abs"; then
    emit_finding "$label" "$lineno" "$cand"
    FOUND=1
  fi
}

# Read file once, run rg once, dispatch findings against the in-memory line array.
# File-level skip and per-line ignore are applied here, not per-finding.
scan_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  if head -30 "$f" 2>/dev/null | grep -qF "$FILE_SKIP_MARKER"; then
    return 0
  fi

  local -a lines
  local idx=0 line
  while IFS= read -r line || [ -n "$line" ]; do
    lines[$idx]="$line"
    idx=$((idx + 1))
  done < "$f"

  local rg_line lln cand src
  while IFS= read -r rg_line; do
    [ -z "$rg_line" ] && continue
    local rest="${rg_line#*:}"
    lln="${rest%%:*}"
    cand="${rest#*:}"
    src="${lines[$((lln - 1))]:-}"
    case "$src" in
      *"$IGNORE_MARKER"*) continue ;;
    esac
    check_candidate "$f" "$lln" "$cand"
  done < <(rg -PHn --no-heading --color=never -or '$path' "$PATTERN_STRICT" "$f" 2>/dev/null || true)
}

# Walk a directory by listing files-with-matches and dispatching each to scan_file.
scan_dir() {
  local d="$1"
  [ -d "$d" ] || return 0
  local f
  while IFS= read -r f; do
    [ -n "$f" ] && scan_file "$f"
  done < <(rg -Pl "${SKIPS[@]}" "$PATTERN_STRICT" "$d" 2>/dev/null || true)
}

# Scan an in-memory string. Used for commit messages and branch names.
# Defaults to lax boundary so embeddings like `fix/Users/jamie` are caught.
scan_text() {
  local label="$1" content="$2"
  local pat="$PATTERN_STRICT"
  [ $LAX -eq 1 ] && pat="$PATTERN_LAX"
  local lineno=0 line cand
  while IFS= read -r line; do
    lineno=$((lineno + 1))
    case "$line" in
      *"$IGNORE_MARKER"*) continue ;;
    esac
    while IFS= read -r cand; do
      [ -n "$cand" ] && check_candidate "$label" "$lineno" "$cand"
    done < <(rg -oP --replace '$path' --no-line-number "$pat" <<<"$line" 2>/dev/null || true)
  done <<< "$content"
}

[ -n "$TEXT" ] && scan_text "<text>" "$TEXT"
for f in "${FILES[@]+"${FILES[@]}"}"; do scan_file "$f"; done
for d in "${DIRS[@]+"${DIRS[@]}"}"; do scan_dir "$d"; done

if [ $FOUND -eq 1 ]; then
  if [ $QUIET -eq 0 ]; then
    printf '\nLeak: paths above resolve outside the repo root (%s).\n' "$ROOT"
    printf 'Use a path relative to the repo root, or refer to it generically (e.g. "another project").\n'
  fi
  exit 1
fi
exit 0
