#!/usr/bin/env bash
# Stop hook: catch kernel/solver drift in explainer-video scenes the moment a
# turn ends, instead of waiting for someone to run smoke.js (which spawns
# Chromium and takes minutes).
#
# WHY Stop AND NOT PostToolUse: updating the kernel means editing 8 files in
# sequence, and parity is legitimately broken after edits 1 through 7. On
# PostToolUse this would fire seven times during correct work, which is exactly
# the "gate that cries wolf gets bypassed" failure this repo already documents.
# By Stop, the multi-file edit is complete and parity genuinely should hold.
#
# Silent unless something is wrong. Exits 0 always -- this is a reminder, not a
# gate; smoke.js is the gate.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$root" ] || exit 0
scenes="$root/skills/explainer-video/skills/explainer-video"
[ -d "$scenes" ] || exit 0

# Only speak up if scene files were actually touched. A clean tree means this
# turn did not edit scenes, and a reminder about them would be pure noise.
dirty=$(git -C "$root" status --porcelain -- \
  "skills/explainer-video/skills/explainer-video/templates/*.html" \
  "skills/explainer-video/skills/explainer-video/examples/*.html" 2>/dev/null)
[ -n "$dirty" ] || exit 0

# Markers are matched as FIXED strings against the full marker, never as a
# loose "KERNEL-END" substring -- a mangled `KERNEL-ENDX` satisfies the loose
# form while the block stops extracting, so the file silently drops out of the
# comparison. smoke.js had exactly that gap; both now anchor the same way.
report_drift() {  # $1=marker-stem  $2=human name
  local stem="$1" name="$2" f h
  local s="/* ==== $stem-START ====" e="/* ==== $stem-END ==== */"
  local -a files=() hashes=()
  for f in "$scenes"/templates/*.html "$scenes"/examples/*.html; do
    [ -e "$f" ] || continue
    # No block at all is legitimate -- 2D scenes carry no solver.
    grep -qF -- "$s" "$f" || continue
    # A half-fenced file is a real problem: it silently drops out of every
    # parity comparison, the one thing the duplicated-block pattern cannot
    # survive.
    if ! grep -qF -- "$e" "$f"; then
      echo "  $(basename "$f") has $stem-START with no well-formed $stem-END"
      echo "    (an unterminated fence is EXCLUDED from parity checks)"
      return 1
    fi
    h=$(awk -v s="$s" -v e="$e" \
          'index($0,s){b=1} b{print} b&&index($0,e){exit}' "$f" \
        | shasum -a256 | cut -d' ' -f1)
    files+=("$(basename "$f")"); hashes+=("$h")
  done
  [ "${#hashes[@]}" -ge 2 ] || return 0
  local uniq
  uniq=$(printf '%s\n' "${hashes[@]}" | sort -u | wc -l | tr -d ' ')
  [ "$uniq" -eq 1 ] && return 0
  echo "  $name blocks differ across these scenes:"
  local i
  for i in "${!files[@]}"; do
    echo "    ${hashes[$i]:0:8}  ${files[$i]}"
  done
  return 1
}

out=$( { report_drift KERNEL "kernel"; report_drift SOLVER "solver"; } 2>/dev/null )
[ -n "$out" ] || exit 0

echo "explainer-video: shared-block drift detected"
echo "$out"
echo "  These blocks are byte-identical by design; smoke.js hard-fails on drift."
echo "  Edit them in ALL scenes or in none."
exit 0
