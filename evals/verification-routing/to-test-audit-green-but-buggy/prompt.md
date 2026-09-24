---
description: "Doubt about whether a whole suite's greens mean anything routes to test-audit, not adversarial-verify."
tags: [routing, test-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Our suite has been green for months and we still ship bugs every week. I want to know which of the tests under tests/ would actually go red if the code they cover broke, and which ones are just along for the ride.
