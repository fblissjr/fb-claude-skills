Tighten this repository's always-loaded agent instructions: keep what an agent needs on its first edit, move everything else to where it loads when it matters, and fill the gaps a capable newcomer would fall into. Lose no rule. The test for every line: would removing it cause a mistake? The main target is `AGENTS.md` and `CLAUDE.md`. Anything else loaded every session is in scope when it duplicates them: unconditional `.claude/rules/` files, SessionStart hook output, and MEMORY.md.

Done means:
- every line still in the target files passes the test in <verdicts>, and the file carries what <keep_or_add> names that this repo actually has;
- every line removed was deleted on purpose or moved to a named home, and the placement map says which;
- every pointer left behind resolves to text that actually says what the pointer promises;
- everything that read or cited the old text still works: docs citing sections by number, and checks that read the file by name;
- a fresh-context reviewer compared the old and new text and found no rule that is now stated nowhere, and a fresh session given typical tasks with the new file got nothing wrong that the old file prevented;
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
5. Mine the evidence. Read the postmortems, session logs, sharp-edges record and fix commits for places an agent actually went wrong. A rule traced to one of them has earned its place. A rule nothing ever needed is a candidate to cut or move.
</inventory>

<verdicts>
Judge each line on its own. It stays only if it passes one of two tests:
- It carries something the model cannot learn from the repo: a convention, a version cascade, a trap that bites on the first edit, a command whose flags matter.
- It overrides something the model would otherwise do, and says why.

Everything else goes: restated general competence ("write clean code", "use descriptive names"), descriptions of what the code already shows, rules a formatter or linter already enforces, and history.

Cut on sight, whatever else the line says:
- "think carefully", "think step by step" and "ultrathink". Depth is set by effort, not prose.
- Step-by-step procedures for work the model plans well by itself.
- Pressure language: capitals or bold spread over many lines, "MUST", threats. Current models follow instructions closely, and pressure makes them overreact. Emphasis marks at most the one rule that was seen being skipped.
- "Ask me rather than guessing" and other check-in rules. They produce the early stops current models are already prone to.
- Requests to explain or show reasoning in the reply. They can be refused.
- Rules that made up for an older model's weakness and no longer reproduce.
- Rules for removed features and retired tools. Keep one line only if it stops someone reviving the thing.
- Long code samples. Point to a real file that shows the pattern.
- Model names and dates that only record when something happened.

Every line that stays gets these checks:
- **It carries its reason in one clause** ("X, because Y"). The model uses the reason for cases the rule doesn't name.
- **It is concrete enough to check.** "Keep functions small" does nothing; "stage files by name, never `git add -A`" does. Make it concrete or cut it.
- **It is scoped.** Current models follow instructions literally, so "always run the tests after an edit" fires on every edit, including the ones it shouldn't. Narrow any rule that applies more widely than intended, and resolve any two rules that clash.
- **It sits in order of how often it matters:** orientation and commands first, subsystem detail last or moved out.
</verdicts>

<keep_or_add>
A capable newcomer needs these. Check that each is present, but add one only when the repo actually has the thing: no parallel-session rules without parallel sessions, no benchmark command without benchmarks. `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md` shows a shape for each.
- **A short north star:** purpose, non-goals, principles, direction, marked as a direction and not a spec.
- **A map of where things live:** status, plans, backlog, settled decisions, sharp edges, local notes, the session log.
- **Exact commands:** setup, building what users get, tests, lint, benchmarks, profiling. These are often the most valuable lines in the file.
- **What "done" means** for the common kinds of change, and the checks to run before committing.
- **The stops you want:** keep going when a step doesn't need the owner, put status in the same message as the next action, and stop only when blocked or before anything destructive. Name the early stops you don't want (a summary that announces the next step, an offer to continue, a list of non-blocking decisions). Anthropic's Opus 5.5 guide recommends this rule for every CLAUDE.md.
- **Rules for working beside other sessions,** if the owner runs them.
- **The hazards:** the non-obvious traps where a capable newcomer goes wrong. These earn their place more than anything else.
- **Which tool verifies which kind of change,** when that isn't obvious.
- **Settled decisions,** or a pointer to them, and the rule not to reopen one without a new reason.
</keep_or_add>

<placement>
A line that fails the test may still be true and worth keeping somewhere else. Move it to the narrowest place that loads when it matters:
- A rule a script can check becomes a hook, test, lint or pre-commit guard, and the prose shrinks to a pointer or disappears. Propose wiring for machinery shared across worktrees (git hooks, `.git/` config) instead of installing it.
- History and incident stories ("retired on", "set up after it misled two sessions") go to the changelog, the sharp-edges record, or the design doc that already records them.
- Rationale goes to the doc it came from. The hub keeps the rule, its one-clause reason, and a pointer.
- Status ("since v2.0.86", "until X lands") goes to the status doc.
- A number copied from code or a measurement becomes a pointer to the constant or the data.
- A preference that applies across all the owner's repos goes to the user-level `CLAUDE.md`, proposed under "Needs from me".
- A rule that matters only while editing certain files goes to a `.claude/rules/` file with `paths:` frontmatter, or a `CLAUDE.md` in that subdirectory, which loads only when those files are touched. A rule that must survive compaction stays unconditional.
- A procedure (release, eval, deploy) goes into a skill.
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
3. Check every claim the new file makes against the repo: every path, function and command still exists and behaves as described. A stale line is worse than a missing one.
4. You made the cuts, so you read your own work generously. Dispatch one fresh-context subagent. Give it the old text (`git show HEAD:<file>`), the new text and the placement map, but not your reasoning. Ask only one question: which rules from the old text are now stated nowhere that loads or that a pointer reaches? Check each claim it makes against the files before acting on it.
5. Spot-test the behaviour. Give three to five fresh-context subagents one typical task each for this repo, drawn from recent session logs or commits, with the new file as their instructions and read-only tools. Ask each what it would do first and what it would need to ask. Anything one gets wrong that the old file would have prevented goes back in, or under "Needs from me".
6. Re-measure with the commands from <inventory> step 1.
</verify>

<report>
Your last message starts with these headings, in this order:
- Needs from me: rules with no home, proposed edits to files outside this run's reach (such as the user-level `CLAUDE.md`), and conflicts with the repo's rules. Give your recommendation for each.
- Sizes: before and after for each always-loaded item, with the command.
- Moved: each moved line and where it went (the placement map).
- Cut: each deleted line and which test it failed.
- Added: what <keep_or_add> filled in, and why the repo needed it.
- Proposed as checks: rules that should become a hook, test or lint, with the wiring.
- Settled decisions touched: any whose wording or home changed. Never drop one without saying so.
- Kept on purpose: lines that look cuttable but stay, and why.
- Consumers re-pointed: checks, citations and indexes you updated.
- Choices made alone.
- Not confirmed: anything you couldn't check, and where you looked.
</report>
