#!/usr/bin/env bash
# path-privacy: skip-file
# path-privacy SessionStart. Keeps this repo's frozen git hook wrappers
# current, and says something only when there is something to act on.
# In a repo whose gate is installed and current it emits NOTHING (or `{}` on
# Antigravity).
#
# Dual-harness: auto-detects Antigravity (`workspacePaths` / `conversationId`
# in stdin JSON) vs Claude Code (`cwd` in stdin JSON).

PAYLOAD=$(cat)
if ! command -v jq >/dev/null 2>&1; then
  case "$PAYLOAD" in
    *'"workspacePaths"'*|*'"conversationId"'*) printf '{}\n' ;;
  esac
  exit 0
fi

HARNESS="claude"
if jq -e 'has("workspacePaths") or has("conversationId")' <<<"$PAYLOAD" >/dev/null 2>&1; then
  HARNESS="antigravity"
fi

emit_empty() {
  if [ "$HARNESS" = "antigravity" ]; then
    printf '{}\n'
  fi
  exit 0
}

CWD=$(jq -r '.workspacePaths[0] // .cwd // ""' <<<"$PAYLOAD" 2>/dev/null)

if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
  emit_empty
fi

pp_git() {
  git "$@" 2>/dev/null || GIT_CONFIG_GLOBAL=/dev/null git "$@" 2>/dev/null
}

# Only inject when inside a git working tree
if ! pp_git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null; then
  emit_empty
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd || echo "$SCRIPT_DIR/..")"
CONTEXT=""

# Shared with install-git-hooks.sh and every generated wrapper. Absent copy
# means never claim "newer", which routes every mismatch to the stale branch --
# the branch whose advice is idempotent.
VERSION_COMPARE_LIB="$PLUGIN_ROOT/skills/path-privacy/scripts/_version_compare.sh"
if [ -r "$VERSION_COMPARE_LIB" ]; then
  # shellcheck source=/dev/null
  . "$VERSION_COMPARE_LIB"
else
  pp_version_is_newer() { return 1; }
  pp_template_is_newer() { return 1; }
fi

# Where the gate lives, shared with the installer. Absent copy: the old plain
# `--git-path hooks`, which misses a gate behind a chaining dispatcher.
HOOKS_DIR_LIB="$PLUGIN_ROOT/skills/path-privacy/scripts/_hooks_dir.sh"
if [ -r "$HOOKS_DIR_LIB" ]; then
  # shellcheck source=/dev/null
  . "$HOOKS_DIR_LIB"
else
  pp_hooks_dir() { pp_git -C "$1" rev-parse --path-format=absolute --git-path hooks; }
fi

# --- outdated-wrapper notice -------------------------------------------------
HOOKS_DIR=$(pp_hooks_dir "$CWD" || echo "")
INSTALLER="$PLUGIN_ROOT/skills/path-privacy/scripts/install-git-hooks.sh"
CURRENT_VERSION=$(sed -n 's/^WRAPPER_TEMPLATE_VERSION=\(.*\)$/t\1/p' "$INSTALLER" 2>/dev/null | head -1)
STALE_HOOKS=""
AHEAD_HOOKS=""
MISSING_HOOKS=""
REFRESHED_HOOKS=""
CANDIDATE_STALE=0
PRE_VER=""
MSG_VER=""

if [ -n "$HOOKS_DIR" ] && [ -n "$CURRENT_VERSION" ]; then
  # Pass 1: classify both hooks before running the installer so a stale hook
  # never triggers an install that overwrites an AHEAD sibling hook or
  # misreports missing/stale state.
  for h in pre-commit commit-msg; do
    f="$HOOKS_DIR/$h"
    if [ ! -f "$f" ] || ! grep -q 'path-privacy:wrapper' "$f" 2>/dev/null; then
      MISSING_HOOKS="${MISSING_HOOKS:+$MISSING_HOOKS, }$h"
      continue
    fi
    have=$(sed -n 's/^# path-privacy:wrapper-version //p' "$f" | head -1)
    [ -z "$have" ] && have="pre-0.6.0"
    if [ "$h" = "pre-commit" ]; then PRE_VER="$have"; else MSG_VER="$have"; fi
    if [ "$have" != "$CURRENT_VERSION" ]; then
      if pp_template_is_newer "$have" "$CURRENT_VERSION"; then
        AHEAD_HOOKS="${AHEAD_HOOKS:+$AHEAD_HOOKS, }$h ($have)"
      else
        CANDIDATE_STALE=1
      fi
    fi
  done

  # Pass 2: if at least one hook is stale and neither is ahead or missing,
  # attempt a single refresh of the repo's hooks.
  if [ "$CANDIDATE_STALE" -eq 1 ]; then
    REFRESH_OK=0
    if [ -z "$AHEAD_HOOKS" ] && [ -z "$MISSING_HOOKS" ] && [ -r "$INSTALLER" ] \
       && bash "$INSTALLER" -C "$CWD" >/dev/null 2>&1; then
      REFRESH_OK=1
    fi
    for h in pre-commit commit-msg; do
      if [ "$h" = "pre-commit" ]; then have="$PRE_VER"; else have="$MSG_VER"; fi
      [ -z "$have" ] && continue
      if [ "$have" != "$CURRENT_VERSION" ] && ! pp_template_is_newer "$have" "$CURRENT_VERSION"; then
        f="$HOOKS_DIR/$h"
        if [ "$REFRESH_OK" -eq 1 ] && grep -q "^# path-privacy:wrapper-version $CURRENT_VERSION\$" "$f" 2>/dev/null; then
          REFRESHED_HOOKS="${REFRESHED_HOOKS:+$REFRESHED_HOOKS, }$h ($have -> $CURRENT_VERSION)"
        else
          STALE_HOOKS="${STALE_HOOKS:+$STALE_HOOKS, }$h ($have)"
        fi
      fi
    done
  fi
fi

if [ -n "$MISSING_HOOKS" ]; then
  COMMON_DIR=$(pp_git -C "$CWD" rev-parse --path-format=absolute --git-common-dir || echo "")
  NOTICE_MARK="${COMMON_DIR:+$COMMON_DIR/path-privacy-gate-notice}"
  if [ -n "$NOTICE_MARK" ] && [ ! -e "$NOTICE_MARK" ]; then
    if [ "$HARNESS" = "antigravity" ]; then
      CONTEXT+="path-privacy: no commit gate in this repo (missing: $MISSING_HOOKS). Antigravity's edits and git/gh commands are still checked; commits made outside the agent are not. Run the path-privacy install-git-hooks.sh script to install it. This notice is shown once per repo."$'\n'
    else
      CONTEXT+="path-privacy: no commit gate in this repo (missing: $MISSING_HOOKS). Claude's edits and commit messages are still checked; commits made outside Claude are not. Installer: /path-privacy:path-privacy. This notice is shown once per repo."$'\n'
    fi
    ( : > "$NOTICE_MARK" ) 2>/dev/null || true
  fi
fi
if [ -n "$STALE_HOOKS" ]; then
  CONTEXT+="path-privacy: this repo's git hooks were generated by an older version of the plugin"
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
  HARNESS_LABEL="Claude Code"
  [ "$HARNESS" = "antigravity" ] && HARNESS_LABEL="Antigravity"
  CONTEXT+="path-privacy: this repo's git hooks ($AHEAD_HOOKS) are NEWER than the running $HARNESS_LABEL plugin ($CURRENT_VERSION)."$'\n'
  CONTEXT+="The commit gate itself is fine -- this $HARNESS_LABEL plugin copy is behind the sibling harness that updated the hooks."$'\n'
  CONTEXT+="Do NOT re-run install-git-hooks.sh from this older copy (it would downgrade the hooks)."$'\n'
  CONTEXT+="To align both harnesses, run sync-peer.sh --install from the newer checkout (or update this plugin). Mention this to the user once, then carry on."$'\n'
fi
# -----------------------------------------------------------------------------

[ -z "$CONTEXT" ] && emit_empty

JSON_CONTEXT=$(printf '[plugin:path-privacy]\n%s' "$CONTEXT" | jq -Rs '.')

if [ "$HARNESS" = "antigravity" ]; then
  cat <<EOF
{
  "injectSteps": [
    {
      "systemMessage": {
        "systemMessage": ${JSON_CONTEXT}
      }
    }
  ]
}
EOF
else
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${JSON_CONTEXT}
  }
}
EOF
fi

exit 0
