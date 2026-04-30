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
#   - missing/empty content (nothing to scan)

set -u

# jq is the only hard dep beyond bash + the scanner. Fail open if absent so a
# fresh clone without jq doesn't block every Write.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

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

# Concatenate Write content + Edit new_string (one of them is set per call).
CONTENT=$(jq -r '[.tool_input.content // empty, .tool_input.new_string // empty] | join("\n")' <<<"$PAYLOAD" 2>/dev/null)
[ -z "$CONTENT" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCANNER="$SCRIPT_DIR/../skills/path-privacy/scripts/find-external-paths.sh"
[ -x "$SCANNER" ] || exit 0

SCANNER_OUT=$("$SCANNER" --against-root "$ROOT_REAL" --text "$CONTENT" 2>&1)
SCANNER_EXIT=$?

# Exit 1 = leak, anything else = clean or scanner internal error (fail open).
if [ "$SCANNER_EXIT" -ne 1 ]; then
  exit 0
fi

# Re-emit findings with the user's actual file path swapped in for the
# scanner's `<text>:N:` label, so the diagnostic points at the right file.
RELABELED=$(printf '%s\n' "$SCANNER_OUT" | sed "s|<text>:|${REL}:|g")

{
  echo "Blocked: would introduce an external path into ${REL}"
  echo ""
  printf '%s\n' "$RELABELED"
  echo ""
  echo "Bypass options:"
  echo "  - replace the path with a repo-relative form or generic placeholder"
  echo "  - append 'path-privacy: ignore' to the offending line"
  echo "  - add '<!-- path-privacy: skip-file -->' near the top of the file"
  echo "  - write to a gitignored path instead"
} >&2

exit 2
