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

## Writing an instruction

Apply per instruction, not per skill. An instruction the current model no
longer needs is not neutral: dated behavioural text degrades behaviour, while
merely irrelevant text is comparatively harmless.

- Keep what the model cannot derive: versioned facts, project conventions,
  measured findings, a threshold with evidence. Delete restated competence: "be
  specific", "handle errors", step lists for tasks the model plans better
  itself, output templates for output that is not format-sensitive.
- An override names the default it overrides and why. Without the reason it is
  applied literally and too widely.
- Procedure earns its place only when the order is load-bearing for a reason
  the model cannot see, or the operation is fragile enough to need an exact
  script.
- Every surviving step carries its reason in one present-tense clause. The
  incident behind it is history and goes in the changelog.
- Examples pin a judgment boundary (this passes, this does not) or a
  format-sensitive shape. Otherwise they narrow the model to the example.
- State the target behaviour, not prohibitions. Keep a prohibition only when
  its failure reproduces on the current model. The exception: where a model
  default is the failure (generic design choices), name the specific patterns
  to leave out.
- One term per concept. Prefer a word the model already holds to a coined one;
  a coined word is paid for in definition tokens.
- Every step ends on a completion criterion that is clear and demanding: "every
  modified model accounted for" forces work that "produce a change list" does
  not. Done is printed evidence: a command and its output, a derived count.
- Scope is literal and requirements are stated as requirements. Say "every"
  when you mean every; "try to" and "if possible" read as permission to
  under-deliver.
- Emphasis marks at most one instruction, one a with-and-without run showed
  being skipped, with its reason.
- Depth goes in `effort:`, re-chosen per model; "think carefully" does not set
  depth. A lookup the answer depends on is stated as required.
- Ask for evidence, never for reasoning: the command and its output.
- Name the finish line and the stops: what done looks like, and when to stop
  (nothing can advance without the user, or before an irreversible action). Ask
  for status in the same message as the next action, not as a stop after each
  phase. Unattended runs end on a text-only turn, so the completion condition
  goes in the prompt.
- Long work keeps its task list in a file, which survives compaction.
- Ask for the unconfirmed remainder and where it was looked for.
- State it once, at the top, as standing instruction: a skill is not re-read on
  later turns and compaction keeps its start. No "unlike before", pinned model
  names or incident IDs in a shipped body.
- A skill earns its place only for what is versioned, project-specific,
  contested or newer than the model. Ask what it supplies that the model cannot
  derive before writing it.

## Where verification runs

Decided by authorship, then isolation, then size. A skill that dispatches says
which case it is in and why.

- The judging context produced the subject: one fresh-context verifier for the
  whole set, briefed with the claims and where the evidence lives, never with
  the reasoning.
- Items interfere (each mutates files): one dispatch per item, in parallel.
- A large set of independent units: fan out per unit; below that, stay in one
  context.
- Otherwise the main context runs the command whose output decides.
- The lead checks each report's evidence before accepting it.

## Descriptions

A description is a reverse query: it describes the intents that should match.

- What it does, in third person with action verbs; when to use it, as
  categories of intent in phrases users type, not a growing list of synonyms;
  negative scope where an adjacent skill could match; core use case first.
- No two installed skills with near-duplicate descriptions.
- Precision and listing cost pull against each other. Write the description
  routing needs and manage the total with fewer listed entries, not by
  shortening descriptions that earn their length.
- Diagnose before editing: not loading when it should is undertriggering (add
  trigger phrases); loading for irrelevant queries is overtriggering (add
  negative scope); zero invocations is ambiguous and needs a trigger eval.
- Negative scope here is routing metadata, not the behavioural prohibition
  "Writing an instruction" warns against.

## Skill folder

No `README.md` inside a skill folder: docs go in SKILL.md or `references/`, so
there is one entry point. Upstream permits it; this is ours.
