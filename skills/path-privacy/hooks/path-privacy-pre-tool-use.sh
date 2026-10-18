#!/usr/bin/env bash
# path-privacy: skip-file
# path-privacy-pre-tool-use.sh -- catch path leaks and the owner's full name
# before they land, and FIX what can be fixed without asking.
#
# Dual-harness: supports Antigravity (CLI, App, IDE) and Claude Code.
#
# What it does, per tool:
#   File write/edit tools:
#     - Antigravity: `write_to_file`, `replace_file_content`, `multi_replace_file_content`
#     - Claude Code: `Write`, `Edit`
#     1. REWRITES absolute and home-relative spellings of a path INSIDE the repo
#        to repo-relative:
#        - In Antigravity: returns `{"decision": "allow", "reason": "...", "overwrite": {...}}`
#          (where `decision: "allow"` delegates to default permission policy, and
#          `overwrite` updates `CodeContent`, `ReplacementContent`, or `ReplacementChunks`).
#        - In Claude Code: returns `hookSpecificOutput.updatedInput` with no
#          `permissionDecision`.
#     2. BLOCKS a path that resolves OUTSIDE the repo.
#     3. BLOCKS the git user.name full name (see _name_guard.sh);
#        LICENSE files excepted, and the skip-file marker does not exempt it.
#   Shell execution tools:
#     - Antigravity: `run_command`
#     - Claude Code: `Bash`
#     4. BLOCKS a commit message, tag message, PR title/body or branch name that
#        carries an external path.
#     5. BLOCKS the full name anywhere in a git/gh command after masking
#        home-directory prefixes.
#     6. BLOCKS `git config user.name` spliced into a command that publishes
#        text (gh; git commit/tag/push/branch/checkout/switch).
#
# Fails open on every error path (missing jq, malformed payload, scanner
# unreachable, file outside any repo). The git hooks are the authoritative gate.

set -u

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

if ! command -v jq >/dev/null 2>&1; then
  case "$PAYLOAD" in
    *'"toolCall"'*|*'"workspacePaths"'*) printf '{"decision":"allow"}\n' ;;
  esac
  exit 0
fi

HARNESS="claude"
if jq -e 'has("toolCall") or has("workspacePaths")' <<<"$PAYLOAD" >/dev/null 2>&1; then
  HARNESS="antigravity"
fi

allow_call() {
  if [ "$HARNESS" = "antigravity" ]; then
    printf '{"decision":"allow"}\n'
  fi
  exit 0
}

block_call() {
  local msg="$1"
  if [ "$HARNESS" = "antigravity" ]; then
    jq -cn --arg r "$msg" '{decision: "deny", reason: $r}'
    exit 0
  else
    printf '%s\n' "$msg" >&2
    exit 2
  fi
}

TOOL=$(jq -r '.toolCall.name // .tool_name // ""' <<<"$PAYLOAD" 2>/dev/null)

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

pp_git() {
  git "$@" 2>/dev/null || GIT_CONFIG_GLOBAL=/dev/null git "$@" 2>/dev/null
}

# --- Shell execution: run_command (Antigravity) / Bash (Claude Code) ----------
if [ "$TOOL" = "Bash" ] || [ "$TOOL" = "run_command" ]; then
  CMD=$(jq -r '.toolCall.args.CommandLine // .tool_input.command // ""' <<<"$PAYLOAD" 2>/dev/null)
  [ -z "$CMD" ] && allow_call

  # The command with heredoc bodies removed. A body is a script (python, cat,
  # a file being written) unless its opening line runs a shell, so text inside
  # it -- a mention of `git commit`, a path, a name -- is not the command.
  OUTER=$(printf '%s' "$CMD" | LC_ALL=C awk '
    BEGIN { RS = "\001" }
    {
      n = split($0, L, "\n"); d = ""
      for (i = 1; i <= n; i++) {
        if (d != "") {
          t = L[i]; gsub(/^[ \t]+|[ \t]+$/, "", t)
          if (t == d) { d = ""; print L[i] }
          continue
        }
        print L[i]
        if (L[i] ~ /(^|[;&|( \t])(ba|z)?sh([ \t;&|)]|$)/) continue
        if (match(L[i], /<<-?[ \t]*[\047"]?[A-Za-z_][A-Za-z0-9_]*[\047"]?/)) {
          d = substr(L[i], RSTART, RLENGTH); gsub(/^<<-?[ \t]*[\047"]?|[\047"]$/, "", d)
        }
      }
    }')
  case "$OUTER" in *git*|*gh\ *) ;; *) allow_call ;; esac

  CWD_B=$(jq -r '.toolCall.args.Cwd // .workspacePaths[0] // .cwd // ""' <<<"$PAYLOAD" 2>/dev/null)
  ROOT_B=""
  if [ -n "$CWD_B" ] && [ -d "$CWD_B" ]; then
    ROOT_B=$(pp_git -C "$CWD_B" rev-parse --show-toplevel || echo "")
  elif [ -z "$CWD_B" ]; then
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR:-}" ]; then
      ROOT_B=$(pp_git -C "$CLAUDE_PROJECT_DIR" rev-parse --show-toplevel || echo "")
    elif [ "$HARNESS" != "antigravity" ]; then
      ROOT_B=$(pp_git rev-parse --show-toplevel || echo "")
    fi
  fi
  [ -z "$ROOT_B" ] && allow_call

  # Heredoc bodies count as message text only when the command writes one: a
  # commit, a tag, or a gh pr/issue/release -- decided on the command outside
  # the bodies, so a script that merely mentions `git commit` is not one.
  SCAN_HEREDOC=0
  printf '%s' "$OUTER" | grep -Eq '(git([[:space:]][^;&|]*)?[[:space:]](commit|tag)([[:space:]]|$)|gh[[:space:]]+(pr|issue|release)[[:space:]])' && SCAN_HEREDOC=1
  NAME_SRC=$OUTER; [ "$SCAN_HEREDOC" = 1 ] && NAME_SRC=$CMD

  # The name guard reads the whole command: gh bodies (-b/--body, comments,
  # `gh api -f body=`), tag names and pushed ref names go public with no git
  # hook behind them. Home-directory prefixes are masked first.
  NAME_CMD=$(printf '%s' "$NAME_SRC" | sed -E \
    -e 's#(/Users|/home)/[^/[:space:]"'"'"']+#\1/HOME#g' \
    -e 's#-(Users|home)-[^-/[:space:]"'"'"']+#-\1-HOME#g' \
    -e 's#~/#HOME/#g' -e 's#\$\{?HOME\}?#HOME#g')
  if NAME_RE=$(pp_name_regex "$ROOT_B") \
     && printf '%s\n' "$NAME_CMD" | pp_name_lines "$NAME_RE" >/dev/null; then
    block_call "$(printf '%s\n%s\n%s' \
      "path-privacy: blocked -- this git/gh command contains the git user.name full name." \
      "Use the GitHub handle or a placeholder such as <author>." \
      "$QUIET_NOTE")"
  fi

  # The same name spliced in by the shell: the hook sees `$(git config
  # user.name)` before expansion, so in a command that publishes text (any
  # gh command; git commit, tag, push, or a new branch) the lookup is the name.
  if printf '%s' "$NAME_SRC" | grep -Eq '(^|[^[:alnum:]_-])(gh[[:space:]]|git([[:space:]][^;&|]*)?[[:space:]](commit|tag|push|branch|checkout|switch)([[:space:]]|$))' \
     && printf '%s' "$NAME_SRC" | grep -Eq 'git[[:space:]]+config([[:space:]]+-[-[:alnum:]]+)*[[:space:]]+user\.name'; then
    block_call "$(printf '%s\n%s\n%s' \
      "path-privacy: blocked -- this command splices git user.name into text it publishes." \
      "The shell expands it after this check, so the full name would go out unseen." \
      "Use the GitHub handle or a placeholder such as <author>.")"
  fi

  # Message text and branch names only.
  MSG=$(printf '%s' "$CMD" | LC_ALL=C awk -v scan_heredoc="$SCAN_HEREDOC" '
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
      if (!scan_heredoc) n = 0
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
  [ -z "$MSG" ] && allow_call
  [ -r "$SCANNER" ] || allow_call
  OUT_B=$(bash "$SCANNER" --against-root "$(cd "$ROOT_B" && pwd -P)" --text "$MSG" --lax-boundary 2>&1)
  [ $? -eq 1 ] || allow_call
  FINDINGS_B=$(printf '%s\n' "$OUT_B" | grep '^<text>:' | sed 's|^<text>:|  message line |')
  block_call "$(printf '%s\n%s\n%s\n%s' \
    "path-privacy: blocked -- an external path in a commit/PR message or branch name:" \
    "$FINDINGS_B" \
    "Use a repo-relative path or say it generically (\"another project\")." \
    "$QUIET_NOTE")"
fi

# --- File write/edit tools ----------------------------------------------------
MODE=""
FIELD=""
case "$TOOL" in
  Write)                      MODE="claude_single"; FIELD="content" ;;
  Edit)                       MODE="claude_single"; FIELD="new_string" ;;
  write_to_file)              MODE="agy_single";    FIELD="CodeContent" ;;
  replace_file_content)       MODE="agy_single";    FIELD="ReplacementContent" ;;
  multi_replace_file_content) MODE="agy_multi";     FIELD="ReplacementChunks" ;;
  *)                          allow_call ;;
esac

FILE_PATH=$(jq -r '.toolCall.args.TargetFile // .tool_input.file_path // ""' <<<"$PAYLOAD" 2>/dev/null) || allow_call
[ -z "$FILE_PATH" ] && allow_call

# Resolve relative FILE_PATH against workspace/cwd if not already absolute.
case "$FILE_PATH" in
  /*) ;;
  *)
    BASE_CWD=$(jq -r '.workspacePaths[0] // .cwd // ""' <<<"$PAYLOAD" 2>/dev/null)
    [ -z "$BASE_CWD" ] && BASE_CWD="${CLAUDE_PROJECT_DIR:-}"
    if [ -n "$BASE_CWD" ]; then
      FILE_PATH="${BASE_CWD%/}/${FILE_PATH#./}"
    fi
    ;;
esac

# Exempt Antigravity conversation artifacts and scratch files.
ARTIFACT_DIR=$(jq -r '.artifactDirectoryPath // ""' <<<"$PAYLOAD" 2>/dev/null)
if [ -n "$ARTIFACT_DIR" ]; then
  case "$FILE_PATH" in
    "$ARTIFACT_DIR"|"$ARTIFACT_DIR"/*) allow_call ;;
  esac
fi
case "$FILE_PATH" in
  */.gemini/antigravity*/brain/*|*/.gemini/antigravity*/artifacts/*) allow_call ;;
esac

# Resolve the git root containing FILE_PATH by walking up from its directory,
# falling back to CLAUDE_PROJECT_DIR only when no parent directory exists yet.
ROOT=""
FILE_DIR=$(dirname "$FILE_PATH" 2>/dev/null || echo ".")
if [ -d "$FILE_DIR" ]; then
  ROOT=$(pp_git -C "$FILE_DIR" rev-parse --show-toplevel || echo "")
else
  # New file in a not-yet-created subdirectory: walk up until an existing parent is found
  PROBE_DIR="$FILE_DIR"
  while [ -n "$PROBE_DIR" ] && [ "$PROBE_DIR" != "/" ] && [ "$PROBE_DIR" != "." ] && [ ! -d "$PROBE_DIR" ]; do
    PROBE_DIR=$(dirname "$PROBE_DIR")
  done
  [ -d "$PROBE_DIR" ] && ROOT=$(pp_git -C "$PROBE_DIR" rev-parse --show-toplevel || echo "")
fi
[ -z "$ROOT" ] && ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -z "$ROOT" ] && allow_call
ROOT_REAL=$(cd "$ROOT" 2>/dev/null && pwd -P) || allow_call

case "$FILE_PATH" in
  "$ROOT_REAL"/*) REL="${FILE_PATH#"$ROOT_REAL"/}" ;;
  "$ROOT"/*)      REL="${FILE_PATH#"$ROOT"/}" ;;
  *)              allow_call ;;
esac

# Gitignored targets cannot reach a commit, so no rule binds on them.
if pp_git -C "$ROOT_REAL" check-ignore -q "$FILE_PATH"; then
  allow_call
fi

if [ "$MODE" = "claude_single" ]; then
  TEXT=$(jq -r --arg f "$FIELD" '.tool_input[$f] // empty' <<<"$PAYLOAD" 2>/dev/null)
elif [ "$MODE" = "agy_single" ]; then
  TEXT=$(jq -r --arg f "$FIELD" '.toolCall.args[$f] // empty' <<<"$PAYLOAD" 2>/dev/null)
else
  TEXT=$(jq -r '(.toolCall.args.ReplacementChunks // []) | map(.ReplacementContent // "") | join("\n")' <<<"$PAYLOAD" 2>/dev/null)
fi
[ -z "$TEXT" ] && allow_call

# File-level opt-out (path checks only). Shared definition in _skip_marker.sh;
# a missing or broken library fails closed -- nothing is exempt.
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
elif { [ "$TOOL" = "Write" ] || [ "$TOOL" = "write_to_file" ]; } && printf '%s\n' "$TEXT" | pp_text_has_skip_marker; then
  PATH_EXEMPT=1
fi

# --- 1. rewrite in-repo absolute / home-relative spellings -------------------
NEWTEXT="$TEXT"
REWRITES=0
RESULT='{"n":0}'
if [ $PATH_EXEMPT -eq 0 ]; then
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
  if [ "$MODE" = "claude_single" ]; then
    RESULT=$(jq -c --arg f "$FIELD" --argjson p "$PREFIXES" '
      def esc: gsub("(?<c>[.^$|?*+()\\[\\]{}\\\\/-])"; "\\\(.c)");
      ($p | map(esc) | join("|")) as $alt
      | ("(?<![A-Za-z0-9._~/-])(?:" + $alt + ")") as $root
      | "(?=[\\s\"'"'"'`)\\],;:>]|$)" as $end
      | .tool_input[$f] as $t
      | ([$t | match($root + "(?:/|" + $end + ")"; "g")] | length) as $n
      | if $n == 0 then {n: 0}
        else ($t
          | gsub($root + "/" + $end; "./")
          | gsub($root + "/"; "")
          | gsub($root + $end; ".")) as $nt
          | {n: $n, newtext: $nt, input: (.tool_input | .[$f] = $nt)}
        end' <<<"$PAYLOAD" 2>/dev/null) || RESULT='{"n":0}'
  elif [ "$MODE" = "agy_single" ]; then
    RESULT=$(jq -c --arg f "$FIELD" --argjson p "$PREFIXES" '
      def esc: gsub("(?<c>[.^$|?*+()\\[\\]{}\\\\/-])"; "\\\(.c)");
      ($p | map(esc) | join("|")) as $alt
      | ("(?<![A-Za-z0-9._~/-])(?:" + $alt + ")") as $root
      | "(?=[\\s\"'"'"'`)\\],;:>]|$)" as $end
      | .toolCall.args[$f] as $t
      | ([$t | match($root + "(?:/|" + $end + ")"; "g")] | length) as $n
      | if $n == 0 then {n: 0}
        else ($t
          | gsub($root + "/" + $end; "./")
          | gsub($root + "/"; "")
          | gsub($root + $end; ".")) as $nt
          | {n: $n, newtext: $nt, overwrite: {($f): $nt}}
        end' <<<"$PAYLOAD" 2>/dev/null) || RESULT='{"n":0}'
  else
    RESULT=$(jq -c --argjson p "$PREFIXES" '
      def esc: gsub("(?<c>[.^$|?*+()\\[\\]{}\\\\/-])"; "\\\(.c)");
      ($p | map(esc) | join("|")) as $alt
      | ("(?<![A-Za-z0-9._~/-])(?:" + $alt + ")") as $root
      | "(?=[\\s\"'"'"'`)\\],;:>]|$)" as $end
      | (.toolCall.args.ReplacementChunks // []) as $chunks
      | ([$chunks[] | (.ReplacementContent // "") | match($root + "(?:/|" + $end + ")"; "g")] | length) as $n
      | if $n == 0 then {n: 0}
        else ($chunks | map(
          if has("ReplacementContent") and (.ReplacementContent | type == "string") then
            .ReplacementContent |= (
              gsub($root + "/" + $end; "./")
              | gsub($root + "/"; "")
              | gsub($root + $end; ".")
            )
          else . end
        )) as $newchunks
        | {
            n: $n,
            newtext: ($newchunks | map(.ReplacementContent // "") | join("\n")),
            overwrite: {ReplacementChunks: $newchunks}
          }
        end' <<<"$PAYLOAD" 2>/dev/null) || RESULT='{"n":0}'
  fi
  REWRITES=$(jq -r '.n // 0' <<<"$RESULT" 2>/dev/null || echo 0)
  if [ "${REWRITES:-0}" -gt 0 ] 2>/dev/null; then
    NEWTEXT=$(jq -r '.newtext' <<<"$RESULT")
  else
    REWRITES=0
  fi
fi

BLOCK=""

# --- 2. external paths ---------------------------------------------------------
if [ $PATH_EXEMPT -eq 0 ] && [ -r "$SCANNER" ]; then
  SCAN_OUT=$(bash "$SCANNER" --against-root "$ROOT_REAL" --allow-skip-file --text "$NEWTEXT" 2>&1)
  if [ $? -eq 1 ]; then
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
  block_call "${BLOCK}${QUIET_NOTE}"
fi

# --- 4. emit the rewrite, if any ------------------------------------------------
if [ "$REWRITES" -gt 0 ]; then
  CTX="path-privacy: rewrote ${REWRITES} absolute in-repo path(s) in ${REL} to repo-relative form; they now resolve against the repo root. ${QUIET_NOTE}"
  if [ "$HARNESS" = "antigravity" ]; then
    jq -c --arg reason "$CTX" '{decision: "allow", reason: $reason, overwrite: .overwrite}' <<<"$RESULT"
    exit 0
  else
    jq -c --arg ctx "$CTX" '{hookSpecificOutput: {hookEventName: "PreToolUse",
        updatedInput: .input, additionalContext: $ctx}}' <<<"$RESULT"
    exit 0
  fi
fi

allow_call
