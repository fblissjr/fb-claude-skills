#!/usr/bin/env bash
# advisor: build the digest for an already-authorized consult.
#
# This script does NOT authorize anything. That is the point.
#
# It used to mint the authorization itself, which quietly defeated the gate:
# the script runs under Bash, so the agent could call it and satisfy the very
# constraint it was supposed to be bound by. Minting now happens only in
# hooks/advisor-user-prompt-expansion.sh, on an event the agent cannot reach --
# a user-typed slash command.
#
# So this reads the authorization rather than creating one, and takes its
# parameters from it rather than from flags. Single source of truth: whatever
# the user typed is what gets used, and there is no argument here that can
# disagree with it.

set -euo pipefail

usage() {
  cat <<'EOF'
usage: prepare-consult.sh

Takes no arguments. Reads the authorization created when the user typed
/advisor, builds the session digest, and prints:

  DIGEST=<path>  MODEL=<tier>  WORDS=<cap>

Exits non-zero if no valid authorization exists. Model, word cap, and digest
budget come from what the user typed; they cannot be overridden here.
EOF
}

if [ $# -gt 0 ]; then
  case "$1" in
    -h | --help) usage; exit 0 ;;
    *)
      echo "advisor: this script takes no arguments." >&2
      echo "advisor: bounds come from the user's /advisor invocation, not from flags." >&2
      usage >&2
      exit 2
      ;;
  esac
fi

SESSION_ID="${CLAUDE_CODE_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  echo "advisor: CLAUDE_CODE_SESSION_ID is unset -- cannot identify this session." >&2
  exit 1
fi

STATE_DIR="${TMPDIR:-/tmp}/claude-advisor/${SESSION_ID}"
AUTH_FILE="$STATE_DIR/authorization.json"

# The digest written below is a condensation of the session transcript. It is
# not filtered for secrets -- if something sensitive was pasted into the chat,
# it is in there. Keep it readable only by this user; the TMPDIR fallback is a
# shared /tmp on Linux.
umask 077

if [ ! -r "$AUTH_FILE" ]; then
  cat >&2 <<'EOF'
advisor: no authorization for this session.

A consult is authorized only when the user types /advisor. Nothing else can
create one, including running this script.

If a consult would help here, say so and let the user decide. Do not attempt
to work around this.
EOF
  exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "advisor: jq is required." >&2; exit 1; }

AUTH_TS=$(jq -r '.ts // 0' "$AUTH_FILE")
MODEL=$(jq -r '.model // "opus"' "$AUTH_FILE")
WORD_CAP=$(jq -r '.words // 250' "$AUTH_FILE")
MAX_CHARS=$(jq -r '.max_chars // 40000' "$AUTH_FILE")
ORIGIN=$(jq -r '.origin // ""' "$AUTH_FILE")

if [ "$ORIGIN" != "user_typed_command" ]; then
  echo "advisor: authorization lacks user-typed provenance; refusing." >&2
  exit 1
fi

AGE=$(( $(date +%s) - AUTH_TS ))
if [ "$AGE" -gt 300 ]; then
  rm -f "$AUTH_FILE"
  echo "advisor: authorization expired (${AGE}s old, limit 300s). Ask the user to run /advisor again." >&2
  exit 1
fi

# The SessionStart hook records the exact transcript path. Fall back to
# deriving it only if the hook has not run -- the derivation guesses at the
# project-directory slug, and a wrong guess means advising on someone else's
# session.
TRANSCRIPT=""
if [ -r "$STATE_DIR/session.json" ]; then
  TRANSCRIPT=$(jq -r '.transcript_path // ""' "$STATE_DIR/session.json" 2>/dev/null)
fi

if [ -z "$TRANSCRIPT" ] || [ ! -r "$TRANSCRIPT" ]; then
  SLUG=$(printf '%s' "$PWD" | sed 's|[/.]|-|g')
  CANDIDATE="$HOME/.claude/projects/${SLUG}/${SESSION_ID}.jsonl" # path-privacy: ignore
  if [ -r "$CANDIDATE" ]; then
    TRANSCRIPT="$CANDIDATE"
  fi
fi

if [ -z "$TRANSCRIPT" ] || [ ! -r "$TRANSCRIPT" ]; then
  echo "advisor: could not locate this session's transcript." >&2
  echo "advisor: the SessionStart hook may not have run. Is the plugin enabled?" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIGEST_PATH="$STATE_DIR/digest.md"

if ! uv run --script "$SCRIPT_DIR/digest.py" \
  "$TRANSCRIPT" --max-chars "$MAX_CHARS" -o "$DIGEST_PATH"; then
  echo "advisor: digest failed." >&2
  exit 1
fi

echo "DIGEST=$DIGEST_PATH"
echo "MODEL=$MODEL"
echo "WORDS=$WORD_CAP"
