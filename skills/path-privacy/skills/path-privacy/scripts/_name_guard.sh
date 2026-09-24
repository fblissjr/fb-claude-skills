# shellcheck shell=bash
# _name_guard.sh -- the one definition of "this text contains the owner's full name".
#
# Sourced by the PreToolUse hook, git-pre-commit and git-commit-msg, the same way
# _skip_marker.sh is, so the three cannot drift apart.
#
# THE NAME IS READ, NEVER STORED. It comes from `git config user.name` at run
# time, in the repo being written to. Nothing in this plugin, its tests or its
# fixtures carries a real name, and no message this library feeds ever prints
# the name back: callers report `file:line` only.
#
# WHAT COUNTS AS A FULL NAME. Two or more words, first and last at least two
# characters long. A one-word user.name is a handle, and a handle is allowed.
# Trailing generational suffixes (Jr, Sr, II, III, IV) are dropped before the
# last word is picked, or "A B Jr." would guard "a ... jr." and miss "A B".
#
# WHAT MATCHES. First word, optional middle words, last word, in that order,
# joined by any run of spaces, dots, dashes or underscores -- including none,
# which is the concatenated form a home directory often takes. Case-insensitive
# (ASCII). Bounded by a non-letter on both sides, so a longer word containing
# the name is not the name.
#
# WHAT IT DOES NOT DO. Reversed order ("Last, First"), initials alone, and
# nicknames are not matched. Those are not mechanically detectable with a low
# false-positive rate, which is the bar for a blocking hook.

# pp_name_regex [repo] -- print a lowercase ERE for the full name, or return 1
# when there is no full name to guard. Apply it to lowercased text (awk) or with
# `grep -iE`; both are equivalent because the pattern is built lowercase.
pp_name_regex() {
  local repo="${1:-.}" name w lw
  name=$(git -C "$repo" config user.name 2>/dev/null) || return 1
  [ -n "$name" ] || return 1

  local -a words=()
  set -f
  for w in $name; do words+=("$w"); done
  set +f

  # Drop generational suffixes from the end.
  while [ ${#words[@]} -gt 2 ]; do
    lw=$(printf '%s' "${words[${#words[@]}-1]}" | tr '[:upper:]' '[:lower:]')
    case "$lw" in
      jr|jr.|sr|sr.|ii|iii|iv) unset "words[${#words[@]}-1]" ;;
      *) break ;;
    esac
  done
  [ ${#words[@]} -ge 2 ] || return 1

  local first="${words[0]}" last="${words[${#words[@]}-1]}"
  first="${first%.}"; last="${last%.}"
  [ ${#first} -ge 2 ] && [ ${#last} -ge 2 ] || return 1

  local sep='[[:space:]._-]*' mid="" i
  for (( i=1; i<${#words[@]}-1; i++ )); do
    mid="${mid}$(_pp_ere_escape "${words[$i]%.}")\\.?${sep}"
  done
  [ -n "$mid" ] && mid="(${mid})?"

  printf '(^|[^[:alpha:]])%s%s%s%s([^[:alpha:]]|$)' \
    "$(_pp_ere_escape "$first")" "$sep" "$mid" "$(_pp_ere_escape "$last")" \
    | tr '[:upper:]' '[:lower:]'
}

_pp_ere_escape() {
  printf '%s' "$1" | sed 's/[][\.*^$+?(){}|/]/\\&/g'
}

# pp_name_lines <regex> -- read text on stdin, print the 1-based line numbers
# that contain the name. Lines that are a `Signed-off-by:` trailer are skipped:
# `git commit -s` writes that line from git config, which is the author
# metadata the owner exempts. Prints nothing and returns 1 when clean.
pp_name_lines() {
  PP_NAME_RE="$1" LC_ALL=C awk '
    BEGIN { re = ENVIRON["PP_NAME_RE"]; hit = 0 }
    { l = tolower($0) }
    l ~ /^[[:space:]]*signed-off-by:/ { next }
    l ~ re { print NR; hit = 1 }
    END { exit hit ? 0 : 1 }
  '
}

# pp_is_license_file <path> -- LICENSE/LICENCE/COPYING, any extension, any case.
# Copyright lines are the owner's own exception; they are managed by hand.
pp_is_license_file() {
  local b
  b=$(basename "$1" | tr '[:upper:]' '[:lower:]')
  case "$b" in
    license|license.*|licence|licence.*|copying|copying.*) return 0 ;;
  esac
  return 1
}
