#!/usr/bin/env bash
# path-privacy: skip-file
# pre-tool-use.sh - block Write/Edit calls that would introduce a path leak
# BEFORE the bytes ever hit disk.
#
# Why: the existing pre-commit hook catches leaks at commit time, after the
# user (or Claude) has already spent tokens authoring + reading the leaked
# content. This hook fails the Write/Edit immediately — Claude sees the
# block in the same turn and can re-author with a placeholder.
#
# Hook contract:
#   stdin:  Claude Code hook payload (JSON) with .tool_input.file_path
#           plus .tool_input.content (Write) or .tool_input.new_string (Edit).
#   stdout: ignored.
#   stderr: diagnostic shown to user + Claude when blocking.
#   exit 0: allow the write.
#   exit 2: block the write (Claude Code surfaces stderr).
#
# Fails open on every error path: missing jq, malformed payload, scanner
# unreachable, file outside any repo. The git-side hooks remain the
# authoritative gate; this is a UX accelerator.
#
# Skipped contexts:
#   - file_path outside the repo (nothing to enforce against)
#   - file_path that's gitignored (can't reach a commit anyway)
#   - file carrying the `path-privacy: skip-file` marker as a line's leading
#     content, on disk or in the content being written (see _skip_marker.sh;
#     a prose mention of the marker is not an opt-out)
#   - missing/empty content (nothing to scan)

set -u

# jq is the only hard dep beyond bash + the scanner. Fail open if absent so a
# fresh clone without jq doesn't block every Write.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

TOOL=$(jq -r '.tool_name // ""' <<<"$PAYLOAD" 2>/dev/null)

# --- Bash: commit messages and branch names ----------------------------------
# These reach the repo without ever passing through Write or Edit, so until now
# they were caught only by the commit-msg git hook -- correct, but one step too
# late: the commit fails and has to be retried. Catching it here turns a failed
# commit into a corrected argument, and lets the SessionStart directive stop
# explaining a rule that is now enforced.
#
# Narrow on purpose. Only `-m`/`--message` values and `-b`/`-B`/`-c` branch
# names are extracted, and anything that does not parse cleanly falls through
# untouched. `if`-style Bash matching fails open by design, so this must never
# pretend to be exhaustive -- the commit-msg hook remains the real backstop.
if [ "$TOOL" = "Bash" ]; then
  CMD=$(jq -r '.tool_input.command // ""' <<<"$PAYLOAD" 2>/dev/null)
  [ -z "$CMD" ] && exit 0
  case "$CMD" in *git*) ;; *) exit 0 ;; esac
  SUBJECT=$(printf '%s' "$CMD" | sed -n \
    -e "s/.*-m[[:space:]]*'\([^']*\)'.*/\1/p" \
    -e 's/.*-m[[:space:]]*"\([^"]*\)".*/\1/p' \
    -e 's/.*checkout[[:space:]]\{1,\}-[bB][[:space:]]\{1,\}\([^[:space:]]*\).*/\1/p' \
    -e 's/.*switch[[:space:]]\{1,\}-c[[:space:]]\{1,\}\([^[:space:]]*\).*/\1/p' | head -1)
  [ -z "$SUBJECT" ] && exit 0
  ROOT_B="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || echo "")}"
  [ -z "$ROOT_B" ] && exit 0
  SELF_B="$(cd "$(dirname "$0")" && pwd)"
  SCANNER_B="$SELF_B/../skills/path-privacy/scripts/find-external-paths.sh"
  [ -x "$SCANNER_B" ] || exit 0
  OUT_B=$("$SCANNER_B" --against-root "$(cd "$ROOT_B" && pwd -P)" --text "$SUBJECT" 2>&1)
  RC_B=$?
  if [ "$RC_B" -ne 1 ]; then exit 0; fi
  {
    echo "Blocked: would put an external path into a commit message or branch name."
    printf '%s\n' "$OUT_B" | sed 's|<text>:|message:|g'
    echo
    echo "These reach the repo without passing through Write or Edit. Use a"
    echo "repo-relative path, or say it generically."
  } >&2
  exit 2
fi

FILE_PATH=$(jq -r '.tool_input.file_path // ""' <<<"$PAYLOAD" 2>/dev/null) || exit 0
[ -z "$FILE_PATH" ] && exit 0

# Resolve repo root. Prefer CLAUDE_PROJECT_DIR (set by the harness on session
# start), fall back to walking from the file's parent.
ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ]; then
  ROOT=$(git -C "$(dirname "$FILE_PATH" 2>/dev/null || echo .)" rev-parse --show-toplevel 2>/dev/null || echo "")
fi
[ -z "$ROOT" ] && exit 0

ROOT_REAL=$(cd "$ROOT" 2>/dev/null && pwd -P) || exit 0

# Compute repo-relative form. If the file lives outside the repo, nothing to enforce.
case "$FILE_PATH" in
  "$ROOT_REAL"/*) REL="${FILE_PATH#"$ROOT_REAL"/}" ;;
  "$ROOT"/*)      REL="${FILE_PATH#"$ROOT"/}" ;;
  *)              exit 0 ;;
esac

# Skip gitignored targets — they can't reach a commit, so the rule doesn't bind.
if git -C "$ROOT_REAL" check-ignore -q "$FILE_PATH" 2>/dev/null; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCANNER="$SCRIPT_DIR/../skills/path-privacy/scripts/find-external-paths.sh"

# Shared definition of the file-level opt-out; see _skip_marker.sh for why it is
# anchored. Resolved BEFORE the check below, which is why SCRIPT_DIR moved up
# from under it. Missing library fails closed, matching the scanner: nothing is
# exempt, so a genuine marker stops working loudly rather than a prose mention
# working silently.
_PP_SKIP_LIB="$SCRIPT_DIR/../skills/path-privacy/scripts/_skip_marker.sh"
# Sourced with its stderr discarded, then VERIFIED. Both halves matter here.
# `[ -r ]` alone tests readability rather than definition, so a broken library
# left `pp_head_has_skip_marker` undefined, and an undefined function exits 127,
# which the check below reads as "not exempt". And bash's own diagnostic for a
# broken library names an absolute path under the plugin root -- which this hook
# would then capture and print back to the user, leaking a home path from inside
# the tool whose only job is stopping that.
# shellcheck source=/dev/null
[ -r "$_PP_SKIP_LIB" ] && . "$_PP_SKIP_LIB" 2>/dev/null
if [ -z "${PP_SKIP_MARKER_RE:-}" ] \
   || ! command -v pp_head_has_skip_marker >/dev/null 2>&1; then
  pp_head_has_skip_marker() { return 1; }   # fail closed: nothing is exempt
fi

# File-level opt-out, read from the TARGET as it exists on disk. An Edit sends
# only `new_string` — a fragment from the middle of the file — so a marker at the
# top is never in the payload and scanning the payload alone can never honour it.
# Write of a brand-new file has no disk copy; that case is covered by passing
# --allow-skip-file below, which reads the marker out of the content itself.
if [ -f "$FILE_PATH" ] && pp_head_has_skip_marker "$FILE_PATH"; then
  exit 0
fi

# Concatenate Write content + Edit new_string (one of them is set per call).
CONTENT=$(jq -r '[.tool_input.content // empty, .tool_input.new_string // empty] | join("\n")' <<<"$PAYLOAD" 2>/dev/null)
[ -z "$CONTENT" ] && exit 0

[ -x "$SCANNER" ] || exit 0

# --allow-skip-file: the string being scanned is a FILE's contents, so the
# file-level marker has to mean here what it means on disk. Without it this hook
# blocked writes to files carrying the marker while advertising that very marker
# as the way out -- including the plugin's own files, every one of which uses it.
SCANNER_OUT=$("$SCANNER" --against-root "$ROOT_REAL" --allow-skip-file --text "$CONTENT" 2>&1)
SCANNER_EXIT=$?

# Exit 1 = leak, anything else = clean or scanner internal error (fail open).
if [ "$SCANNER_EXIT" -ne 1 ]; then
  exit 0
fi

# Re-emit findings with the user's actual file path swapped in for the
# scanner's `<text>:N:` label, so the diagnostic points at the right file.
RELABELED=$(printf '%s\n' "$SCANNER_OUT" | sed "s|<text>:|${REL}:|g")

# Name the comment syntax that is actually legal in THIS file. The message used
# to suggest the HTML-comment form unconditionally, which is a syntax error in
# Python, shell, and Makefiles, and has no valid equivalent at all in JSON --
# sending the user to an escape hatch that cannot work in the file they are in.
case "$REL" in
  *.md|*.markdown|*.html|*.htm|*.xml|*.svg) SKIP_FORM='<!-- path-privacy: skip-file -->' ;;
  *.js|*.jsx|*.ts|*.tsx|*.c|*.h|*.cc|*.cpp|*.go|*.rs|*.java|*.swift|*.kt|*.scala)
                                            SKIP_FORM='// path-privacy: skip-file' ;;
  *.sql|*.lua|*.hs|*.ada)                   SKIP_FORM='-- path-privacy: skip-file' ;;
  *.json|*.jsonc|*.csv|*.tsv)               SKIP_FORM='' ;;
  *)                                        SKIP_FORM='# path-privacy: skip-file' ;;
esac

{
  echo "Blocked: would introduce an external path into ${REL}"
  echo ""
  printf '%s\n' "$RELABELED"
  echo ""
  echo "Bypass options:"
  echo "  - replace the path with a repo-relative form or generic placeholder"
  echo "  - append 'path-privacy: ignore' to the offending line"
  if [ -n "$SKIP_FORM" ]; then
    echo "  - put '$SKIP_FORM' at the START of a line near the top of the file"
    echo "    (it must lead the line; a mention inside a sentence is not an opt-out)"
  else
    echo "  - this file type has no file-level opt-out (no comment syntax);"
    echo "    use the per-line marker above, or write to a gitignored path"
  fi
  echo "  - write to a gitignored path instead"
} >&2

exit 2
