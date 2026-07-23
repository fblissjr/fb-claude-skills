#!/usr/bin/env bash
# Stop hook: report explainer-video marker drift and template damage at the end
# of a turn, instead of waiting for someone to run the full gate (which spawns
# Chromium and takes minutes).
#
# THIS FILE DELIBERATELY CONTAINS NO PARITY LOGIC. It calls
# `smoke.js --parity-only`, which is the same code the real gate runs. The
# first version of this hook reimplemented the check in bash and had already
# diverged from smoke.js on day one -- it dropped a file with a mangled
# `KERNEL-STARTX` marker out of the comparison in total silence, which is the
# exact self-exemption bug the check exists to catch, and the exact
# two-copies-drift failure the marker fences exist to prevent. Keep it a
# wrapper. If the check needs to change, change it in smoke.js.
#
# WHY Stop AND NOT PostToolUse: a kernel edit touches eight files and parity is
# legitimately broken after the first seven, so PostToolUse would cry wolf
# through every correct multi-file edit, and a gate that cries wolf gets
# bypassed. By Stop the edit is complete and parity genuinely should hold.
#
# Runs on EVERY stop, with no working-tree precondition. An earlier version
# only ran when scene files were dirty, which sounded frugal and silently
# defeated the whole hook: this repo commits at the end of a turn, so the tree
# was clean exactly when the check mattered most and it never fired.
#
# Silent on success. Exits 0 always -- a reminder, not a gate; smoke.js is the
# gate.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$root" ] || exit 0
scenes="$root/skills/explainer-video/skills/explainer-video"
[ -d "$scenes" ] || exit 0

# Repo-relative paths, run from the repo root: the output is easier to read and
# no absolute path can end up quoted into a commit or a doc by a later reader.
cd "$root" || exit 0
rel="skills/explainer-video/skills/explainer-video"
files=()
for f in "$rel"/templates/*.html "$rel"/examples/*.html; do
  [ -e "$f" ] && files+=("$f")
done
[ "${#files[@]}" -gt 0 ] || exit 0

out=$(node "$rel/templates/smoke.js" --parity-only "${files[@]}" 2>&1) || {
  echo "explainer-video: scene integrity check"
  # Drop the trailing status line; the FAIL lines above it carry the detail.
  echo "$out" | grep -v '^parity/integrity:' | sed 's/^/  /'
  echo "  Marked blocks are byte-identical by design and templates stay small."
  echo "  Full gate: bun run smoke.js (spawns Chromium)."
}
exit 0
