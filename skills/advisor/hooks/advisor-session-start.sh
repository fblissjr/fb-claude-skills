#!/usr/bin/env bash
# advisor: pin this session's transcript path so /advisor can find it later.
#
# This hook is deliberately silent. It emits no additionalContext and no
# stdout, so it costs zero tokens on every session start, fork, resume, clear
# and compact. See docs/internals/context-cost.md: SessionStart fired 54 times
# in this repo and emitted 53% of all hook bytes, because the hooks that speak
# are the expensive ones. This one only writes a file.
#
# Why it exists at all: a skill running in the main loop is never told which
# transcript belongs to it. Hooks are -- `transcript_path` and `session_id`
# arrive on stdin. Guessing "newest .jsonl in the project directory" picks the
# wrong file whenever two sessions share a repo, which is exactly when wrong
# advice is most expensive.

set -u

command -v jq >/dev/null 2>&1 || exit 0

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

SESSION_ID=$(jq -r '.session_id // ""' <<<"$PAYLOAD" 2>/dev/null)
TRANSCRIPT=$(jq -r '.transcript_path // ""' <<<"$PAYLOAD" 2>/dev/null)
CWD=$(jq -r '.cwd // ""' <<<"$PAYLOAD" 2>/dev/null)

[ -z "$SESSION_ID" ] && exit 0

STATE_DIR="${TMPDIR:-/tmp}/claude-advisor/${SESSION_ID}"
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# Session state lives in TMPDIR, not in the repo and not in the user's Claude
# config directory. It is per-session and worthless after the session ends, so
# writing it into a project would be litter and writing it into the config
# directory would outlive its meaning.
jq -n \
  --arg session_id "$SESSION_ID" \
  --arg transcript "$TRANSCRIPT" \
  --arg cwd "$CWD" \
  '{session_id: $session_id, transcript_path: $transcript, cwd: $cwd}' \
  >"$STATE_DIR/session.json" 2>/dev/null

exit 0
