# postmortem

*Last updated: 2026-07-24*

Evidence-grounded retrospectives. One skill runs a postmortem of finished work
— a session, a feature, or a span of sessions mined from git history, session
logs, and changelogs. The other audits an existing test suite for meaning and
drift: whether each green test still verifies what its authors believed.

Both skills share one discipline: findings are claims, claims need citations,
and empty sections are valid output. The postmortem format (what went well /
what did not / deviations table / escapes / forward items, annotate-don't-
rewrite) was distilled from a real run postmortem in this repo that caught its
own process errors; the test-audit method (claim / oracle / envelope, spot
mutation, "a green suite proves what its conditions can express") generalizes
the same run's verification lessons.

## Installation

```bash
/plugin install postmortem@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `postmortem` | "postmortem", "retrospective", "what went well", "what would you do differently" | Verdicted retrospective of finished work; session mode (the conversation) or span mode (git history, session logs, changelogs, plan docs). Output is always a durable file. |
| `test-audit` | "audit the tests", "are these tests testing the right thing", "test drift", "do we trust this suite" | Per-test claim recovery, oracle verification by spot mutation, envelope mapping, and keep/rewrite/delete verdicts. Per-architecture question packs in `references/architectures.md`. |

## Invocation

```
/postmortem:postmortem                # this session
/postmortem:postmortem <feature|range|plan doc|"last N sessions">
/postmortem:test-audit                # audit the current repo's suite
```

Or trigger naturally: "run a postmortem on the auth migration", "which of our
tests are dead weight".

## Design notes

- Every finding must cite a concrete artifact (a file, commit, measurement,
  failed command). Generic advice is banned; "Nothing." is a valid section.
- Postmortems are append-corrected: later evidence gets a dated annotation
  under the original finding, never a silent rewrite.
- The escapes section (bugs vs. the tests that should have caught them) is the
  bridge between the two skills: repeated green-but-blind escapes in
  postmortems are the trigger for a full test-audit.
- Test deletions are recommended with evidence, never applied unasked.
