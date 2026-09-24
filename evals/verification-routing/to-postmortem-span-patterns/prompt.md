---
description: "A multi-week look at recurring failure patterns across history routes to postmortem (span mode), not claim-audit."
tags: [routing, postmortem]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Go through the last month of commits and session notes in this repo and tell me what keeps going wrong in how we work. I suspect we repeat the same mistakes but I can't name them.
