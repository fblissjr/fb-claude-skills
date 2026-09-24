Trim this repository's always-loaded agent instructions to what an agent needs on its first edit, without losing a rule. The main target is `AGENTS.md` and `CLAUDE.md`. Anything else loaded every session is in scope when it duplicates them: unconditional `.claude/rules/` files, SessionStart hook output, and MEMORY.md.

Done means:
- every line still in the target files passes the test in <verdicts>;
- every line removed was deleted on purpose or moved to a named home, and the placement map says which;
- every pointer left behind resolves to text that actually says what the pointer promises;
- everything that read or cited the old text still works: docs citing sections by number, and checks that read the file by name;
- a fresh-context reviewer compared the old and new text and found no rule that is now stated nowhere;
- sizes before and after are recorded with the commands that produced them;
- the work is committed, and the report is written.

<parameters>
- Targets: `AGENTS.md` and `CLAUDE.md` at the repo root. (Or name others, such as a nested `CLAUDE.md` or a `.claude/rules/` file.)
- Also read, never edit: the user-level `CLAUDE.md`, user rules, and the project's auto-memory `MEMORY.md`. They reveal duplication; they are not this run's to change. Propose edits to them under "Needs from me".
- Depth: trim. Keep the file's structure and cut lines that fail the test. (Or "rebuild": restructure into what the repo is, commands, a done criterion, invariants, and where to look first.)
- Hub: if the repo has only `CLAUDE.md`, leave it as the hub. (Or "agents-md": move the content to `AGENTS.md` and reduce `CLAUDE.md` to the one line `@AGENTS.md`.)
- Landing: one commit on the current branch, with a changelog entry if the repo keeps one. Don't push.
</parameters>

<how_to_run>
When a step doesn't need my input, keep going. Put status notes in the same message as your next action. Don't end your turn with a summary that announces the next step, an offer to continue, or a list of decisions that don't block the work.

Stop and ask only when a cut would remove a rule I may still want and no home for it exists, or before editing anything outside the repository. Everything else is yours to decide; list those decisions under "Choices made alone".

The repo's own rules apply, including its conventions for docs, changelogs and commit messages. Where they and this prompt disagree, follow them and name the conflict under "Needs from me".
</how_to_run>

<inventory>
Before cutting anything, find out what depends on the text.
1. Measure what loads every session: each target file, the unconditional rules, what each SessionStart hook prints (run it and count), the skill listing, and MEMORY.md. Record bytes and lines with the command used. `/context` and `/doctor` show the same from inside a session.
2. Find the file's readers. From the repo root, `git grep` for each target's filename, and for every section name or number the file uses ("invariant 1c", "rule 3"). A section cited by number keeps its number: remove an entry, never renumber.
3. Find the machinery that reads the file: pre-commit hooks, lint or size checks, CI steps, scripts. A check that reads `CLAUDE.md` by name goes blind the moment the content moves to `AGENTS.md`, and it keeps passing.
4. Note duplicates: a rule that also lives in the user-level file, a rule file, a skill, or the README.
</inventory>

<verdicts>
Judge each line on its own. It stays only if it passes one of two tests:
- It carries something the model cannot learn from the repo: a convention, a version cascade, a trap that bites on the first edit, a command whose flags matter.
- It overrides something the model would otherwise do, and says why.

Everything else goes: restated general competence ("write clean code", "handle errors"), descriptions of what the code already shows, and history.

Cut on sight, whatever else the line says:
- "think carefully", "think step by step" and "ultrathink". Depth is set by effort, not prose.
- Step-by-step procedures for work the model plans well by itself.
- Capitals or bold spread over many lines. Emphasis marks at most the one rule that was seen being skipped.
- "Ask me rather than guessing" and other check-in rules. They produce the early stops current models are already prone to.
- Requests to explain or show reasoning in the reply.
- Model names and dates that only record when something happened.

Don't add a "keep going, stop only when blocked" rule pre-emptively. Add one only if runs actually end with "Want me to continue?".
</verdicts>

<placement>
A line that fails the test may still be true and worth keeping somewhere else. Move it to the narrowest place that loads when it matters:
- History ("retired on", "since v2") goes to the changelog or to the design doc that already records it.
- Rationale goes to the doc it came from. The hub keeps the rule and a pointer.
- A rule that matters only while editing certain files goes to a `.claude/rules/` file with `paths:` frontmatter, which loads only when those files are touched. A rule that must survive compaction stays unconditional.
- A procedure goes into a skill.
- A long table of docs becomes a short "where to look first" list of the rows that change what someone does on their first edit, plus a pointer to the docs index.

An `@import` is not a cut: an imported file loads in full at launch. Splitting a file into imports moves text without moving cost.

Keep a commands block and one sentence on what "done" means for a change. Most agent instruction files that work well are little more than that plus the traps.

Record every moved or deleted line in the placement map: the line, its verdict, and its new home or "deleted". Keep the map in a file you don't commit (the repo's local-notes location if it has one, otherwise the session scratchpad), so it survives compaction and can be handed to the reviewer.
</placement>

<pointers>
Every pointer left behind must resolve to text that says what the pointer promises. Open the target and find the sentence. A pointer to a file that doesn't cover the topic is worse than no pointer, so delete it and put the gap under "Needs from me".

If a docs index becomes the fallback for what you cut, check that index too. It inherits every stale entry it has, such as a finished feature listed as "not started" or a count that has drifted.
</pointers>

<hub_file>
When the content lives in `AGENTS.md`, keep `CLAUDE.md` as the single line `@AGENTS.md` rather than deleting it. Claude Code's direct reading of `AGENTS.md` stops silently when anyone adds a `CLAUDE.local.md`, and some session types skip it; the import works everywhere.

Then re-point every consumer from <inventory> step 3 to the file that now holds the text, and update citations that said "CLAUDE.md invariant N".
</hub_file>

<verify>
1. Re-run the reference sweep. Every remaining hit on the old names should be one you chose to keep, such as a changelog entry.
2. Run the repo's own checks and tests.
3. You made the cuts, so you read your own work generously. Dispatch one fresh-context subagent. Give it the old text (`git show HEAD:<file>`), the new text and the placement map, but not your reasoning. Ask only one question: which rules from the old text are now stated nowhere that loads or that a pointer reaches? Check each claim it makes against the files before acting on it.
4. Re-measure with the commands from <inventory> step 1.
</verify>

<report>
Your last message starts with these headings, in this order:
- Needs from me: rules with no home, proposed edits to files outside this run's reach (such as the user-level `CLAUDE.md`), and conflicts with the repo's rules. Give your recommendation for each.
- Sizes: before and after for each always-loaded item, with the command.
- Moved: each moved line and where it went.
- Cut: each deleted line and which test it failed.
- Kept on purpose: lines that look cuttable but stay, and why.
- Consumers re-pointed: checks, citations and indexes you updated.
- Choices made alone.
- Not confirmed: anything you couldn't check, and where you looked.
</report>
