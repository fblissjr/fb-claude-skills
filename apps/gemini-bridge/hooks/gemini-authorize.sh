#!/usr/bin/env bash
# gemini-bridge: mint a spend authorization. This is the ONLY place one is made.
#
# UserPromptExpansion fires when a *user-typed* command expands into a prompt.
# That is the entire point: the main loop cannot reach this event. When Claude
# invokes a skill or runs a command it goes through the Skill or Bash tool,
# which are different paths -- so a token carrying this origin can only have
# come from a human keystroke.
#
# Minting deliberately does not live in the CLI. Anything the CLI can do, the
# agent can do, since the agent is what runs the CLI. Enforcement is the half
# that belongs there; creation has to happen somewhere the agent cannot reach.
#
# Honest limit: this raises the bar, it does not make forgery impossible. The
# authorization is a file, and anything holding Bash or Write can fabricate
# one. What it guarantees is that nothing on the normal, helpful path creates
# one -- an eager agent is the risk here, not a hostile one.
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

# The matcher should already narrow to this command; check anyway, so a
# misconfigured matcher cannot mint on an unrelated one.
case "$COMMAND_NAME" in
  gemini-authorize | *:gemini-authorize) ;;
  *) exit 0 ;;
esac

# The ceiling the approval carries. Generous enough that an ordinary "yes, go
# ahead" is not immediately refused, bounded enough that it is not a blank
# cheque -- roughly an hour of video at the default sampling rate.
MAX_TOKENS=200000

# `set -f` disables globbing for the split: without it, an unquoted expansion
# containing `*` is matched against the working directory and the typed value
# is lost. `set --` rather than `read -ra` because the array form needs bash
# 4.4+ to be safe under `set -u` when empty, and macOS still ships bash 3.2.
set -f
# shellcheck disable=SC2086  # word splitting intended; globbing is off
set -- $ARGS
set +f
while [ $# -gt 0 ]; do
  case "$1" in
    --max-tokens) [ -n "${2:-}" ] && MAX_TOKENS="$2" && shift ;;
  esac
  shift
done

# A typo becomes the default rather than an unbounded approval. So does zero:
# the CLI refuses a ceiling of 0 rather than reading it as "no ceiling", and
# minting one here would only produce an authorization guaranteed to be
# rejected.
case "$MAX_TOKENS" in *[!0-9]* | "") MAX_TOKENS=200000 ;; esac
[ "$MAX_TOKENS" -gt 0 ] 2>/dev/null || MAX_TOKENS=200000

# The session id lands in a filesystem path. Claude Code sends a uuid, but a
# value carrying a separator would write somewhere neither half of the gate
# looks -- and the CLI applies the same rule when reading, so an id it would
# reject is one there is no point minting for.
# Must match `authorization.SESSION_ID_RE` exactly: a leading alphanumeric,
# then alphanumerics/dot/underscore/hyphen, 128 characters at most. The looser
# earlier version minted for ids the CLI then always refused -- an approval the
# user typed that could never be spent, with `doctor` the only place saying so.
# A parity arm in tests/test_authorize_hook.py runs both sides over the same
# ids, because a claim of agreement between two implementations is a thing to
# test rather than a thing to write in a comment.
case "$SESSION_ID" in
  "" | [!A-Za-z0-9]* | *[!A-Za-z0-9._-]*) exit 0 ;;
esac
[ "${#SESSION_ID}" -le 128 ] || exit 0

STATE_ROOT="${TMPDIR:-/tmp}/claude-gemini-bridge"
STATE_DIR="$STATE_ROOT/${SESSION_ID}"

# 077 because the TMPDIR fallback is a shared /tmp on Linux, and this file is
# what stands between another local account and spending on this API key.
umask 077
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# `mkdir -p` succeeds against a directory that already exists, whoever owns it.
# On a shared /tmp another account can create `claude-gemini-bridge` first, at
# which point the `chmod` below fails, the old `|| true` swallowed it, and the
# authorization was written into a path that account controls. Minting into a
# root we do not own is refused instead -- the fail-closed direction, and the
# one `doctor` reports so it is not another invisible failure. The CLI checks
# ownership again when it reads, since this half may not be installed at all.
for d in "$STATE_ROOT" "$STATE_DIR"; do
  [ -L "$d" ] && exit 0
  [ -O "$d" ] || exit 0
  chmod 700 "$d" 2>/dev/null || exit 0
done

# Nothing else prunes these, so they would sit until reboot. Bounded to this
# plugin's own directory.
find "$STATE_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +7 \
  -exec rm -rf {} + 2>/dev/null || true

jq -n \
  --argjson ts "$(date +%s)" \
  --argjson max_tokens "$MAX_TOKENS" \
  '{ts: $ts, max_tokens: $max_tokens, origin: "user_typed_command"}' \
  >"$STATE_DIR/authorization.json" 2>/dev/null

exit 0
