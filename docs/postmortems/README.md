last updated: 2026-08-17

# Postmortems

Verdicted retrospectives of finished work in this repo. Each file covers one
session, one feature, or one span, and is named `YYYY-MM-DD_<mode>_<slug>.md`
so that listing the directory sorts by date and a slug grep finds a topic.

**This page is the frame, not an index.** It lists nothing. A checked-in listing
would be a copy whose only consumer is the check confirming it matches the
directory, and it would drift the first time a file landed without it. To browse
by date, conclusion, or which files a postmortem examined, run
`/postmortem:postmortem-index`, which builds that view from the frontmatter each
time it is asked.

## The standard of evidence

**No citation, no finding.** Every claim names a concrete artifact — a file, a
commit, a failed command, a measurement, a decision visible in the record.
Generic advice is banned. A section with nothing grounded says "Nothing.", and
an empty section is valid output rather than a failure.

Findings distinguish what was measured from what was inferred, and anything not
directly observed is labelled as inference.

## Why these read the way they do

They are deliberately, specifically self-critical, and most of what they record
is failure. That is the point: a postmortem set holding only wins is worth
nothing, because the reason to keep one is to stop paying for the same mistake
twice. Sentences here describe defects in this repo's own shipped plugins,
measurements taken by the wrong method, and controls that turned out to test
nothing.

Read cold, any one of them can be quoted against the project. Read as a set,
they are the reason the project's claims can be checked at all.

## What these documents do and do not promise

**Annotate, do not rewrite.** When later evidence contradicts a finding, a dated
annotation is added under it. The original stands. A document that quietly
revises its own conclusions is worse than one that is wrong in public.

**The body is past tense and cannot become false.** A finding records what
happened, so age is not a defect in it. Staleness is not something to fix here.

**Forward items are the exception.** Section 5 of each file is a claim about the
future sitting inside a frozen record, so it does not inherit that safety. Those
items carry closure annotations as they resolve; one without an annotation may
simply not have been revisited, and should be checked against the tree rather
than believed.

## What is not here

Some material is held back, and where that happened the file says so in place
rather than closing the gap silently: session logs and other working notes stay
private, and a citation pointing at one carries its load-bearing sentence inline
so the finding stands without the pointer. Where a passage was redacted before
publication, a dated note explains what was removed and why.

Rendered HTML versions are generated on demand and deliberately not committed.
