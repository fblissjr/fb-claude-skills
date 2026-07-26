#!/usr/bin/env bash
# PostToolUse hook: when the working copy of best_practices.md is edited,
# mirror the change to the plugin-bundled reference so new `skill-maintain
# init` runs pull the latest rules.
#
# Runs from the repo's working directory. Exits 0 regardless -- hook is
# advisory, never blocks. Writes a single line to stderr when it syncs.

set -euo pipefail

# Read hook input JSON from stdin (PostToolUse passes tool_input).
input=$(cat)

# Extract the edited file path. Tool-input shape varies by tool:
#   Edit/Write: tool_input.file_path
#   MultiEdit:  tool_input.edits[].file_path (array, any of which may match)
#   Legacy:     tool_input.path
# Collect all candidates; resolve each below.
candidates=$(echo "$input" | jq -r '
  [
    (.tool_input.file_path // empty),
    (.tool_input.path // empty),
    (.tool_input.edits[]?.file_path // empty)
  ]
  | map(select(. != ""))
  | .[]
' 2>/dev/null || true)

[ -z "$candidates" ] && exit 0

# Resolve a candidate to an absolute path and check if it is the working
# copy. Returns absolute path on match, empty string otherwise.
match_working_copy() {
  local p="$1"
  # Absolute path: basename check is enough.
  # Relative path: resolve against CWD so we can derive repo_root reliably.
  local abs
  if [ "${p#/}" = "$p" ]; then
    abs="$PWD/$p"
  else
    abs="$p"
  fi
  case "$abs" in
    */.skill-maintainer/best_practices.md)
      # Collapse `..` segments if any.
      abs="$(cd "$(dirname "$abs")" 2>/dev/null && pwd)/$(basename "$abs")" || return 1
      echo "$abs"
      ;;
  esac
}

working_copy=""
while IFS= read -r candidate; do
  [ -z "$candidate" ] && continue
  resolved=$(match_working_copy "$candidate") || continue
  if [ -n "$resolved" ]; then
    working_copy="$resolved"
    break
  fi
done <<< "$candidates"

[ -z "$working_copy" ] && exit 0

# Derive repo root from the resolved working-copy path: strip the
# trailing `.skill-maintainer/best_practices.md`.
repo_root="${working_copy%/.skill-maintainer/best_practices.md}"

bundled_ref="$repo_root/skills/skill-maintainer/references/best_practices.md"

# Bail quietly if either file is missing -- this hook is installed across
# many projects, but not every project has the bundled reference.
if [ ! -f "$working_copy" ] || [ ! -f "$bundled_ref" ]; then
  exit 0
fi

# No-op when already in sync (cmp is silent + fast).
if cmp -s "$working_copy" "$bundled_ref"; then
  exit 0
fi

cp "$working_copy" "$bundled_ref"

echo "[skill-maintainer] synced bundled best_practices.md from working copy" >&2

exit 0
