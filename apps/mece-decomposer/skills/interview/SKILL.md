---
name: interview
description: Extract process knowledge from an SME through structured MECE interview. Use when user says "interview me about a workflow", "help me map this process", "extract process knowledge", or wants to build a decomposition through guided conversation.
---

# /interview

Extract process knowledge from a subject matter expert through conversation, ending in a MECE decomposition they have confirmed. The user is the SME.

Usage: `/interview <process to map>`, or `/interview` and let the user name it.

<protocol>
Follow `references/sme_interview_protocol.md` in the mece-decomposer skill: the five phases (scope, happy path, exceptions, boundaries, validation), the mode to pick from how much time and documentation the SME has, and the gotchas. Ask one question at a time; a compound question gets half an answer.

Open by telling the SME what helps most: describe how things actually work rather than how they are documented, include the exceptions and messy parts, say "it depends" wherever it does, and correct the tree freely. SMEs otherwise tidy their answers, and the tidied-away parts are what the interview exists to find.

Adapt to how the SME thinks: work top-down with a structured thinker, let a narrative thinker tell stories and organize afterward, and with a time-constrained SME start from a draft tree for them to correct.
</protocol>

<stops>
The SME answers every turn, so each turn carries one short recap line and the next question. Stop for explicit confirmation only at the protocol's three points: the scope sentence at the end of phase 1, the L1 structure before L2, and completion. Keep the running tree current in the conversation so the SME can correct it at any time.
</stops>

<done>
The SME has confirmed the L1 and L2 structure, at least 3 scenarios have been walked through without a gap, no overlap is unresolved, and the SME says it covers the process. Then produce the same output as `/decompose`: the human-readable tree, the JSON (with `metadata.source_type` set to `sme_interview`), and the interactive view via `mece-decompose` when the MCP server is connected.
</done>
