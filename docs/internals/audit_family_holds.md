last updated: 2026-08-17

# What the audit family deliberately does not have

Companion to `claim_audit_design.md` and `control_audit_design.md`. Those record
what was built and why. This records what was **considered, specified, and not
built** — and what would reopen each one.

It exists because an enumerated hold is honest and an unenumerated one reads as
an oversight, which is the same reason a check must print what it did not cover.

## The tripwire

**No new drift instrument until a drift instance appears that the existing gates
provably could not have caught.**

Adopted 2026-08-17 from a peer repo's session, which arrived at it after three
consecutive proposals were each answered by machinery that already existed and
was simply not being used in the form it reads. This repo reached the same
result independently in the same week: a proposed classification pass over
numeric claims died against its own measurement, and the disposition it wanted
turned out to be one sentence riding a directive mechanism already shipped.

The rule is falsifiable and it binds the author as much as anyone: a proposal
must cite the instance, and must say which existing gate failed on it and why.
"This would be useful" does not clear it.

## Held: the postmortem filing validator

`filing.md` states rules nothing checks — filename agreeing with frontmatter,
mode within its enumerated set, `supersedes` naming a file that exists, no
absolute paths, and the `artifacts` projection.

**Not built** because the one contract violation in this repo's corpus was
output from a report-only skill that had been filed as a record type it is not;
removing it left a clean corpus, and a gate guarding a clean corpus earns
nothing yet.

The spec is recorded now, while the evidence is fresh, so a later build does not
re-derive it from memory:

- **Check the `artifacts` projection.** `filing.md` already calls it checkable —
  every entry appears as a body citation and every body citation appears in the
  list. Running it by hand over this repo's corpus found a real defect: an entry
  naming a file that exists under no name in the directory it points at, which
  is either a rename since or a list written from memory, and `filing.md` warns
  explicitly against the latter.
- **The matcher must normalize, not substring-match.** The same hand run
  false-positived badly, reporting `CHANGELOG.md` as uncited in files whose
  bodies cite `CHANGELOG 1.3.0` — a legitimate citation form. This is a design
  constraint, not a footnote; a naive matcher would make the check noisy enough
  to be disabled.
- **Citations couple by `path::symbol`, never `path:line`.** Established by
  adversarial refutation in a peer repo: a line-numbered citation goes red when
  anyone inserts a line above it, and a false red is worse than no check. See
  the coupling section in `adversarial-verify`.

**Reopens when:** a postmortem is filed that violates the contract without
anyone noticing at the time.

## Held: ranking absence claims as the highest-consequence class

The argument is sound from mechanism rather than frequency — a false "nothing
enforces this" costs someone a rebuild of work that already exists, which is the
most expensive possible response to a wrong claim, and absence claims carry a
Popper asymmetry where one positive instance refutes and only exhaustive search
confirms.

**Not adopted** because the ranking had no local evidence. Every absence claim
in this repo's shipped skills and internals was tested by attempting to refute
it, and none was false. The peer repo that proposed the ranking found several in
its own tree; ours has none, and a priority ordering shipped on someone else's
base rate is exactly the "someone else's scar tissue" failure `claim-audit`
warns about.

**Reopens when:** the first false absence claim is found here. At that point the
right form is probably an instruction to spend the budget *refuting* absence
claims and never attempting to confirm one, reporting "not refuted, search was
N" rather than a green.

## Held: a second copy of the counts rule in `best_practices.md`

The substitution test ships in the `claims-in-docs` directive, which reaches any
repo with `dev-conventions` installed. A second copy in `best_practices.md`'s
authoring-shape section would reach `/maintain` instead, and would cover
`SKILL.md` bodies specifically.

**Not added** under the one-copy test: a copy earns its place only if something
other than the check confirming it is a copy reads it, and no evidence yet says
`SKILL.md` bodies are a different case from docs.

**Reopens when:** a `SKILL.md` body is found carrying a decorative count that
the directive did not prevent.
