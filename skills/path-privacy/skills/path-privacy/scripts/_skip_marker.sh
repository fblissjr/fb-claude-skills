#!/usr/bin/env bash
# path-privacy: skip-file
# _skip_marker.sh -- the one definition of what counts as a file-level opt-out.
#
# Sourced by find-external-paths.sh, scrub-paths.sh, and both hooks. It is a
# library for the same reason `_version_compare.sh` is: this logic was written
# out separately at every call site, and a defect in it survived being "fixed"
# because repairing one copy looks exactly like repairing the rule.
#
# THE RULE: a file is exempt when one of its first 30 lines has the marker as its
# LEADING content -- at most three spaces of indent, an optional comment
# introducer, then `path-privacy: skip-file`. Anything after the marker on that
# line is free text, so `marker -- why this file is exempt` works and is the form
# to prefer.
#
# WHY EACH RESTRICTION EXISTS. Every one of them was reached by a real bypass,
# so widening any of them needs a better reason than "it would be convenient":
#
#   Anchored at all, rather than matching the token anywhere on the line.
#   Otherwise a file that merely *discusses* the marker exempts itself from the
#   audit. That is not hypothetical -- this repo's own CHANGELOG left the gate
#   that way twice, the second time in the entry documenting the first fix.
#
#   A single `#`, not `#+`. `## path-privacy: skip-file` is an ordinary markdown
#   H2. Allowing repeated `#` let any doc with a section heading named after the
#   marker silently un-gate itself, which is the same class the anchoring exists
#   to close, arriving through a door the anchoring opened.
#
#   No `*`. That is a markdown bullet, so `* path-privacy: skip-file exempts a
#   file` -- a sentence in a feature list -- was a working opt-out.
#
#   At most three spaces of indent. Four spaces (or a tab) is markdown's own
#   boundary for an indented code block, i.e. a doc *demonstrating* the marker.
#
# What is deliberately still reachable: a fenced code block, which is not
# indented, can hold a line that is a valid marker. There is no regex that both
# accepts a marker and rejects documentation quoting one, because they are the
# same string. That residue is why `check_marker_denylist` in skill-maintainer
# asserts the file classes this keeps happening to -- changelogs and skill docs
# -- are never exempt. The rule narrows the hole; the deny-list is what closes it.
#
# The failure direction is what makes this worth a file of its own. A broken
# exemption is loud: the gate blocks something it should not and you go look. A
# working exemption is indistinguishable from a file with nothing to hide.

# ERE, not PCRE: `grep -E` here is BSD grep on macOS as often as GNU. `{0,3}` and
# `[[:blank:]]` are both POSIX. Every grep below forces LC_ALL=C so the class
# means exactly space-and-tab -- under a UTF-8 locale BSD grep folds U+00A0 into
# it, which made the shell gate quietly more permissive than the Python audit,
# and made both locale-dependent.
PP_SKIP_MARKER_RE='^ {0,3}(<!--|#|//|--|;)?[[:blank:]]*path-privacy: skip-file'

# How many lines from the top are searched. A marker below this is not a marker;
# it is almost certainly a file talking about the marker.
PP_SKIP_MARKER_LINES=30

# pp_is_skip_marker_line <line> -- is this ONE line a marker rather than prose?
# The primitive; the other two are defined in terms of it, so a call site cannot
# reach the raw pattern and get the answer subtly wrong. That is not theoretical
# either: the SessionStart hook did exactly that, and its degraded path shipped
# with `grep -vE '$^'`, commented "matches nothing", which under BSD grep matches
# every EMPTY line and silently stripped the blank lines out of the directive.
pp_is_skip_marker_line() {
  printf '%s\n' "$1" | LC_ALL=C grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_head_has_skip_marker <file> -- exempt by inspecting the file on disk.
pp_head_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" "$1" 2>/dev/null | LC_ALL=C grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_text_has_skip_marker -- the same question asked of a string on stdin, for
# callers holding content not yet on disk (a Write payload, a brand-new file).
pp_text_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" | LC_ALL=C grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_filter_skip_marker_lines -- drop marker lines from stdin, pass the rest
# through untouched. For emitters: text that carries a marker line out of a file
# and into somewhere else (injected context, `--help` output) hands the next
# reader a working opt-out they did not ask for.
pp_filter_skip_marker_lines() {
  LC_ALL=C grep -vE "$PP_SKIP_MARKER_RE"
}
