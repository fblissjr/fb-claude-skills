# writing

*Last updated: 2026-08-13*

Skills for how the agent writes and explains. Two are about prose: an American plain-language house style (plain English, active voice, front-loaded content, sentence case, no bold or italics for emphasis) and one that matches the user's own voice from the conversation and a saved profile. Two are about prose that should not have been prose: one replaces a wall of text with a compact visual, the other repairs a message that did not land.

## Installation

```bash
/plugin install writing@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `plain-language-us` | "plain English", "plain language", "rewrite this clearer", "make this clearer" | Write and edit reports, guidance, and summaries in an American plain-language house style |
| `voice-match` | "write this in my voice", "match my tone", "sound like me", "in my style" | Write in the user's own voice, learned from the conversation and a saved global or per-project profile |
| `show-me` | "show me", "draw this", "diagram it", "what does this look like" | Answer with a compact visual instead of a paragraph: pseudocode, call tree, component tree, file tree, types and signatures, a diff of any of those, mermaid, or one focused HTML page |
| `wait-what` | you type it; the agent cannot fire it | Rewrite the last message when it did not land, with more context and the project's own vocabulary |

## Invocation

```
/writing:plain-language-us
/writing:voice-match
/writing:show-me
/writing:wait-what
/writing:voice show | correct <note> | scope <session|project|global|off> | reset | save
```

`plain-language-us`, `voice-match`, and `show-me` also trigger on their own: ask to write in plain English, ask for something in your own voice, or ask to be shown rather than told.

`wait-what` is user-invoked only, and that is not a preference. The model cannot detect that its own message failed to land, so there is no signal for it to fire on. You are the trigger.

## The three that overlap, and how they differ

They address one problem from different angles, so it is worth knowing which to reach for.

| Reach for | When |
|---|---|
| `plain-language-us` | The draft is prose and should stay prose, but the register is wrong: padded, hedged, machine-sounding |
| `show-me` | It should not be prose at all. The subject is structure, and the structure is easier to read than a paragraph about it |
| `wait-what` | A specific message already failed. You want that one re-pitched, not a general style change |

## Voice profiles

`voice-match` remembers a voice across sessions in two layered files: a global `<HOME>/.claude/voice-profile.md` applied everywhere, and a per-repo `.claude/voice-profile.local.md` for project-specific adjustments. Reads layer global then project; the per-repo profile is personal, not shared team config, and should stay gitignored. The skill stores durable voice traits only — never personal identifiers, secrets, or the content of what was written.

A `learning` mode controls when the profile is written: `session` (persist nothing), `project`, `global`, or `off` (read-only). Per-request phrasing overrides it ("just this session", "save that globally").

The `/writing:voice` command gives explicit control: `show` renders what the skill thinks your voice is, `correct <note>` records a fixed preference that inference will not override, `scope` sets the learning mode, `reset` clears a profile, and `save` writes what it learned this session. Plain language works too ("show my voice profile", "that didn't sound like me").

## Background

The style follows the American federal plain-language tradition — plainlanguage.gov, the Plain Writing Act of 2010, and the PLAIN network. Its content-design discipline (front-loading, one idea per sentence, no emphasis formatting) also draws on the UK Government Digital Service (GDS) style guide, adapted here to American conventions: American spelling, double quotation marks, periods and commas inside quotes, the serial comma, and month-first dates. The goal is to open the content up so anyone understands it on first read, without losing substance, nuance, or precision.

Attribution and external references are kept here in the README rather than in the skill body, so the loaded skill instructions carry no handles or URLs. The style was adapted from a skill shared by [@fofr](https://twitter.com/fofr).

`show-me` is adapted from the skill of that name in [humanlayer/skills](https://github.com/humanlayer/skills) (MIT) and the article behind it. Two things changed on the way in. The article treats a types-and-signatures sketch as a first-class shape and the shipped skill had dropped it, so it is restored here — it is the highest-value shape during design, when the code does not exist yet. And the article's cost ordering, that text shapes are lighter than HTML and good enough for most dev-shaped problems, is stated outright rather than implied by ordering. HTML publishes through the `Artifact` tool, where the upstream version could only open a local file.

`wait-what` is adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). The original leans on a `CONTEXT.md` ubiquitous-language file; with none here, the instruction degrades to whatever vocabulary the project already uses.
