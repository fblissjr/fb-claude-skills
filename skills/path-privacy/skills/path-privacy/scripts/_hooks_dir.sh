# shellcheck shell=bash
# _hooks_dir.sh - sourced by install-git-hooks.sh and the SessionStart hook.
# Where this repo's pre-commit and commit-msg gate lives.
#
# Usually that is `git rev-parse --git-path hooks`, which already follows
# core.hooksPath, worktrees and submodules. The exception is a hooks directory
# set as a global core.hooksPath that runs each repo's own
# <git-common-dir>/hooks/<name> from every hook. There `--git-path hooks` names
# the shared dispatcher, so the installer refused to write into it (that would
# gate every repo) and SessionStart reported a gated repo as ungated.
#
# Such a dispatcher declares itself with a file named `.chains-to-repo-hooks`.
# The declaration is trusted only when the dispatcher also has executable
# pre-commit and commit-msg hooks: git runs only hook names present in
# core.hooksPath, so without them a repo's own gate never runs. Whether those
# hooks really chain is the dispatcher's promise; nothing here can check it.

pp_chains_to_repo_hooks() { # <hooks dir>
  local h
  [ -f "$1/.chains-to-repo-hooks" ] || return 1
  for h in pre-commit commit-msg; do
    [ -x "$1/$h" ] || return 1
  done
}

pp_hooks_dir() { # <repo>
  local hooks common
  hooks=$(git -C "$1" rev-parse --path-format=absolute --git-path hooks 2>/dev/null) || return 1
  [ -n "$hooks" ] || return 1
  if pp_chains_to_repo_hooks "$hooks"; then
    common=$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
    hooks="$common/hooks"
  fi
  printf '%s\n' "$hooks"
}
