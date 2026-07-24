---
description: Inspect or adjust your saved writing voice profile
argument-hint: "[show | correct <note> | scope <session|project|global|off> | reset [global|project] | save]"
---

Load the `voice-match` skill and carry out the requested voice-profile action: `$ARGUMENTS`

- `show` (default when no argument): show what the skill currently thinks the user's voice is
- `correct <note>`: record a correction the user is making
- `scope <mode>`: set the learning mode
- `reset [global|project]`: clear a saved profile
- `save`: save what was learned about the voice this session

The `voice-match` skill is the single source of truth for how each action behaves, the profile locations and merge order, the profile format, and the guardrails. Follow it.
