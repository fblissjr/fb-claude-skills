---
description: "A 'this prompt change helps' belief routes to adversarial-verify (build the without version)."
tags: [routing, adversarial-verify]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

I added a line telling the model to think step by step to our summarization prompt, and the outputs seem better. I don't trust my own eyes on this. Set something up that would show me whether that line actually makes a difference.
