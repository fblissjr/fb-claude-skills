---
description: "Verifying an agent-written work summary before it is shared routes to claim-audit, not postmortem."
tags: [routing, claim-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

An agent wrote up a summary of today's work: all tests pass, three bugs fixed, coverage went up. Check each of those against the repo before I paste it into the team update.
