---
description: "An inventory of hooks and validators with what would notice if each stopped working routes to control-audit."
tags: [routing, control-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

List every hook and validator this repo depends on, what triggers each one, and which of them could quietly stop working without anybody noticing.
