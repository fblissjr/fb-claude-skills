---
description: "Deciding which inherited tests to keep or delete routes to test-audit."
tags: [routing, test-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

I inherited this project and it has a few hundred tests. Some of them look like they were written against bugs that don't exist anymore. Help me work out which are worth keeping and which I can delete.
