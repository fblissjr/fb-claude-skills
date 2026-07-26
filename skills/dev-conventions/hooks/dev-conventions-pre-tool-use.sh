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

# One jq spawn, not three. This fires on every Bash/Edit/Write call -- measured
# at ~5,000 per project -- so a subprocess saved here is ~10,000 saved overall.
IFS=$'\t' read -r TOOL CWD FILE CMD <<EOF
$(printf '%s' "$IN" | jq -r '[.tool_name // "", .cwd // "", .tool_input.file_path // "", .tool_input.command // ""] | @tsv' 2>/dev/null)
EOF
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

# The head of each command in the pipeline, one per line: split on ;|& , strip
# leading blanks, drop env-var prefixes. Extracted because both rule blocks need
# it and a divergence between two copies of a PARSER is a silent correctness
# bug, unlike the rule blocks themselves, which are deliberately separate.
command_heads() {
  printf '%s' "$1" | tr ';|&' '\n' | sed -e 's/^ *//' -e 's/^[A-Za-z_][A-Za-z0-9_]*=[^ ]* *//'
}

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
  # Scan the head of each command in the pipeline, not the whole string. The
  # phrase appearing as an argument or inside quotes is not a violation:
  # `rg "pip install" .` and `git commit -m "stop using pip install"` are things
  # people legitimately run, and this file's own header argues a false block is
  # worse than a directive the model can weigh in context.
  while IFS= read -r head; do
    [ -n "$head" ] || continue
    case " $head " in *" uv pip "*) continue ;; esac   # uv's own shim is fine
    case " $head " in
      *" pip install "*|*" pip3 install "*|*"-m pip install "*|\
      *" pip uninstall "*|*" pip3 uninstall "*|*"-m pip uninstall "*)
        block "Blocked: this project is uv-managed (uv.lock present); pip would desync it.
  add:     uv add <pkg>          (exact pin for apps: uv add 'pkg==1.2.3')
  remove:  uv remove <pkg>
  install: uv sync
  one-off: uv pip install <pkg>  (uv's own shim, if you really mean it)
Set DEV_CONVENTIONS_ALLOW=1 to override." ;;
    esac
  done <<EOF
$(command_heads "$NORM")
EOF
fi

# --- JS: npm/yarn/pnpm in a bun project ---------------------------------------
# Requires bun.lock AND the absence of a competing lockfile, so a repo that
# genuinely uses both is left alone.
if { [ -f "$root/bun.lock" ] || [ -f "$root/bun.lockb" ]; } && enforced js-package-manager; then
  if [ ! -f "$root/package-lock.json" ] && [ ! -f "$root/yarn.lock" ] && [ ! -f "$root/pnpm-lock.yaml" ]; then
    while IFS= read -r head; do
      [ -n "$head" ] || continue
      case " $head " in
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
    done <<EOF
$(command_heads "$NORM")
EOF
  fi
fi

exit 0
