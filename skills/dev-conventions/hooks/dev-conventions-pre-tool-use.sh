#!/usr/bin/env bash
# dev-conventions PreToolUse enforcement.
#
# Blocks the small set of convention violations that can be detected
# mechanically, so they stop occupying the always-loaded tier as prose. Upstream
# is explicit that prose is advisory and hooks are not: "Claude treats them as
# context, not enforced configuration. To block an action regardless of what
# Claude decides, use a PreToolUse hook instead."
#
# What it blocks, and only when the project actually says so:
#   * pip / pip3 / python -m pip install   -- only where uv.lock exists
#   * npm / yarn / pnpm install            -- only where bun.lock exists and no
#                                             package-lock.json / yarn.lock does
#   * edits to uv.lock / bun.lock          -- always; both are generated
#
# Detection gating is the whole safety story. A blanket "never run pip" would
# fire inside a Dockerfile, a CI script, or a repo that legitimately uses pip,
# and a false block is far more disruptive than a directive the model can weigh
# in context. So every rule requires positive evidence from the project itself.
#
# The `if` field in hooks.json is an optimisation, NOT the boundary: upstream
# warns the filter "fails open, running your hook regardless of pattern, when
# the Bash command can't be parsed", and advises the permission system rather
# than a hook matcher for hard allow/deny. All real decisions are made here,
# from the parsed tool_input.
#
# Escape hatch: DEV_CONVENTIONS_ALLOW=1 in the environment disables every block.
#
# Silent on the passing path (exit 0, no output). Blocks with exit 2 and a
# stderr message naming the correct command, because a block the model cannot
# act on just becomes a retry loop.

set -u

[ "${DEV_CONVENTIONS_ALLOW:-0}" = "1" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0
IN=$(cat 2>/dev/null) || exit 0
[ -n "$IN" ] || exit 0

TOOL=$(printf '%s' "$IN" | jq -r '.tool_name // ""' 2>/dev/null)
CWD=$(printf '%s' "$IN" | jq -r '.cwd // ""' 2>/dev/null)
[ -n "$CWD" ] && cd "$CWD" 2>/dev/null

# Walk up for a project marker; hooks can fire from a subdirectory.
root=""
d=$(pwd -P 2>/dev/null) || exit 0
while [ "$d" != "/" ]; do
  if [ -f "$d/uv.lock" ] || [ -f "$d/bun.lock" ] || [ -d "$d/.git" ]; then root="$d"; break; fi
  d=$(dirname "$d")
done
[ -n "$root" ] || exit 0

block() { printf '%s\n' "$1" >&2; exit 2; }

# Per-repo overrides. The plugin ships the defaults -- uv for Python, bun for
# JS -- and a repo that genuinely differs says so in a tracked file rather than
# reaching for DEV_CONVENTIONS_ALLOW=1, which disables everything everywhere for
# one call. Omitted keys stay enabled, so the file only ever states exceptions.
CFG="$root/.dev-conventions.json"
enforced() {
  [ -f "$CFG" ] || return 0
  # NOT `.enforce[$k] // empty`: jq's `//` treats `false` as absent, so the
  # alternative fires on exactly the value this check exists to read, and every
  # override silently did nothing. Ask whether the key is present, then read it.
  v=$(jq -r --arg k "$1" \
      'if (.enforce? | type) == "object" and (.enforce | has($k))
       then (.enforce[$k] | tostring) else "" end' "$CFG" 2>/dev/null)
  [ "$v" = "false" ] && return 1
  return 0
}

# --- Lockfile edits -----------------------------------------------------------
if [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ] || [ "$TOOL" = "NotebookEdit" ]; then
  FILE=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
  enforced lockfile-edits || exit 0
  case "$(basename "${FILE:-}")" in
    uv.lock)
      block "Blocked: uv.lock is generated, not edited.
Change the dependency in pyproject.toml, then run \`uv lock\` (or \`uv add <pkg>\`).
Verify with \`uv lock --check\`. Set DEV_CONVENTIONS_ALLOW=1 to override." ;;
    bun.lock|bun.lockb)
      block "Blocked: bun.lock is generated, not edited.
Change the dependency in package.json, then run \`bun install\`.
Set DEV_CONVENTIONS_ALLOW=1 to override." ;;
  esac
  exit 0
fi

[ "$TOOL" = "Bash" ] || exit 0
CMD=$(printf '%s' "$IN" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -n "$CMD" ] || exit 0

# Normalise: collapse whitespace so `pip   install` and `pip\ninstall` match.
NORM=$(printf '%s' "$CMD" | tr '\n\t' '  ' | tr -s ' ')

# --- Python: pip in a uv project ----------------------------------------------
# Requires uv.lock. A pyproject.toml alone is not evidence -- plenty of pip
# projects have one.
if [ -f "$root/uv.lock" ] && enforced python-package-manager; then
  case " $NORM " in
    *" pip install "*|*" pip3 install "*|*"-m pip install "*|\
    *" pip uninstall "*|*" pip3 uninstall "*|*"-m pip uninstall "*)
      # `uv pip install` is uv's own compatibility shim and is fine.
      case " $NORM " in *" uv pip "*) exit 0 ;; esac
      block "Blocked: this project is uv-managed (uv.lock present); pip would desync it.
  add:     uv add <pkg>          (exact pin for apps: uv add 'pkg==1.2.3')
  remove:  uv remove <pkg>
  install: uv sync
  one-off: uv pip install <pkg>  (uv's own shim, if you really mean it)
Set DEV_CONVENTIONS_ALLOW=1 to override." ;;
  esac
fi

# --- JS: npm/yarn/pnpm in a bun project ---------------------------------------
# Requires bun.lock AND the absence of a competing lockfile, so a repo that
# genuinely uses both is left alone.
if { [ -f "$root/bun.lock" ] || [ -f "$root/bun.lockb" ]; } && enforced js-package-manager; then
  if [ ! -f "$root/package-lock.json" ] && [ ! -f "$root/yarn.lock" ] && [ ! -f "$root/pnpm-lock.yaml" ]; then
    case " $NORM " in
      *" npm install "*|*" npm i "*|*" npm add "*|*" npm ci "*|*" npm uninstall "*|\
      *" yarn add "*|*" yarn install "*|*" yarn remove "*|\
      *" pnpm add "*|*" pnpm install "*|*" pnpm remove "*)
        block "Blocked: this project is bun-managed (bun.lock present, no competing lockfile).
  add:     bun add <pkg>       (exact pin for apps: bun add pkg@1.2.3)
  remove:  bun remove <pkg>
  install: bun install
  run:     bun run <script> / bunx <tool>
Set DEV_CONVENTIONS_ALLOW=1 to override." ;;
    esac
  fi
fi

exit 0
