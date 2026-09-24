---
description: "Wanting a clickable page of past retrospectives routes to postmortem-index, not postmortem."
tags: [routing, postmortem-index]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

We've written a pile of retros in docs/postmortems over the past few months. I'd like a page I can click through to find them by date and by which files each one looked at.
