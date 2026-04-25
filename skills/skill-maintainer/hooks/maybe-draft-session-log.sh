#!/usr/bin/env bash
# Stop hook: when the model tries to stop, check whether the session
# touched enough files to warrant a session-log entry. If yes AND
# today's log file doesn't exist yet, write a one-line nudge to stderr
# pointing Claude at /skill-maintainer:finish-session (which in turn
# invokes session-log-drafter).
#
# Exit codes:
#   0 -- always (hook is advisory, never blocks the stop).
#
# Design choices:
# - Only triggers on "substantive" sessions (>= SUBSTANTIVE_THRESHOLD
#   distinct files touched in `git diff HEAD` or `git status`). Small
#   fixes shouldn't trigger a wrap-up ceremony.
# - Excludes the session log itself, lock files, and the auto-generated
#   state/ directory from the count so hook-driven edits don't inflate it.
# - Exits silently (no stderr) when there's nothing to nudge about.
# - Reads the hook's "stop_hook_active" field from stdin. If true (we
#   already fired once this turn and Claude ignored us), exit 0 without
#   re-nudging to avoid infinite loops.

set -euo pipefail

SUBSTANTIVE_THRESHOLD=3

# Parse stop_hook_active to avoid re-nudging. jq is optional -- grep
# fallback works because the field is a simple boolean in the JSON.
input=$(cat)
if echo "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

# Bail early if we're not inside a git repo -- this hook only makes
# sense where session logs are tracked.
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  exit 0
fi

repo_root=$(git rev-parse --show-toplevel)

# Today's session log path (must match the convention in CLAUDE.md and
# .claude/rules/general.md: internal/log/log_YYYY-MM-DD.md).
today=$(date +%Y-%m-%d)
log_path="$repo_root/internal/log/log_${today}.md"

# If the log exists and was modified today, assume it's being maintained.
if [ -f "$log_path" ]; then
  # stat -f is macOS; Linux uses stat -c. Prefer -f, fall back.
  mtime=$(stat -f "%Sm" -t "%Y-%m-%d" "$log_path" 2>/dev/null \
          || stat -c "%y" "$log_path" 2>/dev/null | cut -d' ' -f1)
  if [ "$mtime" = "$today" ]; then
    exit 0
  fi
fi

# Count substantive files touched. Combine tracked changes and
# untracked-not-ignored files. Exclude paths that are hook-driven or
# otherwise uninteresting for "did substantive work happen?".
changed=$(
  {
    git -C "$repo_root" diff --name-only HEAD 2>/dev/null || true
    git -C "$repo_root" ls-files --others --exclude-standard 2>/dev/null || true
  } \
  | { grep -Ev "^(internal/log/|uv\.lock$|bun\.lockb$|package-lock\.json$|\.skill-maintainer/state/)" || true; } \
  | sort -u \
  | wc -l \
  | tr -d ' '
)

if [ "$changed" -lt "$SUBSTANTIVE_THRESHOLD" ]; then
  exit 0
fi

cat >&2 <<EOF
[skill-maintainer] $changed files changed this session, no entry yet in $log_path.
Consider running /skill-maintainer:finish-session to draft one (session-log-drafter
subagent reads the conversation + git diff and returns a house-style draft).
EOF

exit 0
