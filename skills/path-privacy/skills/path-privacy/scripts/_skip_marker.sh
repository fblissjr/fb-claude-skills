#!/usr/bin/env bash
# path-privacy: skip-file
# _skip_marker.sh -- the one definition of what counts as a file-level opt-out.
#
# Sourced by find-external-paths.sh, scrub-paths.sh, and the PreToolUse hook.
# It exists as a library for the same reason `_version_compare.sh` does: this
# logic was written out separately at every call site, and a subtle defect in it
# survived several sweeps because fixing one copy looked like fixing the rule.
#
# THE RULE: a file is exempt when one of its first 30 lines has the marker as its
# LEADING content -- optional indentation, an optional comment introducer, then
# `path-privacy: skip-file`. Anything after the marker on that line is free text,
# so the `marker -- why this file is exempt` idiom keeps working and is the form
# to prefer.
#
# WHY ANCHORED, which is the whole point of this file: matching the token
# anywhere on a line means any file that merely *discusses* the marker exempts
# itself from the audit. That is not hypothetical -- it is how the repo's own
# CHANGELOG silently left the gate, twice. The first fix narrowed the search to
# the first 30 lines, which helps every file except the ones most likely to
# describe the marker: skill docs and changelogs, which grow from the top and
# push their newest prose straight into the window. Anchoring fixes the class,
# because prose that mentions the marker always has sentence before it.
#
# The failure direction is what makes this worth the file. A broken exemption is
# loud -- the gate blocks something it should not, and you go look. A working
# exemption is indistinguishable from a file with nothing to hide.

# Kept as a separate constant so the literal appears once. Note it is NOT
# anchored on its own; PP_SKIP_MARKER_RE is the thing to match with.
PP_SKIP_MARKER='path-privacy: skip-file'

# ERE, not PCRE: `grep -E` here is BSD grep on macOS as often as GNU, and the
# POSIX class is the portable spelling of \s. Comment introducers cover the
# syntaxes the marker actually appears in across this repo's file types; a
# language whose comment character is missing can still use the bare form,
# since the introducer is optional.
PP_SKIP_MARKER_RE='^[[:space:]]*(<!--|#+|//|--|;|\*)?[[:space:]]*path-privacy: skip-file'

# How many lines from the top are searched. A marker below this is not a marker;
# it is almost certainly a file talking about the marker.
PP_SKIP_MARKER_LINES=30

# pp_head_has_skip_marker <file> -- exempt by inspecting the file on disk.
pp_head_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" "$1" 2>/dev/null | grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_text_has_skip_marker -- same question asked of a string on stdin, for
# callers holding content that is not on disk yet (a Write payload, a new file).
pp_text_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" | grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_is_skip_marker_line -- true when a single line is a marker line rather than
# prose mentioning one. Used to strip markers out of emitted text; the same
# anchoring that decides exemption decides removal, so the two cannot disagree.
pp_is_skip_marker_line() {
  printf '%s\n' "$1" | grep -qE "$PP_SKIP_MARKER_RE"
}
