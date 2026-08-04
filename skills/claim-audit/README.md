last updated: 2026-08-04

# claim-audit

Audit the added prose of a diff as untrusted claims. Every count, status, and
attribution is re-derived by executing a command whose output is that claim —
never by reading the code and nodding. What cannot be derived gets labeled
(`(memory)`, `(local)`, `(reported)`) or recommended for deletion, and the
report states its own scope so a green result is distinguishable from a run
that read nothing.

Motivated by two measured samples in a sibling repo: reading a diff yielded
approximately zero findings; executing quoted claims against their code found
real disagreements — including ten claims wrong in a single day's carefully
written output, nine authored that day. The failure concentrates in summary
prose, and the newest prose is most likely to be wrong about a change because
it was written closest to it.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install claim-audit@fb-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [claim-audit](skills/claim-audit/SKILL.md) | Extract counts, statuses, and attributions from added prose; name a deriving command per claim before running anything; run, record both sides, label the unsourceable, and report without rewriting. |

## Invocation

```
/claim-audit:claim-audit                          # audit the pending diff's prose
"audit the claims in this changelog entry"        # natural language
"verify this summary against the code"
"is what the session log says actually true"
```

## What it deliberately does not do

- **Rewrite.** The caller fixes; auditor findings shrink on caller
  verification often enough that the weigh-it-yourself step is load-bearing.
- **Scan by regex.** Claim extraction is done by reading; a pattern scanner
  measured above 85% false positives on this task.
- **Audit test suites.** That is `postmortem:test-audit` — a different subject
  with a different procedure.
