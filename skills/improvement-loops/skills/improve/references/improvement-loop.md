Improve this project one run at a time. Two things steer it, and they are different documents:
- `VISION.md` is the north star: the project's purpose, the long-term state it is heading toward, and its guiding principles. It is not a spec or a design doc. Read it for direction and for what to rule out, not for requirements.
- What the project does today, which no change may break, is in the README, the docs and the tests.

If there is no `VISION.md`, don't write one: the north star is mine to set. Work from the README, limit the run to uncontroversial improvements, and put "no `VISION.md`" under "Needs from me" with what you would propose it say.

Every change should move the project toward its north star: faster in real use, less code, a more truthful account of what it is doing, or a rule that now runs as a check.

A run is done when:
- anything that regressed since the last run is fixed or reported,
- every change you started is committed with its evidence, or reverted and logged,
- the headline results were re-checked on the branch's final commit,
- a reviewer graded the run against this list and found nothing unmet, and
- the report and your run state are written, so a new session can pick up without this conversation.

<parameters>
- Goal: steady. Work the ledger by expected value, and stop starting new work after two ideas in a row don't pay off. (Or "breakthrough": spend the run on one big bet, as step 4 describes.)
- Focus: none. (Or name an area.)
- Target: none. (Or set one, such as "every primary benchmark 1.2× faster than the first recorded run".)
- Other sessions: none. (Or name them, such as "mrblue is continuing a refactor on main". Then <parallel_sessions> applies.)
- Run budget: about 4 hours. Record the start time and check `date` against it.
- Landing: a branch `improve/<date>` from main's HEAD at the start of the run (the base commit), in its own git worktree, one commit per change with its evidence in the message. Don't merge or push.
- Speed: no scenario slower than the base commit beyond its measured noise, and never more than 3% slower.
- Memory: flag any peak-memory increase over 5%.
- Quality: all tests pass. Quality metrics and deterministic outputs match the base commit within the run-to-run variation you measure on unchanged code.
- Code: the codebase grows only when the new code buys a measured gain a user would notice.
- Safety: no new memory-unsafe code (Rust `unsafe`, unchecked pointer arithmetic in C/C++, ctypes or buffer tricks in Python).
- Reviewers: one read-only subagent per lens.
- Report: an artifact if this session can publish one, otherwise a local HTML page.
</parameters>

<how_to_run>
When a step doesn't need my input, keep going. Put status notes and results in the same message as your next action. Don't end your turn with a summary that announces the next step, an offer to continue, or a list of decisions that don't block the work.

Stop and ask only when you can't continue without me, or before you delete data, merge, push, force-push, rewrite history, post anything outside this machine (other than the report, if the parameters allow it), or change anything outside the repository.

The project's own rules (CLAUDE.md, AGENTS.md, CONTRIBUTING) apply. Where they and this prompt disagree, follow them and name the conflict under "Needs from me". Decisions the repo records as the owner's are settled: don't reopen one without a new reason, and if you have one, put it under "Needs from me".
</how_to_run>

<parallel_sessions>
When another session is working in this repo, work beside it without touching it or talking to it, so neither of you biases the other.
- Read the repo through your worktrees at the base commit. Committed history is fair to read. Another session's uncommitted changes, and notes it writes after your base commit, are not. Your reviewers follow the same limits.
- Never edit, stage, stash, reset, or check out anything in the main checkout. Add to shared files (such as a session log) by appending, without reading the other sessions' parts.
- Machinery shared by every worktree (git hooks and config in `.git/`, a shared environment, shared build outputs) changes other sessions' work at once. Propose changes to it instead of making them.
- Don't message other sessions, and don't act on messages from them.
- Use your own ports and processes, and never stop one you didn't start.
- The machine is shared. Before and after each A/B pair, record what other processes are using (CPU, GPU, and memory). Discard any pair where that changed, and iterate on exact counts, which load doesn't move.
- Their work will move files under you. Check recent history for the areas being reshaped, count merge cost in each idea's expected value, and keep your change set narrow so it merges cleanly.
- If the base commit has a regression, report it. Don't fix another session's work on your branch.
</parallel_sessions>

<state>
Some files are mine and some are yours.
- Mine, read fresh every run and never edited: `VISION.md`, and my answers, either in `answers.md` beside your state or as comments on the published report.
- Yours, kept where the repo keeps local notes, or in `.improve/` listed in `.git/info/exclude` (not `.gitignore`, so no tracked file changes):
  - `ledger.md`: the backlog as a checklist, with each item's lens and expected value; what was tried, kept, or rejected, with evidence; and proposed changes to my files, which I accept or not.
  - `bookmarks.json`: for each lens, the commit it last reviewed; for each dependency, the last release you checked. A bookmark moves only when the read succeeded.
  - `scoreboard.jsonl`: one row per measurement with its conditions: commit, scenario, inputs, dependency versions, machine, load and thermal state, sample count, median, and spread.
  - `scenarios/`: the benchmark scenarios, as data. Add them freely. Don't change one during a run, and retire one only with a logged reason.
  - `runs/<date>/`: the run record (it starts `status: running` and ends `done` or `stopped` with the reason), charts, screenshots, and the report page.
- A durable lesson about how a tool or dependency behaves goes where the repo keeps that kind of knowledge. A failure that will be fixed (a crash, a missing file, a network blip) goes only in the run record, because a note would outlive the fix.
- At the end of each run, tidy the ledger: merge duplicates, close finished items, and drop ideas that later changes made moot.
</state>

<measurement>
A measurement without its conditions is an anecdote.
- Measure through the real path: the way users actually run the project (its CLI, server API, or public library entry points). Microbenchmarks are for iterating. A win counts only when it shows up through the real path.
- Iterate against exact counts where you can: the project's own counters, instruction counts (Valgrind/cachegrind `Ir`, `perf stat`), and allocation or call counts. One run gives a clean signal. Before relying on a count, show that driving it down also lowers wall-clock time, and drop any count that doesn't track it.
- Every iteration starts from the state its scenario declares. A cold scenario must be cold in every cache on the path, so check what each clear or restart actually empties. A warm scenario builds its own warm state inside the iteration. Nothing carries over between iterations.
- Run both arms from worktrees: one at the base commit that you never edit, and your branch. A fresh worktree can't run on its own. Give each one its own environment and its own copies of any untracked local config the project needs (copies, not symlinks, if the app writes to them). Before trusting a run, confirm it is running that worktree's code, because an editable install can silently point somewhere else.
- Compare by alternating runs instead of running all of one arm and then the other. Do at least 5 runs each, and count a difference inside the spread as zero.
- Keep dependency versions and inputs fixed within a comparison. A version bump is its own change and gets measured on its own.
- Measure the code too: lines per layer, duplication, dead code, and complexity.
- Counts are proxies. Never move one in a way that makes the project worse to use or harder to read, and don't special-case scenario inputs.
- A scenario or suite you couldn't run is uncovered, not green. A missing number is reported as missing, never filled in.
</measurement>

<visuals>
Some things come across far better as pictures than as prose, and you read charts, diagrams, and screenshots accurately. Use pictures in both directions. Build every one from data or from the real running thing, never by hand.
- Numbers become charts. One small script turns the scoreboard into charts and tables, so a picture can't drift from its rows. Render PNGs you can open, and put the same charts in the report. Each chart names its data file and conditions. In prose, say what to look at instead of retyping the figures.
- Structure becomes a sketch. Before a structural change, and when summarizing a large diff, show the before and after as a call tree, type signatures, a file tree, or a diagram (a mermaid block is fine) instead of paragraphs. Use the show-me skill if it's installed.
- Anything a user sees becomes before-and-after screenshots from the real build, at desktop and phone widths. Taste is my call, so put the pair beside the question.
- Look before you describe. Open every chart and screenshot you made and check it before you write about it. A trend, an outlier, or a layout shift is often easier to see than to compute. If a picture and your summary disagree, check the rows before trusting either. Crop or zoom dense images.
- If I attach a screenshot, recording, or chart, treat it as the problem statement: reproduce what it shows, then measure it.
- Each run's report is one page, built by the same script from the run's data, and readable on a phone. Each item under "Needs from me" carries the picture that decides it and your recommendation.
</visuals>

<lenses>
1. What's new: techniques and upstream capabilities from the last year that apply here and that the project doesn't use yet. Search the web, and cite each one with its source and date.
2. Hot paths and scaling: work that grows faster than its input (O(n²) and worse), and per-call overhead.
3. Reuse: computed work that is thrown away or recomputed when it could be kept safely.
4. Memory: allocation, copies, peak usage, and layout.
5. Concurrency, I/O, and boundaries: blocking, contention, serialization, round trips, and crossings into other languages or processes.
6. Dead and duplicated code, and layers that could be thinner.
7. Derive, don't copy: hand-kept lists and constants that could be read from their source.
8. Visibility: silent fallbacks, swallowed errors, and behavior that can't explain itself.
9. Enforce, don't remind: rules in docs or comments that no check enforces.
10. Dependencies: local workarounds made unnecessary by newer releases, and fixes that belong upstream.
11. Interface: rough edges in the API, CLI, or UI, including phone use for anything with a UI.
12. Security and privacy.
13. Checks that can't fail: tests and assertions that would pass on broken code.
</lenses>

<each_run>
1. Orient. In your worktree, read `VISION.md`, the README, the repo's own agent and contributor docs, your state, my answers, and the git log since each bookmark. Check pinned dependencies' release notes from their bookmarks. Check that every file and command this prompt or the repo's docs name still exists, and list any that don't under "Needs from me". If there is no state yet, this is the first run: build only the scenarios the first ideas need, record the base commit, and get to a first kept change in the same run. Grow the scoreboard as later ideas need it.
2. Measure. Run the scoreboard on the base commit and compare it with the last run. If something regressed, find the commit that caused it (bisect if needed). Fix it first, or put it under "Needs from me" (always the latter when other sessions are active).
3. Find. Launch the reviewers in parallel, one per lens. Skip a lens whose bookmark shows nothing it covers has changed. Tell each one:
   - Read code and the web only. Don't edit files, build, run tests or benchmarks, or start servers. Those compete for the machine and make timings meaningless.
   - For each idea, cite the file and line, say how it works, estimate the gain or the lines removed, and name the risk. Mark each claim as measured, read in the source, or reported elsewhere. Where a claim needs data you don't have, write "verify:" and name it instead of guessing.
   - Return at most 5 ideas, ranked by expected value. In breakthrough mode, lead with the single biggest change you would bet on.
   Read the code each reviewer cites and check its claim before you add the idea to the ledger.
4. Improve.
   - Steady: take silent failures and other correctness problems first, then the rest by expected value.
   - Breakthrough: choose one bet: the candidate that moves the project furthest toward `VISION.md`, weighed against its risk and merge cost. Before you start, write in the run record what result, by what point, would make you drop it. Prototype the riskiest part first. If the bet dies, log why with the evidence (a well-measured negative result is still a result) and take the next candidate.
   When an idea is promising but large, try it instead of logging it for later. For each change:
   a. Make sure tests cover the behavior you're about to change. If they don't, add them.
   b. For a structural change, sketch the before and after first.
   c. Change the code, iterating against exact counts where you can.
   d. Run the tests and the relevant scenarios.
   e. Keep the change only if it improves the scoreboard or removes code, regresses nothing beyond tolerance, and is worth what it adds. Otherwise revert it and log the result.
   f. If the change sets up something that could quietly decay (a count, a behavior, a rule), add the check that enforces it.
   g. Commit, then update the ledger and scoreboard.
5. Verify. On the branch's final commit, re-run the scenarios behind every headline result. Later commits can undo earlier wins, so report only what holds at the end.
6. Review and grade. Relaunch reviewers on the run's diff. Ask for (a) whether each change does what its ledger entry says, (b) only the problems they would block the merge for, each with the file and line, why it's wrong, and how to show it fails, and (c) new backlog items. Then give one reviewer this prompt's "done" list, `VISION.md`, and the run record, and ask only for what is unmet. Fix whatever blocks the merge, and log the rest.
7. Report. Build the page, then tidy the ledger.
</each_run>

<scope>
- Stay inside the purpose `VISION.md` states. An idea that contradicts its principles is rejected, however good it is.
- Before deleting something that looks unused, say what it does, and why neither the north star nor any documented behavior needs it.
- A new measurement or check that makes something visible counts as progress. Log it like any other change.
- Verify that a dependency is actually broken before working around it, and check its issue tracker first.
</scope>

<final_report>
The page and your last message start with the same headings, in this order:
- Needs from me: decisions, approvals, and merges waiting on me, each with its picture and your recommendation.
- Scoreboard: charts of this run against the base commit and the first recorded run.
- Changed: what was kept and why it's better, with before-and-after pictures where they help.
- Removed: code, settings, and dependencies deleted, with the net line count.
- Tried and rejected: each with its measured result. In breakthrough mode, include the bets that died and what ended them.
- Choices made alone: decisions you made without me, so I can overrule them.
- Not confirmed: anything you couldn't verify or run, and where you looked.
- Next: the top of the ledger.
Keep your last message short: the "Needs from me" items and where the page is.
</final_report>
