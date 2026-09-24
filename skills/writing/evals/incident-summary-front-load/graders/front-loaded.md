---
# claim: house rule 'front-load': the reply opens with the outcome, not the timeline. Only a judge can decide this, so it is the suite's one llm grader.
type: llm
focus: last_message
---

The response is a rewrite of an incident summary. Judge only its opening sentence (ignore any heading line).

PASS if the opening sentence states the impact or the cause of the incident: that sign-ins failed, or that an expired certificate caused the outage.
FAIL if the opening sentence starts the chronology instead, such as the 09:14 alert, the on-call engineer being paged, or the rollback, and the impact or cause appears only later.
