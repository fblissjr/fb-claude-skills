#!/usr/bin/env bash
# advisor: the spend gate. Two jobs, neither of which spends anything.
#
#   1. Deny any advisor subagent spawn that the user did not authorize by
#      running /advisor. This is the whole reason the plugin has a hook.
#      Shipping agents/advisor.md makes the advisor visible in the agent-type
#      listing, which means the main loop can spawn a Fable-tier model on its
#      own initiative. A description saying "only via /advisor" is a request.
#      This is the enforcement.
#
#   2. Optionally block the first Write/Edit until a consult has happened --
#      the "hard rule" checkpoint from the upstream advisor-tool docs. Off by
#      default, because Anthropic's own measurements show it helping Haiku
#      executors by ~7.5pp and costing ~4pp on retrieval-heavy workloads.
#
# Critically, neither job ever spawns a model. The hook detects and refuses;
# it never acts. That separation is what makes "only a slash command spends
# money" a guarantee rather than a hope. The block message therefore has to
# terminate in a HUMAN decision -- if it told Claude to "consult the advisor
# first", the main loop would helpfully do exactly that, and the surprise
# spend would be back.
#
# Hook contract:
#   stdin:  PreToolUse payload with .tool_name and .tool_input
#   exit 0: allow
#   exit 2: block, stderr shown to the user and to Claude
#
# Failure policy is NOT uniform, and getting that wrong was a total bypass.
#
# The write checkpoint fails OPEN: it is a convenience, and wedging a session
# because a dependency is missing is worse than skipping a reminder.
#
# The spend gate fails CLOSED. An earlier version opened this script with a
# blanket `command -v jq || exit 0`, copied from a hook where fail-open is
# correct. Here exit 0 means "allow the spend", so on any machine without jq on
# the hook's PATH the gate silently became a no-op -- no authorization check, no
# model check, no trace. That needs no hostile actor, just an ops condition.
#
# So: if we cannot verify, we refuse the spawn. Never the reverse.

set -u

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0

HAVE_JQ=1
command -v jq >/dev/null 2>&1 || HAVE_JQ=0

# Without jq we cannot parse the payload, but we can still recognise an advisor
# spawn well enough to refuse it. Crude on purpose: over-matching here costs a
# denied consult the user can retry, while under-matching costs an unauthorized
# frontier-model call.
if [ "$HAVE_JQ" -eq 0 ]; then
  case "$PAYLOAD" in
    *'"subagent_type"'*advisor*)
      echo "advisor: blocked -- jq is unavailable, so this spawn's authorization cannot be verified. Install jq, or tell the user the consult could not be authorized. Refusing rather than allowing an unverified frontier-model call." >&2
      exit 2
      ;;
  esac
  exit 0
fi

TOOL=$(jq -r '.tool_name // ""' <<<"$PAYLOAD" 2>/dev/null)
SESSION_ID=$(jq -r '.session_id // ""' <<<"$PAYLOAD" 2>/dev/null)
CWD=$(jq -r '.cwd // ""' <<<"$PAYLOAD" 2>/dev/null)

STATE_DIR="${TMPDIR:-/tmp}/claude-advisor/${SESSION_ID}"
AUTH_FILE="$STATE_DIR/authorization.json"
CONSULT_LOG="$STATE_DIR/consults.log"

# Authorizations expire. An approval you granted twenty minutes ago should not
# silently fund a spawn you have forgotten about.
AUTH_TTL_SECONDS=300

now_epoch() { date +%s; }

# --- Job 0: refuse model-initiated invocation of the skill itself ------------
# `disable-model-invocation: true` in the skill frontmatter already keeps the
# advisor skill out of Claude's context, so this should be unreachable. It is
# here because the cost of being wrong is a surprise frontier-model charge, and
# the cost of the check is one string comparison.
if [ "$TOOL" = "Skill" ]; then
  SKILL_NAME=$(jq -r '.tool_input.skill // .tool_input.name // ""' <<<"$PAYLOAD" 2>/dev/null)
  case "$SKILL_NAME" in
    advisor | *:advisor)
      echo "advisor: blocked -- the advisor skill is user-invoked only. Suggest that the user run /advisor; do not invoke it yourself." >&2
      exit 2
      ;;
  esac
  exit 0
fi

# --- Job 1: gate advisor spawns ---------------------------------------------
if [ "$TOOL" = "Agent" ] || [ "$TOOL" = "Task" ]; then
  SUBAGENT=$(jq -r '.tool_input.subagent_type // ""' <<<"$PAYLOAD" 2>/dev/null)

  # Only advisor spawns are gated. Every other subagent is none of this
  # plugin's business.
  case "$SUBAGENT" in
    advisor | *:advisor) ;;
    *) exit 0 ;;
  esac

  REQUESTED_MODEL=$(jq -r '.tool_input.model // ""' <<<"$PAYLOAD" 2>/dev/null)

  # Without a session id the state directory cannot be located, so nothing can
  # be verified. That is a denial, not a pass -- the same mistake as the old
  # blanket jq check, one field further in.
  if [ -z "$SESSION_ID" ]; then
    echo "advisor: blocked -- no session id in the hook payload, so this spawn's authorization cannot be located or verified." >&2
    exit 2
  fi

  # Claim the token atomically BEFORE validating it. Parallel tool calls are a
  # supported pattern, so two advisor spawns in one turn could otherwise both
  # read the same still-present file, both pass every check, and both proceed --
  # one `/advisor` funding two consults. Only the process that wins this `mv`
  # gets to continue; `mv` on the same filesystem is atomic.
  CLAIM_FILE="$AUTH_FILE.claimed.$$"
  if [ -r "$AUTH_FILE" ] && mv "$AUTH_FILE" "$CLAIM_FILE" 2>/dev/null; then
    AUTH_FILE="$CLAIM_FILE"
    # Whatever happens next, this claim is spent.
    trap 'rm -f "$CLAIM_FILE" 2>/dev/null' EXIT
  fi

  if [ ! -r "$AUTH_FILE" ]; then
    cat >&2 <<'EOF'
advisor: blocked -- this consult was not authorized.

The advisor runs on a higher-tier model and costs real money, so it spawns
only when the user asks for it by name. Nothing in the session may authorize
it on the user's behalf, including this turn.

Do not retry, and do not work around this by spawning a different agent type
or by calling the advisor's model directly. Tell the user that a consult would
help here and what you would ask, then continue without it. If they want one,
they will run:

    /advisor

They can pass bounds explicitly, for example: /advisor --model opus --words 120
EOF
    exit 2
  fi

  AUTH_TS=$(jq -r '.ts // 0' "$AUTH_FILE" 2>/dev/null)
  AUTH_MODEL=$(jq -r '.model // ""' "$AUTH_FILE" 2>/dev/null)
  AUTH_ORIGIN=$(jq -r '.origin // ""' "$AUTH_FILE" 2>/dev/null)
  AGE=$(( $(now_epoch) - AUTH_TS ))

  # Only a user-typed slash command mints an authorization carrying this
  # provenance. Anything else -- including a script the agent ran itself --
  # produces a token that fails here.
  if [ "$AUTH_ORIGIN" != "user_typed_command" ]; then
    rm -f "$AUTH_FILE" 2>/dev/null
    echo "advisor: blocked -- authorization lacks user-typed provenance. Only the user running /advisor can authorize a consult." >&2
    exit 2
  fi

  if [ "$AGE" -gt "$AUTH_TTL_SECONDS" ]; then
    rm -f "$AUTH_FILE" 2>/dev/null
    echo "advisor: blocked -- authorization expired (${AGE}s old, limit ${AUTH_TTL_SECONDS}s). Ask the user to run /advisor again if a consult is still wanted." >&2
    exit 2
  fi

  # The authorization names a model. The spawn must match it. Otherwise
  # "approve haiku, spawn fable" is a one-word edit away, and the user's
  # control over tier would be nominal.
  if [ -z "$REQUESTED_MODEL" ]; then
    echo "advisor: blocked -- the spawn must name a model explicitly so it can be checked against what the user authorized ('${AUTH_MODEL}'). Pass model: \"${AUTH_MODEL}\" on the Agent call." >&2
    exit 2
  fi

  if [ "$REQUESTED_MODEL" != "$AUTH_MODEL" ]; then
    echo "advisor: blocked -- the user authorized '${AUTH_MODEL}' but this spawn requests '${REQUESTED_MODEL}'. Spawn the authorized model, or ask the user to re-run /advisor --model ${REQUESTED_MODEL}." >&2
    exit 2
  fi

  # One authorization funds exactly one spawn. The claim above already made
  # that true against concurrent spawns; this and the EXIT trap just clear the
  # claimed file.
  rm -f "$AUTH_FILE" 2>/dev/null
  printf '%s consult model=%s\n' "$(now_epoch)" "$AUTH_MODEL" >>"$CONSULT_LOG" 2>/dev/null
  exit 0
fi

# --- Job 2: the write checkpoint (opt-in) ------------------------------------
if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ] || [ "$TOOL" = "MultiEdit" ]; then
  [ -z "$CWD" ] && exit 0
  CONFIG="$CWD/.claude/advisor.json"
  [ -r "$CONFIG" ] || exit 0

  MODE=$(jq -r '.checkpoint // "off"' "$CONFIG" 2>/dev/null)
  case "$MODE" in
    block | warn) ;;
    *) exit 0 ;;
  esac

  # Already consulted this session: the checkpoint is satisfied for good.
  [ -s "$CONSULT_LOG" ] && exit 0

  if [ "$MODE" = "warn" ]; then
    echo "advisor: first write of the session with no consult on record. If this task has a design decision worth a second opinion, the user can run /advisor." >&2
    exit 0
  fi

  cat >&2 <<'EOF'
advisor: blocked -- checkpoint. This is the session's first file write and no
advisor consult is on record.

This is a checkpoint, not a judgment about difficulty; it applies to one-line
edits too. It is configured in .claude/advisor.json ("checkpoint": "block").

You cannot clear this yourself -- spawning the advisor requires the user to
authorize it. Say what you are about to write and why, then let the user
decide between:

    /advisor                          consult first, then write
    setting "checkpoint" to "off"     in .claude/advisor.json
EOF
  exit 2
fi

exit 0
