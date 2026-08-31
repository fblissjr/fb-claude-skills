---
mode: session
scope: heylook-provider-twin-alignment
date: 2026-08-31
summary: Diffing prose against source found what neither document's own delta contained, but no check here could observe a wire claim — the worst defect ran five upstream releases and was found by a third party measuring the route live.
artifacts:
  - skills/heylook-provider/skills/heylook-provider/SKILL.md
  - skills/heylook-provider/skills/heylook-provider/references/wire_reference.md
  - skills/heylook-provider/skills/heylook-provider/references/client_recipes.md
  - skills/heylook-provider/tests/test_image_recipe.py
  - skills/heylook-provider/tests/test_probe.py
  - CHANGELOG.md
  - fc39c4f
  - d7b1c63
  - 19a74f7
  - 4326c33
  - e552174
  - 5a4bd16
  - 77ac5fe
  - a528441
  - 7b330ed
  - 912ccd8
  - 545c7f4
---

The task as given: check that `skills/heylook-provider/` is aligned with the
current state of the heylookitsanllm server, whose integration doc and OpenAPI
schema were said to be up to date.

It shipped eleven releases (`fc39c4f`..`545c7f4`, plugin 0.4.5 → 0.9.0)
covering upstream 1.79.43 through 1.79.53.

The framing comes from the server's own integration guide, which states of this
skill: "That skill and this document are TWINS and must move together. They
describe one contract from the two ends, so a change to the wire belongs in
both in the same pass." They had not moved together; the doc had advanced
through two releases the skill did not carry.

Citations to the server repo name commits rather than paths, since that tree is
not one a reader of this file can open. Load-bearing sentences from it are
quoted inline, as above.

## 1. What went well

- **Diffing the twin doc against the server source found three defects that
  were in neither document's delta.** The upstream prose delta since the
  skill's old baseline contained exactly two changes plus a meta note; the
  findings that mattered came from the source and the generated schema instead.
  The sharpest: both copies used "audio to any MLX model" as an example of
  `capabilities` over-reporting, when the MLX branch of the server's capability
  resolver never appends `audio` at all — so gating alone already keeps a
  client off it, and the refusal is what you get for ignoring the gate rather
  than a broken promise (`fc39c4f`, `CHANGELOG.md` 1.44.0). Reading either
  prose copy on its own would have reproduced the error in both.

  *Structural version: when two documents describe one system, the defect they
  share is invisible to any comparison between them.*

- **Enumerating the extensions list from the exported schema instead of writing
  a count paid off two releases later without an edit.** `SKILL.md` had named
  four request fields where twelve had no Anthropic equivalent — the same
  defect upstream had already fixed in its own copy and this skill inherited
  unfixed. Replacing it with an enumeration derived from `MessageCreateRequest`
  (`fc39c4f`) meant that when `include_performance` was removed upstream, the
  list corrected itself — the exported schema went 23 declared properties to
  22, that field the only removal (`19a74f7`, `CHANGELOG.md` 1.46.0).

- **Checking reported claims at the read sites changed what shipped, three
  times.** A peer session reported that `/v1/chat/completions` honoured
  `X-Request-ID` before `/v1/messages` did — true of the header read, and it
  would have shipped as though cancellation predated 1.79.44 on that wire. The
  server's `.44` diff shows the pre-existing line reading the header for log
  correlation only; all three copies now say the route is `.44` on both wires
  (`e552174`). Separately, a report that the non-streaming response omitted
  three `performance` fields turned out to conflate the two modes, and tracing
  the builder showed which one actually dropped them (`4326c33`).

- **Two of fifteen code-review findings were wrong, and rejecting one exposed a
  different real defect.** The review claimed a malformed cancel id returns 422;
  the server's handler takes a bare string, so nothing validates and the id
  misses the registry and 404s. But checking it showed this skill's own 422 row
  described a branch that could not be entered — the defect its history already
  condemns twice over. Row dropped (`5a4bd16`, `CHANGELOG.md` 1.46.3).

- **The version cascade held across all eleven releases.** Each carries
  `plugin.json`, the root `marketplace.json` and a `CHANGELOG.md` entry;
  `skill-maintain validate` passes on the final tree. No `tools/heylook-provider`
  exists, so no fourth bump was owed.

## 2. What did not go well

- **The worst defect ran from `d7b1c63` to `545c7f4` and was found by neither
  documentation side.** 0.6.0 documented `POST /v1/models/{id}/load` with its
  400 and its warm-failure 200 and gave it no backpressure branch at all. The
  server answered **500** for backpressure on that route — the same condition
  `/v1/messages` has always returned as a 503 — carrying, in the server's own
  words, "the identical sentence", on a route where 500 also means the model
  genuinely failed to load. A client following this skill sent a transient,
  self-clearing wait down its broken-model path. Fixed upstream in 1.79.53 and
  carried in `545c7f4` (`CHANGELOG.md` 1.48.0). It was found by a consuming
  client measuring the route live.

  *Structural version: two documentation sides diffing against source both read
  what a route does; neither asks what it fails to do.*

- **Advice was reversed one release after it shipped.** 0.7.0 told clients to
  send `include_performance: true` explicitly "to survive either resolution"
  while the question was open upstream; 0.7.1's evidence closed it the other way
  — the field was removed, not gated — so on that wire there is nothing to send
  (`19a74f7`, then `CHANGELOG.md` 1.46.0). The advice was correct when written
  and wrong within the hour. Recorded as a reversal in the changelog rather
  than edited in place, which is the only reason a reader of 0.7.0 can tell.

- **A code review of the first five commits returned fifteen findings, thirteen
  of them real** (`5a4bd16`). Among them: the cancel advice depended on a
  response header a client recipe's own comment said did not exist; per-request
  id uniqueness was load-bearing and stated nowhere; and `DELETE /v1/requests/{id}`
  is api-key gated with the skill silent on it. That work had already been
  through per-commit self-review and a peer's audit.

- **The same failure shape recurred four times: the summary looser than the
  reference beneath it.** `SKILL.md` generalized what `wire_reference.md` stated
  precisely — the telemetry claim (`77ac5fe`), and three `Done means` items. The
  fourth was the inversion: the id-uniqueness rule sat in the checklist while
  the operational instruction it corrects never mentioned it, and the checklist
  pointed at that section as its source (`912ccd8`, `CHANGELOG.md` 1.47.3).
  Each was fixed as found, which is the pattern that guarantees the next one;
  only after the third was the form changed rather than the text (`a528441`).

- **The fix for an under-specified claim created a duplicate of it in the same
  commit.** Splitting the `performance` absence cases into three standings put
  the durations claim in the streaming section while the non-streaming section
  kept its own copy — a second copy created by the edit that added the
  precision, one release after adopting an index rule whose purpose is
  preventing exactly that (`7b330ed`, `CHANGELOG.md` 1.47.2). The rule did not
  fire because the new text was not a summary; it was strictly better than what
  it duplicated.

  *Structural version: a precise statement added beside the vague one it
  supersedes starts out agreeing with it, so the moment of duplication carries
  no signal.*

- **A presence-count grep under-reported on its first run here.** Run across
  five files to check where the uniqueness rule had landed, it returned zero for
  both client recipes, which carry it worded differently. Trusting the count
  would have meant editing two files that were already correct
  (`CHANGELOG.md` 1.47.3).

- **A route-name typo shipped into an edit and was caught by grepping the same
  edit.** `/v1/models/{id}/read` for `/load` in the 0.9.0 status table, fixed
  before commit (`545c7f4`).

## 3. Deviations from the plan

| Planned | Shipped | Verdict |
|---|---|---|
| Align the skill with the current server state | Eleven releases across upstream 1.79.43–1.79.53, plus a code-review round and a running exchange with a session in the server repo | Far beyond scope, because the server kept moving during the work |
| One alignment pass against the twin doc and the schema | The twin doc's delta covered two of the findings; the rest came from source and schema | Better than planned — the doc alone was insufficient |
| — (not planned) | A code review returning thirteen real findings against the first five commits | Necessary; the work was not clean |
| — (not planned) | Prior postmortem's forward item 5 annotated as resolved | Required by the filing rules, not by the task |
| Build a schema-versus-prose checker (proposed mid-session) | Declined, with a reopen trigger | Scoped down honestly — retrodiction showed it green on both real finds |

## 4. Escapes (tests)

**No test in this repo could have caught any defect found this session, and no
test was added.** The suite is two files: `skills/heylook-provider/tests/test_image_recipe.py`,
which executes the Pillow resize recipe extracted from `client_recipes.md`, and
`skills/heylook-provider/tests/test_probe.py`, which pins `probe.py`'s exit
codes. Every defect this session was a claim about an external server's wire.
Neither file can observe one. This is missing coverage in the sense that nothing
watches, not green-but-blind — there is no test to be blind.

The harness did its job where it applies: it ran green after the two
`client_recipes.md` comment edits (`5a4bd16`), confirming the extraction still
matches.

Two escapes are worth naming as classes rather than gaps:

- **Retrodiction of the checker that was proposed and declined.** Run backwards
  against the session's real defects, it would have caught the extensions-count
  regression and a stale path left in prose; it would have reported green on
  the audio over-report and on `include_performance` controlling nothing —
  both cases where the schema and the prose agreed with each other and the
  running code was elsewhere. A second, independent reason surfaced later: the
  `Done means` index broke in a way an anchor checker would also pass, because
  the anchor resolved and the target section simply lacked the rule
  (`912ccd8`).

  *Structural version: a check comparing two descriptions can only find them
  disagreeing, so it is green precisely when both are wrong the same way.*

- **Absence is unobservable to everything considered here.** The upstream 503
  omission existed because a new caller never reached a shared responder that
  was correct throughout — nothing was duplicated and nothing could drift.
  Presence-count greps, schema-versus-prose comparison, and anchor checking all
  ask what is present. None answers "who should have called this and did not".

## 5. Forward items

1. **A route added to this skill gets its status set derived from the route's
   declared responses in the exported schema, not from prose.** The 503 gap
   existed because `/v1/models/{id}/load` was documented from the narrative that
   introduced it. Checkable: the next release adding or changing a route in
   `SKILL.md` cites the export in its `CHANGELOG.md` entry. Refuted if a route's
   status set is again taken from a doc or a report.

2. **Forward items name an event, not a repeating state.** The 2026-08-04
   postmortem's item 5 ("`git log origin/main..HEAD` empty") went false eleven
   times during this session and true again only at the end, so it could never
   record that the stack it meant had shipped. Checkable: items in postmortems
   filed after this one name a commit, a file, or a one-time condition. Refuted
   by any new item phrased as a persistently-checkable tree state.

3. **The declined schema-versus-prose checker reopens on evidence, not on a
   date.** Its one real class is field lists and counts drifting from the
   export. Checkable: if two consecutive releases correct a field list or count
   that the export already contradicted, build it. If instead the next such
   correction again comes from source-diffing, the decline was right.

4. **A third instance of the shared-speller omission is the trigger to act on
   absence-blindness.** Two are recorded: upstream's busy-503 responder gaining
   a route that never called it, and its own docstring counting its callers by
   hand. Checkable: a third instance in either repo, in which case the cheapest
   form — a helper's docstring naming its callers with the reason attached — gets
   proposed as a convention rather than left as one module's habit. Refuted if
   the next such omission is caught by something mechanical instead.

5. **`verified_against` is the skill's only staleness signal and it is
   manual.** It reads `heylookitsanllm 1.79.53`. The server published 1.79.48
   through 1.79.53 while this one session ran, so the field was stale at six
   separate points within a day and was corrected each time only because
   someone happened to be editing the file. Checkable: if a future session finds the
   skill more than two upstream minor releases behind without anyone noticing,
   the field is not doing the job and an upstream-hash trigger should be
   considered. Refuted if drift is caught each time by the twin arrangement.

## Routing

- The check-design lessons (oracle that cannot go red; input silently
  half-parsed; absence unobservable) are already folded into the existing
  `signal-honesty-over-green-boards` memory rather than a new file.
- The declined-checker decision and the three blindness classes are in the
  session log with the reopen triggers.
- Nothing here proposes a `CLAUDE.md` change. The version-cascade invariant and
  the numbers-in-prose rule both held; no hub-level rule was found wanting.
