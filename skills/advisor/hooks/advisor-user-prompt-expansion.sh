#!/usr/bin/env bash
# advisor: mint the spend authorization. This is the ONLY place one is created.
#
# UserPromptExpansion fires when a *user-typed* command expands into a prompt.
# That is the whole point: the main loop cannot reach this event. When Claude
# invokes a skill it goes through the `Skill` tool, which is a different path
# entirely -- upstream states it directly: "a PreToolUse hook matching the Skill
# tool fires only when Claude calls the tool, but typing /skillname directly
# bypasses PreToolUse. UserPromptExpansion fires on that direct path."
#
# Minting used to live in prepare-consult.sh, which was wrong: that script runs
# under Bash, so the agent could mint its own authorization and satisfy the gate
# it was supposed to be constrained by. Moving the mint here means the token can
# only originate from a human keystroke.
#
# Honest limit: this raises the bar, it does not make forgery impossible. The
# authorization is a file, and anything holding Bash or Write can fabricate one.
# What it guarantees is that nothing on the *normal, helpful* path creates one --
# which is the actual threat here. An eager agent is the risk, not a hostile one.
#
# Emits nothing on stdout and never blocks. A prompt is never rejected by this.

set -u

command -v jq >/dev/null 2>&1 || exit 0

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

COMMAND_NAME=$(jq -r '.command_name // ""' <<<"$PAYLOAD" 2>/dev/null)
EXPANSION=$(jq -r '.expansion_type // ""' <<<"$PAYLOAD" 2>/dev/null)
SESSION_ID=$(jq -r '.session_id // ""' <<<"$PAYLOAD" 2>/dev/null)
ARGS=$(jq -r '.command_args // ""' <<<"$PAYLOAD" 2>/dev/null)

[ -z "$SESSION_ID" ] && exit 0
[ "$EXPANSION" = "slash_command" ] || exit 0

# The matcher should already narrow to this command; check anyway so a
# misconfigured matcher cannot mint on an unrelated command.
case "$COMMAND_NAME" in
  advisor | *:advisor) ;;
  *) exit 0 ;;
esac

# Housekeeping invocations do not spend anything, so they get no token.
case "$ARGS" in
  install* | remove* | uninstall* | config* | help* | status*) exit 0 ;;
esac

# Defaults, overridable by flags the user typed and by project config.
MODEL="opus"
WORDS=250
MAX_CHARS=40000

CWD=$(jq -r '.cwd // ""' <<<"$PAYLOAD" 2>/dev/null)
CONFIG="$CWD/.claude/advisor.json"
if [ -n "$CWD" ] && [ -r "$CONFIG" ]; then
  CFG_MODEL=$(jq -r '.defaults.model // ""' "$CONFIG" 2>/dev/null)
  CFG_WORDS=$(jq -r '.defaults.words // ""' "$CONFIG" 2>/dev/null)
  CFG_CHARS=$(jq -r '.defaults.maxChars // ""' "$CONFIG" 2>/dev/null)
  [ -n "$CFG_MODEL" ] && MODEL="$CFG_MODEL"
  [ -n "$CFG_WORDS" ] && WORDS="$CFG_WORDS"
  [ -n "$CFG_CHARS" ] && MAX_CHARS="$CFG_CHARS"
fi

# Parse what the user typed. Flags win over config.
#
# `set -f` disables pathname expansion for the duration of the split. Without
# it, bash globs the unquoted expansion against the working directory, so
# `/advisor --model *` run where files exist becomes `--model <filename> ...`
# and the typed value is lost. The validation below coerces the result back to
# a default, so this failed safe rather than spawning an unexpected model --
# but it silently discarded what the user asked for.
#
# `set -f` rather than `read -ra`: the array form needs bash 4.4+ to be safe
# under `set -u` when empty, and macOS still ships bash 3.2.
set -f
# shellcheck disable=SC2086  # word splitting is intended here; globbing is off
set -- $ARGS
set +f
while [ $# -gt 0 ]; do
  case "$1" in
    --model) [ -n "${2:-}" ] && MODEL="$2" && shift ;;
    --words) [ -n "${2:-}" ] && WORDS="$2" && shift ;;
    --max-chars) [ -n "${2:-}" ] && MAX_CHARS="$2" && shift ;;
  esac
  shift
done

# Reject anything that is not a plausible model identifier, so a typo becomes a
# refusal at spawn time rather than a silently different tier.
case "$MODEL" in
  opus | fable | sonnet | haiku | claude-*) ;;
  *) MODEL="opus" ;;
esac

case "$WORDS" in *[!0-9]* | "") WORDS=250 ;; esac
case "$MAX_CHARS" in *[!0-9]* | "") MAX_CHARS=40000 ;; esac

STATE_DIR="${TMPDIR:-/tmp}/claude-advisor/${SESSION_ID}"
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

jq -n \
  --arg model "$MODEL" \
  --argjson ts "$(date +%s)" \
  --argjson words "$WORDS" \
  --argjson max_chars "$MAX_CHARS" \
  '{model: $model, ts: $ts, words: $words, max_chars: $max_chars, origin: "user_typed_command"}' \
  >"$STATE_DIR/authorization.json" 2>/dev/null

exit 0
