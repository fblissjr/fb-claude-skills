#!/usr/bin/env bash
# path-privacy: skip-file
# install-git-hooks.sh - install path-privacy git hooks into a repo.
#
# Default behavior: install pre-commit and commit-msg hooks that delegate to the
# scanner. If a hook already exists, the existing hook is preserved by being
# moved to <hook>.local and the new wrapper invokes it first, then runs the
# path-privacy check.
#
# Usage:
#   install-git-hooks.sh                      # install into the current repo
#   install-git-hooks.sh -C <path-to-repo>    # install into a different repo
#   install-git-hooks.sh --uninstall          # restore .local backups, remove wrappers
#   install-git-hooks.sh --doctor             # report this repo's gate, read-only
#   install-git-hooks.sh --doctor <root>      # same, for every repo under <root>
#
# --doctor answers the question the install model otherwise cannot: which repos
# carry the gate, at what version, and is it failing open? Hooks live in .git/,
# so they are per-repo, uncommittable and installed by hand -- there is no
# inventory anywhere. Exit 1 if any repo reports a problem, so it is scriptable.
# It takes an EXPLICIT root and never sweeps your home directory on its own: a
# privacy tool should not decide by itself to enumerate everything you own.

set -eu

TARGET_REPO=""
UNINSTALL=0
DOCTOR=0
DOCTOR_ROOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    -C|--cwd)       TARGET_REPO="$2"; shift 2 ;;
    --uninstall)    UNINSTALL=1; shift ;;
    --doctor)
      DOCTOR=1; shift
      # Optional positional root. Only consumed when it is an existing
      # directory, so `--doctor --uninstall` and a typo'd path both stay errors
      # rather than being silently swallowed as a scan target.
      if [ $# -gt 0 ] && [ -d "$1" ]; then DOCTOR_ROOT="$1"; shift; fi
      ;;
    -h|--help)      sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "install-git-hooks: unknown arg: $1" >&2; exit 2 ;;
  esac
done

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

# Stamp generated wrappers with the plugin version that produced them. Without
# this an old wrapper is indistinguishable from a current one by inspection, so
# nothing -- not the user, not a hook, not a reviewer -- can tell that a repo is
# carrying logic fixed several releases ago.
PLUGIN_JSON="$SELF_DIR/../../../.claude-plugin/plugin.json"
WRAPPER_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" 2>/dev/null | head -1)
[ -z "$WRAPPER_VERSION" ] && WRAPPER_VERSION="unknown"

# One authored copy of the wrapper-vs-plugin comparison, shared by --doctor
# below and injected verbatim into every generated wrapper. If it is missing,
# define the conservative fallback rather than letting an unbound function
# decide a gate: never claim "newer", so every mismatch takes the stale branch,
# whose remedy is idempotent.
VERSION_COMPARE_LIB="$SELF_DIR/_version_compare.sh"
VERSION_COMPARE_SRC='pp_version_is_newer() { return 1; }'
if [ -r "$VERSION_COMPARE_LIB" ]; then
  # shellcheck source=/dev/null
  . "$VERSION_COMPARE_LIB"
  # Same text, captured for injection into the generated wrapper, which is
  # frozen at install time and so cannot source this at run time.
  VERSION_COMPARE_SRC=$(cat "$VERSION_COMPARE_LIB")
else
  eval "$VERSION_COMPARE_SRC"
fi

# --- doctor ------------------------------------------------------------------
# Read-only. Reports one line per wrapper found, and says so plainly when a repo
# has no gate at all -- "no gate" is the finding that matters most, because the
# SessionStart directive keeps asserting the rule either way, so an ungated repo
# looks exactly like a gated one from inside a session.
DOCTOR_RC=0

doctor_repo() {
  local repo="$1"
  local hooks h f ver scanner frozen openness

  hooks=$(git -C "$repo" rev-parse --path-format=absolute --git-path hooks 2>/dev/null || echo "")
  if [ -z "$hooks" ]; then
    printf '%s\n  could not determine hooks directory\n' "$repo"
    DOCTOR_RC=1
    return 0
  fi

  printf '%s\n' "$repo"
  for h in pre-commit commit-msg; do
    f="$hooks/$h"
    # A repo with ONE of the two is not half-gated in any useful sense: the
    # pre-commit hook never sees the message and the commit-msg hook never sees
    # the diff, so whichever is absent is a whole class of leak going unchecked.
    # Say which one, rather than reporting only what happens to be there.
    if [ ! -f "$f" ] || ! grep -q 'path-privacy:wrapper' "$f" 2>/dev/null; then
      printf '  %-11s not installed\n' "$h"
      DOCTOR_RC=1
      continue
    fi
    # No stamp at all means pre-0.6.0, which a version comparison cannot detect.
    # Absence has to be read as "ancient, reinstall", not as "unknown, probably
    # fine" -- those releases are exactly the ones with the fail-open wrapper.
    ver=$(sed -n 's/^# path-privacy:wrapper-version //p' "$f" | head -1)
    [ -z "$ver" ] && ver="<unstamped, pre-0.6.0>"

    # The fail-closed block is the security property that matters. Pre-0.6.0
    # wrappers ended `if [ -x ... ]; then run; fi; exit 0`: scanner missing meant
    # a silent success and a commit allowed with the gate doing nothing.
    if grep -q 'leak gate is NOT running' "$f" 2>/dev/null; then
      openness="fail-closed"
    else
      openness="FAILS OPEN"
      DOCTOR_RC=1
    fi

    scanner=$(sed -n 's/^PATH_PRIVACY_SCRIPT="\(.*\)"$/\1/p' "$f" | head -1)
    if [ -n "$scanner" ] && [ -x "$scanner" ]; then
      frozen="frozen-path ok"
    else
      # Not fatal on its own: every wrapper from 0.3.0 on re-resolves. Reported
      # because on a pre-0.3.0 wrapper it IS fatal, and it is the tell that a
      # plugin update has rotated the cache out from under this repo.
      frozen="frozen-path DEAD"
    fi

    # Direction matters here too. A wrapper NEWER than the plugin doctor is
    # running from is a healthy gate seen from a lagging copy; flagging it and
    # printing the blanket "Fix with: install-git-hooks.sh" would send the user
    # to regenerate that wrapper from the older plugin -- the downgrade this
    # release exists to prevent. Report it, do not fail on it.
    ver_note=""
    if [ "$ver" != "$WRAPPER_VERSION" ]; then
      if pp_version_is_newer "$ver" "$WRAPPER_VERSION"; then
        ver_note="  (newer than this plugin -- gate is fine, do NOT reinstall)"
      else
        DOCTOR_RC=1
      fi
    fi
    printf '  %-11s ver=%-24s %-11s %s%s\n' "$h" "$ver" "$openness" "$frozen" "$ver_note"
  done
  return 0
}

if [ "$DOCTOR" -eq 1 ]; then
  echo "path-privacy doctor -- plugin version $WRAPPER_VERSION"
  echo ""
  if [ -n "$DOCTOR_ROOT" ]; then
    # -maxdepth first: GNU find warns when it follows other primaries. Prune the
    # heavy directories rather than descending them; a vendored dependency tree
    # can hold thousands of entries and none of them is a repo you commit from.
    SEEN=0
    while IFS= read -r gitentry; do
      [ -n "$gitentry" ] || continue
      SEEN=$((SEEN + 1))
      doctor_repo "$(dirname "$gitentry")"
    done < <(find "$DOCTOR_ROOT" -maxdepth 6 \
               \( -name node_modules -o -name .venv -o -name venv \) -prune -o \
               -name .git -print 2>/dev/null | sort)
    # Zero repos found must not read as a clean bill of health. A mistyped root,
    # or one whose repos sit deeper than the depth limit, would otherwise report
    # "all current" -- the same false reassurance this command exists to remove.
    if [ "$SEEN" -eq 0 ]; then
      echo "No git repos found under $DOCTOR_ROOT (searched 6 levels deep)."
      exit 2
    fi
  else
    if [ -z "$TARGET_REPO" ]; then
      TARGET_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    fi
    if [ -z "$TARGET_REPO" ]; then
      echo "install-git-hooks: --doctor with no root must run inside a git repo." >&2
      exit 2
    fi
    doctor_repo "$TARGET_REPO"
  fi
  echo ""
  if [ "$DOCTOR_RC" -eq 0 ]; then
    echo "All reported gates are current and fail closed."
  else
    echo "Findings above. Fix with: install-git-hooks.sh -C <repo>"
  fi
  exit "$DOCTOR_RC"
fi
# -----------------------------------------------------------------------------

if [ -z "$TARGET_REPO" ]; then
  TARGET_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
fi
# `.git` is a FILE in worktrees and submodules, so -d rejected them with a
# misleading "missing" message and no way to install.
if [ -z "$TARGET_REPO" ] || ! git -C "$TARGET_REPO" rev-parse --git-dir >/dev/null 2>&1; then
  echo "install-git-hooks: not a git repo: $TARGET_REPO" >&2
  exit 2
fi

# Ask git where hooks live rather than assembling the path ourselves. This one
# call is correct for every case we previously got wrong by hand: a subdirectory
# of a repo (we used to fabricate a dead .git/hooks under it and report success),
# a worktree or submodule (.git is a FILE there, so mkdir -p died), and any
# core.hooksPath including the tilde form git expands and we did not (we created
# a directory literally named "~" inside the work tree).
HOOKS_DIR=$(git -C "$TARGET_REPO" rev-parse --path-format=absolute --git-path hooks 2>/dev/null || echo "")
if [ -z "$HOOKS_DIR" ]; then
  echo "install-git-hooks: could not determine the hooks directory for $TARGET_REPO" >&2
  exit 2
fi

# A core.hooksPath from GLOBAL config makes a per-repo install machine-wide:
# every repo you own starts running this gate, and --uninstall from any one of
# them mutates that shared state. Refuse rather than surprise.
HOOKS_SCOPE=$(git -C "$TARGET_REPO" config --show-scope --get core.hooksPath 2>/dev/null | awk '{print $1}' || echo "")
if [ -n "$HOOKS_SCOPE" ] && [ "$HOOKS_SCOPE" != "local" ] && [ "$HOOKS_SCOPE" != "worktree" ]; then
  echo "install-git-hooks: core.hooksPath is set in $HOOKS_SCOPE config -> $HOOKS_DIR" >&2
  echo "  Installing there would gate EVERY repo on this machine, and --uninstall" >&2
  echo "  from any repo would remove it for all of them. Refusing." >&2
  echo "  Set a repo-local hooks path first: git -C \"$TARGET_REPO\" config --local core.hooksPath <dir>" >&2
  exit 2
fi

# A hooks dir inside the work tree is usually tracked (.husky/, .githooks/). The
# wrapper embeds this machine's absolute plugin-cache path, so committing it
# would plant the very leak class this plugin polices and hand teammates a dead
# path that fails closed on their machines.
case "$HOOKS_DIR" in
  "$TARGET_REPO"/*)
    if git -C "$TARGET_REPO" ls-files --error-unmatch "$HOOKS_DIR" >/dev/null 2>&1 \
       || [ -n "$(git -C "$TARGET_REPO" ls-files -- "$HOOKS_DIR" 2>/dev/null)" ]; then
      echo "install-git-hooks: $HOOKS_DIR is inside the work tree and tracked by git." >&2
      echo "  The generated wrapper embeds a machine-specific absolute path; committing" >&2
      echo "  it would leak that path and break the hook for everyone else. Refusing." >&2
      exit 2
    fi ;;
esac
mkdir -p "$HOOKS_DIR"

uninstall_one() {
  local name="$1"
  local hook="$HOOKS_DIR/$name"
  local backup="$hook.local"
  if [ -f "$backup" ]; then
    # If the live hook is neither ours nor the backup, the user has written their
    # own since installing. Restoring over it would silently destroy their work.
    if [ -f "$hook" ] && ! grep -q 'path-privacy:wrapper' "$hook" 2>/dev/null; then
      echo "install-git-hooks: $hook is not a path-privacy wrapper." >&2
      echo "  Leaving it alone. Your earlier hook is still at $backup." >&2
      return 0
    fi
    mv "$backup" "$hook"
    echo "restored $hook from $backup"
  elif [ -f "$hook" ] && grep -q 'path-privacy:wrapper' "$hook" 2>/dev/null; then
    rm -f "$hook"
    echo "removed $hook"
  else
    echo "no path-privacy wrapper at $hook (nothing to do)"
  fi
}

if [ $UNINSTALL -eq 1 ]; then
  uninstall_one pre-commit
  uninstall_one commit-msg
  exit 0
fi

install_wrapper() {
  local name="$1"          # pre-commit | commit-msg
  local source_script="$2" # absolute path to the path-privacy script
  local hook="$HOOKS_DIR/$name"
  local backup="$hook.local"

  # If an existing hook is present and is NOT a path-privacy wrapper, back it up.
  if [ -f "$hook" ] && ! grep -q 'path-privacy:wrapper' "$hook" 2>/dev/null; then
    if [ ! -f "$backup" ]; then
      cp "$hook" "$backup"
      chmod +x "$backup"
      echo "preserved existing $hook -> $backup"
    else
      # A .local already exists AND the live hook is not ours -- the user has
      # replaced it since. Overwriting with no copy anywhere loses their work.
      echo "install-git-hooks: $hook is not a path-privacy wrapper and $backup" >&2
      echo "  already exists. Refusing to overwrite; move or remove one of them." >&2
      exit 2
    fi
  fi

  # A hook can be a SYMLINK into the work tree (ln -s ../../scripts/pre-commit.sh
  # is a common pattern). `cat > "$hook"` follows it and writes the wrapper into
  # the user's tracked source file, which they may then commit. Replace the link
  # itself, never write through it. The backup above already captured contents.
  if [ -L "$hook" ]; then
    echo "replacing symlink $hook (target left untouched)"
    rm -f "$hook"
  fi

  cat > "$hook" <<EOF
#!/usr/bin/env bash
# path-privacy:wrapper -- generated by install-git-hooks.sh. Edit .local file instead.
# path-privacy:wrapper-version $WRAPPER_VERSION
set -u
HOOK_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
HOOK_NAME="$(basename "$hook")"
LOCAL_HOOK="\$HOOK_DIR/\$HOOK_NAME.local"
SCRIPT_NAME="$(basename "$source_script")"
PATH_PRIVACY_SCRIPT="$source_script"
WRAPPER_VERSION="$WRAPPER_VERSION"

$VERSION_COMPARE_SRC

FROZEN_ROOT="\${PATH_PRIVACY_SCRIPT%/skills/path-privacy/scripts/*}"
PLUGIN_CACHE="\$HOME/.claude/plugins/cache"  # path-privacy: ignore

# Run the pre-existing hook first, if any.
if [ -x "\$LOCAL_HOOK" ]; then
  "\$LOCAL_HOOK" "\$@" || exit \$?
fi

# Highest version that is ACTUALLY EXECUTABLE, not merely highest. A newest copy
# with the exec bit lost must not shadow a working older one and block every
# commit. Sort by the VERSION component alone -- the 5th field from the right in
# <ver>/skills/path-privacy/scripts/<name> -- because sort -rV over whole paths
# compares the marketplace directory first, so cache/mp-z/0.0.1 beat
# cache/mp-a/9.9.9. And sort -V rather than glob order, which is lexicographic
# and would pick 0.1.9 over 0.1.10.
newest_exec() {
  printf '%s\\n' "\$@" \\
    | awk -F/ 'NF>4 {print \$(NF-4)"\\t"\$0}' \\
    | sort -rV | cut -f2- | {
        while IFS= read -r c; do
          if [ -x "\$c" ]; then printf '%s' "\$c"; break; fi
        done
      }
}

# The path above is frozen at install time; treat it as a HINT, not a pin.
CAND=""
case "\$FROZEN_ROOT" in
  "\$PLUGIN_CACHE"/*/path-privacy/*)
    # Marketplace install. The frozen path is version-stamped, so an update
    # writes a SIBLING version dir and leaves this one intact until cleanup ~14
    # days later. Re-resolving only when the frozen path is GONE therefore keeps
    # running the superseded scanner for that entire window: the gate silently
    # trails the installed plugin and self-corrects only as a side effect of
    # garbage collection. So resolve to the newest version on every run.
    #
    # Scoped to this marketplace's own path-privacy directory, never across
    # marketplaces: two marketplaces shipping a plugin of the same name are
    # unrelated packages, and one's version number says nothing about the
    # other's. Sibling VERSIONS are safe to prefer; sibling PUBLISHERS are not.
    CAND="\$(newest_exec "\${FROZEN_ROOT%/*}"/*/skills/path-privacy/scripts/"\$SCRIPT_NAME")"
    ;;
  *)
    # Local checkout or --plugin-dir install. Nothing rotates it, so the frozen
    # path stays authoritative while it works -- silently moving such a user to
    # a cached marketplace copy would run code they did not install.
    if [ -x "\$PATH_PRIVACY_SCRIPT" ]; then
      CAND="\$PATH_PRIVACY_SCRIPT"
    else
      # Last-resort recovery, only once their own copy is gone. Searches the
      # cache by version; never the frozen path's PARENT, which reached every
      # neighbouring project on disk, so a broken checkout silently ran an
      # unrelated adjacent project's scanner -- arbitrary sibling repo code, or
      # on a shared machine another user's, executed as a commit gate. That glob
      # also matched <plugin>.backup snapshots, which sort ABOVE the real one.
      CAND="\$(newest_exec "\$PLUGIN_CACHE"/*/path-privacy/*/skills/path-privacy/scripts/"\$SCRIPT_NAME")"
    fi
    ;;
esac
[ -n "\$CAND" ] && PATH_PRIVACY_SCRIPT="\$CAND"

# Fail CLOSED and loudly. This hook is a leak gate; if it cannot run, allowing
# the commit silently is the worst outcome -- that is how a gate becomes
# decorative without anyone noticing.
if [ ! -x "\$PATH_PRIVACY_SCRIPT" ]; then
  echo "path-privacy: scanner not found -- the leak gate is NOT running." >&2
  echo "" >&2
  echo "  Why now: this usually means the plugin was updated and the old cached" >&2
  echo "  copy has since been cleaned up. It fires on the next commit after that," >&2
  echo "  which is why it looks unrelated to what you are committing." >&2
  echo "" >&2
  echo "  Looked for: \$SCRIPT_NAME under" >&2
  echo "    \${FROZEN_ROOT:-<install dir>}/ and \$PLUGIN_CACHE/*/path-privacy/*/" >&2
  echo "  Reinstall:  /path-privacy:path-privacy   (or re-run install-git-hooks.sh)" >&2
  if [ -f "\$LOCAL_HOOK" ]; then
    # This wrapper CHAINS your previous hook. Deleting it would silently drop
    # that hook too, so restore it rather than remove the wrapper.
    echo "  Remove:     mv \$LOCAL_HOOK \$HOOK_DIR/\$HOOK_NAME" >&2
    echo "              (restores the \$HOOK_NAME hook you had before path-privacy)" >&2
  else
    echo "  Remove:     rm \$HOOK_DIR/\$HOOK_NAME" >&2
  fi
  exit 1
fi

# This wrapper's own logic is frozen at install time and NOTHING rewrites it --
# it is the thing that locates the plugin, so the plugin cannot update it. A
# wrapper bug fixed in a later release therefore stays live here forever, and
# pre-0.6.0 wrappers FAIL OPEN: scanner missing meant a silent exit 0, commit
# allowed, no message. That is not detectable from the outside, so say it out
# loud, once per commit, rather than leave the repo quietly running old logic.
# Reported, never auto-applied: rewriting a file in someone's .git/ mid-commit
# is exactly the surprise a privacy gate should not spring.
RESOLVED_ROOT="\${PATH_PRIVACY_SCRIPT%/skills/path-privacy/scripts/*}"
RESOLVED_VERSION=\$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p' \\
                   "\$RESOLVED_ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)
if [ -n "\$RESOLVED_VERSION" ] && [ "\$RESOLVED_VERSION" != "\$WRAPPER_VERSION" ]; then
  if pp_version_is_newer "\$WRAPPER_VERSION" "\$RESOLVED_VERSION"; then
    echo "path-privacy: this \$HOOK_NAME hook (\$WRAPPER_VERSION) is NEWER than the resolved plugin (\$RESOLVED_VERSION)." >&2
    echo "  The gate is fine; the plugin is behind. Do NOT re-run install-git-hooks.sh -- it would" >&2
    echo "  regenerate this hook from the older plugin. Update the plugin instead." >&2
  else
    echo "path-privacy: this \$HOOK_NAME hook was generated by \$WRAPPER_VERSION; plugin is now \$RESOLVED_VERSION." >&2
    echo "  Wrapper logic is frozen at install time. Re-run install-git-hooks.sh to refresh it." >&2
  fi
fi

"\$PATH_PRIVACY_SCRIPT" "\$@" || exit \$?
exit 0
EOF
  chmod +x "$hook"
  echo "installed $hook"
}

install_wrapper pre-commit "$SELF_DIR/git-pre-commit"
install_wrapper commit-msg "$SELF_DIR/git-commit-msg"

echo ""
echo "path-privacy hooks installed in $TARGET_REPO."
echo "To uninstall: $0 --uninstall"
