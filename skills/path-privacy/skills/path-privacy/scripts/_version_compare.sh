# shellcheck shell=sh
# Canonical wrapper-vs-plugin version comparison. Sourced by install-git-hooks.sh
# (for --doctor) and by hooks/session-start.sh, and injected verbatim into every
# generated wrapper -- a wrapper is frozen at install time by design, so it
# cannot source anything at run time and must carry its own copy. One authored
# source keeps those copies from drifting the way the first three did.
#
# pp_version_is_newer A B -- true only when A is a semver strictly greater than B.
#
# The asymmetry is deliberate and load-bearing. The two remedies are opposites:
# a wrapper OLDER than the plugin should be refreshed with install-git-hooks.sh,
# while a wrapper NEWER than the plugin must NOT be, because regenerating it from
# the older plugin downgrades a working gate. So "newer" is the claim that has to
# be earned. Anything this function cannot positively verify -- the "unknown"
# stamp written when plugin.json is unreadable, a "pre-0.6.0" wrapper, a build
# suffix, a `sort` without -V -- returns false and lands in the stale branch,
# whose advice is idempotent and harmless even when unnecessary.
pp_version_is_newer() {
  # Both sides must be plain dotted numerics. `case` is used rather than a regex
  # so this holds under any POSIX sh, not just bash.
  case "$1" in ''|*[!0-9.]*) return 1 ;; esac
  case "$2" in ''|*[!0-9.]*) return 1 ;; esac
  [ "$1" = "$2" ] && return 1
  # sort -V orders 0.9.0 before 0.10.0, which a lexicographic compare inverts --
  # a bug this plugin shipped for real in 0.3.2. If -V is unsupported, sort errors
  # out, the substitution is empty, the test fails, and the caller gets "not
  # newer": the safe direction.
  [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V 2>/dev/null | tail -1)" = "$1" ]
}
