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

# Extract the edited file path. Tool-input shape varies by tool; try a few.
file_path=$(echo "$input" | jq -r '
  (.tool_input.file_path // .tool_input.path // empty)
' 2>/dev/null || true)

if [ -z "$file_path" ]; then
  exit 0
fi

# Only act on edits to the working-copy best_practices.md. Match on suffix
# to handle both absolute and relative paths in the hook input.
case "$file_path" in
  *"/.skill-maintainer/best_practices.md"|".skill-maintainer/best_practices.md")
    ;;
  *)
    exit 0
    ;;
esac

# Locate repo root from the edited path so we work correctly regardless of
# where the session's CWD is.
repo_root=$(cd "$(dirname "$file_path")/.." && pwd)

working_copy="$repo_root/.skill-maintainer/best_practices.md"
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
