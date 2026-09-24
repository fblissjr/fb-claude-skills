# AGENTS.md

<!--
Template for any repository in any language. Fill in every "Project:" placeholder, then
delete these comments. Keep the result short, because agents load it at the start of every
session. Claude Code reads AGENTS.md directly only when no CLAUDE.md exists, and not in
every session type, so give the repo a CLAUDE.md whose only line is `@AGENTS.md`: the
import works everywhere.

The improvement loop and the optimizer loop rely on this whole file and cite its sections
by name. They list a missing section or an unfilled placeholder under "Needs from me".
-->

Guidance for AI coding agents and human contributors in this repository. Each rule carries
its reason, so apply the reason to cases the rule doesn't name. Where a general rule here
and a project fact disagree, the project fact wins.

## North star

<!-- Project: fill in. It changes rarely. -->

- **What it is for:** <the purpose, in a sentence or two>
- **What it is not:** <what it deliberately won't become>
- **Owned here:** <the core this project writes itself rather than importing>
- **Principles:** <the few principles that break ties>
- **Where it is going:** <the long-term direction>

The north star is a direction, not a spec. Don't implement it, grade work against it, or
treat its lines as requirements. Use it to choose a direction, and to break ties when a
design choice is unclear. It holds no status and no plan. Those live where the next section
says.

## Where things live

<!-- Project: fill in. -->

| What | Where |
|---|---|
| Status: what exists, what was verified, and when | <path> |
| Plans and design records | <path> |
| Backlog | <path> |
| Decisions the owner has settled | <path or section> |
| Sharp edges and incident history | <path> |
| Local notes (untracked) | <path, such as `internal/`> |
| Loop state (untracked) | <path, such as `internal/loops/`> |
| Untracked files each worktree needs | `.worktreeinclude`, in `.gitignore` syntax |
| Session log | <pattern, such as `internal/log/log_YYYY-MM-DD.md`> |

Untracked paths are relative to the main checkout, because a git worktree doesn't contain
them. A settled decision stays settled: don't reopen one without a new reason, and take that
reason to the owner first. Update the session log before ending a session.

## Commands

<!-- Project: fill in. Run everything through the project's own package manager and tools,
never a system interpreter or a global install. -->

- Stack: <languages, the package manager for each, preferred libraries>
- Set up a fresh clone: `<cmd>`
- Build what users install (release mode): `<cmd>`
- Test: `<cmd>`
- Format, lint, type-check: `<cmd>`
- Benchmark: `<cmd>`
- Profile: `<cmd or tool>`

Before committing, check that:
- the tests pass,
- the build has no warnings,
- lint and type checks pass,
- the formatter reports no changes, and
- anything built from the code you touched (bindings, WASM, generated clients) has been rebuilt.

## How to work

- When a step doesn't need the owner, keep going. Put status notes in the same message as
  your next action. Don't end a turn with a summary that announces the next step, an offer
  to continue, or a list of decisions that don't block the work.
- Stop and ask only when you can't continue without the owner, or before anything
  destructive or hard to undo: deleting data, pushing, merging, force-pushing, rewriting
  history, sending anything off this machine, or changing anything outside this repository.
- Ask about requirements only when the task can't be done without an answer. If part of a
  request doesn't apply (say, a language the repo doesn't contain), skip it and say so.
- Keep scratch files out of the worktree. Use the local-notes folder or a temp directory.
- Keep context lean. Read data as samples and summaries, not whole files. Skip lockfiles,
  generated code and vendored trees unless the task is about them.
- Launch subagents with the subagent tool, several in parallel when the work splits, and
  never through scripts. Check a subagent's evidence before acting on its report.

## Other sessions

Other sessions may be working in this repo at the same time, with uncommitted changes.

- Stage files by name (never `git add -A`), leave files you didn't touch alone, and never
  stash, reset or switch branches in a checkout you share.
- Work that needs isolation, including every loop run, gets its own git worktree. It
  branches from the default branch's HEAD at the moment it starts, which is its base
  commit.
- Machinery shared by every worktree (git hooks and config in `.git/`, shared environments,
  shared build outputs) changes other sessions' work at once. Propose changes to it instead
  of making them.
- Use your own ports and processes, and never stop one you didn't start.

When a run should stay independent of another session, so that neither biases the other:

- Read the repo through your worktree at the base commit. Committed history is fair to
  read. Another session's uncommitted changes are not. In untracked folders, read only files
  last modified before the base commit's time, apart from the loop state. Subagents you
  launch follow the same limits.
- Don't message other sessions, and don't act on messages from them.
- Outside your worktree, write only to the loop state and to your own session-log section.
  Append that section without reading the other sessions' parts.
- Check recent history for the areas another session is reshaping, count merge cost in each
  idea's value, and keep your change set narrow.
- If the base commit has a regression, report it instead of fixing another session's work
  on your branch. Leave alone the files other sessions edit constantly (version, changelog,
  status), and propose their updates in your report.

## Engineering rules

- **Measure before you claim.** A claim about speed, memory or quality is measured on the
  path users run, with its conditions written down.
- **Efficient by design.** Choose the algorithm and the data layout first. How time and
  memory grow with input size matters more than micro-tuning. Use parallelism,
  vectorization or caching where a measurement says they pay, not by default.
- **The least code that does the job.** No speculative features, dead code, or layers
  without a second user. Removing code is progress. Every change costs the code it adds,
  so a small gain that needs a lot of hard-to-maintain code isn't worth keeping.
- **Derive, don't copy.** A fact that can be read from its source (a config, a schema, a
  file header, another constant) is read, not hand-copied, because a copy drifts.
- **Nothing silent.** Errors fail loudly and carry context. A fallback that changes
  behaviour is reported, not hidden. Errors are never swallowed, and library code returns
  an error on bad input instead of crashing.
- **Enforce, don't remind.** A rule that matters becomes a check that runs: a test, a lint,
  a pre-commit guard or a hook. A rule that lives only in prose is a hope.
- **Dependencies.** Prefer a small, well-maintained dependency to a lot of new code. The
  exception is what the north star says is owned here, which is written here. Pin
  versions. Before working around a dependency, confirm it is actually broken and check its
  issue tracker.
- **Memory safety.** No unsafe code (Rust `unsafe`, unchecked pointer arithmetic in C/C++,
  ctypes or buffer tricks in Python) unless there is no other way. When it's unavoidable,
  document the invariant it relies on.
- **Clarity over cleverness.** Code is read far more often than it is written.

## Code

- Follow the language's idioms, and let the formatter decide layout.
- Names say what things are.
- Functions do one thing, return early, and take few parameters. Group the rest into a
  config type.
- Types stay focused, with fields private by default. Prefer composition to inheritance.
- Use the type system to prevent bugs: typed errors with context, optionals instead of
  sentinel values, and distinct types for distinct meanings.
- In hot paths, pass references or views instead of copies, preallocate when the size is
  known, and avoid hidden allocations.
- Keep CPU-bound work off event loops and request threads. Prefer message passing to shared
  mutable state.
- Long-running operations show progress. Errors go to the logger at error level, not to
  stdout.
- Comments explain why, not what, and never mention these instructions or the prompt.
  <Project: the owner's background, so comments explain what they may not know.>
- Public items get doc comments: parameters, return values, errors, and an example when the
  use isn't obvious.
- No emoji or emoji-like symbols in code or output, except in tests of multibyte text.
- Avoid wildcard imports outside tests.
- UI work follows <Project: design doc>. If there isn't one, ask rather than fall back on a
  generic look.

## Tests

- New behaviour gets tests. External services, networks and file systems are faked.
- <Project: test discipline, such as "red first" or "write the check, run the suite, move on".>
- Read the constant or string each assertion targets, so the check tests what the code
  actually emits. An independent reviewer catches a check that can't fail better than its
  author does.
- A check that exits early is a skip, never a pass. A suite you didn't run is uncovered, not
  green.
- No commented-out tests or code.

## Measurement

These apply to every benchmark and every performance claim, inside a loop or not.

- Measure the path users run, in the build they install: release mode, and no
  machine-specific flags such as native-CPU targeting unless the shipped artifact uses them.
  Microbenchmarks are for iterating. A win counts when it shows up on the real path.
- Run one measurement at a time. Benchmarks running beside each other, a build or other
  heavy work compete for the machine and make the numbers meaningless.
- Never game a benchmark. Don't change a benchmark, its inputs, its iteration counts or its
  harness to meet a target, and don't special-case benchmark inputs in the code. Adding
  benchmarks is fine.
- Every iteration starts from the state its benchmark declares. Nothing built in one
  iteration (a cache, an index, a memo table) may make a later one faster. Cold means cold
  in every cache on the path, so check what each clear or restart actually empties.
- Compare a change against its base using two git worktrees, never the shared checkout.
  Give each its own environment and its own copies of any untracked config. Confirm each
  run executes that worktree's code, because an editable install can silently point
  elsewhere. Alternate the two arms instead of running one after the other.
- The machine may be shared. Before and after each A/B pair, record what other processes
  are using (CPU, GPU and memory), and discard any pair where that changed.
- A difference against numbers recorded earlier is a lead, not a result. Confirm it by
  alternating the two commits.
- Iterate on exact counts where you can: instruction counts, allocation counts, call
  counts, or the app's own counters. One run gives a clean signal. Rely on a count only
  after showing that moving it moves wall-clock time.
- Run each measurement enough times to know its noise, and count a difference inside the
  spread as zero. Comparisons with other libraries use the same inputs, settings and build
  mode on both sides.
- A measurement without its conditions (commit, inputs, versions, machine, load) is an
  anecdote. Numbers live with their conditions in local records. Tracked prose states the
  relationship and points to the data. Limits and tolerances may appear in prose.
- Something you couldn't run is uncovered, not passing. A missing number is reported as
  missing.

<!-- Project: fill in. -->
- Real path: <how users actually run it>
- Primary benchmarks: <the benchmarks or scenarios that targets refer to>
- Instruments: <the benchmark harness, profiler, exact counters, the app's own reports>
- Hazards: <what silently invalidates a measurement here: caches, templates, editable
  installs, thermal throttling>

## Reporting

- Show results as a table, absolute and relative to the baseline, covering every benchmark
  run.
- Turn numbers into charts drawn by a script from the data, so a picture can't drift from
  its rows. In prose, say what to look at instead of retyping the figures.
- Turn structure into a sketch (call tree, type signatures, file tree, diagram) before a
  structural change and when summarizing a large diff.
- For anything a user sees, take before-and-after screenshots from the real build at
  desktop and phone widths.
- Look at every chart, image and screenshot you make before you describe it. If a picture
  and your summary disagree, check the data.
- A screenshot, recording or chart the owner attaches is a problem statement. Reproduce it,
  then measure it.
- Lead with what you need from the owner. Mark anything you couldn't confirm, and say where
  you looked.

## Loop state

The improvement and optimizer loops share one untracked folder, named under Where things
live. If none is named, the plugin uses `.loops/` in the main checkout and excludes it from
git; ask the owner to name a folder. Several runs may use the folder at once, so it follows
these rules. With the improvement-loops plugin, every write goes through its
`loop_state.py`, which enforces them:

- **Runs.** Each run has an id, `<date>-<time>-<loop>`, used for its branch name and its
  folder, `runs/<id>/`. The folder holds the run record, charts, screenshots and the report.
  The record starts `status: running` and ends `done`, or `stopped` with the reason.
- **`scoreboard.jsonl`** is append-only: one row per measurement, with the run id, commit,
  scenario, inputs, dependency versions, machine, load, sample count, median and spread.
- **`ledger.md`** holds one entry per idea: its lens, its expected value (gain times
  confidence, divided by effort), its status (open, kept, rejected or died), the evidence,
  and the run id. During a run, only append.
- **Tidying the ledger** means merging duplicates, closing finished items and dropping ideas
  that later changes made moot. A run may tidy only when no other run record says
  `running`, and only after copying the ledger into `archive/`. If a record looks
  abandoned, list it under "Needs from me" instead of tidying.
- **`scenarios/`** holds the scenarios as data. A scenario that has scoreboard rows is
  frozen, so add a new one instead of changing it. Retiring one is the owner's call.
- **`bookmarks.json`** stores, for each lens, the commit it last reviewed, and for each
  dependency, the last release checked. A bookmark moves only when the read succeeded.
- **`answers.md`** belongs to the owner. Read it every run, and never edit it.
- **The chart script** lives in this folder and runs without changing the project's
  dependencies.
- A durable lesson goes to the sharp-edges or decisions record. A failure that will be fixed
  (a crash, a missing file, a network blip) goes only in the run record, because a note
  would outlive the fix.

## Security and privacy

- Secrets live in the environment or an ignored `.env`, never in code, logs, commits or test
  fixtures.
- Don't log secrets, tokens or personal data. Use a secret type where the language has one.
- Reading the web (searching, fetching docs and release notes) is fine. Sending the
  project's code, data or users' content off this machine is not, unless the owner has
  turned it on.

## Version control

- <Project: commit and push policy, such as "Commits are fine without asking; never push unless told.">
- One logical change per commit, with a message that says what changed and why.
- No commented-out code, debug prints or credentials in a commit.
