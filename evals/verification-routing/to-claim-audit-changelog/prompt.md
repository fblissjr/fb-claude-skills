---
description: "Checking the counts in a just-written changelog entry routes to claim-audit, not postmortem."
tags: [routing, claim-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Before I commit, sanity check the changelog entry I just wrote. It says 14 tests were added and that the migration covers all six tables. I don't want to find out later those numbers were invented.
