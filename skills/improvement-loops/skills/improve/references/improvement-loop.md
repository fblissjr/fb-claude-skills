Improve this project one run at a time: faster in real use, less code, a more truthful account of what it does, and rules that now run as checks.

This prompt works with the repo's AGENTS.md. Its North star gives the direction and breaks ties. It is not a spec, so don't implement it or grade work against it. The rest of AGENTS.md applies as written: how to work, other sessions, measurement, reporting, and the loop state's files and formats. This prompt adds only what a run needs. If AGENTS.md lacks a section this prompt relies on, or leaves a placeholder unfilled, list it under "Needs from me" and use the nearest thing the repo has.

A run is done when:
- anything that regressed since the last run is reported, and fixed if it is yours to fix,
- every change you started is committed with its evidence, or reverted and logged,
- the headline results were re-checked on the branch's final commit,
- the report, the run record and your session-log section are written, so a new session can pick up without this conversation, and
- a reviewer graded the finished run against this list and found nothing unmet.

<parameters>
- Goal: steady. Work the ledger by expected value until the budget is spent or nothing worth doing is left. Two ideas in a row that don't pay off mean it's time to relaunch the reviewers, not to stop. (Or "breakthrough": spend the run on one big bet, as step 4 describes.)
- Focus: none. (Or name an area or a plan item.)
- Target: none. (Or set one, such as "the primary benchmarks 1.2× faster than the first recorded run".)
- Other sessions: none. (Or name them, such as "mrblue is continuing a refactor on the default branch". Then the rules for staying independent in AGENTS.md's Other sessions section apply.)
- Run budget: about 4 hours. Record the start time and check `date` against it.
- Landing: a branch `improve/<run id>` from the base commit, in its own git worktree, one commit per change. State each commit's evidence as a relationship plus a pointer to its scoreboard rows. Don't merge or push.
- Speed: no scenario slower than the base commit beyond its measured noise, and never more than 3% slower.
- Memory: flag any peak-memory increase over 5%.
- Quality: all tests pass. Quality metrics and deterministic outputs match the base commit within the run-to-run variation you measure on unchanged code.
- Code: the codebase grows only when the new code buys a measured gain a user would notice, or fixes a correctness or visibility problem.
- Reviewers: one read-only subagent per lens.
- Report: a local page. (Or "artifact": also publish it, if this session can, so I can read it on my phone.)
</parameters>

<measurement>
AGENTS.md's Measurement section applies in full, including the project's real path, primary benchmarks, instruments and hazards. For a run:
- Cover real use with scenarios: the common paths, the slow paths users feel, and edge sizes. Each scenario declares whether it starts cold or warm.
- Where the project has its own reports and counters, use them as the main instrument. If they can't show something you need, making them show it is an improvement in its own right.
- Keep dependency versions and inputs fixed within a comparison. A version bump is its own change, measured on its own.
- Measure the code too: lines per layer, duplication, dead code and complexity.
- Counts are proxies. Never move one in a way that makes the project worse to use or harder to read.
</measurement>

<visuals>
AGENTS.md's Reporting section applies. For a run:
- The chart script in the loop state turns `scoreboard.jsonl` into charts and tables. Each chart names its data file and conditions.
- Each run's report is one page, built by that script from the run's data and readable on a phone. Each item under "Needs from me" carries the picture that decides it and your recommendation.
- Calls of taste are mine. Put before-and-after pairs beside the question.
</visuals>

<lenses>
Start each lens from what the repo already knows: the status, plans, backlog and sharp edges AGENTS.md points to.
1. What's new: techniques and upstream capabilities from the last year that apply here and that the project doesn't use yet. Search the web, and cite each one with its source and date.
2. Hot paths and scaling: work that grows faster than its input, and per-call overhead.
3. Reuse: computed work that is thrown away or recomputed when it could be kept safely.
4. Memory: allocation, copies, peak usage and layout.
5. Concurrency, I/O and boundaries: blocking, contention, serialization, round trips, and crossings into other languages or processes.
6. Dead and duplicated code, and layers that could be thinner.
7. Derive, don't copy: hand-kept lists and constants that could be read from their source.
8. Visibility: silent fallbacks, swallowed errors, and behaviour that can't explain itself.
9. Enforce, don't remind: rules in docs, comments or AGENTS.md that no check enforces.
10. Dependencies: local workarounds that newer releases make unnecessary, and fixes that belong upstream.
11. Interface: rough edges in the API, CLI or UI, including phone use for anything with a UI.
12. Security and privacy.
13. Checks that can't fail: tests and assertions that would pass on broken code.
</lenses>

<each_run>
1. Orient. Create the run id and the worktree, and start the run record. In your worktree, read AGENTS.md and the status, plans and backlog it points to. In the loop state, read the ledger, the scoreboard, the bookmarks and my answers. Read the git log since each bookmark, and check pinned dependencies' release notes since theirs. Check that every file, command and behaviour this prompt and AGENTS.md name still holds on the base commit, and list any that don't under "Needs from me".
   If the loop state is empty, this is the first run. Build only the scenarios the first ideas need, record the base commit, and get to a first kept change in the same run. Grow the scoreboard as later ideas need it.
2. Measure. Run the scenarios on the base commit and compare them with the last run's rows. Any difference is a lead. Before calling it a regression, confirm it by alternating the two commits in two worktrees. Then find the commit that caused it (bisect if needed), and fix it first or put it under "Needs from me".
3. Find. Launch the reviewers in parallel, one per lens. Skip a lens whose bookmark shows that nothing it covers has changed. Tell each one:
   - Read code and the web only. Don't edit files, build, run tests or benchmarks, or start processes. Those compete for the machine and make timings meaningless.
   - For each idea, cite the file and line, say how it works, estimate the gain or the lines removed, and name the risk. Mark each claim as measured, read in the source, or reported elsewhere. Where a claim needs data you don't have, write "verify:" instead of guessing.
   - Return at most 5 ideas, ranked by expected value. In breakthrough mode, lead with the single biggest change you would bet on.
   Before you add an idea to the ledger, read the code the reviewer cites to check its claim, and check whether the ledger already rejected it.
4. Improve.
   - Steady: take silent failures and other correctness problems first, then the rest by expected value.
   - Breakthrough: choose one bet, the candidate with the largest expected effect in the direction the north star points, weighed against its risk and merge cost. Before you start, write in the run record what result, by what point, would make you drop it. Prototype the riskiest part first. If the bet dies, log why with the evidence and take the next candidate.
   When an idea is promising but large, try it instead of logging it for later. For each change:
   a. Make sure a check covers the behaviour you're about to change, following AGENTS.md's Tests section.
   b. For a structural change, sketch the before and after first.
   c. Change the code, iterating on exact counts where you can.
   d. Run the tests and the relevant scenarios, alternating with the base worktree.
   e. Keep the change only if it improves the scoreboard, removes code, or fixes a correctness or visibility problem; regresses nothing beyond tolerance; and is worth what it adds. Otherwise revert it and log the result.
   f. If the change sets up something that could quietly decay (a count, a behaviour, a rule), add the check that enforces it. For shared machinery such as git hooks, propose the wiring instead of installing it.
   g. Commit, then append to the ledger and the scoreboard. Put the updated table in the same message as your next action.
5. Review. Relaunch reviewers on the run's diff. Ask them for:
   a. whether each change does what its ledger entry says,
   b. only the problems they would block the merge for, each with the file and line, why it's wrong, and how to show it fails, and
   c. new backlog items.
   Fix whatever blocks the merge, and log the rest.
6. Verify. On the branch's final commit, re-run the scenarios behind every headline result. Later commits can undo earlier wins, so report only what holds.
7. Report. Build the page, finish the run record, append your session-log section, and tidy the ledger if AGENTS.md's Loop state section allows it.
8. Grade. Give one reviewer this prompt's "done" list, the run record and the report. Ask only for what is unmet, plus any change that pulls against the north star's principles or its "What it is not" list. If something is unmet, fix it, then repeat from step 6.
</each_run>

<scope>
- Stay inside what the north star says the project is for. An idea its principles or its "What it is not" list rules out is rejected, however good it is.
- Before deleting something that looks unused, say what it does and why nothing the project is for needs it.
- A new measurement or check that makes something visible counts as progress. Log it like any other change.
</scope>

<final_report>
The page and your last message start with the same headings, in this order:
- Needs from me: decisions, approvals and merges waiting on me, each with the picture that decides it and your recommendation.
- Scoreboard: charts of this run against the base commit and the first recorded run.
- Changed: what was kept and why it's better, with before-and-after pictures where they help.
- Removed: code, settings and dependencies deleted, with the net line count.
- Tried and rejected: each with its measured result. In breakthrough mode, include the bets that died and what ended them.
- Choices made alone: decisions you made without me, so I can overrule them.
- Not confirmed: anything you couldn't verify or run, and where you looked.
- For the merge: proposed updates to files other sessions edit, when other sessions are active.
- Next: the top of the ledger.
Keep your last message short: the "Needs from me" items and where the page is.
</final_report>
