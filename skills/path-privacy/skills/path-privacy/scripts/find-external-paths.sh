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
#                          [--lax-boundary] [--against-root <path>] [--config <path>]
#                          [--allow-skip-file] [--quiet]
#
# Exit 0 = clean, 1 = at least one leak, 2 = bad usage.
#
# Optional config (--config or auto-loaded from <ROOT>/.path-privacy.local.json):
#   {
#     "suggestions": [
#       {"match": "/home/foo/ComfyUI/", "suggest": "<comfyui>/"},
#       {"match": "/home/foo/",         "suggest": "<home>/"}
#     ],
#     "allow": [
#       "$HOME/.toolname",
#       {"prefix": "~/.cursor/agents/", "_why": "generic, names no user"}
#     ]
#   }
# Each finding whose matched text contains a `match` substring gets an
# additional `→ use: ...` line showing the substituted form. Suggestions
# are auto-sorted longest-match-first so specific entries win over general
# ones; the user does not need to order them by hand. Requires jq;
# silently no-ops if jq is missing or the config is malformed.
#
# `allow` exempts candidates by literal PREFIX, for generic tool-config paths
# that appear inside runnable code and so cannot be rewritten. Prefix is
# anchored at the start, never a substring. See the ALLOW_PREFIX block below
# for why, and prefer `suggestions` whenever the text can simply be rewritten.
#
# `--allow-skip-file` lets `--text` honour a `path-privacy: skip-file` marker
# leading one of its first 30 lines, the same way a file on disk is treated
# (shared definition in _skip_marker.sh). Off by default so
# a commit message cannot exempt itself; the PreToolUse hook passes it because
# there the string IS a file's contents.
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
CONFIG_PATH=""
ALLOW_SKIP_FILE=0

# Print the header comment block, starting BELOW this file's own skip-file
# marker on line 2. Emitting that line was the same defect fixed in the
# SessionStart hook: redirect `--help` into a file and the file is silently
# exempt from the entire audit. `usage` also runs on any unknown argument, so
# the leak needed no deliberate act.
#
# Bounded by "the header block ends at the first non-comment line" rather than a
# hardcoded range. The old `2,21p` was a magic number tied to comment length,
# and editing the header above it silently truncated the help text elsewhere --
# which is exactly what happened to this script's sibling.
usage() { awk 'NR>2 { if (/^#/) print; else exit }' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--directory)    DIRS+=("$2"); shift 2 ;;
    -f|--file)         FILES+=("$2"); shift 2 ;;
    --staged)          STAGED=1; shift ;;
    --text)            TEXT="$2"; shift 2 ;;
    --lax-boundary)    LAX=1; shift ;;
    --against-root)    ROOT="$2"; shift 2 ;;
    --config)          CONFIG_PATH="$2"; shift 2 ;;
    --allow-skip-file) ALLOW_SKIP_FILE=1; shift ;;
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

# Default to scanning the cwd ONLY if no explicit target mode was selected.
# `--staged` is an explicit target mode even when its file list comes back
# empty (e.g. `git commit` is forming, the staged set has no
# matching-pattern paths) — in that case we want a clean exit, not a
# whole-tree scan that surfaces unrelated unstaged leaks.
if [ $STAGED -eq 0 ] && [ ${#DIRS[@]} -eq 0 ] && [ ${#FILES[@]} -eq 0 ] && [ -z "$TEXT" ]; then
  DIRS=(".")
fi

# Skip globs (mirror scan-for-secrets/scripts/regex-scan.sh)
#
# --hidden because rg skips dotfiles and dot-directories by DEFAULT, which made
# the whole-tree audit (`-d .`) silently blind to exactly the files most likely
# to carry a machine-specific path: .claude-plugin/, .github/, dotfiles at the
# root. The gap was invisible because the per-file and --staged modes pass
# explicit paths, which rg does not filter -- so the pre-commit hook caught
# leaks the audit had just declared clean. An audit that under-reports is worse
# than no audit; it is read as a clean bill of health.
# .git is still excluded below, and rg's .gitignore handling is left on --
# ignored files cannot reach a commit, so the rule does not bind on them.
SKIPS=(
  --hidden
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
PATTERN_STRICT='(?:^|[^A-Za-z0-9_/])(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))(?:[^[:space:]"'"'"'`<>()\[\]\\]|<[A-Za-z0-9._-]+>)*)'
# Lax pattern: no left boundary. Used for commit messages and branch names where
# the embedding context (e.g., `fix/Users/jamie`) puts a word char immediately
# before the path segment.
PATTERN_LAX='(?<path>(?:/Users/|/home/|~/|\$HOME(?:/|\b)|\$\{HOME\}(?:/|\b))(?:[^[:space:]"'"'"'`<>()\[\]\\]|<[A-Za-z0-9._-]+>)*)'

IGNORE_MARKER='path-privacy: ignore'

# The file-level opt-out is defined once, in _skip_marker.sh, and shared with the
# scrub script and the PreToolUse hook. A missing library fails CLOSED -- nothing
# is exempt and every file is scanned. That direction is deliberate: a false
# positive is visible and gets fixed, while a silent exemption is exactly the
# defect the library exists to prevent, so the degraded mode must not be the
# permissive one.
_PP_LIB_DIR="$(cd "$(dirname "$0")" && pwd)"
# Source, then VERIFY what got defined. `[ -r ]` alone tests readability, not
# definition: a truncated or syntactically broken library passes it, the else
# branch never runs, and the resulting undefined function exits 127 -- which
# every call site here reads as "not exempt", i.e. fails OPEN in the one place
# that must not. Suppressing the source's own stderr matters for a second
# reason: bash's diagnostic for a broken library quotes an absolute path under
# the plugin root, and this scanner's stderr is captured and re-shown to the
# user by the PreToolUse hook. A privacy tool must not leak a path while
# complaining that it cannot check for leaked paths.
# shellcheck source=/dev/null
[ -r "$_PP_LIB_DIR/_skip_marker.sh" ] && . "$_PP_LIB_DIR/_skip_marker.sh" 2>/dev/null
if [ -z "${PP_SKIP_MARKER_RE:-}" ] \
   || ! command -v pp_head_has_skip_marker >/dev/null 2>&1 \
   || ! command -v pp_text_has_skip_marker >/dev/null 2>&1; then
  echo "find-external-paths: _skip_marker.sh missing or unusable; file-level opt-outs are OFF." >&2
  pp_head_has_skip_marker() { return 1; }
  pp_text_has_skip_marker() { cat >/dev/null 2>&1; return 1; }
fi

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

# --- Suggestion config: parallel arrays of (match-substring, suggested-replacement).
# Loaded from --config or auto-resolved <ROOT>/.path-privacy.local.json.
# Sorted longest-match-first so specific entries win over more general ones.
SUGGEST_MATCH=()
SUGGEST_TO=()

# --- Allow config: literal path PREFIXES that are not leaks.
#
# For the shape a substitution cannot fix: a generic tool-config path that
# appears inside RUNNABLE code. `D="$HOME/.impeccable"` in a hook command
# names no user and reveals no machine layout, but rewriting it to a
# placeholder would make the hook create a directory literally called
# <HOME>. The suggestion mechanism is the wrong tool there, because its whole
# job is to rewrite the text.
#
# PREFIX, anchored at the start, never a substring. A substring rule would
# let "$HOME/.impeccable" in an allow list exempt "/Users/jamie/x # see
# $HOME/.impeccable", which is the class the gate exists to catch. Prefix
# also gives the useful widening for free: allowing "$HOME/.impeccable"
# allows "$HOME/.impeccable/node-unsupported" and nothing else under $HOME.
#
# Entries are literal matched text, not resolved paths, so "~/.cursor/" and
# "$HOME/.cursor/" are distinct and both must be listed if both appear.
ALLOW_PREFIX=()

load_suggestions() {
  local cfg="${CONFIG_PATH:-$ROOT/.path-privacy.local.json}"
  [ -f "$cfg" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0

  # jq sorts by match-length descending so we don't burden the user with ordering.
  local m s
  while IFS=$'\t' read -r m s; do
    [ -z "$m" ] && continue
    SUGGEST_MATCH+=("$m")
    SUGGEST_TO+=("$s")
  done < <(jq -r '
    .suggestions // []
    | sort_by(.match | length) | reverse
    | .[]
    | "\(.match)\t\(.suggest // "")"
  ' "$cfg" 2>/dev/null || true)

  # Accepts both the bare-string form and {"prefix": ..., "_why": ...}, so an
  # entry can carry its justification the way suggestions do. An allow list
  # without reasons rots into a list nobody dares prune.
  local a
  while IFS= read -r a; do
    [ -z "$a" ] && continue
    ALLOW_PREFIX+=("$a")
  done < <(jq -r '
    .allow // []
    | .[]
    | if type == "string" then . else (.prefix // empty) end
  ' "$cfg" 2>/dev/null || true)
}

# Return 0 when the candidate is covered by an allow prefix.
is_allowed_path() {
  local cand="$1" a
  for a in ${ALLOW_PREFIX[@]+"${ALLOW_PREFIX[@]}"}; do
    case "$cand" in
      "$a"|"$a"*) return 0 ;;
    esac
  done
  return 1
}

# Return 0 + print substituted form on stdout if a suggestion matches; else return 1.
lookup_suggestion() {
  local matched="$1"
  local i m s
  for (( i=0; i<${#SUGGEST_MATCH[@]}; i++ )); do
    m="${SUGGEST_MATCH[$i]}"
    s="${SUGGEST_TO[$i]}"
    case "$matched" in
      *"$m"*)
        printf '%s\n' "${matched/$m/$s}"
        return 0
        ;;
    esac
  done
  return 1
}

load_suggestions

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
  [ $QUIET -eq 1 ] && return
  printf '%s:%s: %s\n' "$1" "$2" "$3"
  local sug
  if sug=$(lookup_suggestion "$3"); then
    printf '  → use: %s\n' "$sug"
  fi
}

FOUND=0
# Files rg reported as binary-and-matching. They cannot be line-scanned, and
# silently dropping them is what let a poisoned scan look like a clean one.
BINARY_UNSCANNED=''

# Decide whether a candidate path is a leak; emit + flag if so.
check_candidate() {
  local label="$1" lineno="$2" cand="$3"

  # Bare leak-prefix with no segment after (e.g. "/home/", "/Users/", "~/")
  # is not a real leak. The pattern matches these when it terminates early
  # against an excluded char like `<` (so a doc reference such as
  # "/home/<user>/foo" yields a candidate of just "/home/" which would
  # otherwise resolve outside the repo and falsely flag). The bare prefix
  # is also benign in shell-history-style references like "cd /home/".
  case "$cand" in
    /Users/|/home/|'~/') return 0 ;;
  esac

  # Any path containing a <placeholder> segment is treated as documentation,
  # not a real path. Covers cases like "~/.claude/<plan-name>.md" and
  # "/Users/<your-name>/code/x" without enumerating every placeholder
  # word in PLACEHOLDER_USERS.
  case "$cand" in
    *'<'*'>'*) return 0 ;;
  esac

  # Explicit per-repo allow list. Checked before resolution, because these are
  # exempt on the strength of the literal text naming no user, not on where
  # they happen to resolve on this machine.
  if is_allowed_path "$cand"; then
    return 0
  fi

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
  if pp_head_has_skip_marker "$f"; then
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

    # rg does not always emit `file:line:match`. When a file named directly on
    # the command line is binary AND matches, it emits a diagnostic instead:
    #   path: binary file matches (found "\0" byte around offset 0)
    # That put the word `matches` inside the arithmetic expansion below. Under
    # `set -u`, bash 3.2 -- which is what `env bash` resolves to on a stock
    # Mac -- treated it as an unbound variable, killed the script, and still
    # exited 0. The pre-commit hook read that as "scan passed".
    #
    # The effect was not "binaries are skipped". It was that ONE staged binary
    # aborted the scan for every file after it, so unrelated plain-text leaks
    # in the same commit went through unreported. Staging a compiled artifact
    # with an embedded build path is entirely ordinary, so this was reachable
    # without doing anything unusual.
    #
    # Anything that is not a plain line number is therefore handled explicitly
    # rather than fed to arithmetic.
    case "$lln" in
      ''|*[!0-9]*)
        BINARY_UNSCANNED="${BINARY_UNSCANNED}${f}"$'\n'
        continue
        ;;
    esac

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
  # File-level skip is OFF by default here. `--text` serves two callers with
  # opposite needs: the PreToolUse hook, where the string is a file's future
  # contents and the marker means what it means for a file on disk, and the
  # commit-msg hook, where honouring it would let any commit message exempt
  # ITSELF from the gate by quoting one token. Only the first passes the flag.
  if [ $ALLOW_SKIP_FILE -eq 1 ] \
     && printf '%s\n' "$content" | pp_text_has_skip_marker; then
    return 0
  fi
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

if [ -n "$BINARY_UNSCANNED" ] && [ $QUIET -eq 0 ]; then
  printf '\nNot scanned (binary, contains a matching byte sequence):\n'
  printf '%s' "$BINARY_UNSCANNED" | sort -u | sed 's/^/  /'
  printf 'Line-level scanning cannot report these. Check them by hand before committing.\n'
fi

if [ $FOUND -eq 1 ]; then
  if [ $QUIET -eq 0 ]; then
    printf '\nLeak: paths above resolve outside the repo root (%s).\n' "$ROOT"
    printf 'Use a path relative to the repo root, or refer to it generically (e.g. "another project").\n'
  fi
  exit 1
fi
exit 0
