#!/usr/bin/env bash
# path-privacy: skip-file
# path-privacy-pre-tool-use.sh -- catch path leaks and the owner's full name
# before they land, and FIX what can be fixed without asking.
#
# Why here: the git hooks catch the same things at commit time, after tokens
# have been spent writing and re-reading the leaked content. Here the problem
# is caught in the same turn.
#
# What it does, per tool:
#   Write / Edit (content / new_string of a tracked file inside the repo)
#     1. REWRITES absolute and home-relative spellings of a path INSIDE the repo
#        to repo-relative, via `updatedInput` with no permissionDecision -- the
#        call proceeds through the normal permission flow with the fixed input,
#        and one line of additionalContext says what changed. These used to pass
#        silently and then fail the whole-tree audit, since they carry the
#        username.
#     2. BLOCKS (exit 2) a path that resolves OUTSIDE the repo.
#     3. BLOCKS (exit 2) the git user.name full name (see _name_guard.sh);
#        LICENSE files excepted, and the skip-file marker does not exempt it.
#   Bash (git / gh commands)
#     4. BLOCKS a commit message, tag message, PR title/body or branch name that
#        carries an external path. Message text only -- including heredoc bodies,
#        the default Claude Code commit shape -- never the whole command, which
#        is full of legitimate absolute paths.
#     5. BLOCKS the full name anywhere in a git or gh command. A lookup can pass
#        "$(git config user.name)" instead of the literal.
#
# Every block message carries the one rule no hook can enforce: the correction
# is routine and stays out of commit messages, branch names and the changelog.
# That sentence used to be a SessionStart directive re-injected on every start,
# resume, clear and compact; it now appears only when a leak is actually being
# corrected, which is the moment it applies.
#
# WHY NOT permissionDecision "allow" with the rewrite: allow skips the
# permission prompt, which would make a privacy hook loosen permissions. The
# field-less form is not in the upstream docs; it was read from Claude Code
# 2.1.281, where a PreToolUse result with updatedInput and no decision replaces
# the input and falls through to the normal flow. If that ever stops holding, the
# failure is benign: the original input runs, exactly as before this hook
# learned to rewrite. Another PreToolUse hook rewriting the same Edit/Write call
# would race this one (last to finish wins, per upstream).
#
# Fails open on every error path (missing jq, malformed payload, scanner
# unreachable, file outside any repo). The git hooks are the authoritative gate.

set -u

command -v jq >/dev/null 2>&1 || exit 0

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

TOOL=$(jq -r '.tool_name // ""' <<<"$PAYLOAD" 2>/dev/null)

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$SELF_DIR/../skills/path-privacy/scripts"
SCANNER="$SCRIPTS/find-external-paths.sh"

QUIET_NOTE="The correction is routine: commit messages, branch names and changelog entries do not mention it."

# Name guard: fail open here (the git hooks fail closed on the same condition).
# shellcheck source=/dev/null
[ -r "$SCRIPTS/_name_guard.sh" ] && . "$SCRIPTS/_name_guard.sh" 2>/dev/null
if ! command -v pp_name_regex >/dev/null 2>&1 \
   || ! command -v pp_name_lines >/dev/null 2>&1 \
   || ! command -v pp_is_license_file >/dev/null 2>&1; then
  pp_name_regex() { return 1; }
  pp_is_license_file() { return 1; }
fi

# --- Bash: git and gh commands -------------------------------------------------
if [ "$TOOL" = "Bash" ]; then
  CMD=$(jq -r '.tool_input.command // ""' <<<"$PAYLOAD" 2>/dev/null)
  [ -z "$CMD" ] && exit 0
  case "$CMD" in *git*|*gh\ *) ;; *) exit 0 ;; esac
  ROOT_B="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || echo "")}"
  [ -z "$ROOT_B" ] && exit 0

  if NAME_RE=$(pp_name_regex "$ROOT_B") \
     && printf '%s\n' "$CMD" | pp_name_lines "$NAME_RE" >/dev/null; then
    {
      echo "path-privacy: blocked -- this git/gh command contains the git user.name full name."
      echo "Use the GitHub handle or a placeholder such as <author>. To look the name up, pass"
      echo "\"\$(git config user.name)\" rather than the literal."
      echo "$QUIET_NOTE"
    } >&2
    exit 2
  fi

  # Message text and branch names only. One awk pass over the whole command:
  #   - quoted values of -m / --message / --title / --body, across newlines
  #   - heredoc bodies (<<EOF, <<'EOF', <<-EOF), which the old line-by-line sed
  #     never saw -- and `-m "$(cat <<'EOF' ... EOF)"` is how Claude Code commits
  #   - branch names after checkout -b/-B and switch -c/-C
  MSG=$(printf '%s' "$CMD" | LC_ALL=C awk '
    BEGIN { RS = "\001" }
    {
      s = $0
      while (match(s, /(^|[ \t])(-m|--message|--title|--body)[ =]*"[^"]*"/)) {
        v = substr(s, RSTART, RLENGTH); sub(/^[^"]*"/, "", v); sub(/"$/, "", v)
        if (v !~ /<</) print v
        s = substr(s, RSTART + RLENGTH)
      }
      s = $0
      while (match(s, /(^|[ \t])(-m|--message|--title|--body)[ =]*\047[^\047]*\047/)) {
        v = substr(s, RSTART, RLENGTH); sub(/^[^\047]*\047/, "", v); sub(/\047$/, "", v)
        print v
        s = substr(s, RSTART + RLENGTH)
      }
      s = $0
      while (match(s, /(checkout[ \t]+-[bB]|switch[ \t]+-[cC])[ \t]+[^ \t\n;&|]+/)) {
        v = substr(s, RSTART, RLENGTH); sub(/^.*[ \t]/, "", v)
        print v
        s = substr(s, RSTART + RLENGTH)
      }
      n = split($0, L, "\n"); d = ""
      for (i = 1; i <= n; i++) {
        if (d != "") {
          t = L[i]; gsub(/^[ \t]+|[ \t]+$/, "", t)
          if (t == d) { d = ""; continue }
          print L[i]; continue
        }
        if (match(L[i], /<<-?[ \t]*[\047"]?[A-Za-z_][A-Za-z0-9_]*[\047"]?/)) {
          d = substr(L[i], RSTART, RLENGTH); gsub(/^<<-?[ \t]*[\047"]?|[\047"]$/, "", d)
        }
      }
    }')
  [ -z "$MSG" ] && exit 0
  [ -x "$SCANNER" ] || exit 0
  OUT_B=$("$SCANNER" --against-root "$(cd "$ROOT_B" && pwd -P)" --text "$MSG" --lax-boundary 2>&1)
  [ $? -eq 1 ] || exit 0
  {
    echo "path-privacy: blocked -- an external path in a commit/PR message or branch name:"
    printf '%s\n' "$OUT_B" | grep '^<text>:' | sed 's|^<text>:|  message line |'
    echo "Use a repo-relative path or say it generically (\"another project\")."
    echo "$QUIET_NOTE"
  } >&2
  exit 2
fi

# --- Write / Edit -------------------------------------------------------------
case "$TOOL" in
  Write) FIELD=content ;;
  Edit)  FIELD=new_string ;;
  *)     exit 0 ;;
esac

FILE_PATH=$(jq -r '.tool_input.file_path // ""' <<<"$PAYLOAD" 2>/dev/null) || exit 0
[ -z "$FILE_PATH" ] && exit 0

# Prefer CLAUDE_PROJECT_DIR (set by the harness), else walk from the file.
ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ]; then
  ROOT=$(git -C "$(dirname "$FILE_PATH" 2>/dev/null || echo .)" rev-parse --show-toplevel 2>/dev/null || echo "")
fi
[ -z "$ROOT" ] && exit 0
ROOT_REAL=$(cd "$ROOT" 2>/dev/null && pwd -P) || exit 0

case "$FILE_PATH" in
  "$ROOT_REAL"/*) REL="${FILE_PATH#"$ROOT_REAL"/}" ;;
  "$ROOT"/*)      REL="${FILE_PATH#"$ROOT"/}" ;;
  *)              exit 0 ;;
esac

# Gitignored targets cannot reach a commit, so no rule binds on them.
if git -C "$ROOT_REAL" check-ignore -q "$FILE_PATH" 2>/dev/null; then
  exit 0
fi

TEXT=$(jq -r --arg f "$FIELD" '.tool_input[$f] // empty' <<<"$PAYLOAD" 2>/dev/null)
[ -z "$TEXT" ] && exit 0

# File-level opt-out (path checks only). Shared definition in _skip_marker.sh;
# a missing or broken library fails closed -- nothing is exempt. Read from the
# file on disk for an Edit (the fragment never contains the header), and from
# the content itself for a Write via --allow-skip-file below.
# shellcheck source=/dev/null
[ -r "$SCRIPTS/_skip_marker.sh" ] && . "$SCRIPTS/_skip_marker.sh" 2>/dev/null
if [ -z "${PP_SKIP_MARKER_RE:-}" ] \
   || ! command -v pp_head_has_skip_marker >/dev/null 2>&1 \
   || ! command -v pp_text_has_skip_marker >/dev/null 2>&1; then
  pp_head_has_skip_marker() { return 1; }
  pp_text_has_skip_marker() { cat >/dev/null; return 1; }
fi
PATH_EXEMPT=0
if [ -f "$FILE_PATH" ] && pp_head_has_skip_marker "$FILE_PATH"; then
  PATH_EXEMPT=1
elif [ "$TOOL" = "Write" ] && printf '%s\n' "$TEXT" | pp_text_has_skip_marker; then
  PATH_EXEMPT=1
fi

# --- 1. rewrite in-repo absolute / home-relative spellings -------------------
# Prefixes that spell the repo root: its canonical and given forms, and the
# ~/, $HOME/ and ${HOME}/ forms when it lives under HOME. Anchored on the left
# (not preceded by a path character) and on the right (followed by `/`, or a
# terminator for the bare root), so `<root>-old/x` and `/mnt<root>` are left
# alone. `<root>/` becomes empty, a bare root becomes `.`.
NEWTEXT="$TEXT"
REWRITES=0
if [ $PATH_EXEMPT -eq 0 ]; then
  # A function, not inline in $( ): bash 3.2 (stock macOS) cannot parse a
  # `case` arm's `)` inside command substitution.
  root_spellings() {
    local r h rest home_real
    printf '%s\n' "$ROOT_REAL" "$ROOT"
    home_real=$(cd "${HOME:-/nonexistent}" 2>/dev/null && pwd -P)
    for r in "$ROOT_REAL" "$ROOT"; do
      for h in "${HOME:-}" "$home_real"; do
        [ -n "$h" ] || continue
        case "$r" in
          "$h"/*) rest="${r#"$h"/}"
                  printf '%s\n' "~/$rest" "\$HOME/$rest" "\${HOME}/$rest" ;;
        esac
      done
    done
  }
  PREFIXES=$(root_spellings | awk 'NF && !seen[$0]++' | jq -R . | jq -sc .)
  RESULT=$(jq -c --arg f "$FIELD" --argjson p "$PREFIXES" '
    def esc: gsub("(?<c>[.^$|?*+()\\[\\]{}\\\\/-])"; "\\\(.c)");
    ($p | map(esc) | join("|")) as $alt
    | ("(?<![A-Za-z0-9._~/-])(?:" + $alt + ")") as $root
    | "(?=[\\s\"'"'"'`)\\],;:>]|$)" as $end
    | .tool_input[$f] as $t
    | ([$t | match($root + "(?:/|" + $end + ")"; "g")] | length) as $n
    | if $n == 0 then {n: 0}
      else {n: $n,
            input: (.tool_input | .[$f] = ($t
              | gsub($root + "/" + $end; "./")
              | gsub($root + "/"; "")
              | gsub($root + $end; ".")))}
      end' <<<"$PAYLOAD" 2>/dev/null) || RESULT='{"n":0}'
  REWRITES=$(jq -r '.n // 0' <<<"$RESULT" 2>/dev/null || echo 0)
  if [ "${REWRITES:-0}" -gt 0 ] 2>/dev/null; then
    NEWTEXT=$(jq -r --arg f "$FIELD" '.input[$f]' <<<"$RESULT")
  else
    REWRITES=0
  fi
fi

BLOCK=""

# --- 2. external paths ---------------------------------------------------------
if [ $PATH_EXEMPT -eq 0 ] && [ -x "$SCANNER" ]; then
  SCAN_OUT=$("$SCANNER" --against-root "$ROOT_REAL" --allow-skip-file --text "$NEWTEXT" 2>&1)
  if [ $? -eq 1 ]; then
    # Keep the finding lines and their suggestions; drop the scanner's footer,
    # which repeats the rule and prints the absolute repo root.
    FINDINGS=$(printf '%s\n' "$SCAN_OUT" | awk '/^<text>:/ || /^  → use:/' | sed "s|^<text>:|  ${REL}:|")
    SKIP_FORM=""
    case "$REL" in
      *.md|*.markdown|*.html|*.htm|*.xml|*.svg) SKIP_FORM='<!-- path-privacy: skip-file -->' ;;
      *.js|*.jsx|*.ts|*.tsx|*.c|*.h|*.cc|*.cpp|*.go|*.rs|*.java|*.swift|*.kt|*.scala)
                                                SKIP_FORM='// path-privacy: skip-file' ;;
      *.sql|*.lua|*.hs|*.ada)                   SKIP_FORM='-- path-privacy: skip-file' ;;
      *.json|*.jsonc|*.csv|*.tsv)               SKIP_FORM='' ;;
      *)                                        SKIP_FORM='# path-privacy: skip-file' ;;
    esac
    BLOCK+="path-privacy: blocked -- ${REL} would gain a path outside the repo:"$'\n'
    BLOCK+="${FINDINGS}"$'\n'
    BLOCK+="Write it repo-relative, or say it generically (\"another project\", <HOME>/...)."$'\n'
    if [ -n "$SKIP_FORM" ]; then
      BLOCK+="For a file that is ABOUT such paths: 'path-privacy: ignore' on the line, or '${SKIP_FORM}' leading a line in the first 30."$'\n'
    else
      BLOCK+="For a line that must keep it: append 'path-privacy: ignore' (this format has no file-level opt-out)."$'\n'
    fi
  fi
fi

# --- 3. full name ---------------------------------------------------------------
if ! pp_is_license_file "$REL" && NAME_RE=$(pp_name_regex "$ROOT_REAL"); then
  if NAME_LINES=$(printf '%s\n' "$NEWTEXT" | pp_name_lines "$NAME_RE"); then
    BLOCK+="path-privacy: blocked -- ${REL} would contain the git user.name full name:"$'\n'
    BLOCK+="$(printf '%s\n' "$NAME_LINES" | sed "s|^|  ${REL}:|")"$'\n'
    BLOCK+="Use the GitHub handle or a placeholder such as <author>."$'\n'
  fi
fi

if [ -n "$BLOCK" ]; then
  { printf '%s' "$BLOCK"; echo "$QUIET_NOTE"; } >&2
  exit 2
fi

# --- 4. emit the rewrite, if any ------------------------------------------------
if [ "$REWRITES" -gt 0 ]; then
  CTX="path-privacy: rewrote ${REWRITES} absolute in-repo path(s) in ${REL} to repo-relative form; they now resolve against the repo root. ${QUIET_NOTE}"
  jq -c --arg ctx "$CTX" '{hookSpecificOutput: {hookEventName: "PreToolUse",
      updatedInput: .input, additionalContext: $ctx}}' <<<"$RESULT"
fi
exit 0
