last updated: 2026-09-24

# claim-audit

Audit prose as untrusted claims, and re-derive each one by running a command
whose output is that claim, never by reading the code and nodding. It works on
three kinds of prose:
- the added lines of a diff;
- a standing doc (README, AGENTS.md, SKILL.md) checked against today's code;
- a summary, changelog entry or PR text about to be sent.

It checks counts, statuses, capabilities, pointers, attributions and numbers in
prose. What cannot be derived is labelled or recommended for deletion. With
`--fix`, it applies the corrections the evidence settles and leaves the rest as
findings. Every report ends with its own scope line, so a clean result can be
told apart from a run that read nothing.

Motivated by two measured samples in a sibling repo. Reading a diff yielded
almost no findings. Executing quoted claims against their code found real
disagreements, concentrated in the newest summary prose.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install claim-audit@fb-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [claim-audit](skills/claim-audit/SKILL.md) | Extract claims from a diff, a standing doc or a summary; name a deriving command per claim before running anything; run, record both sides, label the unsourceable, check numbers against the three kinds, and optionally apply the settled fixes. |

## Invocation

```
/claim-audit:claim-audit                          # audit the pending diff's prose
/claim-audit:claim-audit README.md AGENTS.md      # audit standing docs against today's code
/claim-audit:claim-audit docs/ --fix              # apply the corrections the evidence settles
"is this README still true"                       # natural language
"audit the claims in this changelog entry"        # natural language
"verify this summary against the code"
"is what the session log says actually true"
```

## What it deliberately does not do

- **Rewrite judgment.** Even with `--fix` it changes only what a command's
  output settles: a wrong value, a dead pointer, a number with no home.
  Anything partly right, a rationale, or an ambiguous result stays a finding for
  the caller.
- **Scan by regex.** Claim extraction is done by reading; a pattern scanner
  measured above 85% false positives on this task.
- **Audit test suites.** That is `postmortem:test-audit` — a different subject
  with a different procedure.
