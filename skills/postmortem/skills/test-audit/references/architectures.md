# Envelope question packs by project shape

The claim/oracle/envelope method is invariant; which envelope questions bite
depends on the shape of the system. Use the pack that matches, and treat every
"no" answer as a suite-level finding: defects of that kind are unreachable by
construction.

## API / LLM server (backend only)

- Which of the server's real backends/providers/models does the harness start?
  A suite that always runs against one mock or one small model cannot see
  provider-specific serialization, streaming, or token-limit behavior.
- Are streaming responses tested as streams (chunk boundaries, early client
  disconnect, mid-stream errors), or collected into a string first? Collected
  streams hide every framing defect.
- Do e2e tests exercise the real serialization path (actual HTTP, actual
  content types), or call handlers in-process?
- Concurrency: does any test run two requests at once? Single-request suites
  cannot see shared-state bleed (caches, KV state, session leakage between
  conversations).
- For LLM-shaped outputs: what is the oracle? Exact-match oracles rot on model
  or prompt changes (scar tissue in the making); property oracles (schema,
  bounds, invariants) age better. Note which kind each assertion is.
- Error paths: are provider timeouts, 429s, and malformed upstream responses
  ever injected?

## Full-stack e2e (frontend + backend together)

- How many viewport sizes, and which? One viewport means aspect-dependent
  layout defects are unreachable — the canonical envelope failure.
- One browser or several? One color scheme, locale, timezone?
- Is the backend the real one or a mock? If mocked, the contract between the
  mock and reality is itself an unaudited claim — when did fixtures last get
  regenerated from real responses?
- Do tests wait on real readiness signals or on timeouts? Timeout-based waits
  are oracles that pass by luck and fail by machine load.
- Auth states: is anything tested logged-out, expired, or under-privileged, or
  is the fixture always an admin?

## CLI tool

- Are exit codes asserted, or only stdout? A CLI that prints the right thing
  and exits nonzero (or the reverse) passes stdout-only oracles.
- Golden files: when were they blessed, by whom, against what claim? A golden
  file updated by re-running the tool "because the output changed" is an
  oracle that approves everything — decorative by definition.
- Is stderr separated from stdout in assertions? Interleaved capture hides
  broken pipelines.
- Does any test run the installed artifact (packaged entry point) rather than
  the in-repo module? Packaging defects are invisible to in-process tests.
- Non-tty, piped, and empty-stdin conditions: exercised at all?

## Perceptual / generative pipeline (rendering, media, film)

- **A proxy can reject, never approve.** Luminance checks, motion profiles,
  and structural lints gate the floor; only a human (or a measured perceptual
  bar) approves the output. Which of the suite's checks are proxies being
  treated as approvals?
- What rendering conditions does the harness reach — one viewport, one
  renderer, one sample timestamp? A gate met at one condition proves that
  condition only. Sample multiple timestamps; a single `t` can land on a blank
  frame and approve anything.
- Determinism oracles: byte-identical comparisons hold only within one
  renderer/platform; crossing renderers needs a perceptual metric (PSNR or
  equivalent) with a stated bar.
- For every visual check: did the positive control run? Feed it a known-bad
  input and confirm it rejects. A green visual check with no verified positive
  control is the "green control that never ran" failure.

## Data pipeline / warehouse

- Fixture scale: row counts small enough that every plan is a full scan cannot
  see partition, ordering, or spill behavior.
- Are schema oracles structural (column names/types) or semantic (grain,
  uniqueness of keys, referential integrity, accepted-values)? Structural-only
  suites pass while the data is wrong.
- Idempotency and late-arriving data: is any test a re-run over the same
  input, or an out-of-order arrival? Single-pass suites cannot see either.
- Null/empty envelope: empty partitions, all-null columns, zero-row sources —
  reached at all?
- Time: are tests pinned to a frozen clock, or do they pass only for dates
  near when they were written?
