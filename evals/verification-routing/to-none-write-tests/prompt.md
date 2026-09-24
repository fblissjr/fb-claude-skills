---
description: "Writing new tests is out of scope for test-audit (its negative scope says so); no verification-family skill fires."
tags: [routing, none]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Write unit tests for the new parse_duration function in utils/time.py. Cover the edge cases.
