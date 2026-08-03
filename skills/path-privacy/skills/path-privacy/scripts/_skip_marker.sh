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
#   Not inside a fenced code block. See pp_strip_fenced below. This is the one
#   restriction a line pattern cannot express, and it was left open for a
#   release on the argument that no pattern could separate a fenced quotation
#   from a marker. True of a line regex; false of a scan, which is what fence
#   state requires and gets here.
#
# Even so, the pattern is not the last line of defence, and should not be
# treated as one. `check_marker_denylist` in skill-maintainer asserts that the
# file classes this keeps happening to -- changelogs, skill docs, plugin READMEs
# -- are never exempt by any route, including routes not yet thought of. The
# rule narrows the hole; the deny-list is what makes a recurrence loud.
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

# pp_strip_fenced -- drop fenced code blocks from stdin.
#
# This is the part a line-oriented pattern genuinely cannot do, and claiming
# otherwise is what left the last hole open: a fenced block is not indented, so
# `# path-privacy: skip-file` shown as an EXAMPLE inside ``` is byte-identical to
# a real marker. No regex over a single line can separate them, because they are
# the same string. Fence state is not a property of the line; it is a property of
# what came before it, so it takes a scan.
#
# Strictly fail-closed: removing lines can only ever remove matches, so this can
# turn an exempt file into a scanned one and never the reverse. A stray ``` above
# a genuine marker therefore costs a false positive, which is loud and gets
# fixed, rather than a silent exemption, which is the failure that keeps
# happening here.
#
# Applied to every file type, not just markdown. A ``` line in a .py or .sh file
# is already a syntax error, so the only realistic place one appears is inside a
# docstring or heredoc -- which is a quotation too, and treating it as one lands
# on the safe side either way.
#
# The fence rules are markdown's own, and each one is load-bearing:
#
#   A fence CLOSES only with the character that opened it, in a run at least as
#   long, with nothing but blanks after. The first version toggled on ``` OR
#   ~~~ interchangeably, so a ~~~ line inside a ``` block flipped the state
#   back off and a marker that renders as an example to a human was live to the
#   scanner -- the exact bypass the fence pass exists to close, reopened by the
#   pass itself. Same shape for run length: an inner ``` must not close an
#   outer ```` that is demonstrating it.
#
#   Indent is 0-3 ASCII SPACES, written as a byte test rather than a character
#   class. The old [[:space:]] under LC_ALL=C meant ASCII-only while the Python
#   twin's \s matched U+00A0 and friends, so a NBSP-prefixed fence was a fence
#   to one engine and not the other -- and any string the two engines disagree
#   about is a file one of them exempts and the other does not. Markdown does
#   not treat NBSP as indentation either, so bytes here IS the semantics, on
#   both sides.
#
#   Only closing is strict; opening stays liberal (info strings allowed, ```sh).
#   The asymmetry is the fail-closed direction: an over-eager OPEN hides a
#   marker and costs a loud false positive, an over-eager CLOSE un-hides one
#   and costs a silent exemption. An unclosed fence swallows to EOF for the
#   same reason.
#
# LC_ALL=C for the same reason the greps have it, plus one specific to awk: on a
# BINARY file under a UTF-8 locale, macOS awk writes "towc: multibyte conversion
# failure" to stderr for every undecodable record. The scanner runs over whole
# trees, which contain binaries, and the PreToolUse hook captures its stderr and
# shows it to the user -- so without this the fence pass turns every binary file
# in the repo into noise inside a block message. In the C locale awk treats the
# input as bytes and stays silent.
#
# Procedural rather than regex because the portable middle ground does not
# exist: interval expressions like {0,3} are missing from older mawk and
# one-true-awk, and this library runs on whatever awk the host has.
pp_strip_fenced() {
  LC_ALL=C awk '
    # pp_fence(line): 1 when the line is a fence -- at most three spaces of
    # indent, then a run of three or more backticks or tildes. Sets FCH to the
    # fence character, FLEN to the run length, and FCLOSE to 1 when nothing
    # but blanks follows the run, the only shape allowed to CLOSE a fence.
    function pp_fence(line,  i, n, tail) {
      FCH = ""; FLEN = 0; FCLOSE = 0
      i = 1
      while (substr(line, i, 1) == " ") i++
      if (i > 4) return 0
      FCH = substr(line, i, 1)
      if (FCH != "`" && FCH != "~") { FCH = ""; return 0 }
      n = 0
      while (substr(line, i + n, 1) == FCH) n++
      if (n < 3) { FCH = ""; return 0 }
      FLEN = n
      tail = substr(line, i + n)
      gsub(/[ \t\r]/, "", tail)
      FCLOSE = (tail == "") ? 1 : 0
      return 1
    }
    flen == 0 {
      if (pp_fence($0)) { fch = FCH; flen = FLEN; next }
      print
      next
    }
    { if (pp_fence($0) && FCLOSE && FCH == fch && FLEN >= flen) flen = 0 }
  '
}

# pp_head_has_skip_marker <file> -- exempt by inspecting the file on disk.
pp_head_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" "$1" 2>/dev/null \
    | pp_strip_fenced | LC_ALL=C grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_text_has_skip_marker -- the same question asked of a string on stdin, for
# callers holding content not yet on disk (a Write payload, a brand-new file).
pp_text_has_skip_marker() {
  head -"$PP_SKIP_MARKER_LINES" | pp_strip_fenced | LC_ALL=C grep -qE "$PP_SKIP_MARKER_RE"
}

# pp_filter_skip_marker_lines -- drop marker lines from stdin, pass the rest
# through untouched. For emitters: text that carries a marker line out of a file
# and into somewhere else (injected context, `--help` output) hands the next
# reader a working opt-out they did not ask for.
pp_filter_skip_marker_lines() {
  LC_ALL=C grep -vE "$PP_SKIP_MARKER_RE"
}
