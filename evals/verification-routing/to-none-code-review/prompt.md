---
description: "A request to review a branch diff for bugs belongs to the built-in code review; no verification-family skill fires (claim-audit's negative scope names this)."
tags: [routing, none]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Review the diff on this branch for bugs before I open the PR.
