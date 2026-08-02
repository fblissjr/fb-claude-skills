#!/usr/bin/env bash
# Detect whether cwd is a git repo. If so, emit the path-privacy directive(s)
# as additionalContext so Claude has the rule loaded.

CWD=$(jq -r '.cwd // ""' 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  exit 0
fi

# Only inject when inside a git working tree
if ! git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT=""

# Shared with install-git-hooks.sh and every generated wrapper. Absent copy
# means never claim "newer", which routes every mismatch to the stale branch --
# the branch whose advice is idempotent.
VERSION_COMPARE_LIB="$SCRIPT_DIR/../skills/path-privacy/scripts/_version_compare.sh"
if [ -r "$VERSION_COMPARE_LIB" ]; then
  # shellcheck source=/dev/null
  . "$VERSION_COMPARE_LIB"
else
  pp_version_is_newer() { return 1; }
  pp_template_is_newer() { return 1; }
fi

# Same definition of a marker line the scanner exempts on, so removal here and
# exemption there cannot drift apart. Degraded mode emits the directive
# UNFILTERED: a stray marker comment in context is the harmless failure, and
# dropping lines by a guessed pattern is not.
#
# That degraded path is expressed as a passthrough FUNCTION, never as a pattern.
# The previous attempt set `PP_SKIP_MARKER_RE='$^'` with the comment "matches
# nothing" and fed it to `grep -vE`; under BSD grep `$^` matches every EMPTY
# line, so the fallback silently stripped the blank lines out of the directive
# and merged its paragraphs. A readable-but-broken library was worse still --
# the variable stayed unset, `grep -vE ""` matched every line, `-v` inverted it,
# and the entire privacy directive stopped loading in every repo, invisibly.
# A function cannot fail that way, and it degrades identically on every platform.
SKIP_MARKER_LIB="$SCRIPT_DIR/../skills/path-privacy/scripts/_skip_marker.sh"
# shellcheck source=/dev/null
[ -r "$SKIP_MARKER_LIB" ] && . "$SKIP_MARKER_LIB" 2>/dev/null
if [ -z "${PP_SKIP_MARKER_RE:-}" ] \
   || ! command -v pp_filter_skip_marker_lines >/dev/null 2>&1; then
  pp_filter_skip_marker_lines() { cat; }
fi

# --- outdated-wrapper notice -------------------------------------------------
# A plugin update refreshes the scanner the wrapper CALLS, but not the wrapper
# itself -- its logic is baked in at install time. So a repo can quietly carry a
# wrapper whose bugs were fixed several releases ago, with nothing to reveal it:
# before 0.6.0 the generated file had no version marker at all, so old and new
# were indistinguishable by inspection.
#
# This tells you once, per repo, in the repo where it matters.
#
# It also REFRESHES a stale wrapper in place, which reverses this hook's original
# policy. That policy said rewriting a file in someone's .git/hooks at session
# start was a surprise a privacy gate should never spring, citing four
# repo-damaging bugs in the install path before 0.6.0. The reversal is deliberate
# and the caveat is answered rather than withdrawn: the alternative was telling
# every user to run a shell script in every repo on every template change, which
# is work a hook already standing in the right place can do. What makes it safe
# now is that ownership is exact -- only a file carrying our own byte-for-byte
# stamp is ever touched, a wrapper AHEAD of the plugin is left alone, and the
# refresh is verified by re-reading the stamp before it is reported as done.
# A foreign or hand-edited hook is still never rewritten.
HOOKS_DIR=$(git -C "$CWD" rev-parse --path-format=absolute --git-path hooks 2>/dev/null || echo "")
# Compare against the WRAPPER TEMPLATE version the installer stamps ("t1"), not
# the plugin version. They were the same value until unrelated plugin bumps
# started marking every installed wrapper stale; see install-git-hooks.sh.
INSTALLER="$SCRIPT_DIR/../skills/path-privacy/scripts/install-git-hooks.sh"
CURRENT_VERSION=$(sed -n 's/^WRAPPER_TEMPLATE_VERSION=\(.*\)$/t\1/p' "$INSTALLER" 2>/dev/null | head -1)
STALE_HOOKS=""
AHEAD_HOOKS=""
MISSING_HOOKS=""
REFRESHED_HOOKS=""
if [ -n "$HOOKS_DIR" ] && [ -n "$CURRENT_VERSION" ]; then
  for h in pre-commit commit-msg; do
    f="$HOOKS_DIR/$h"
    # The directive below loads in EVERY git repo, whether or not the gate is
    # installed, so from inside a session an ungated repo is indistinguishable
    # from a gated one -- it reads as protection either way. That gap between
    # feeling covered and being covered is this plugin's main failure mode, and
    # this is the one place already running where it can be closed.
    if [ ! -f "$f" ] || ! grep -q 'path-privacy:wrapper' "$f" 2>/dev/null; then
      MISSING_HOOKS="${MISSING_HOOKS:+$MISSING_HOOKS, }$h"
      continue
    fi
    have=$(sed -n 's/^# path-privacy:wrapper-version //p' "$f" | head -1)
    [ -z "$have" ] && have="pre-0.6.0"
    # Direction decides the remedy and they are opposites, so this cannot be a
    # string comparison -- see _version_compare.sh for why "newer" is the claim
    # that has to be earned. Non-semver stamps ("pre-0.6.0", the "unknown"
    # written when plugin.json was unreadable at install time) are not newer,
    # so they land in the stale branch and get the harmless advice.
    if [ "$have" != "$CURRENT_VERSION" ]; then
      # A stale wrapper is REFRESHED, not reported. Telling a user to go run a
      # shell script is asking them to do work a hook already standing in the
      # right place can do, and every repo would need it on every template
      # change. The installer is re-run in place; only if that fails does this
      # fall back to telling anyone.
      #
      # Safe because ownership is exact: we reached this branch only after
      # confirming the file carries our own `path-privacy:wrapper` stamp, so a
      # hand-written or foreign hook is never touched. `pp_template_is_newer`
      # guards the other direction -- a wrapper AHEAD of the plugin is left
      # alone, because regenerating it would install OLDER logic.
      if pp_template_is_newer "$have" "$CURRENT_VERSION"; then
        AHEAD_HOOKS="${AHEAD_HOOKS:+$AHEAD_HOOKS, }$h ($have)"
      elif [ -x "$INSTALLER" ] && "$INSTALLER" -C "$CWD" >/dev/null 2>&1 \
           && grep -q "^# path-privacy:wrapper-version $CURRENT_VERSION\$" "$f" 2>/dev/null; then
        REFRESHED_HOOKS="${REFRESHED_HOOKS:+$REFRESHED_HOOKS, }$h ($have -> $CURRENT_VERSION)"
      else
        STALE_HOOKS="${STALE_HOOKS:+$STALE_HOOKS, }$h ($have)"
      fi
    fi
  done
fi
if [ -n "$MISSING_HOOKS" ]; then
  CONTEXT+="path-privacy: the commit gate is NOT installed in this repo (missing: $MISSING_HOOKS)."$'\n'
  CONTEXT+="The rule below still applies, but nothing is enforcing it here -- follow it by hand."$'\n'
  CONTEXT+="Install with: install-git-hooks.sh (or /path-privacy:path-privacy)."$'\n'
  CONTEXT+="Mention this to the user once, then carry on; do not install it yourself unasked."$'\n'
fi
if [ -n "$STALE_HOOKS" ]; then
  CONTEXT+="path-privacy: this repo's git hooks were generated by an older version of the plugin"
  # Plain ASCII punctuation here on purpose. This line used $'\u2014', but
  # \uXXXX needs bash 4.2+ and macOS ships bash 3.2, so the escape passed
  # through unexpanded and the notice literally read "... of the plugin \u2014
  # pre-commit (0.6.2)". Nothing downstream needs a dash, so the encoding
  # question is removed rather than answered.
  CONTEXT+=": $STALE_HOOKS; current is $CURRENT_VERSION."$'\n'
  CONTEXT+="Their logic is frozen at install time, and an automatic refresh was attempted and FAILED."$'\n'
  CONTEXT+="Something is blocking the rewrite -- a read-only .git, a core.hooksPath pointing elsewhere,"$'\n'
  CONTEXT+="or a missing installer. Mention it to the user once; do not rewrite the hooks yourself."$'\n'
fi
if [ -n "$REFRESHED_HOOKS" ]; then
  CONTEXT+="path-privacy: refreshed this repo's frozen git hooks to the current wrapper template"
  CONTEXT+=" ($REFRESHED_HOOKS). No action needed."$'\n'
fi
if [ -n "$AHEAD_HOOKS" ]; then
  CONTEXT+="path-privacy: this repo's git hooks are NEWER than the running plugin"
  CONTEXT+=": $AHEAD_HOOKS; running plugin is $CURRENT_VERSION."$'\n'
  CONTEXT+="The gate itself is fine -- it is the installed plugin that is behind."$'\n'
  CONTEXT+="Do NOT re-run install-git-hooks.sh: it would regenerate the hooks from the"$'\n'
  CONTEXT+="older plugin and downgrade them. Update the plugin instead"
  CONTEXT+=$' ('"claude plugin update path-privacy)."$'\n'
  CONTEXT+="Mention this to the user once, then carry on."$'\n'
fi
# -----------------------------------------------------------------------------

# Each directive file has "# trigger: <signal>" on line 1. Trigger 'git' fires
# when inside a git repo (the check above already enforced this). Other triggers
# can be added later (e.g., 'history' if a leak in history is detected).
for f in "$SCRIPT_DIR"/directives/*.md; do
  [ -f "$f" ] || continue
  trigger=$(head -1 "$f" | sed 's/^# trigger: //')
  case "$trigger" in
    git|any) ;;
    *)        continue ;;
  esac
  [ -n "$CONTEXT" ] && CONTEXT+=$'\n'
  # Drop the file-level opt-out marker on the way out. A directive that explains
  # the rule necessarily contains path-shaped prose -- this one names the
  # home-directory variable while defining what a leak is -- so the SOURCE file
  # has to carry the marker or the plugin blocks its own directive. The EMISSION
  # needs nothing of the kind, and until now the marker rode along as the first
  # line of every injected block, since `tail -n +2` strips only the trigger
  # line above it.
  # Anchored on purpose: a line that merely mentions the marker in prose (a
  # future directive documenting the escape hatch) survives, and only a line
  # whose LEADING content is the marker is dropped.
  CONTEXT+=$(tail -n +2 "$f" | pp_filter_skip_marker_lines)
done

[ -z "$CONTEXT" ] && exit 0

# Attribution, stated rather than inherited. `hook_additional_context` transcript
# records carry only the EVENT name, so an injected block cannot otherwise be
# traced back to the plugin that produced it. This hook used to get that for free
# from the skip-file marker filtered out above -- a coincidence that read as a
# stray comment and broke the moment the marker was removed. Same bracket form
# dev-conventions emits, so the two are greppable together.
JSON_CONTEXT=$(printf '[plugin:path-privacy]\n%s' "$CONTEXT" | jq -Rs '.')

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF

exit 0
