---
paths:
  - "**/SKILL.md"
---

# Skill authoring rules

## Trigger phrases, unless the skill is user-invoked only

A model-invocable skill's description includes the phrases users would say
("Use when the user says 'decompose this', 'break down this workflow'..."), because
the description is what the model matches a request against.

A skill with `disable-model-invocation: true` is the exception: its description
never enters Claude's context, so a trigger phrase there cannot fire, and writing
one to satisfy the check touches what the check measures. `skill-maintain
validate` skips the WHEN check for these and still requires the WHAT, which is
what a person reads in the slash-command menu; state the action and, where it is
not obvious, that invocation is manual.

## State the rule flatly

Skill bodies carry no hedges for hypothetical installers ("this is the owner's
preference, not a universal layout"). That these are one person's house style is
stated once, in `README.md` and `VISION.md`; a per-instance qualifier loads on
every activation and tells the reader nothing the front door did not. Put the
stance in the plugin README, where it costs nothing per activation.

## No angle brackets in descriptions

Upstream's skill-creator `quick_validate.py` rejects a description containing `<`
or `>`; `skill-maintain validate` only warns. This collides with path-privacy's
`<HOME>/...` placeholder form, which stays legal in bodies, references and docs.
In a description, name the location in prose: "the user's Claude config
directory", "absolute home-directory paths under /Users or /home".

## Frontmatter

Metadata values are strings: the spec defines `metadata` as a string-to-string
map, so quote scalars that YAML would otherwise type as a date or number. Which
`metadata` keys never appear: AGENTS.md invariant 1.

Description length and body length are checked by `skill-maintain validate`;
move verbose material to `references/` with a one-line pointer from SKILL.md.

## Script paths

`uv run` commands in SKILL.md use paths relative to the project root (where
`uv run` is called from), not relative to the SKILL.md file.

Correct: `skill-maintain quality`, or `uv run python tools/<pkg>/scripts/<script>.py` for a script that really is bundled.
Wrong: `uv run python scripts/<script>.py` — resolved against the SKILL.md, which is not where `uv run` starts.
