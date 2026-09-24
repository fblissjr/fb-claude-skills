---
description: "Trigger plus outcome: a user lost in a prose explanation of call structure gets show-me, and the answer is a visual (fenced block or tree) that keeps the nesting."
tags: [show-me, trigger]
max_turns: 4
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

Paragraphs aren't working for me here. The request handler calls validate(), which calls load_schema() and check_types(). Then the handler calls save(), which calls serialize() and write_row(), and write_row() retries through with_backoff(). Lay it out so I can see the shape at a glance.
