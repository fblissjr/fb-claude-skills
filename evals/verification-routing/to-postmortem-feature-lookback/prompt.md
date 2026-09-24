---
description: "A look back at a shipped feature (where time went, what slipped past tests) routes to postmortem, not test-audit."
tags: [routing, postmortem]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

We shipped the webhook retry feature on Friday after three weeks of back and forth. Before we start on the next thing I want an honest look at how that went: where we lost time, what we'd change, and whether anything got past the tests that shouldn't have.
