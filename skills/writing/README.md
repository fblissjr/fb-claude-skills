# writing

*Last updated: 2026-07-26*

Writing skills for clear, accessible prose. One skill is an American plain-language house style — plain English, active voice, front-loaded content, sentence case, and no bold or italics for emphasis. A second matches the user's own voice, learning it from the conversation and a saved profile.

## Installation

```bash
/plugin install writing@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `plain-language-us` | "plain English", "plain language", "rewrite this clearer", "make this clearer" | Write and edit reports, guidance, and summaries in an American plain-language house style |
| `voice-match` | "write this in my voice", "match my tone", "sound like me", "in my style" | Write in the user's own voice, learned from the conversation and a saved global or per-project profile |

## Invocation

```
/writing:plain-language-us
/writing:voice-match
/writing:voice show | correct <note> | scope <session|project|global|off> | reset | save
```

Or trigger `plain-language-us` automatically by asking to write or rewrite in plain, accessible English, and `voice-match` by asking for something in your own voice.

## Voice profiles

`voice-match` remembers a voice across sessions in two layered files: a global `<HOME>/.claude/voice-profile.md` applied everywhere, and a per-repo `.claude/voice-profile.local.md` for project-specific adjustments. Reads layer global then project; the per-repo profile is personal, not shared team config, and should stay gitignored. The skill stores durable voice traits only — never personal identifiers, secrets, or the content of what was written.

A `learning` mode controls when the profile is written: `session` (persist nothing), `project`, `global`, or `off` (read-only). Per-request phrasing overrides it ("just this session", "save that globally").

The `/writing:voice` command gives explicit control: `show` renders what the skill thinks your voice is, `correct <note>` records a fixed preference that inference will not override, `scope` sets the learning mode, `reset` clears a profile, and `save` writes what it learned this session. Plain language works too ("show my voice profile", "that didn't sound like me").

## Background

The style follows the American federal plain-language tradition — plainlanguage.gov, the Plain Writing Act of 2010, and the PLAIN network. Its content-design discipline (front-loading, one idea per sentence, no emphasis formatting) also draws on the UK Government Digital Service (GDS) style guide, adapted here to American conventions: American spelling, double quotation marks, periods and commas inside quotes, the serial comma, and month-first dates. The goal is to open the content up so anyone understands it on first read, without losing substance, nuance, or precision.

Attribution and external references are kept here in the README rather than in the skill body, so the loaded skill instructions carry no handles or URLs. The style was adapted from a skill shared by [@fofr](https://twitter.com/fofr).
