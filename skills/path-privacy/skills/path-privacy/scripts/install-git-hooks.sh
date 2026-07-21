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

set -eu

TARGET_REPO=""
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    -C|--cwd)       TARGET_REPO="$2"; shift 2 ;;
    --uninstall)    UNINSTALL=1; shift ;;
    -h|--help)      sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "install-git-hooks: unknown arg: $1" >&2; exit 2 ;;
  esac
done

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

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

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
set -u
HOOK_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
HOOK_NAME="$(basename "$hook")"
LOCAL_HOOK="\$HOOK_DIR/\$HOOK_NAME.local"
SCRIPT_NAME="$(basename "$source_script")"
PATH_PRIVACY_SCRIPT="$source_script"

# Run the pre-existing hook first, if any.
if [ -x "\$LOCAL_HOOK" ]; then
  "\$LOCAL_HOOK" "\$@" || exit \$?
fi

# The path above is frozen at install time. For a marketplace install it points
# into the VERSION-STAMPED plugin cache: an update writes a new version dir and
# orphans the old one, deleted 14 days later, so the path dies on a 14-day fuse.
# Re-resolve to the newest copy. sort -V, not last-wins over glob order, which is
# lexicographic and would pick 0.1.9 over 0.1.10.
if [ ! -x "\$PATH_PRIVACY_SCRIPT" ]; then
  # Search the frozen path's own tree first, so a LOCAL checkout or --plugin-dir
  # install (whose scripts never live under the plugin cache) can still recover.
  FROZEN_ROOT="\${PATH_PRIVACY_SCRIPT%/skills/path-privacy/scripts/*}"
  # Highest version that is ACTUALLY EXECUTABLE, not merely highest. A newest
  # copy with the exec bit lost must not shadow a working older one and block
  # every commit.
  newest_exec() {
    printf '%s\\n' "\$@" | sort -rV | {
      while IFS= read -r c; do
        if [ -x "\$c" ]; then printf '%s' "\$c"; break; fi
      done
    }
  }
  # Group 1 is the frozen tree ITSELF, never its siblings. Globbing the parent
  # (\${FROZEN_ROOT%/*}/*/...) reached every neighbouring project on disk, so a
  # broken local checkout at ~/dev/plugin-a silently ran ~/dev/plugin-zzz's
  # scanner -- an arbitrary sibling repo's code, or on a shared machine another
  # user's, executed as a commit gate. It also matched <plugin>.backup snapshot
  # directories, which sort ABOVE the real one.
  CAND="\$(newest_exec "\$FROZEN_ROOT"/skills/path-privacy/scripts/"\$SCRIPT_NAME")"
  # Group 2 is the version-stamped cache, which is what actually rotates. Sort by
  # the VERSION component alone: sort -rV over whole paths compares the
  # marketplace directory first, so cache/mp-z/0.0.1 beat cache/mp-a/9.9.9.
  if [ -z "\$CAND" ]; then
    for _v in \$(ls -1 "\$HOME"/.claude/plugins/cache/*/path-privacy/ 2>/dev/null | sort -rV -u); do
      for _c in "\$HOME"/.claude/plugins/cache/*/path-privacy/"\$_v"/skills/path-privacy/scripts/"\$SCRIPT_NAME"; do
        if [ -x "\$_c" ]; then CAND="\$_c"; break 2; fi
      done
    done
  fi
  [ -n "\$CAND" ] && PATH_PRIVACY_SCRIPT="\$CAND"
fi

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
  echo "    \${FROZEN_ROOT:-<install dir>}/ and \$HOME/.claude/plugins/cache/*/path-privacy/*/" >&2
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
