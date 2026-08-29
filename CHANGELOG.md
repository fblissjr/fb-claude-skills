# changelog

## 1.37.0

### changed
- **`heylook-provider` 0.1.0 → 0.2.0 — the upstream server was fixed, so most of what this skill carried stopped being true, in the best way.** 0.1.0 was built around four divergences between `/v1/messages` and the Anthropic Messages API it advertises. Checking them against Anthropic's actual published shapes rather than the skill author's memory turned up a fifth and reclassified a second: the thinking block and its delta named the field `text` where Anthropic names it `thinking`, so a conformant reader found the block and no content in it; and `stop_reason` carried the provider's OpenAI `finish_reason` vocabulary (`"stop"`/`"length"`) straight onto an otherwise Anthropic-shaped response. Meanwhile the missing `[DONE]` sentinel, listed in 0.1.0 as a trap, is Anthropic being Anthropic — heylook was already right, and the trap only exists for someone porting from the OpenAI wire one route over. heylook 1.79.39 fixed all three real ones (nested `source` accepted alongside the flat form, both thinking spellings emitted, Anthropic's stop vocabulary mapped through one table), so the skill now says "assume Anthropic's spec is the answer" and carries a **closed list** of what is deliberately different: `max_tokens` optional, `thinking` a bool rather than a config object, no tools, the `error` stop reason, and the request/stream extensions.
- **This is the version-of-record for why conformance beats documentation.** The flat-image explanation existed in five prose locations across two repos, and 0.1.0's own changelog entry recorded that nothing watched the set. Fixing the server deleted four of them. What remains is a note that the older spelling still works and a version boundary for anyone who has to support both — which is the difference between a fact you maintain forever and one that maintains itself.
- Both streaming recipes were re-executed against the new grammar and read `thinking` with a `text` fallback.

### fixed
- **`probe.py` answered "yes, go ahead" to a server serving nothing.** `--need vision` against an empty roster exited **0** in text mode and **2** under `--json`, because the two renderers derived the exit code independently. The invocation the skill body documents is the text one, so a gate written from the skill passed on the case it exists to catch. The code is now derived once and both renderers return it, which is the divergence fixed rather than the constant.
- **Three more defects in the same script, all reproduced before fixing.** An HTTP error was caught as a connection failure — `HTTPError` subclasses `URLError` subclasses `OSError` — so a 401 from an authenticated off-machine server answered "start the server with `heylookllm`", advice for a server already running. There was no way to send a bearer token at all, so the probe could not reach the non-loopback server the skill tells you to expect; it now takes `--api-key`, defaults to `$HEYLOOK_API_KEY` (what the server itself reads, so the secret need not enter shell history), and never prints the value on any path. A non-JSON body — the realistic trigger is another service already on `:8000` — raised `JSONDecodeError` as a traceback, since it is a `ValueError` and the handler caught `OSError`. And a `/v1/models` row with no `id` raised `KeyError`, on rows the adjacent line already read with `.get`.
- **The Pillow resize recipe's PNG branch had never run.** `keep_png` read `.format` *after* `ImageOps.exif_transpose`, which returns a new image whose `.format` is `None` — so the check was always false and every PNG was re-encoded to JPEG, including the screenshots the recipe's own comment singles out as showing JPEG ringing. The sibling `sharp` recipe reads `metadata()` before transforming and was never wrong. `client_recipes.md` had labelled its image recipes transcribed-not-executed; the label was right and the risk it named landed. The Pillow recipe is now executed on Pillow 12.3.0 across PNG and JPEG on both sides of `MAX_EDGE` plus an EXIF-orientation case, and the note splits executed from transcribed rather than covering both with one hedge.
- **The 503 retry path no longer depends on the error body being JSON.** `_http_error` parsed the body before checking the status, so a non-JSON 503 lost the `model_overloaded` string that `with_backoff` matched on and the retry never happened. 503 is now decided first and raises a typed `Overloaded` carrying `retry_after`, so the backoff honours the server's `Retry-After` — which the skill body already told you to do, and which the TypeScript sibling already did — instead of string-matching an exception message.
- **1.36.0 claimed this script "was exercised against canned responses ... across all four paths" and left no artifact.** There were no tests; that sentence is struck below. The suite that would have caught the exit-code bug now exists at `skills/heylook-provider/tests/test_probe.py` — 23 cases against a real loopback HTTP server rather than a stubbed `fetch`, because two of the four defects originate inside `fetch` and a stub cannot reach them. Six pin already-correct behaviour and so were born green; each was proved fallible at birth by mutating the behaviour and confirming red. One of those mutations earned its keep immediately by failing to redden, which exposed a real weakness in its own test: `"*" in out` was satisfied by the trailing summary line rather than by the table row it meant to check.
- `heylook-provider` was missing from the root README's plugin table, install list, and slash-command list — the only one of the marketplace's plugins absent from all three. Added under a new **provider integrations** heading rather than beside `gemini-bridge`: that plugin ships a CLI that calls out, this one ships knowledge and calls nothing.
- `openai_wire.md` said server-side image downscaling was "the only functional capability `/v1/messages` lacks". `continue_final_message` is a second, a `ChatRequest` field with no Messages-wire equivalent (`config.py`).

## 1.36.0

### added
- **`heylook-provider` 0.1.0 — the integration contract for heylook (`heylookitsanllm`), written from its source rather than its docs, because the endpoint's resemblance to Anthropic's is the thing that costs you.** heylook serves an Anthropic-style `/v1/messages` beside an OpenAI-compatible `/v1/chat/completions`, and the natural read — "it's Anthropic-shaped, use the Anthropic mental model" — is right about the envelope and wrong at four points, each of which fails silently or fails late. Its image content block is **flat** (`source_type`, `media_type`, `data` at the top level of the block); Anthropic's nested `source` object matches none of the block union's members and comes back a 422. Its stream ends at `message_stop` with **no `[DONE]` sentinel**, so a reader ported from the OpenAI wire sitting one route over hangs until timeout. Its response `content` is a typed block list where `thinking` and `text` are separate, so joining everything puts the model's reasoning into the product's output. And every sampler field is optional with absent meaning *the server cascade decides*, so a client-side `max_tokens` default — required by Anthropic's schema, habitual everywhere — silently overrides the model's configured floor on every request that had no opinion. All four were confirmed against the running schema, not read off prose: the 422 by constructing both spellings through `MessageCreateRequest`, the rest at `schema/content_blocks.py`, `messages_api.py` and `schema/messages.py` in heylookitsanllm 1.79.37.
- **Discovery is a constraint here, not a nicety, and the skill leads with it.** heylook's registry is override-only — anything under a scanned folder is served with derived defaults — so the model roster is whatever the operator downloaded and a literal id in source is a 400 on someone else's machine. The skill also splits `capabilities` from `modalities` and says which one to gate on: the first is what the server will serve, the second is what the checkpoint author declared, and they diverge on purpose, since MLX strips audio towers at load. `scripts/probe.py` (standard library, no install) prints the matrix and exits 2 when a required capability is unserved. *(Corrected in 1.37.0: this entry originally claimed the script had been exercised across all four of its paths. It had not — no test artifact existed, and a review found the empty-roster path answering 0 where it owed 2.)*
- **Four references carry the lookup weight so the body carries only what cannot be derived.** `wire_reference.md` (every `/v1/messages` field, block, streaming event and error payload), `openai_wire.md` (when the other wire is the better choice, the resize params it alone has, and the `processing_mode` schema switch), `gemini_migration.md` (field mapping plus the structural mismatches an abstraction shaped around Gemini has to grow a seam for), and `client_recipes.md` (streaming clients in Python and TypeScript, and the image-resize recipes the Messages wire requires because it has no server-side resize at all).

## 1.35.2

### changed
- **`dev-conventions` 0.17.0 → 0.18.0 — `dep-audit` finally got the pass its two siblings got in 0.17.0, and it needed it most.** It was the longest of the three at 86 lines and the most derivable, and it was the only one that never stated what it carried that a reader could not work out alone — `python-tooling` opens by saying Claude already knows uv and this file holds only the traps, and `doc-conventions` says it holds only what a repo cannot tell you by being read. `dep-audit` made no such claim and could not have. Out went interpreting the tools' output (running them shows you that), a generic audit-assess-upgrade-record workflow, a "when to audit" list that was the same already-default-behaviour class cut from `doc-conventions`, and a flag table reproducing `--help`. What stayed is the actual payload, now stated as the reason the file exists: **both uv and bun ship a native audit subcommand**, which is the non-obvious part, because without knowing that the reflex is to reach for `pip-audit` or `safety` and never find them. Plus the two judgment calls that survive any tool release — check reachability before upgrading on sight, and report the delta rather than pasting a dependency tree. The file now also marks which of its claims are about someone else's tool and therefore the perishable ones, so a future review knows what to re-derive rather than re-reading everything. 86 lines to 52; every remaining command re-verified against uv 0.11.32 and bun 1.3.14.
- **The plugin's identity question resolves as a non-question.** `dep-audit` had been flagged twice as misfiled — a security procedure sitting in a conventions plugin. That was the wrong diagnosis: the topic fits the stated center (what a repo cannot state by being read) and what did not fit was the writing. Slimmed, it belongs where it is, and no move is needed.

## 1.35.1

### fixed
- **`claim-audit` 0.2.0 → 0.3.0 — a single-line `grep` over hard-wrapped prose produces false negatives, and the skill did not say so.** Step 3 already warned that piping a validator through `tail` masks exit status; this is the same class and it bites harder, because the verdict it corrupts is "this rule is stated nowhere" — the one that leads to deleting things. Three instances in one day: a check reported the TDD claim-recoverability rule as uncovered when the phrase merely wrapped between two lines, minutes before a delete that would have relied on it; a check reported `VISION.md` as having no tie-breaker twenty minutes after the sentence had been read aloud, because "when the two / disagree" spans a break; and a third used `\|` inside `grep -E`, where it is a literal pipe rather than alternation, so five rules were reported missing that were all present. The step now says to join lines before deriving an absence claim, and flags the dialect trap. This is the instrument correcting itself with its own evidence, which is the only reason it clears the tripwire.

## 1.35.0

### removed
- **`dev-conventions` 0.16.0 → 0.17.0 — the hooks, the directives, `init` and `configure` are gone, and the plugin is three on-demand skills.** The enforcement hook's premise was that prose is advisory and hooks are not. The measurement says otherwise: across 4,700 transcripts on this machine, **every denial that can be identified was either a search command containing the literal string or a deliberate live-fire test. None was an attempt to run pip.** The mechanism is `command_heads()`, which splits a command on `;|&` **including pipes inside quoted strings** — so `grep -rn "uv lock --upgrade\|pip install -U\|--upgrade"` is torn into a fake command head reading `pip install -U`, which then matches. The function is named for extracting the head of each pipeline stage and does neither reliably. Its own comment at lines 112-116 named ``git commit -m "stop using pip install"`` as a case it must not block; that exact string is in fact allowed, spared by the closing quote sitting where the pattern needs a trailing space — the same accident that spares `rg "pip install"`. Move the phrase one word left, as in ``git commit -m "docs: why pip install is banned"``, and it blocks. So the comment describes a class the implementation half-guards by coincidence rather than by parsing. It has never caught a real violation, because the rule it enforces is already stated in prose the model follows. The SessionStart directives went for a different reason: three of the four were silent in this repo, and the mechanism's whole purpose was to stop an ambient broadcast from duplicating rules a repo had already written. The cheaper answer was to stop broadcasting. `init` scaffolded conventions into a repo's own files — the best idea in the plugin — but it existed to silence the machinery that is now gone, and `configure` managed a config file nothing reads any more. This is the invariant 1c re-audit finally run on a rule written for an older model generation.
- **The `claims-in-docs` directive shipped in 1.34.0 and was retired in 1.35.0, the same day.** It was the right rule delivered by the wrong mechanism, and the audit that killed the mechanism came after. The rule itself survives in both homes that matter: write-time in `/dev-conventions:doc-conventions`, audit-time in `claim-audit` step 5. What it loses is ambient reach, which is the trade this whole release makes deliberately.

### changed
- **Two rules would have been lost silently, and were relocated first.** A sweep before the delete — the order `dangling-refs:retire` exists to enforce, and the one this repo has got wrong before — found that "do not auto-run linters, formatters, or tests after edits unless asked" lived **only** in the Python directive, and the substitution test only in the directive shipped that morning. Everything else the directives carried (uv over pip, bun over npm, both pinning policies, red-first TDD, the recoverable-claim rule) is already stated in this repo's own `.claude/rules/general.md`, which is the arrangement the release is arguing for. The auto-run rule moved to `python-tooling`; the substitution test moved to `doc-conventions`. One intermediate check reported five of those rules uncovered and was wrong — the grep used `\|` inside `grep -E`, where it is a literal pipe rather than alternation, and a sixth miss came from a rule whose text line-wraps mid-phrase. The corrected run is the one above.
- **`doc-conventions` had four sections cut against a single test — does the repo already say this by being read — and grew anyway**, from 61 lines to 81, because the retired directive's content was folded in at the same time. Both halves are true and the net is an increase; an earlier draft of this entry claimed a cut of roughly a third, which was the intent rather than the result and is exactly the descriptive-count failure this release ships a rule about. Out went lowercase filenames and no-camelCase, organising docs into subfolders by topic, "document the why, not just the what", and a "how to generate" section whose content was `git diff pyproject.toml` — an instruction to perform a derivation, which is redundant with performing it. What stayed is what a repo cannot tell you: the last-updated-date convention, where unshared notes and session logs live (already hedged as the owner's layout rather than a universal one), the dependency-change table, and the do-not bullets, since "do not create a `deps.md`" overrides a plausible default.
- **`python-tooling` keeps its shape and loses a claim that the release made false.** It already stated the principle the rest of the plugin now follows — "Claude already knows uv. This skill carries only what it cannot derive" — but its closing bullet said pip and lockfile edits "are blocked by this plugin's PreToolUse hook, so the package-manager preference is enforced rather than explained." No longer true, and it was load-bearing: with the directive gone this skill is the only home for that preference. Its frontmatter also declared no `review_interval_days`, silently defaulting to 30 while its siblings declare 90 and 365; now set deliberately.
- **`skill-maintainer` 0.24.0 → 0.25.0 — `best_practices.md` stopped recommending the pattern this release deleted.** Its "composable directive pattern" section taught `hooks.json` plus `session-start.sh` plus `directives/*.md` with trigger and ground lines as the shape to reach for, and by invariant 3 that is the single copy `/maintain` reads here and in every installed repo — so a plugin author following it today would build the machinery this release retired for being ineffective. The section now leads with the cheaper answer (write it into the repo's own always-loaded files), records that three of four directives were permanently silent in the repo that authored the pattern, names the shape of the trap (a mechanism whose success condition is silence is a bootstrap, not a feature), and asks for a transcript measurement before the pattern is trusted. Kept rather than deleted, because it is still right for behavioural content a repo genuinely cannot state for itself.
- **`python-tooling`'s description could not retrieve what was relocated into it.** The body gained the auto-run override and already held the pinning policy, but the description spoke only of pyright and Pydantic symptoms — so a session editing a clean Python file, or running `uv add`, matched nothing and never loaded the skill at the moment the rules applied. The description now names dependency pinning, `uv add`, and being about to run linters, formatters or tests after an edit. Residual limit worth stating: a retrieval trigger cannot reliably catch a *reflex*, so the auto-run rule is also stated in this repo's own `.claude/rules/general.md`, where it is unconditional.
- **Both relocated rules are deliberately duplicated.** They live in `.claude/rules/general.md` for this repo and in the two skills that ship. That is two copies with different readers at different moments — always-loaded here, retrieved on invocation elsewhere — and nothing watches the pair. Recorded rather than resolved: the alternative is that installs get the rule and the authoring repo does not, or vice versa.
- **The reference sweep, run across both READMEs and three design records.** The root README's plugin row and invocation list described hooks and named two retired skills, and it labelled `dep-audit` "Full bun conversion tables" — it is a CVE audit and always was. `plugin-patterns.md`'s filed-for-0.16.0 proposal (have `init` declare its coverage so the ground regex could demote to a fallback) is marked closed-overtaken rather than deleted, since it is a design record of an approach reasoned through and then removed. `postmortem_output_formats.md` had left "does postmortem read `.dev-conventions.json` or its own file" as an open question; it is settled as its own, and this release confirms it — a shared config would have taken `.postmortem.json` down with the rest. `gotchas.md` was **missed by the first sweep and caught by review**: its retired-disables section, though already headed as history, still asserted in the present tense that the enforcement hooks were "active here again" and cited a test arm as a live tripwire that "goes red before a re-enabled plugin starts broadcasting" — an arm deleted in the same commit. Both now carry a dated closing note. That is the second time in this release that a sweep claimed to have run and had not reached everything, which is the argument for the checker rather than the procedure.
- **The tests that existed only to exercise the directive machinery went with it**, along with `init` and `configure` from the validated skill set. An earlier draft said "nineteen", a number produced by a grep that counted `@pytest.mark.parametrize` decorators alongside `def test_` lines; the file held 18 test functions expanding to 22 collected cases, so the figure was neither, and it was decorative in the first place — the count changes no reader's action.
- **Upgrading with a `.dev-conventions.json` in your repo:** its `rules[]` silently stop loading, because the hook that read them is gone. Move them into `CLAUDE.md` or `.claude/rules/`, which is where this release argues they belonged all along.

## 1.34.0

### added
- **`dev-conventions` 0.15.5 → 0.16.0 — a new `claims-in-docs` directive, carrying the write-time half of a problem the audit family only ever caught after the fact.** The rule is a substitution test: before writing a number into prose, replace it with a different plausible value, and if the reader's next action is unchanged the number is decorative — delete it. "Sixteen constraints are enforced by nothing" and "seventeen constraints are enforced by nothing" prompt the same next step, so the count is liability carrying no information. What survives the test is either **normative** (a limit you are setting, which cannot drift because the world moves toward it) or **descriptive**, and descriptive counts need an observation point and belong only in dated records. The directive states plainly that binding is *not* a lesser fix for a decorative number: it makes the claim permanently true and permanently useless, and still charges every reader a reconciliation against what they can see. Delete first; bind only what passed. It ships as its own file rather than a bullet on `doc-conventions` because ground coverage is per block and a directive file *is* a block — `doc-conventions` declares a ground matching any session-log convention, so it is already silent in this repo, and a bullet added there would never have loaded here. Verified with `--explain`: `claims-in-docs LOADS`, `doc-conventions silent — ground covered`. `trigger: any` rather than `docs`, because the `docs` trigger fires on the presence of a session-log directory, which would mean the repos most likely to carry unaudited README and changelog prose are exactly the ones that never see the rule.
- **`postmortem` 0.8.1 → 0.9.0 — `filing.md` gains closure write-back, because forward items do not inherit the freeze.** A postmortem's body is past tense and cannot become false, which is what makes a dated record safe to leave alone. Its section 5 is the exception: claims about the future sitting inside a frozen document, which read as open work forever if nobody returns. A run in a repo that already has postmortems now scans for forward items carrying no closure annotation and annotates the ones that have since resolved, deriving each item's stated condition against the tree rather than recalling it. The write-back is also a derivation pass, and that is where its second value lies — this repo's own corpus had two items closed in reality and unannotated in the record, and checking them turned up that one had resolved by a route its checkable never anticipated (the disable was not lifted, the whole mechanism was retired) while a second that looked like a shortfall was in fact met, its fourth arm having shipped in a different step from the other three. The scan is bounded rather than sweeping a growing directory forever, and an item whose condition cannot be cheaply derived stays unannotated, which is honest.
- **`postmortem` — a citation the reader cannot reach must carry its load-bearing sentence inline.** Scoped to file paths: a commit hash is a stable identifier anyone holding the repo resolves and a command is reproducible, but a path into a gitignored tree or a private sibling repo is simply dead for an outside reader. Without the rule, "no citation, no finding" holds only for readers who share the author's filesystem, and a postmortem published wider than its evidence quietly degrades into assertion.
- **`adversarial-verify` states how a control couples to its subject, in both directions.** The known half was that a control whose input derives from the thing it checks cannot fail. The other half arrived from a peer repo's adversarial refutation of its own proposed check: a control carrying a *copy* of its subject's content goes red when the subject is correctly changed, and a false red is worse than no check because it teaches people to override the gate. The stable middle is coupling by stable identifier, with `path::symbol` named as the checkable form — it survives insertions above the target and fails only when the named thing stops existing. Positional coupling (`path:line`, "step 4", "the third bullet") is ruled out because it misaims silently, failing without ever looking wrong. Where an enumeration's order carries meaning, a third disposition applies and this repo already used it without naming it: freeze the numbering, declaring entries removed rather than renumbered, which makes position a stable identifier by fiat.
- **`claim-audit` 0.1.0 → 0.2.0 — a fourth disposition, for the prose no command can derive.** Step 5 offered rewrite, tag, or delete, which meant a judgment or design rationale — unsourceable *by construction*, and that is what makes it worth writing — got nudged toward deletion. There is now an explicit out-of-scope disposition, counted in the report's own tallies. A pass that only preserves derivable prose starves the class of writing docs exist for.
- **`claim-audit` — counts take one more question, including the ones that derived green.** A live count that derives correctly today and stays unbound in the prose drifts on the next commit, so a green verdict on one is a temporary result recorded as permanent, which is this skill's own failure class one level up. The audit now applies the same substitution test and recommends deletion rather than a corrected figure where the number is decorative, in the order delete, then bind, then derive. This landed as a sentence rather than the classification machinery first designed for it. Eight commits of real added prose carry 86 markdown lines with a digit in them; classifying roughly half showed the machinery would have fired on two or three claims while emitting rows for the rest, because the house style of dated measurements, attribution and past-tense deltas already does what it would recommend. The sample was half, not all — enough to kill the design, not enough to have measured the base rate.
- **This repo's postmortems are tracked and public, at `docs/postmortems/`.** They were inferred into a gitignored tree by filing's rung 3, which reads the sibling session-log directory — a correct inference that has now been deliberately overridden by a root `.postmortem.json`, since session logs stay private and rung 3 would otherwise keep sending postmortems back. The directory carries a README that states the collection's standard of evidence and **lists nothing**, which is the distinction filing.md's ban actually draws: a listing is a copy whose only consumer is the check that it matches the directory, while a frame makes no claims about contents and cannot drift. `--html` renders are gitignored as derived artifacts. The corpus was reviewed for disclosure before publication by a separate pass that read every file; where a passage was held back, a dated note in that file says so in place rather than closing the gap silently.

### fixed
- **Two positional cross-references that would have misaimed without ever looking wrong.** `adversarial-verify` pointed at the control-builder agent's "step 4" and `postmortem-index` at filing's "rung 4". Both resolved correctly, and nothing would have noticed if a step or rung were inserted above them. Both now cite by name.
- **`claim-audit` claimed its report ends with three numbers while the example beside it showed four.** A live count of the skill's own output format, already wrong, and the new out-of-scope disposition would have made it wrong again. The prose now names the fields instead of counting them — the first thing the new rule caught was the file shipping its audit-time twin.
- **Decorative counts removed from `best_practices_maintenance.md`'s queue.** The specimen that prompted the whole rule was there: a queue item asserting a precise number of hook and agent constraints enforced by nothing, where the count changes no reader's action and the sentence is strictly better without it. Its siblings went the same way, since fixing only the named instance would be making a rule pass by touching what it measures. Removing a decorative number needs no annotation — by definition it changed no finding.

## 1.33.1

### fixed
- **`writing` 0.6.0 → 0.6.1 — the review pass over 1.33.0's two new skills, applied.** `show-me`'s `allowed-tools` granted `Read, Grep, Glob, Artifact`, which pre-approves publishing an HTML page while leaving every other step of that same path prompting: writing the file (`Write`, `Edit`), loading `artifact-design` first (`Skill`), and the no-Artifact fallback (`Bash`). The grant now covers the path it exists for, with Bash scoped to `open`/`xdg-open` rather than blanket. One finding from the same review was refuted on cross-check and produced no change: the description's routing of chart work to `dataviz` was flagged as a pointer at an owner-local skill installers would not have, but `dataviz` sits in the harness's skill listing on the same footing as the `artifact-diagramming` reference beside it — unprefixed, with no repo, user, or project copy on disk supplying it — so both references are bundled and the clause stays. The residual risk is real and shared: the bundled set moves between Claude Code versions and `disableBundledSkills` exists, but that argues for dropping both or neither, and the routing precision is what the description's negative scope is paying for. The fallback said `open`, which is macOS-only; it now shows `open` and `xdg-open` side by side. And the attribution footers came out of the loaded bodies — `show-me`'s "Adapted from…" trailer and `wait-what`'s fifteen-line HTML comment — because the plugin's own README states the convention in as many words: attribution lives in the README so the loaded skill instructions carry no handles or URLs. Everything those blocks said is already in the README and the 1.33.0 entry; in the body it was context cost on every activation. The README also said "Two things changed on the way in" and then described three; the changelog had it right, and the README now agrees.
- **`grilling` 0.1.0 → 0.1.1 — same two classes.** The body carried the same "Adapted from…" footer the writing convention forbids, duplicating the README's Credit section into every activation; removed. The README had no invocation examples, which `.claude/rules/general.md` requires of every plugin README; it now shows `/grilling:grilling` and the trigger phrases.
- **Root `README.md` catches up with 1.33.0.** The plugins table, install list, and invocation list never learned about `grilling`, and the writing row still described a two-skill plugin. `grilling` gets a row and both list entries; the writing row now names all four skills.
- **`phase_boundaries.md` corrected a behavioural claim carried over from upstream.** The options table said `/compact` compresses the context and seeds a fresh session with the summary; in this harness it replaces the history in place and the same session continues. The adaptation pass had checked the doc's numbers and links but not this, and the Adaptations section now records the lesson: adopting a doc means checking its behavioural claims against this harness too.

## 1.33.0

### added
- **`writing` 0.5.0 → 0.6.0 — two skills for prose that should not have been prose.** `show-me` answers with a compact visual instead of a paragraph: pseudocode, call tree, component tree, shallow file tree, types-and-signatures, a diff of any of those, mermaid, or one focused HTML page. Adapted from `humanlayer/skills` (MIT) and the article behind it, with three changes made on the way in. The article treats a **types-and-signatures sketch** as a first-class shape and the shipped skill had dropped it; restored, because it is the highest-value shape during design, when the code does not exist yet and an agent will otherwise infer it wrong. The article's **cost ordering** — text shapes are lighter than HTML and good enough for most dev-shaped problems — is stated outright rather than left implied by list order. And HTML publishes through `Artifact`, where upstream could only write a file and `open` it, which was a limit of their harness rather than a design choice. The description was rewritten around what the article says the problem actually is: not "the user wants a picture" but that agents default to a paragraph when the subject is structure, so it also triggers unprompted during design and while reading a large diff. `wait-what` rewrites a message that did not land, in plainer terms with the project's own vocabulary. User-invoked by necessity rather than preference: the model cannot detect that its own message failed to land, so there is no signal for it to fire on. Adapted from `mattpocock/skills` (MIT); the original assumes a `CONTEXT.md` ubiquitous-language file, and with none here the instruction degrades to whatever vocabulary the project already uses. The plugin README now carries a table for the three-way overlap, since `plain-language-us` (the register is wrong), `show-me` (it should not be prose) and `wait-what` (this specific message failed) are easy to confuse.
- **New plugin `grilling` 0.1.0 — a design interview that works the problem as a tree.** The **frontier** is every decision whose prerequisites are already settled; ask that whole set in one round, wait, then recompute it from the answers. A question whose answer depends on another open question belongs to a later round, because asking it early produces an answer the user will revise, and revised answers invalidate whatever was built on them. Two rules carry most of the value: every question ships with a recommended answer, so the user makes one judgment instead of two; and **facts are the agent's job** — anything the filesystem, config, or codebase can settle gets looked up, never asked, with the lookup dispatched rather than blocking the round. Adapted from `mattpocock/skills` (MIT) with emoji stripped per house style, an `AskUserQuestion` path added for frontiers of two to four enumerable choices, and the fact-finding instruction aligned with this repo's delegation practice.
- **`docs/internals/phase_boundaries.md`** — the ordered tree at a phase boundary: continue, `/clear`, hand off, subagent, `/compact`, first yes wins. Adopted from `mattpocock/skills` (MIT) because this repo had session logs, `finish-session`, and an `advisor` that spawns a bounded subagent, and no written policy on which to reach for when. Two ideas do the work: every move except Continue converts a **primary source** into a secondary one, which is why Continue is ruled out first rather than last; and `/compact` is the **default, not the first reach**, because the four questions above it are each cheaper or more precise and the failure mode of starting there is a fresh session confidently wrong about a decision the summary flattened. Two adaptations: the original's context-headroom figure is model-dependent and moves, so the doc says to re-derive it from `/context` rather than carrying a constant, and the published-vocabulary links are dropped.

### changed
- **The description-quality checker rejected a legitimate verb, and the description moved rather than the vocabulary.** `wait-what` first read "Re-pitch the last message…", which `check_description_quality` failed as "missing WHAT verb" — `_WHAT_VERBS` is a fixed whitelist and `re-pitch` is not in it. Expanding a controlled vocabulary for a single case is how whitelists rot, and `rewrite` is both already accepted and clearer to someone scanning the slash menu, so the description leads with that and the body keeps `re-pitch` as its leading word. Worth recording that the checker is already invocation-aware: it skips the WHEN-trigger arm for `disable-model-invocation` skills, on the stated grounds that requiring a trigger phrase in a description Claude never sees demands text that provably cannot do anything.

## 1.32.0

### changed
- **`skill-maintainer` 0.23.3 → 0.24.0, CLI 0.32.0 → 0.33.0 — `best_practices.md` is one file, and the three mechanisms that existed to keep two copies identical are gone.** The duplication had a PostToolUse mirror hook, a `tests.py` arm asserting the copies matched, and a `gotchas.md` section explaining the arrangement — three controls servicing a copy that failed the repo's own test, that a copy earns its place only if it has a consumer other than the check confirming it is a copy. The decisive part is that the fix was already documented and simply not implemented: `init-maintenance/SKILL.md` has always said "`init` does **not** write a `best_practices.md` into the repo. The plugin's bundled `references/best_practices.md` is the copy `/maintain` reads," while `config.py` returned `config_dir(root) / "best_practices.md"` with no fallback. Both consumers of that path — the provenance join in `upstream` and its arm in `test` — are guarded by `.exists()`, so a repo that ran `init` and never hand-copied the file did not fail loudly; `skill-maintain upstream` printed "Provenance join skipped" and the join silently never ran. `best_practices_file()` now resolves a deliberate per-repo copy first and the bundled reference otherwise, reusing the search that already existed as `tests.py:_find_canonical_best_practices` rather than adding a second one. Verified by the arm that would have gone quiet: `best_practices provenance` reports 23 harness annotations parsed, not a skip. The removed hook was a `PostToolUse` matcher on `Edit|Write|MultiEdit` spawning bash plus jq on every edit to test one path — `docs/internals/context-cost.md` measured `PostToolUse` at 5,994 firings across 27 transcripts at roughly 58ms each, so deleting it is a latency win in every repo where the plugin is installed, for a duplication that no longer exists. The two versions move independently because the marketplace `source` is `./skills/skill-maintainer` and does not ship `tools/`; `sync-versions` step 3d would have bumped the CLI to the plugin's number and downgraded it from 0.32.0, which is a gap in that skill rather than in this change.

- **`best_practices.md` absorbs three authoring levers and takes ownership of three claims it was sharing with `docs/internals/context-cost.md`.** The levers go into the existing `## authoring shape` section rather than a new file, because that section is already `model` class, already rechecked on a model family release, and already a per-instruction checklist — three of the four "new" levers turned out to be constraints with tests, which is exactly what it holds. They are: prompt the positive rather than the prohibition (a ban drags the forbidden behaviour into context and half-reads as an instruction to do it); prefer a pretrained word to a coined one (a coined word recruits no priors, so you pay in definition tokens what an existing word gives free); and every step ends on a completion criterion with two dimensions, clarity and demand, with premature completion as the failure clarity guards and a stated fix order — sharpen the bound before splitting the sequence, and splitting only works across a real context boundary. Adapted from `mattpocock/skills` (MIT), credited in the section. The fourth lever, the two-budget model, landed in `VISION.md` instead, because it is a principle rather than a rule. On the shared claims: the tier test and the emission finding are now stated once as rules here and cited as measurements there, and `context-cost.md` keeps the 27-transcript table, the per-project variance result, the four mining traps, and the "do not rebuild these" list. The emission wording is aligned to the measurement's own term — *emission, not invocation*, since the finding is that a hook fired 5,109 times and emitted zero bytes; "not registration" was the drifted copy. Two tensions are now named instead of left implicit: negative scope in a description is routing metadata read by a selector and is not the behavioural prohibition `authoring shape` warns against, and `description precision` genuinely pulls against `distribution and budgets` because negative scope is the expensive part of a description — neither rule yields, and the total is managed at the set level rather than by shortening descriptions that are earning their length.
- **The skill listing is measured rather than assumed, and the first measurement of it was wrong in the direction that would have justified work.** `/doctor` reports this repo's listing on 2026-08-13 at **26 entries, ~2,300 tokens**, against the ~2,000 a 1% allocation gives at a 200k window: marginally over, comfortable above it. A hand-rolled count taken the same session said 4,391 tokens across 36 skills and was measuring a different quantity — every description *authored* in the repo, including `apps/` plugins that are not enabled. The listing carries enabled plus bundled skills only; this repo contributes 8 of the 26 entries, ~1,358 tokens. Authored is not installed, and any repo shipping more plugins than it enables will overstate its own listing by counting files. The gap that prompted the count was real: the existing budget gates measure SKILL.md bodies, which are conditional on the skill triggering, while the listing is the unconditional cost. But `context-cost.md` already listed `/doctor` (skill-listing cost) and `claude plugin details` (per-plugin always-on versus on-invoke) under "do not rebuild these", and the rebuild happened anyway and lost to the built-in on its first attempt. That is better evidence for the rule than the rule's own argument, and it is recorded next to it. The wrong figure reached `best_practices.md`, which ships; it was corrected in the same working tree, before commit, but it did exist. Also recorded, unaffected by the correction: overflow is silent and drops the least-invoked first, so the rarely-reached skills are exactly the ones that disappear, and the allocation is a fraction of the window, so the answer differs per model and must be computed rather than asserted as a constant.

### changed
- **The per-skill token budget gate moves from 4,000 to the 5,000-token re-attachment cap, and the board goes green.** `skill-maintain test` failed at `TOKEN_BUDGET_WARN`, a house number expressing an opinion about attention. It had been red on `gemini-multimodal` (4,033) and `path-privacy` (4,091) — 0.8% and 2.3% over — for long enough that the red carried no information, while the skill *listing*, loaded unconditionally every session rather than only when a skill triggers, went unmeasured entirely. The gate now fires at `TOKEN_BUDGET_REATTACH`, where behaviour actually changes: above 5,000 tokens a skill is silently truncated when re-attached after a compaction, per upstream. 4,000 and 8,000 survive as reported observations so growth stays visible without failing anything, and `measure`'s report now says which number gates. Repo suite 267 passed / 2 failed → **269 passed / 0 failed**. New `test_token_budget_gate.py` pins all three sides of the boundary; the red-side arm is the load-bearing one, since a threshold edit is precisely the change that can silently stop gating anything, and a gate that cannot go red is decoration. Its import of `test_skills` is aliased because pytest would otherwise collect the source function as a test case, the same reason `test_repo_hygiene_provenance.py` aliases its own.

### fixed
- **`sync-versions` step 3d told you to downgrade a separately-shipped CLI.** It directed `tools/<plugin>/pyproject.toml` to the plugin's new version unconditionally. Applied literally to this release it would have moved the `skill-maintainer` CLI from 0.32.0 to 0.24.0, eight minor versions backwards, because the plugin and its CLI are on independent version lines: the marketplace `source` is `./skills/skill-maintainer` and does not include `tools/`. The step now says to read the `source` first, bump independently where the CLI ships separately, and record that in the changelog entry. Found by following the skill and noticing the number went the wrong way.
- **A sweep of references to the deleted `best_practices.md` mirror.** Removing the second copy and its hook left four places still describing the arrangement as current: `plugin-versioning.md` cited it as the live example of the "mechanical mirror" shape (that shape now has no instance here, and the entry says so rather than pretending otherwise), `maintenance.md` listed the deleted hook as an active control, the `skill-maintainer` README documented a manual sync command, and `finish-session`'s workflow step 3 instructed the agent to `cmp` two files, one of which no longer exists. The last was a runnable instruction, which is the class that matters. The sweep should have run before the delete rather than after; `dangling-refs:retire` exists for exactly this and was not used.
- **`model-routing` 0.5.1 → 0.5.2 — two pointers into a section that moved.** `SKILL.md` and the plugin README both cited `VISION.md "route to the cheapest capable model"`, which now lives in `docs/internals/architecture.md` after the split below. The links resolved, so nothing broke loudly; they just named a section the target file no longer contains, which is the failure mode a link checker cannot see. The `SKILL.md` one is the reason this got a version rather than riding along: it is runtime content, read by the agent whenever the skill activates, so an installed user following it lands on the wrong file. Both now point at `architecture.md`.

### docs
- **`plugin-versioning.md` gains the case invariant 1 could not answer: shipped but inert.** Invariant 1 says plugin content is whatever the marketplace `source` ships, which answers "does this file travel" and not "does it do anything on arrival". `apps/readwise-reader/CLAUDE.md` is the specimen: it sits under a shipped source, so by the letter it is plugin content, but Claude Code loads a plugin's skills, agents, hooks, commands and MCP servers, never its memory files, so a bump would reach installed users with nothing. The rule is now stated as a behavioural test — does an installed session behave differently after `marketplace update` — with the counter-examples named, since a `SKILL.md` body, a `references/` file a skill reads, and a hook script all sit firmly inside the cascade. Used the same day to decide that `model-routing`'s `SKILL.md` pointer fix earned a version while its README alone would not have.
- **`apps/readwise-reader/CLAUDE.md` trimmed by 54 lines** (8,957 → 6,181 chars) by a `/doctor` run: an annotated directory tree that `ls` plus file heads reconstructs, and four convention bullets already stated in `.claude/rules/general.md`, which loads unconditionally in every session of this repo including under that app. Coverage was verified per-bullet rather than taken on trust. Design rationale, the two-API and staging-table patterns, the ruff and DuckDB gotchas, and the TLS setup all stay. No version bump, per the ships-but-inert rule above — `/doctor` reached the same conclusion through a different and incorrect premise, that the file is not shipped plugin content at all.
- **`VISION.md` split and de-duplicated: 296 → 128 lines.** The architecture worldview — trees not workflows, model tiering, harness coupling, context isolation, use-before-prepare, structured outputs as state, verify by construction, compound feedback — moved intact to `docs/internals/architecture.md`, keeping its section names because five documents cite them by name, and those citations were repointed. What stayed is retrieval: context versus friction, progressive disclosure, descriptions as reverse queries, and why a practice carries the event that reopens it. The friction half is new and names the second budget the file had been missing — the human as index — which is the cost that "the user can always ask for more context" quietly assumed away. A first pass then pulled five *rules* up out of `best_practices.md` into it (the retrieval boundary, the with-and-without falsifier, the evidence-class table, "elapsed time is not evidence", "freshness does not catch wrongness"); those are removed again under one rule now stated in the file: one claim, one home, chosen by what reopens it. `VISION.md` holds principles, `best_practices.md` holds rules and gates, `docs/internals/` holds the measurements rules cite, and where a sentence appears in two tiers the lower one keeps it. `best_practices_maintenance.md` gains a header marking the two-copies question it analyses as closed, since it is a dated design record and its `tests.py` line numbers describe the state at filing rather than now.

## 1.31.0

### added
- **`path-privacy` 0.16.2 → 0.17.0 — an `allow` key, for the paths a substitution cannot fix.** The config had exactly one mechanism, `suggestions`, and it works by rewriting the text. That is right for prose and comments and wrong for anything runnable, where the rewritten form still has to work. The case that forced it: an upstream merge in a consuming repo introduced a Node-version guard whose hook command runs `D="$HOME/<tool-cache>"`, embedded in two tracked JSON files and built by a transformer in a third. The scanner flags it correctly by its own rule, since it resolves outside the repo — but the path names no user and discloses no machine layout, and substituting a placeholder would make the hook `mkdir` a directory literally named `<HOME>`. JSON can carry neither a per-line `path-privacy: ignore` nor a leading `skip-file` marker, so every existing escape was unavailable at once and the only remaining move was `--no-verify` on precisely the commit that most deserved the gate. `allow` exempts a candidate by **literal prefix, anchored at the start, never a substring** — a substring rule would let an allowed path appearing later in a line exempt a real leak earlier in it, which is the class the gate exists to catch. Verified against that: a private-key path under `$HOME`, a sibling directory under an allowed parent (`~/<tool>/extensions/` against an allowed `~/<tool>/agents/`), and a line pairing a genuine leak with an allowed prefix all still flag. Entries take a bare string or `{"prefix": ..., "_why": ...}`, because an allow list without reasons rots into a list nobody dares prune.

### fixed
- **`scrub-paths.sh` would have rewritten a working install command into a broken one, and had simply never been asked to.** Found while wiring the above: a downstream config carried a tool's global skills directory as a *suggestion*, and one of its two occurrences was a copy-pasteable `cp -r ... ~/<tool>/skills/` in a README. Applying it substitutes a placeholder into a command whose whole value is that it can be pasted. It had not fired only because the sync that runs the scrubber halts on merge conflicts before reaching that step, so the entry sat live and harmless for as long as nothing succeeded. The scrubber now refuses any suggestion whose `match` overlaps an allow prefix **in either direction** and names both colliding entries — overlap either way matters because sed does blunt substring replacement and cannot reason about candidates, so a broad suggestion (`~/`) rewrites an allowed path on its way past just as surely as an exact-match entry does. The scrubber is the consumer that actually writes to files, which makes it the one that most needs to respect the list; a config that says two contradictory things about one path is an authoring error only its author can resolve, so this is loud rather than silent.

## 1.30.1

### fixed
- **`gemini-bridge` 0.15.0 → 0.15.1 — the second review round's surviving findings, applied.** The five angle reviews of 0.15.0 confirmed one correctness defect and a cluster of drift hazards. The spend counter is now written via tmp-file-and-`os.replace` instead of truncate-in-place: a concurrent reader could catch the truncated file empty, read the count as zero, and write back `0 + its tokens` — resetting the accumulated total, worse than the lose-one-update bound the docstring claimed (the one-update race remains, and remains accepted). The state-root derivation collapses to a single `state_root()` helper — it existed inline in three places, and a writer/reader divergence would have made the cap silently never accrue. `add_session_spend` reads the spend file directly instead of nesting `session_spent_tokens()` (which re-resolved the session and rebuilt the path just validated). The strict type-check validation shipped for `max_session_tokens` now covers its siblings `max_unauthorized_tokens` and `ttl_seconds` — bare `int()` coercion had kept accepting `true` (a live threshold of 1), negatives, floats, and quoted strings in the same block the changelog had just described fixing. The accrual policy (all token classes, unauthorized only) moves into `authorization.accrue_call_spend` so no future recording path can half-know it. `Estimate` carries a `sized_from_bytes` flag set where the fallback fires, instead of the formatter re-deriving duration-based kinds from `att.kind`. The redundant source scrub on the `interactions.create` error path is dropped — the three sinks it flows into all scrub — while `UploadError` keeps scrubbing at construction, with the reason now stated: its messages also reach bare WARNING prints that are not scrubbing sinks. Declined with reasons: lazier spend-file reading inside `classify` (one ~30-byte read per gated call is not worth making the pure function read files) and scrubbing the two local-OSError WARNING lines (their text is local filesystem errors; the SDK-derived WARNING already prints construction-scrubbed text).

## 1.30.0

### changed
- **`gemini-bridge` 0.14.0 → 0.15.0 — the session cap's counter moves out of the project ledger, closing the review's finding that the gated party controlled its own gate.** A code review of 0.14.0 confirmed the cap was trivially resettable: spend was summed from the ledger under `project_root`, and `--project-root /tmp/fresh` handed a refused agent an empty ledger with no user keystroke. The counter now lives in the session state directory beside the authorization token — session-keyed, ownership-checked (symlinks rejected, unowned roots refused), keyed by the *validated* session id (the raw-id sum let a session whose id failed validation accrue spend it could never authorize away — a permanent refusal no command could clear). It accrues **all token classes** (output bills highest; an input-only cap left the expensive axis uncapped) and **unauthorized spend only** (tokens a user approved must not later gate unrelated cheap calls under a message that says "unauthorized spend"). Overriding `TMPDIR` still resets it — the same documented honest limit as clearing the agent-marker variables — and the skill's refusal guidance now names both dodges. The ledger read leaves the ask path entirely, which also removes the review's crash finding (an unreadable `ledger.jsonl` was a bare traceback on every ask) and its eager-evaluation finding (projects that opted out of the cap paid a full-ledger parse per call).

### fixed
- **A probed duration of `"0.000000"` bypassed the size fallback.** The string is truthy, so `float(value) if value else None` returned a *measured* 0.0 for some fragmented/live containers — the fallback never ran, and a file of any size estimated at the 70-token floor: the exact under-count class 0.14.0 fixed, arriving by the path that has ffprobe. Zero now degrades to the size guess.
- **The manifest's unknown-duration marker blamed a tool it had not checked.** It said "no ffprobe" for any unmeasured duration, but ffprobe present-and-failed (bad container, timeout, probed zero) takes the same path — sending users to install what they already had. The line now states the fact (duration unknown, sized from bytes) and names no cause; `doctor` reports the absent-tool case, the one it can see.
- **`doctor`'s ffprobe warning printed only with the gate on** — nested in the gate's else-branch, so `required = false`, exactly the configuration where the manifest estimate is the only cost signal left, got a clean bill of health. Moved outside the branch.
- **Session-cap config validation garbled its own error and accepted nonsense.** The tailored complaint for `true` was raised inside a try whose own except re-wrapped it into a self-contradicting composite; `int()` coercion accepted `-1` (the common "unlimited" idiom) as a live cap gating every call, truncated floats, and parsed quoted strings. Now validated outside that try, type-checked, negatives rejected; `false` disables and `0` stays a live gate-everything cap.
- **`ledger.read` hardened for its remaining consumers** (`stats`, `uploads`, refusal audit rows): an unreadable file reads as empty — matching `record()`'s own OSError swallow — and a valid-JSON line that is not an object is skipped instead of crashing whoever indexes the row.
- **Error redaction moved into the sinks as well as the sources.** `_fail`, `RunDir.write_error`, and the ledger's `error` field scrub key-shaped content themselves, so the next error path added to the CLI ships scrubbed by default instead of depending on its author remembering.

## 1.29.0

### added
- **`gemini-bridge` 0.13.0 → 0.14.0 — the session spend cap: many cheap calls are one expensive call arriving slowly.** The gate was per-call only, so a hundred calls at 15k tokens each never tripped the 20k per-call limit — the one spend axis with no ceiling. Each session now also carries a cumulative cap (`max_session_tokens`, default 500,000 — 2.5x the default per-approval ceiling, roughly two hours of default-rate video), summed from the project ledger's *recorded* usage for the current session: crossing it classifies the next call expensive, which routes it through the same user-typed `/gemini-bridge:gemini-authorize` everything else expensive needs — who decides changes, not what is possible. Actuals count, not estimates, so refusals cost nothing against it; other sessions' rows are other sessions' money (a mutation arm pins that); `false` disables the cap while `0` deliberately does **not** read as disabled — "the value that reads as allow-nothing" being the one that allows everything is the exact bug the per-call ceiling shipped with, so `0` gates every call. `doctor` reports the session's spend against the cap.

### fixed
- **The secret-scan refusal named its own bypass.** "Pass `--allow-prompt-secrets` if these are false positives" is an instruction the main loop will helpfully follow — the precise failure the spend gate's `_missing_message` documents and avoids, sitting in the sibling guard. The refusal now ends with the user: report the redacted findings, do not add the flag, do not rephrase past the scan; a user who judges them false positives re-runs with the override themselves. The flag stays discoverable in `--help` and the README.
- **The no-ffprobe estimate under-counted, against the module's own rule.** The size fallback assumed 1MB ≈ 10s (~800kbps), while screen recordings of mostly-static content commonly run 100–300kbps — a 15MB, 20-minute recording estimated ~10.5k tokens, under the gate, while billing ~84k, and "an estimate that feeds a spend gate must never under-count" is stated two constants up. The fallback now assumes the low-bitrate end (30s/MB video, 150s/MB audio), the manifest line marks an unknown duration as a size-based guess instead of printing an estimate indistinguishable from a measured one, and `doctor` reports a missing ffprobe as gate degradation. No finite constant bounds every file; saying so where the number appears is the honest half of the fix.
- **SDK error messages are scrubbed before they travel.** The client-constructor path reduces failures to a type name because a key-format error embeds the value — but `interactions.create` and Files API failures surfaced `str(exc)` raw into stderr, `error.txt`, and the ledger's error field at once, on exactly the paths where credentials are in play. Error text now passes through the secret scanner's blocking patterns (`content.redact_secrets`); warn-level shapes are left alone because in an error message the path usually *is* the diagnostic, and the replacement names what was scrubbed so the message stays actionable.

## 1.28.0

### added
- **`gemini-bridge` 0.12.0 → 0.13.0 — every send now announces its manifest before anything leaves the machine.** `--dry-run` was the only way to see what a call sends, and it had to be asked for; a real send printed nothing until the bytes were already gone, so the one moment the user could still stop — the manifest on screen, the call not yet made — existed only on the path that sends nothing. Every `ask` now prints the same manifest (recipe, model, store, per-attachment route and estimate, the text channels, the total, the question) to stderr **before credentials are resolved, before any upload, before the call**. It prints on gate refusals too, because the refusal tells the user to decide and the manifest is what they are deciding about. The dry-run report and the announcement are one function, deliberately — two separately-built descriptions of "what would be sent" is the exact shape that let the scanner and the estimator disagree about outgoing text in 0.12.0 — and a drift arm holds them to it.

### fixed
- **`-r <path>` was the sixth file route, and the only one the path guard did not cover.** `recipes.load` treats an argument with a suffix that exists as a file to read, and its body travels in the request as the system instruction — so `-f deploy.key` was refused while `-r deploy.key` read the same bytes, one release after the README started claiming "every file named on the command line" is guarded. The guard's condition mirrors load's path branch exactly; a bare recipe *name* resolves inside declared recipe directories and is not a user-named file, so it stays unguarded. (A dotfile like `.env` has no pathlib suffix, so the path branch never read one — the exposure was suffixed files.)
- **A bad config was a traceback on the first line of every command.** Malformed TOML raised `TOMLDecodeError` straight through, a non-numeric `[authorization]` threshold raised `ValueError`, and the `[auth]`-in-project-config refusal — a clean message by design — was never caught anywhere. All three failed closed, but every other refusal in this CLI terminates in a sentence a person can act on. `Config.load` now wraps all of it in `ConfigError` naming the file and key, and `main` catches it once, for every command.
- **The gate tier was classified twice from the same arguments**, once per branch of `--dry-run`. Classified once, above the branch, so the report and the enforcement cannot diverge.

## 1.27.0

### added
- **`gemini-bridge` 0.11.1 → 0.12.0 — the two guards now cover every route into the request, and the minting half of the spend gate has tests for the first time.** A follow-up review of the 0.8.0–0.11.1 range found that the sensitive-path guard was wired to `-f` and `-c` only, while `--prompt-file`, `--system-file` and `--schema-file` each read a local file and put its contents straight into the request unchecked. `-f .env` was refused; `--prompt-file .env` sent the same bytes as the question. Verified live, both directions. The guard now runs on **every** path-bearing flag, before any of them is opened — which also makes the ordering rationale honest, since it previously ran after `--prompt-file` had already been read. The content scanner is not a substitute and the README now says so in as many words: it matches key *shapes*, so `DB_PASSWORD=hunter2` goes straight through it.
- **The spend gate counts the whole input.** `budget.total` summed attachments, so a 4.3MB `--prompt-file` — roughly a million input tokens — printed `gate none; runs under the ordinary permission prompt`. Text is billed too, and it was the one billed input nothing measured. `--max-output-tokens` above the same threshold is now a trigger as well, for the reason raised thinking already was: output bills at several times the input rate, and asking for the output directly is the same spend by a plainer route. A question typed on the command line rounds to nothing and changes no verdict, which is what keeps the common path untouched — an arm pins that, and it fails if the text term is ever scaled up.
- **`tests/test_authorize_hook.py` — 20 arms driving the real shell script.** Nothing watched the hook. Every existing arm exercised *enforcement* against a token the test wrote itself, in the shape the test believed the hook used, which is exactly the arrangement that let `session_id()` read a variable Claude Code does not export and still pass the whole suite. The load-bearing arm is the round trip: run the script, hand what it wrote to the real `peek()`, require an approval — nothing mocked in between, so a rename on either side of the pair goes red. Each arm was mutation-proven at birth rather than accepted green.

### fixed
- **The estimator and the secret scanner each built their own list of outgoing text, and they disagreed.** A second review pass found the `--prompt-file` hole still open on its sibling: the scanner has enumerated four channels since 0.6.x — question, system instruction, schema, labels — while the estimator counted two, so a 3MB `--schema-file` was scanned, then costed at **one token**, printing `gate none` on a call of roughly a million. Reproduced end to end. The scanner's own comment already stated the rule ("a channel left out of this list stays unscanned until someone names it"); the fix for a rule that has to hold in two places is to have one place, so both now read a single `_outgoing_text`. A parametrised arm holds each of the four channels to the same standard, so the next one added is costed or the suite goes red.
- **`ultra_high` video estimated *below* the default and slipped the gate.** The rate was chosen by `resolution == "high"`, so `ultra_high` — an accepted video value that `--resolution` offers, `recipes` validates, and the content block carries — fell through to the cheapest branch: a four-minute clip estimated 16,800 tokens where `high` estimated 67,200, and `classify` returned `cheap` against the 20,000 limit. The single most expensive setting was the one that got past the gate. Now a rate table, with unknown values billed at the highest known rate rather than the lowest, because guessing cheap is how a gate gets bypassed. No published per-frame figure exists for `ultra_high` on video; it is priced at twice `high` following the image ladder, and `media.md` says plainly that the number is a deliberately-high guess.
- **The refusal could end in a traceback instead of in the user.** `runs.ensure_runs_root` was the one filesystem call in `ask` evaluated outside a guard — as an argument to `ledger.record`, which is how it escaped notice — so a read-only project root turned a refused call into `PermissionError`. The refusal text is designed to terminate in a human decision; a stack trace terminates in nothing. The audit row is the thing that may be lost there, never the refusal.
- **The authorize command was model-reachable.** It shipped without `disable-model-invocation: true`, so its description entered context and the SlashCommand tool could reach it — leaving the gate's entire premise ("only a user keystroke reaches `UserPromptExpansion`") resting on an unexamined assumption about which paths fire that event, which is precisely the shape of the 0.11.0 no-op. `skills/advisor` guards the same threat with three layers; this now ships two, and the README states that `doctor` cannot detect a regression in either rather than leaving it to be found.
- **Every ledger row recorded a null session on agent calls.** `ledger.py` still read `CLAUDE_SESSION_ID` — the variable `authorization.py` documents, in this same release, as *not exported* by Claude Code. That includes the `run_id: "(refused)"` rows added so an audit could see an agent repeatedly trying to spend more than it may; rows that cannot be attributed to a session cannot show a pattern. Both places now read the session the same way.
- **A re-upload erased the previous handle's name while its bytes were still at Google.** `Cache.get` dropped an entry inside the 30-minute reuse margin, and the fresh upload's `put` rekeyed the same content hash — so the older, still-live handle vanished from the only local record that could name it, unlistable by `uploads` and undeletable by `--delete` for up to another half hour. Same shape as the `Cache.live()` mutation fixed in 0.11.1, arriving by the reuse path instead of the listing path. One set of bytes can have two live handles, so the cache is now keyed by **handle name** — which is also what `files.delete` takes — and matched on the hash. Old files are re-keyed as they load, so there is no migration.
- **The hook and the CLI disagreed about which session ids are usable**, under a comment claiming they agreed. Ids starting with `.`, `-` or `_`, or longer than 128 characters, were minted for and then always refused on read — an approval the user typed that could never be spent. Now identical, and a parity arm runs both implementations over the same ids, because a claim of agreement between two implementations is a thing to test rather than a thing to assert in a comment.
- **The undocumented `authorization_tier: "expensive"` was still shipping — on the other half of the gate.** 0.11.1 fixed the gate-disabled case. It did not fix the consume case: peek-stage refusals were hard-coded to `"expensive-refused"` in the CLI while consume-stage refusals passed through `decision.tier`, which every rejection in `_validate` set to the bare `"expensive"`. Reproduced with a failing assertion. It is reachable exactly where `consume()`'s own docstring says the atomic rename matters — two expensive calls in one turn, both peek clean, one wins the rename — and by a TTL lapsing while a key command waits on a biometric prompt. The tier now comes from the `Decision` on both paths, and the CLI's hard-coded literal is gone; a parametrised arm asserts every refusal `_validate` can produce carries a value the README's table lists.
- **`--max-tokens 0` was a blank cheque.** The ceiling check read `if ceiling and estimated_tokens > ceiling`, so `0` — the value that reads as "allow nothing" — was the one value that bounded nothing, and it is four keystrokes from an ordinary approval. A token with no `max_tokens` at all behaved the same way. Both sides now refuse it: the hook rejects a non-positive ceiling and falls back to the default, and the CLI treats an unusable ceiling as an unverifiable authorization, which this module already decided means no.
- **The gate is hardened against the other account sharing `/tmp`.** The hook's own comment called the token file "what stands between another local account and spending on this API key" and nothing checked it. `mkdir -p` succeeds against a directory someone else created first, at which point `chmod 700` fails and the old `|| true` swallowed it. Both halves now refuse a state root they do not own, reject symlinks without following them, and refuse a session id that is not a plain identifier — it is interpolated into that path by both halves, so a traversal-shaped one writes outside the state root entirely. `doctor` reports the condition, because the hook declining to mint is otherwise the same invisible loop as a missing `jq`: the user runs the command, it appears to work, the call is refused again, and nothing says why.
- **The secret scanner was quadratic, and it hung the CLI on the guard path.** Found by running the real command on real input during verification, not by reading: a 400KB prompt with no separator in it took **~275 seconds**, producing nothing, before anything was sent. Two patterns ended a greedy character class with a literal the class excludes — `[A-Za-z0-9._%+-]+@` and `[a-z][a-z0-9+.-]*://` — so every start position consumed to the end of the text looking for a delimiter that is not there. The trigger is not exotic: a base64 blob, a minified bundle, a hex digest or a `data:` URI pasted into `--prompt-file` is exactly that shape. Fixed in two parts, because the first alone was not enough — possessive quantifiers remove the backtracking *within* a run, but the scan still retried from every position, so a negative lookbehind now rejects interior start positions in constant time. **400KB: 275s → 0.012s, and linear.** A counterweight arm asserts each changed pattern still matches, and it is mutation-proven against the one narrowing mistake available here (making the email *domain* class possessive, where `.` is in the class and the backtracking is load-bearing).
- **A missing `--prompt-file` reached the user as a raw `FileNotFoundError` traceback**, where `--system-file` and `--schema-file` both reported cleanly. It was the one unguarded read in the command.
- **The budget warning named levers a text-only call does not have** — "lower `--resolution`, or attach reference files with `-c`" on a call with nothing attached. Reachable only once the estimate started counting text, so it arrived with that change and left with it.
- **`uploads` documented the bug it no longer has.** The empty-list message still said entries are pruned 30 minutes before expiry — describing, as if it were the design, the exact mutation `live()` was made non-mutating in 0.11.1 to remove. The README was already correct; only the string was stale.

## 1.26.1

### fixed
- **`gemini-bridge` 0.11.0 → 0.11.1 — the spend gate shipped as a no-op, and a code review caught it before anyone relied on it.** `authorization.session_id()` read `CLAUDE_SESSION_ID`. Claude Code exports `CLAUDE_CODE_SESSION_ID`. So on every agent-invoked call the lookup returned None, the gate concluded "not an agent session", stood down, and allowed the call — **the exact case it was built for, failing open and silently**. Every test passed because every test set the variable itself, which proved the tests agreed with the code and nothing about the world. This is the same class the module's own docstring warns about, one release after writing that warning. Now: both names are read, and — more importantly — "no session id" and "no agent" are separated. A shell with no agent markers is a human and is not gated; an agent whose session cannot be identified is **refused**, so a future rename fails closed instead of rebuilding the no-op. Verified unmocked against the real environment: refused, then minted through the hook with the real session id, then allowed all the way to a live API call.
- **A failing credential command burned the user's approval.** The token was consumed before credentials were resolved, so a key command that timed out on a biometric prompt spent a single-use authorization on a call that sent nothing. Split into `peek` (read-only, refuses early so no pointless work happens) and `consume` (atomic claim, immediately before the first irreversible step). Verified: after a credential failure the token is still on disk.
- **Two ways to orphan bytes at Google, both fixed.** `Cache.live` applied the 30-minute *reuse* margin as if it were expiry and popped the entry — and since `uploads --delete` saves the cache afterwards, the prune was persisted, so a handle twelve minutes from expiry was never listed, never deleted, and its only record erased while the file sat there. Listing is now non-mutating and shows everything still present; the margin applies only to reuse. Separately, `cache.put` ran only *after* `_await_active`, so an upload that timed out in PROCESSING was live for 48h with no local record at all — unnameable by `uploads --delete`, and re-uploaded whole on retry. The handle is now recorded the moment `upload` returns, which is the moment the bytes are actually gone.
- **`authorization_tier: "expensive"`** leaked into the ledger when the gate was disabled — a fourth value no doc named, on exactly the large ungated calls an audit exists to find. Now `expensive-gate-disabled`, and the README documents all six values. Refused calls are recorded too, under `run_id: "(refused)"`: a gate whose trail shows only the spends it allowed cannot show an agent repeatedly trying to spend more than it may.
- **A `write_request` failure after a successful upload left no ledger row**, so a disclosure that already happened had no record anywhere. It now writes the error and records the run, like every other post-upload failure.
- **`Cache.get` guarded key drift but not value drift**: a null `uploaded_at` survived construction and raised an uncaught `TypeError` out of `doctor`, `uploads` and `ask`, against the module's own "a corrupt cache is a cold cache" contract.
- **`doctor` can now see the gate's two invisible failures.** Missing `jq` means the hook mints nothing, so the user runs the command, it appears to work, and the call is refused again with no explanation anywhere — an unbreakable loop. An unreadable session id is the other. Both are reported as BROKEN, alongside the resolved session and whether an authorization is currently held.
- **Efficiency and accuracy:** `ffprobe` is memoized per file identity (it was spawned up to four times per file per command, each with a 10s timeout); the preview request no longer base64-encodes inline attachments, so a mixed call reads and encodes each file once instead of twice; `--dry-run` computes its estimate once; and `runs.write_uploads`' docstring no longer claims a behaviour its only caller contradicts.

## 1.26.0

### added
- **`gemini-bridge` 0.10.1 → 0.11.0 — the tiered spend gate the design record specified and did not build.** Until now the only thing standing between an eager agent and forty minutes of uploaded video was Claude Code's Bash permission prompt: real, but allowlistable, click-through-able, and blind to the difference between a screenshot and a feature film. Expensive or irreversible calls now additionally require an authorization that **only a user-typed slash command can mint** — `/gemini-bridge:gemini-authorize`, single use, ten-minute TTL, carrying a token ceiling so "approve a clip, send the feature film" is not one edit away. This is the advisor pattern, reused rather than reinvented.
- **Minting and enforcement are split, and the split is the design.** A `UserPromptExpansion` hook mints, because the main loop cannot reach that event — anything the CLI could mint, the agent could mint, since the agent is what runs the CLI. The CLI *enforces*, rather than a `PreToolUse` hook, for the two reasons the design record already gave: it is the narrower chokepoint (it also covers manual, scripted and subagent callers, including on machines where the hook was never installed), and a hook would have to recognise an expensive call by parsing a bash command line, which quoting and env prefixes make unreliable. The tier decision needs resolved attachments, and only the CLI has those. This is a deliberate, reasoned reversal of the plugin's "no hooks" decision: it adds exactly one hook, of the one type whose job cannot be done anywhere else, and `UserPromptExpansion` costs nothing ambiently since it fires only on its own command.
- **Tiering is by cost and irreversibility, never by modality.** A five-second clip is a few hundred tokens; gating it would teach people to switch the gate off, which costs more than it saves. The triggers are an estimate over `max_unauthorized_tokens` (default 20,000, the same threshold the budget warning uses so the two agree), `--store` (irreversible — `interactions.delete` returns 501), and `thinking_level` at `medium` or `high` (output-rate billing with no ceiling). Everything else is untouched. The gate runs **before credentials are resolved and before any upload**, so a refused call sends nothing — verified end to end, hook through CLI.
- **Fails closed, and says so.** Missing, expired, malformed, unreadable, wrong provenance, over-ceiling: every one is a refusal. This repo has already shipped the opposite bug once — advisor's hook opened with a `command -v jq || exit 0` copied from a fail-open hook, silently turning the gate into a no-op on any machine without jq — so several tests exist purely to pin the *direction* of failure. `ledger.jsonl` gains `authorization_tier` (`cheap` / `expensive-authorized` / `expensive-ungated`), defaulting to `"unknown"` rather than `"cheap"` for the same reason `prompt_scanned` defaults to False: a forgotten kwarg must not positively claim the safe answer.
- **The refusal text terminates in a human decision, and that is load-bearing.** A refusal reading as "authorize this first" is an instruction the main loop will helpfully follow, and the surprise spend comes straight back. It says do not retry, do not split the call to get under the limit, do not disable the gate in config — tell the user what you wanted and let them decide — and a test asserts those phrases are present. `--dry-run` reports whether a call would be gated, so discovering it costs nothing rather than a round trip.

### honest limits
- The authorization is a local file. Anything holding Bash or Write can fabricate one, and dropping `CLAUDE_SESSION_ID` makes a caller look like a human at a terminal (an unauthenticated shell is deliberately not gated — someone typing the command *is* the authorization). **This is not a defence against a determined agent and does not claim to be.** It guarantees that nothing on the normal, helpful path spends at scale. The realistic failure mode here is an eager agent, not a hostile one, and the README says this in as many words rather than letting the feature oversell itself.

## 1.25.1

### fixed
- **`gemini-bridge` 0.10.0 → 0.10.1 — the docs implied one modality per call, and the code never worked that way.** SKILL.md's start-here table had one row per kind ("Ask about one image or PDF"), which reads as mutually exclusive, and nothing anywhere said that `-f` is repeatable across kinds. A reader following it would split "does this recording match the two mockups and the spec?" into three calls, paying three times and denying the model the comparison that was the whole question. **No code changed** — mixed sets already routed correctly, each file on its own kind inside one request — so this is purely the documentation catching up with the feature, plus three tests that pin it: images inline and video by uri in one call with attachment order preserved, subjects and context of different kinds at different resolutions, and a mixed set correctly falling back to the generic default question rather than applying the video one to a PDF. The description now says "singly or mixed in one call" (traded against the weakest trigger phrase to stay inside the 1024-char limit), and `media.md` opens by stating that a request carries any combination.

## 1.25.0

### added
- **`gemini-bridge` 0.9.0 → 0.10.0 — budget transparency, because the expensive thing was never a setting anyone chose.** Every knob in this plugin already defaults to the cheap option — Flash, `thinking_level: minimal`, default media resolution — so the only real cost driver is **clip length**, and that was invisible until the invoice. A minute of video is roughly 4,200 input tokens; a ten-minute recording attached whole to answer a fifteen-second question is most of a dollar of input nobody decided to spend. `budget.py` now estimates input tokens per attachment (duration via `ffprobe` where available, size-based fallback where not), prints it in `--dry-run`, and warns before the send while it is still actionable — naming the lever, since a long video wants trimming and a pile of images wants a lower resolution. It warns and never refuses: a hard ceiling would have to guess a budget it cannot know. No prices anywhere; a dollar figure in code goes stale silently while looking authoritative.
- **SKILL.md now tells the agent to ask before spending.** Not on every call — if the user already said what they want, or is asking about a file they just handed over, get on with it. But when a call is about to be expensive and the agent is choosing on their behalf, put it to them with real options and real numbers ("8 minutes, ~34k tokens: trim to the window you described (~2k), send whole (~34k), or `high` for readable text (~134k)"), recommend one, and make the cheap option the default. The section also states plainly that the defaults are frugal *on purpose* and must not be quietly upgraded because a task feels important.
- **`tests/test_sdk_contract.py`** — our constants asserted against the pinned SDK's generated types: accepted mime types per kind, resolution values, `generation_config` keys, which content types carry `resolution`, and that every model id the plugin recommends actually exists. Shape only, never behaviour — `temperature` is in no SDK type and the API accepts it regardless, and only a live probe settles that class.

### changed
- **`google-genai` pinned exactly at 2.17.0**, up from a `>=2.3.0` floor. This is what `.claude/rules/general.md` requires of an application and what the design record asked for in as many words ("Pin the SDK exactly. This API breaks."), and a floor meant a routine `uv sync` could silently change what the code is talking to. The bump from 2.16.0 was verified against every load-bearing type before landing: mime lists, resolution enum, generation-config keys, and the absence of `resolution` on audio and document blocks all unchanged. The contract test above is what makes the pin worth its inconvenience — bumping it now names what moved instead of the drift arriving later as a 400 on a paid call.

### fixed
- **A test that could not fail for its stated reason.** `test_ledger_write_failure_is_swallowed` staged an unwritable destination with `chmod(0o500)` — but **root ignores permission bits**, so in the container this suite commonly runs in the write simply succeeded, the `except OSError` branch never executed, and the arm failed for a reason unrelated to the code. Deleting the error handling it guards would not have turned it red. Verified rather than assumed: the arm passes as `nobody` and fails as root, `CAP_DAC_OVERRIDE` present. The failure is now injected by monkeypatching `Path.open`, which works at any uid, and mutation-proven — removing the `except OSError` turns it red. **The bridge suite is fully green for the first time: 271 passed, 0 failed.**
- **A zero-token estimate.** The new budget arm caught its own subject: a small file's duration rounded down to zero seconds and reported "~0 input tokens", which reads as free. Nothing is free — estimates now floor at one sampled frame, one second of audio, or one page of PDF.

## 1.24.0

### added
- **`gemini-bridge` 0.8.0 → 0.9.0 — the skill becomes a routing layer and the detail moves into three references.** `gemini-multimodal` was named for every modality and written for images: the body carried the measured image-resolution guidance and little else, so an agent holding a video had no idea what models to use, what formats were accepted, what the upload cost, or which parameters exist. `references/api.md` covers the call (parameter placement, models and the `UnrecognizedStr` trap, thinking, seed vs the ignored `temperature`, structured output, storage and the 501, service tiers, token accounting, and what the CLI deliberately does not expose); `references/media.md` covers attachment (routing per kind, formats, the resolution/token table across modalities, size limits, what the guards miss); `references/video.md` covers video end to end. Every claim in `api.md` is tagged **probed / SDK / docs**, because in this plugin a claim's provenance is how much you trust it. SKILL.md keeps a start-here table by task and one rule per modality, and the two sections that had become verbatim copies of a reference were cut to pointers.
- **`gemini-bridge formats`** — accepted mime types per kind, which route each takes, the size limits, and the extension remappings. Derived from the tables `media.py` enforces, so it cannot drift; that is why it is a command rather than a section in a reference file, which would be a copy with nothing watching it.
- **A `video-analysis` recipe.** The stance a video answer needs — timestamp everything as MM:SS, report what is observable, mark inference as inference, say when something fell between the 1 FPS samples — is the same across most video tasks, and it is exactly what a caller writing a question forgets. Fixing it in a versioned file with a pinned model and seed leaves the caller free to spend their attention on the question, which is the part only they can write. `--system` remains the escape hatch for when the stance itself is the task.

### fixed
- **Two docs told callers to use `gemini-3.6-pro`, which is not in the SDK's model list.** Checked against the installed `_gaos` types: the union has `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.1-pro-preview` and the `gemini-pro-latest` / `gemini-flash-latest` aliases, but no `gemini-3.6-pro`. Because the type is a `Literal` union **plus** an `UnrecognizedStr` escape hatch, a bad id is not caught client-side — it fails at the server, which is the worst place to learn it. Both examples now use `gemini-pro-latest`, and `api.md` states the trap along with the pinned-vs-alias tradeoff.
- **`auth.py`'s header was stale and read like insider shorthand.** It opened "one of the two seams that differ between the Gemini Developer API and Vertex" — three files carry provider assumptions since `files.py` landed — and justified itself with "Vertex funding via Google Developer Program credits is a live option we deliberately did not foreclose", which explains nothing to a reader who was not in that session. Rewritten to say what Vertex actually is, that it is not planned, and concretely what adding it would touch. `media.py` and `files.py` had the same stale seam count and now agree.

## 1.23.0

### added
- **`gemini-bridge` 0.7.2 → 0.8.0 — video and audio, which means the Files API.** Attaching a `.mp4` used to raise "requires the Files API, not implemented until phase 4". It now uploads the file, waits for it to leave PROCESSING, and sends a uri reference — the shape probe 11 verified live on 2026-08-01 and the only one that was ever verified. **Inline video is deliberately not shipped even for a 2KB clip**: the SDK types say `VideoContent` accepts `data`, but a static source is a hypothesis here and nothing more, and a size threshold would route the smallest files down the unproven path first. The size cap becomes a *second*, independent reason to upload, which is what makes a 90MB PDF work as a side effect. New `files.py` is the third provider seam, alongside `auth.py` and `media.py`: `client.files.upload` raises on Vertex clients, so every uploading assumption lives in one file and images keep the inline path that leaves the Vertex door open.
- **Uploads are cached by content hash, and confirmed with the server before reuse.** The motivating case is iterative — "turn this screen recording into HTML" is never one question — and re-uploading the same bytes four times spends wall-clock and the project's 20GB quota to arrive at the same URI. Keyed on content, so it cannot serve a handle for bytes that changed; a re-render gets a new upload. The one staleness a hash cannot see is server-side, so a cached handle is checked with a live `files.get` first and re-uploaded if the file expired or someone deleted it.
- **`gemini-bridge uploads`, and `--delete`, the first real cleanup this plugin has ever had.** Every other disclosure surface here is read-only because `interactions.delete` returns 501. `files.delete` works — so uploads are the one thing that can actually be taken back, and keeping that on its own command rather than folding it into `stored` is deliberate: collapsing them would imply the same remedy applies to interactions, and it does not. The run directory gains `uploads.json` and the runs root gains `upload-cache.json`; both are written **before** the interaction, because an upload is already a disclosure and a call that fails afterwards must not orphan bytes nothing can name. `doctor` reports the count.
- **A default question, and a warning that argues against it.** Attaching media with no question used to be refused outright. It now runs a kind-specific default — the video one asks for MM:SS timestamps and for observation over inference, because prose about a video is unusable to a caller who wants to seek to the moment described. Every use prints a warning naming what was given up and pointing at `--system`, the lever callers forget exists. The defaults are a floor, not a feature: the agent composing the call has read the user's code and is the only party that can ask "does the drawer animation overshoot" instead of "describe this video", and `SKILL.md`, `references/video.md`, and the slash command now all say so at the point of use.
- **Probe 12 (audio).** Audio reaches the API through machinery identical to video's and had still never been confirmed against a live call — "the same code handles it" is a hypothesis about the server, not a fact about it. The arm matches the shipped path exactly, including sending no `resolution`, since `AudioContent` has no such field.

### fixed
- **`mimetypes` disagrees with the API's accepted list, and this was latent until audio became reachable.** Python answers `audio/x-wav` for `.wav`, `audio/x-aiff`, `audio/mp4` for `.m4a`, `video/x-msvideo`, `video/x-ms-wmv` — none of which the Interactions API accepts, and the answers differ across platforms because `mimetypes` reads `/etc/mime.types` where it exists. A `.wav` file was rejected as an unsupported type, which reads as "Gemini cannot take wav" rather than "we asked for the wrong string". The single `video/quicktime` special case is now an explicit alias table, which is the form that survives the next platform.

## 1.22.2

### fixed
- **`.claude/` audited as a unit for the first time; two rules were teaching things that are not true.** `rules/skills.md` gave `uv run python skill-maintainer/scripts/check_freshness.py` as the correct form — a path that has not existed since the CLI absorbed that check, sitting one line from the form that does work. A rule teaching a command that fails is worse than a rule with no example. And `rules/plugins.md`'s heading read "three files" while its own body correctly listed `pyproject.toml` and `uv lock` alongside them; the heading is the part that gets skimmed. Two further findings are recorded rather than acted on, because both need a judgment call: the local `fast-executor` and `task-coder` agents are byte-identical to templates `model-routing` ships, which is the legitimate template-then-install shape but has **nothing watching the pair**, so a template change would leave this repo's copies stale in silence; and `doc-claim-auditor`'s entire evidence base is specimens from `mitate`, which now lives in its own repo.

### added
- **A handoff section in `docs/internals/best_practices_maintenance.md`** — current queue, decisions waiting on the owner, the `.claude/` findings, and the things that will bite. Placed in a tracked document on purpose: the session log is gitignored and does not survive a fresh clone, so anything the next session actually needs is duplicated where it travels.

## 1.22.1

### fixed
- **`dev-conventions` 0.15.4 → 0.15.5 — two skills were red for having no tier, not for being wrong.** `dep-audit` and `doc-conventions` both sat at `last_verified: 2026-07-05` with no `review_interval_days`, so both inherited the 30-day default and went red at 33 days. Reviewed against their actual sources rather than date-bumped: `dep-audit`'s command table was verified live — `uv audit`, `uv audit --frozen`, `bun audit`, and `bun audit --audit-level` all exist and behave as documented — and `doc-conventions`' claims match this repo's practice (last-updated headers, lowercase filenames, gitignored `internal/`, `internal/log/log_YYYY-MM-DD.md`). Both are accurate; neither had a window matching how fast its source moves. `dep-audit` gets 90 days (it wraps two third-party CLIs, the tier `advisor` already uses), `doc-conventions` gets 365 (house methodology with no external source). This is the tiering doctrine applied to the two skills that had been left out of it: a uniform window makes the board permanently red, and a permanently-red board is an ignored board.
- **A tracked doc cited a gitignored file.** `docs/internals/gotchas.md` pointed at `internal/postmortems/2026-08-04_control-audit-census.md` for the control-audit finding that retired the last two `enabledPlugins` disables. The file exists locally but `internal/` is gitignored, so a fresh clone reads a citation it can never follow. The finding is now stated inline — the disable's stated reason named SessionStart hooks both plugins had already deleted, so it suppressed nothing and the rationale was all that kept it alive — which is the part a reader needed anyway.

With these, `skill-maintain test` is **269 passed, 0 failed**.

## 1.22.0

### fixed
- **`skill-maintain` 0.31.1 → 0.32.0 — the freshness arm was dating the wrong event, and its green was an artifact.** `upstream hash state fresh` read the mtime of `upstream_hashes.json` to date the state the provenance join trusts. But `sources.py:206-207` rewrites that same file on every run to store tracked-repo HEADs, while fetching zero documentation pages. On 2026-08-07 the arm was shipped and its `fetched 0d ago` reported as evidence it worked — the number came from a `skill-maintain sources` run minutes earlier, which is nothing but git pulls. A control reporting green on an operation that never touched its subject is the exact class this repo exists to catch, and this one was self-inflicted. Replaced by `upstream fetch fresh`, reading a `state/last_fetch` marker with exactly **one writer**: `upstream.py`, after a successful fetch. Five arms; the separation itself is pinned (`test_marker_is_not_written_by_other_state_writes`), because that is the property that decays. Mutation-proven: backdating the marker 45 days produces `fetched 45d ago > 30d`. A missing marker now **fails** rather than assuming freshness — it went red on first run, as it should have.
- **The provenance arm passed when nothing parsed.** Its condition was `not join.moved`, so a run that parsed zero annotations — a reformatted comment, a broken regex — reported PASS with `0 harness annotations`. That is verbatim the failure `JoinResult`'s own docstring names, in the arm that consumes it. A floor now fails the arm when the file has annotations and the parser returns none.
- **The join was fed the whole hash state instead of the configured pages.** Nothing prunes a URL removed from `upstream_urls`, so its last hash sits in state forever and its sections would report `current` against a page no run will fetch again — live as of dropping `discover-plugins`, whose hash had to be deleted by hand. Now scoped to `get_upstream_urls`, agreeing with `upstream.py`, which already scoped to `watch_pages`.
- **The arm's scope string omitted `unattributed`**, hiding the bucket with the highest measured real-defect rate (5 of 6) from the routine board and leaving it visible only in `skill-maintain upstream` output.

## 1.21.0

### fixed
- **`skill-maintain` 0.31.0 → 0.31.1 — three provenance-join bugs a multi-angle code review surfaced, each confirmed against this repo's own live state.** A blank-but-present `verified_hash` (`verified_hash: `) parsed to `""` rather than absent, and `"".startswith("")` is vacuously true, so a section never actually checked against anything reported **current**; the gate is now `if not ann.verified_hash`. An annotation comment wrapped across two lines matched nothing under the old per-line regex and silently vanished from every bucket; `parse_annotations` now splits the file into section spans first and matches each span as a whole, so a wrapped comment is still found instead of disappearing. A page missing from an `upstream` fetch (renamed or removed) kept its last-known hash forever — `new_hashes` was seeded from `old_hashes` and the NOT-FOUND branch never touched it — so the section it backed kept reading **current** with nothing left to verify it against; the hash is now dropped on NOT FOUND, so the section correctly falls into `untracked`. Also: `test_repo_hygiene`'s read of `best_practices.md` had no `encoding="utf-8"` where `upstream.py`'s equivalent read of the same file did — both now agree.
- **`skill-dashboard` 1.1.3 → 1.2.0 — the TypeScript dashboard gets the provenance join, and stops double-counting a live worktree.** `checks.ts` still shipped the `best_practices.md fresh` date check the Python side retired in 0.29.0 for being misleading; it now runs a direct port of `join_provenance`/`parse_annotations`, verified byte-for-byte against this repo's actual state (`23 harness annotations: 19 current, 4 unbound, 0 untracked source`, matching `skill-maintain test` exactly). Separately, `discoverPlugins()` had no equivalent of Python's `SKIP_PATH_PREFIXES` worktree skip, so a live `.claude/worktrees/` checkout was scanned as a second copy of every plugin — verified live, this repo's own worktree was inflating the count from 19 to 38. Both gaps came out of the same code-review pass that found the Python bugs above; the same "current \|\| empty-string" mistake is fixed in the TS port from the start rather than ported over.

### added
- **`test_repo_hygiene_provenance.py`** — the provenance-join glue inside `test_repo_hygiene` (state loading, the `local_repos` namespace, mtime-based staleness, Result formatting) had no direct test; only the pure `join_provenance`/`parse_annotations` functions underneath were unit tested. Five tests now exercise the actual code path, mutation-proofed against the `local_repos` wiring specifically.

## 1.20.0

### changed
- **`skill-maintain` 0.30.0 → 0.31.0 — the `uncited` bucket is renamed `unattributed`, because its obvious action was wrong five times out of six.** "Cited by nothing" reads as "delete the page". Acting on it the first time showed the bucket has two diagnoses with opposite remedies and identical output: the page is genuinely unused, or **the file asserts a fact that page documents while citing some other page for it**. Of six reported, five were the second: `settings` is the canonical home of `skillListingBudgetFraction` (default `0.01`), `skillListingMaxDescChars` (default `1536`), `disableSkillShellExecution` and `skillOverrides`, all asserted in the file and all sourced to the skills page; `plugins-reference:444` states "If you include a manifest, `name` is the only required field", the exact claim the file quotes; `plugin-marketplaces` holds both required-field tables; `permissions:65` defines the `Tool(specifier)` syntax the `if` field uses. The report now says so in the output rather than leaving the reader to infer it, and the docstring carries the triage rule: grep the page for what the file asserts before dropping anything.
- **`skill-maintainer` 0.23.2 → 0.23.3 — the four miscitations corrected, and `discover-plugins` dropped.** Those four pages are now cited by the sections that depend on them, verified and stamped against today's fetch. `discover-plugins` was the one genuine case-1: no fact in the file has its home there, so it leaves `upstream_urls` and its snapshot and hash are removed. The MCP page is attributed too — the scoped `mcp__plugin_<plugin>_<server>__<tool>` matcher is documented there rather than on the hooks page, which the item now says. **The join is clean for the first time: 23 harness annotations, 19 current, 4 unbound, 0 untracked source, 0 unattributed.**

### added
- **`docs/internals/mcp_spec_2026_07_28.md` — MCP's newest spec is a migration, not a bump, and this records the gap rather than papering over it.** The 2026-07-28 revision removes protocol-level sessions and the `Mcp-Session-Id` header, **removes the `initialize`/`notifications/initialized` handshake entirely** in favour of per-request `_meta`, makes `server/discover` mandatory, replaces the GET endpoint and `resources/subscribe` with `subscriptions/listen`, deletes `ping` and `logging/setLevel`, moves tasks into an extension, replaces server-initiated requests with the MRTR pattern, and requires `resultType` on every result. This repo implements none of it: `readwise-reader` locks `mcp` 1.28.1 and `skill-dashboard` has `@modelcontextprotocol/sdk` 1.27.1. Whether `readwise-reader` should move at all is an open question the doc states rather than assumes — it is a single-user local STDIO server, and most of what the stateless redesign buys, it does not need.

### fixed
- **`readwise-reader` 1.1.3 → 1.1.4 — a live footgun in the dependency pin.** It is an application and floor-pinned `mcp[cli]>=1.26.0`. The current SDK is **2.0.0**, whose `LATEST_PROTOCOL_VERSION` is `2026-07-28`, so any re-lock would have crossed a major boundary silently and pulled an SDK implementing a stateless protocol under code written for a stateful one. Now `==1.28.1`, matching what the lock already resolved and the house convention that applications pin exact. `skill-dashboard`'s `^1.24.0` is the milder version of the same drift — a caret cannot reach 2.x, so it is left pending the same scoping decision rather than changed silently.

## 1.19.0

### changed
- **`skill-maintain` 0.29.0 → 0.30.0 — the provenance join gains a second namespace, so a section can cite a tracked repo instead of a fetched page.** The Agent Skills spec is a git repo this project already clones (`coderef/agentskills`, a clone of `agentskills/agentskills`) and whose HEAD `skill-maintain sources` already records under `local_repos`. Its *website* is fetched by nothing, so the three sections citing `agentskills.io` were structurally unverifiable — the join could only report them as an untracked source forever. `join_provenance` now accepts `repos={path: head_sha}` alongside the page map, comparing by SHA prefix so the annotation can hold a readable short form while state holds the full forty characters. The three citations are repointed at the repo; **untracked source drops from 3 to 0**. Repos are deliberately excluded from the `cited by nothing` bucket: a tracked clone serves the whole project, so "no section cites it" says nothing about the repo.
- **`skill-maintainer` 0.23.1 → 0.23.2** — the three spec citations in the bundled reference now name `coderef/agentskills`, and the prose that told readers to resolve the untracked-source problem is replaced by a description of the state they are actually in.
- **`skill-maintain sources` run for the first time since 2026-05-04**, 95 days. The design record had flagged this arm as effectively dead while the docs arm stayed alive; the join needs current repo HEADs to mean anything, so refreshing it is now load-bearing rather than housekeeping.

### fixed
- **An unearned verification stamp, caught and removed before commit.** Repointing the citations initially wrote `verified_hash: 217be548` onto all three sections — asserting they had been checked against that commit, when this session never read the spec repo at all. That is precisely the false confidence `provenance.py`'s docstring says the optional hash exists to prevent, committed by the person who wrote the docstring. The stamps were removed and `last_verified` left at 2026-04-19, so the three now report **unbound**: correct source, never yet checked against a specific commit, and green only when someone actually reads it.

## 1.18.0

### added
- **`skill-maintain` 0.28.0 → 0.29.0 — the provenance join, so section freshness is a hash comparison instead of a calendar.** New `skill_maintainer/provenance.py` parses the per-section annotations in `best_practices.md` and joins them against the page hashes `skill-maintain upstream` already stores. Sections gain an optional `verified_hash`: the page hash the section was last checked against. The join reports five buckets and prints all of them — **moved** (page changed since the section was verified), **current**, **unbound** (no `verified_hash`, so movement cannot be detected), **untracked source** (cited but never fetched), and **cited by nothing** (fetched every run, used by no section). First real run: 18 harness annotations, 14 current, 1 unbound, 3 untracked, and 6 tracked pages no section uses. `verified_hash` is deliberately not backfillable — a section never checked against a specific fetch reports unbound rather than current, because guessing a hash manufactures the exact false confidence the module exists to remove. Only `harness` sections are joined; `model` and `craft` have no upstream page by construction.
- **Two repo arms replace one, because the join alone lies.** `best_practices provenance` fails when any section has moved and otherwise states its scope (`18 harness annotations: 14 current, 1 unbound, 3 untracked source`). But it reads *stored* hashes, so it reports a comfortable zero when nobody has fetched in months — so `upstream hash state fresh` dates the state the first arm trusts. Hash says what to conclude; date says when to go look, which is the 2026-08-04 dates doctrine applied to the one place a calendar is still honest. Both mutation-proven: corrupting a `verified_hash` produced `2 moved: hooks (hooks), hook types and events (hooks)`, and backdating `upstream_hashes.json` 45 days produced `fetched 45d ago > 30d`; both green on revert.

### removed
- **The `best_practices.md fresh` arm is retired.** It checked that the `last updated` line was within 30 days, which establishes that someone edited the file — not that anyone checked it against its source. On 2026-08-07 it read four days old and green while twelve of fourteen section annotations sat at 2026-04-19 and every cited page had moved twice. Editing is not checking, and the arm could not tell the difference.

### fixed
- **A fabricated finding, caught on the join's first live run.** `upstream_hashes.json` is shared state — `sources.py` writes tracked-repo HEAD SHAs into it under non-URL keys like `local_repos` — so the join reported both as "tracked pages cited by nothing". Callers now pass only watched URLs and the join refuses non-URL keys as a second line of defence. Arm added, red first.
- **One of the module's own tests was decorative and mutation testing caught it.** `test_craft_sections_are_not_counted_as_gaps` used a craft annotation with no `source`, so dropping the class filter entirely left it green — it could not distinguish "excluded because craft" from "excluded because sourceless". The fixture now carries a prose `source`, which is the shape the real file uses (`field-tested in a sibling repo's claims-reminder apparatus`), and the arm fails under that mutation. Three mutations run against the module, three red.

## 1.17.0

### changed
- **`skill-maintainer` 0.22.0 → 0.23.0 — the reconcile finishes, and the sections that resisted it turned out to be misclassified rather than merely stale.** Nineteen of twenty-seven source annotations now carry 2026-08-07, up from eight. The remaining sections were not simply unchecked: several were tagged `harness` while holding house conventions, which is why re-deriving them against upstream kept finding nothing to derive. **`SKILL.md` under 500 lines is upstream** (`skills.md:387`, stated as a Tip). **The 4,000 and 8,000-token thresholds are ours**, as are `references/`-not-inline and the estimation heuristic; token budget now separates the two rather than presenting all six as platform limits. Same correction in skill-and-plugin-structure, where "no `README.md` inside a skill folder" is a house rule and upstream in fact encourages supporting files beside `SKILL.md` — templates, example outputs, scripts, reference docs — so that item is now labelled as the house preference it is. Description precision is likewise one upstream fact (the 1,536-char cap) wrapped in authoring judgment.
- **Two upstream facts we did not have, both about always-loaded cost.** Upstream targets **under 200 lines per CLAUDE.md file**, and gives a reason worth more than the number: longer files consume more context *and reduce adherence* — size is not only a cost problem, a bloated instruction file is followed less well. And an imported file still loads in full at launch, so splitting CLAUDE.md for tidiness moves the text without moving the cost; path-scoped rules are the lever that actually reduces it. Import depth is four hops, and relative paths resolve against the importing file. Distribution gains the three budget levers in order of what they cost you: trim at the source, set low-priority entries to `"name-only"` in `skillOverrides`, or raise the fraction.
- **The one unobservable source is now named as such.** Three sections cite `agentskills.io`, which is not in `upstream_urls`, so `skill-maintain upstream` cannot refresh them and their 2026-04-19 stamps will sit there indefinitely. That includes the 1024-character description limit — the oldest unverifiable number in the file. Each of the three carries the note, and spec compliance states the resolution: track the spec or stop citing it, because leaving one unobservable source in a file organised around observable ones is the inconsistency.

Remaining after this pass: three `agentskills.io` annotations (structurally unrefreshable until the source is tracked), one `plugins` page annotation at 2026-07-21, and four `craft` sections whose stamps are already correct as records of last review.

## 1.16.0

### fixed
- **`skill-maintain` 0.27.0 → 0.28.0 — discovery no longer scans a second checkout of the same repo.** `SKIP_DIRS` is a name-based skip list with no entry for `.claude/worktrees/`, which is where Claude Code puts a git worktree for `isolation: worktree` and `EnterWorktree`. A worktree is a full copy of every SKILL.md and plugin.json in the tree, so scanning it doubles every per-skill arm and makes the duplicate-name check fail listing nearly every skill. Found live: a locked worktree left by a parallel session on `claude/generalized-postmortem-skill-bbqnks` took `skill-maintain test` from 265 passed / 3 failed to **499 passed / 6 failed**, with 36 names reported as duplicates — a verification run corrupted by work happening beside it, which is the worst thing that can happen to a checker that is otherwise trusted. New `SKIP_PATH_PREFIXES` matches whole components against a relative path prefix. Three arms, the behavioural one red first; the two counterweights are born-green pins and mutation-proven at birth by widening the rule to the bare name `worktrees`, which fails them while leaving the behavioural arm green — the asymmetry that matters. **Live-fired against the real condition**: the fix was verified with the offending worktree still on disk, returning the suite to 265 passed / 3 failed.
  - Deliberately a path rule, not a `SKIP_DIRS` name entry: banning the bare name would hide a plugin legitimately called `worktrees`. Deliberately **not** "skip everything git-ignores", which sounds more principled and is more dangerous — a repo that gitignores its own skills directory would scan nothing and report green, the exact failure the `_skipped` docstring already warns about.

### removed
- **Stale documentation and the `schema-processing` research package deleted** (42 files), and every reference repaired rather than left dangling. `research/schema-processing` was a declared `uv` workspace member, so its removal broke `uv sync` until the member was dropped and the lock regenerated — deletion-induced breakage in a file nobody touched, which is why `dangling-refs:retire` exists. Dead links removed from `README.md`, `CLAUDE.md` (the MCP orientation and protocol rows), `docs/README.md` (the `guides`, `domain reports`, and empty `synthesis` sections), and `VISION.md` (the loading-hierarchy diagram embed). `docs/README.md` also gains the four `internals/` documents it had never listed — `context-cost.md`, `control_audit_design.md`, `agent_state_population.md`, `postmortem_output_formats.md` — since it claims to be the authoritative index. Lint is clean: no broken links, no count drift, no orphans.
- **`json-query` 0.1.1 → 0.1.2 — a shipped skill stopped citing deleted evidence.** Its SKILL.md carries a benchmark table with specific numbers (31ms vs 184ms, 3.7-7.5x speedups) sourced to `research/schema-processing/REPORT.md`, which the cleanup removed. A measured table whose warrant has been deleted is exactly the class this repo refuses to ship, so both the SKILL.md and the plugin README now point at `git show cc12498:research/schema-processing/REPORT.md` — the last commit containing the report — rather than a path that no longer resolves.

## 1.15.0

### changed
- **`skill-maintainer` 0.21.1 → 0.22.0 — reconcile against the twelve refreshed pages, eight of seventeen sections now genuinely verified.** A second unsupported claim died on contact: the agent reference asserted that `project` is "the documented default choice" for `memory`, and upstream documents no default at all — it is a three-way scope choice (`user` across all projects, `project` version-controlled, `local` not checked in), now stated that way.
- **The agent sections were the most wrong, because `tools` is not the last word.** Two filters run after it. The first removes a fixed list from every subagent even when listed — our list was missing `TaskOutput`, `Workflow`, and the `Agent`-at-depth-limit condition. The second applies to *background* subagents, which since v2.1.198 is the **default**, and reduces built-ins to twenty named tools; everything else is stripped whether inherited or explicitly listed, **and the removal reports no error** unless it empties the list. So the same definition resolves to different tools in foreground and background, and a `tools` entry outside that set silently does nothing. Also added: forks skip both filters, agent-team teammates keep the task and cron tools, `permissionMode`'s seven values, `background`'s default, `effort` levels depending on the model, worktree auto-cleanup, an agent `name` being unable to contain `:` (v2.1.218+, error to the debug log only), and `Agent(agent_type)` parenthesised type lists being ignored inside a subagent definition. `If NO entry resolves, the subagent refuses to launch` is now `usually fails to launch` — upstream hedges the word, and before v2.1.208 it launched tool-less.
- **Hooks gained the per-event exit-2 audience, `asyncRewake`, and three silent-failure cases.** Exit 2 does not reach Claude on `SessionStart`, `Setup`, or `SubagentStart` — the stderr renders as a hook-error notice to the *user*, so a hook trying to inject a correction there is talking to the wrong audience, and for `SubagentStart` the notice lands in the subagent's own transcript. `asyncRewake: true` is the supported shape for a long-running check that must still report failure. New silent cases: `if` holds exactly one rule with no `&&`/`||`/list syntax; plugin-bundled MCP tools need the scoped `mcp__plugin_<plugin>_<server>__<tool>` matcher or the hook never fires; `Edit(src/**)` rooting is v2.1.214+ behaviour, so a pattern written earlier quietly narrowed. Exec and shell form now carry the platform detail that matters — shell form resolves to `sh -c`, Git Bash, or PowerShell depending on host, and Windows exec form cannot spawn `.sh` files or the `.cmd`/`.bat` shims under `node_modules/.bin`.
- **Substitutions, frontmatter, and surface differences reconciled.** Added `${CLAUDE_PROJECT_DIR}` and `${CLAUDE_EFFORT}` (with Ultracode reporting as `xhigh`); noted that `${CLAUDE_SKILL_DIR}` for a plugin skill is the skill's subdirectory and not the plugin root; documented that both are substituted inside `allowed-tools` Bash rules, which is the supported no-prompt path to a bundled script; and pinned the inline `` !`cmd` `` rules — recognised only at line start or after whitespace, substituted once, output never re-scanned. Skill frontmatter gains `background`, plus the narrower six-field set that claude.ai uploads and the Skills API accept, which `argument-hint` alone is enough to fail. Surface differences gained skill-name precedence (enterprise over personal over project, any level over bundled, plugin skills namespaced), nested `.claude/skills/` discovery below the working directory, the `--add-dir` CLAUDE.md exclusion, and live change detection not covering a top-level skills directory created after session start. All three facts absorbed provisionally in 1.14.0 were confirmed against the live pages and re-stamped.

Stamps now spread across six dates instead of twelve identical ones. Eight sections carry 2026-08-07 and were verified item by item this pass: hooks, agents and tool access, agent frontmatter fields, hook types and events, string substitutions, surface differences, authoring shape, and maintaining-this-file. **Nine did not and keep their older stamps** — always-loaded context, skill and plugin structure, token budget, description precision, skill frontmatter fields (partially checked), distribution and budgets, composable directive pattern, and spec compliance. Several of those had individual items verified in passing; a partial check does not earn a full-section mark, which is the whole point of the per-section stamp.

## 1.14.1

### fixed
- **`skill-maintainer` 0.21.0 → 0.21.1 — a false claim in the file, caught by the first upstream fetch in 17 days.** All twelve tracked pages had moved since the 2026-07-21 snapshot (`hooks` +285/-101 lines and +12,297 chars; `sub-agents` +113/-57; `settings` +94/-65; `skills` +77/-18), so the restructure shipped in 1.14.0 was a reshaping of unverified content — it corrected four section stamps from git evidence and re-derived nothing against upstream. Spot-checking the highest-risk claims against the fresh snapshots confirmed fourteen and killed one: **"what a command hook does when it times out is NOT documented" is no longer true.** It is documented for exactly two events, and for command hooks both fail open — `UserPromptSubmit` cancels the hook and discards its output including `additionalContext` while the prompt proceeds without it, and `MessageDisplay` displays the original text. On every other event it remains unstated, which the item now says instead of overclaiming in either direction. Agent SDK *callback* hooks are separated out as the different surface they are: those fail closed, blocking the prompt and the tool call respectively. The err-long guidance survives with a stronger warrant — the silent bypass is now confirmed rather than inferred.
- **Timeout defaults were one number where upstream has five.** The item said 600 for `command`, `http`, `mcp_tool` and stopped. It now carries 30 for `prompt`, 60 for `agent`, `UserPromptSubmit` lowering the command/http/mcp_tool default to 30, `MessageDisplay` lowering it to 10, and `SessionEnd` hooks sharing a 1.5-second budget that a longer per-hook `timeout` raises to match, up to 60 seconds.
- **The absence-claim rule gains the half it was missing**, with this file as its own specimen. It already said a summarising fetch cannot source a claim that the docs do *not* say something. It now also says absence claims decay fastest and that nothing flags them: upstream adds one sentence and the claim dies, while no diff-watcher reports "a thing you called undocumented now exists". Where a gap must be recorded, state what IS documented and where, then name the remainder — that form fails loudly on recheck instead of silently.

Scope stated, because a partial check that reads as a full one is the failure this file warns about: eight of the sixteen hook constraints were verified, plus the `allowed-tools`/`disallowed-tools` semantics, the 1,536-char cap, the three listing-budget settings, compaction at 5,000/25,000, and the MEMORY.md 200-line/25KB limit. **No section stamp was bumped** — a partial pass does not earn a full-section verified mark. The full reconcile across all twelve refreshed pages is the next pass; roughly eleven further gaps are already identified, including per-event exit-2 stderr rendering, the scoped `mcp__plugin_*` matcher form, `asyncRewake`, `if` holding exactly one rule, and a different frontmatter allow-list for claude.ai uploads and the Skills API.

## 1.14.0

### changed
- **`skill-maintainer` 0.20.1 → 0.21.0 — the bundled best-practices reference is rebuilt in the shape it recommends.** It had become a 128-item checklist in which a line asserting a hard runtime fact (`timeout` is in seconds) was typographically identical to a line asserting taste (bullet points preferred over prose), and neither said what enforced it. It is now three parts — **constraints** (what must not happen, with the silent-failure cases marked), **gates** (each naming the command that produces its number), and **reference** (tables you look up, no checkboxes) — preceded by a new `## authoring shape` section carrying the Claude 5 shift: capability absorbs content, operating mode changes shape, and a three-question per-instruction test (carries what the model cannot derive / overrides a stated default / restates general competence). Every section now declares an **evidence class** — `harness`, `model`, or `craft` — which names the event that reopens it, and states **what enforces it**, with "nothing" stated rather than hidden: that is the honest answer for all 16 hook constraints and all 7 agent constraints. Deleted: `## quality signals` and `## iteration signals` (15 plain bullets asserting a 90% trigger rate and 0 failed calls per workflow, never measured here — the diagnostic half survives inside description precision, the unmeasured numbers do not), and the prose `## spec compliance` list, now a pointer at `cc_schema.py` because the validator is the rule and a prose copy can only disagree with it. The worldview intros that duplicated `VISION.md` are replaced by one pointer.
- **Four section stamps corrected against git rather than guessed.** Twelve of the file's fourteen `last_verified` annotations read `2026-04-19`. `b431907` ("reconcile best_practices.md with upstream", 2026-07-21) rewrote the hooks, frontmatter-fields, invocation-control and distribution content — adding the exit-code correction, the three `if` items, and the `allowed-tools` grants-not-restricts fix — and re-stamped none of them, so a section that *was* reconciled was indistinguishable from one that was not. Those four now read 2026-07-21. The sections that commit did not touch keep 2026-04-19: a reconcile that changed nothing in a section could mean "checked, fine" or "did not look", and the conservative reading is the honest one. Spec compliance keeps its April date because `09ac3d9` changed only the sentence naming which validator enforces it, not the items.
- **Four surface-difference facts absorbed** from the 2026-07-26 multi-agent doc read, where they had sat unabsorbed in `docs/internals/upstream_drift_backlog.md`: user-scope skills are not read in Cowork and cloud sessions; `context: fork` with `agent: Explore` or `agent: Plan` does not load CLAUDE.md; project skills load from every parent `.claude/skills/` up to the repo root; `--add-dir` loads them and `permissions.additionalDirectories` does not. Carried with their read date and an explicit re-verify instruction, because they were verified by that read and not by this one.

### added
- **`VISION.md` gains `### the model is a variable`**, placed after `### the harness is the system` so the pair reads in sequence: that section frames model and harness as one compound system, this one says the model half moves on its own schedule, changing both what a skill must say and what shape it must take. Principle 5 (`controlled retrieval over training data`) gains the boundary it was missing — retrieval earns its cost for knowledge that is versioned, project-specific, contested, or newer than the model, and not for general competence, where a skill spends context competing with a better plan the model already had. Principle 6 now names the three events that reopen the feedback loop, flagging the model release as the one with no mechanical detector. Design record: `docs/internals/best_practices_maintenance.md`, which also carries the evidence that the file's own `### instructions quality` section — "steps include expected commands", "bullet points preferred over prose", "critical instructions at the top" — was written for a generation that needed scaffolding, and has been shaping every skill authored since.

## 1.13.0

### added
- **`skill-maintain` 0.26.0 → 0.27.0 — version alignment learns about the fourth copy, `package.json`.** `check_version_alignment` compared plugin.json, marketplace.json and pyproject.toml. Both MCP-App plugins carried a fourth version string in `mcp-app/package.json` that nothing read and nothing checked, and both had drifted: skill-dashboard 1.1.0 against a plugin.json of 1.1.2, mece-decomposer 0.1.0 against 0.6.1 — five minor versions. The new branch compares every authored package.json under a plugin source against that plugin's manifest and names the offending file in the detail; `node_modules`, `dist`, `build` and `.backup` are excluded, because a check that reports every installed dependency is one people learn to skim past. A package.json with no `version` key is silent by design — that is the shape both apps now ship, and nagging about a deliberately deleted duplicate would reinstate it. Five arms, two red first; the two born-green pins (absent-version, dependency-skip) were mutation-proven at birth by deleting each guard and confirming exactly one arm went red. Live-fired against this tree by restoring the original drifted field: `FAIL repo/skill-dashboard version alignment (plugin.json=1.1.2 vs apps/skill-dashboard/mcp-app/package.json=1.1.0)`, then reverted to 274 passed, 0 failed.

### fixed
- **`skill-dashboard` 1.1.2 → 1.1.3, `mece-decomposer` 0.6.1 → 0.6.2 — the MCP apps stop authoring their own version, and stop misreporting it to their host.** Each app hardcoded `appInfo: { version: "..." }` in `mcp-app-wrapper.tsx`. That literal has a real consumer — it is the identity the app reports to its MCP host — and both were stale, so a host running the app installs resolved as skill-dashboard 1.1.2 was told 1.1.0, and mece-decomposer 0.6.1 was told 0.1.0. `vite.config.ts` now reads `.claude-plugin/plugin.json` at build time and injects `__APP_VERSION__`, throwing if the manifest carries no version rather than shipping a guess; the built single-file bundles were checked and report 1.1.3 and 0.6.2. The `package.json` copy had no consumer at all — nothing imports it, no build reads it — so it is deleted rather than maintained and the packages marked `private`, which is the two-question form in invariant 1b answered honestly: name the copy's consumer, and when the answer is nothing, delete it.
- **The dashboard's own version-alignment check was blind to the dashboard.** `checks.ts` walked every plugin and compared plugin.json, marketplace, pyproject and `SKILL.md`, found 1.1.2 == 1.1.2, and reported aligned while two stale copies sat in its own tree. It now reads authored package.json files under the same skip rules as the Python check, so the two implementations agree rather than quietly diverging. The `SKILL.md` `metadata.version` branch is removed: that field is a removed class per invariant 1, so the branch could only ever fire on a field that is not supposed to exist, reporting drift whose correct fix is deleting what it read.
- **`skill-maintainer` 0.20.0 → 0.20.1** — the plugin README claimed the tool "checks plugin.json/marketplace.json version alignment repo-wide", which stopped being the whole truth with 0.27.0; it now names every copy compared. `docs/internals/maintenance.md` gains the matching row.

## 1.12.0

### added
- **`skill-maintain` 0.25.2 → 0.26.0 + a 14-skill sweep across six plugins — dates migration step 1: skills whose source is in-repo code leave the calendar.** New `metadata.freshness: "cascade"` declaration, honoured by all three staleness consumers (`freshness`, `quality`, `test`): a cascade-covered skill is never stale by elapsed time — its source is code in this repo, whose drift the version cascade already surfaces, so a calendar window there is a proxy adding noise (the evidence class: content-triage red at 124 days, reviewed, zero drift found). `last_verified` stays as the record of the last human review; declaring both mechanisms is reported as a config error; unknown mechanism values fall back to the calendar so a typo cannot grant an unbounded window. Six test arms, behavioral ones red first, the born-green pin mutation-proven at birth; the third consumer (`skill-maintain test`) was caught red by running the tool and its arm pinned before the fix. Converted (calendar → cascade, versions patch-bumped): `gemini-bridge` 0.7.1 → 0.7.2, `mece-decomposer` 0.6.0 → 0.6.1, `readwise-reader` 1.1.2 → 1.1.3, `skill-dashboard` 1.1.1 → 1.1.2, `path-privacy` 0.16.1 → 0.16.2. Methodology skills, `plugin-toolkit` (upstream-docs source), and `advisor` (third-party source) keep their windows — the calendar remains the honest fallback where drift cannot be observed. Steps 2 and 3 (measure the 90-day tier, change-triggered freshness by source hash) stay filed in `docs/internals/maintenance.md`.
- **`skill-maintainer` 0.19.2 → 0.20.0 — maintain gains Phase 6, the mutation sample.** The release-time obligation filed 2026-08-04 fires with this release: each maintenance pass enumerates the test arms whose subject modules changed since the last pass, mutates a handful of subjects, confirms red, reverts, and reports mutations-run over arms-in-frame with exposure stated — re-proving on a rolling sample what red-first proved only at birth. Whole-suite mutation stays `test-audit`'s job. The old Phase 6 (review and propose) becomes Phase 7; maintain and quality skill docs also state the cascade freshness mechanism.

## 1.11.3

### fixed
- **`skill-maintainer` 0.19.1 → 0.19.2 — the manual freshness fallback stops asserting a flat 30 days.** The maintain skill's CLI-less path told the checker "within 30 days of today" while the real system has been tiered by `metadata.review_interval_days` since the interval work; the fallback now states the per-skill window (default 30 only when the field is absent) and the reason the tiers exist — a flat window makes the board permanently red, and a permanently-red board is an ignored board.

## 1.11.2

### fixed
- **`postmortem` 0.8.0 → 0.8.1 — the post-ship review's findings on the day-old skills, closed.** `control-audit`'s safety protocol carried three defects inherited verbatim from the design note: "scratch branch or worktree" conflated isolation levels (a scratch branch reuses the live working tree and isolates only the commit graph — a separate worktree or clone is now the stated mechanism); `git status` as cleanup verification is blind to branch, commit, stash, and reflog residue (verification now runs against the run's own artifact inventory); and the visibly-fake rule structurally conflicted with needle-threading for pattern-anchored controls (resolved: the needle wins at the matched token via a pattern-true dummy, the fakery moves to the surroundings, the token goes first on the inventory). The design note carries a dated correction block rather than a silent rewrite. `adversarial-verify` fixed twice: its step 2 no longer duplicates the agent's failure-shapes list (the list is maintained in the agent's step 4 only — the release that extended invariant 1b was itself carrying an unwatched copy), and its sibling paragraph no longer claims `claim-audit` already dispatches to the primitive (it states the same move independently and gains its pointer at its next content release, per the recorded deferral).
- **`skill-maintainer` 0.19.0 → 0.19.1 — Phase 5 wired in instead of bolted on.** The Rules block's "run all phases" no longer overrides Phase 5's skip-and-note default (an unrequested live-fire on a routine pass was the failure mode); Phase 6's inputs now include Phase 5's census findings, and the final summary reports the controls-audit outcome either way. `docs/internals/maintenance.md` gains the controls-audit row its on-demand table was missing.
- **Changelog 1.11.1 corrected same day**: two of its claims failed derivation against the tree (the agent pair's verdict lists had not diverged, and the deleted agent's specimens do not appear in the design note's evidence base); the entry now states the true warrant and marks the correction. Stale `last updated` headers on CLAUDE.md, README.md, plugin-patterns.md, and maintenance.md bumped to match their actual edit dates.

## 1.11.1

### removed
- **Repo-local `control-builder` agent deleted** — superseded by the portable copy the postmortem plugin ships as of 0.7.0. The pair had no mechanical mirror and no consumer the shipped copy cannot serve, and the local copy sat outside the shipped protocol (the vacuous verdict is `adversarial-verify`'s addition, which nothing routed the local agent through), so the home repo now dogfoods exactly what installs get. The deleted agent's four evidence specimens are the sibling repo's record and remain recoverable there and from git history at the deleted path; the design note's evidence base lists this repo's own, different, specimens. Repo-local config only — never part of any published plugin, so no plugin version or renames mapping is involved. Historical changelog and design-note mentions kept as history; the design note carries a status line pointing at the retirement. (Two claims in this entry corrected same day after a post-ship review derived them against the tree: the original text claimed the agent pair's verdict lists had diverged — they were identical — and that the specimens survive in the design note's evidence base — they do not.)

## 1.11.0

### added
- **`postmortem` 0.7.0 → 0.8.0 — `control-audit`, the third audit; the plugin is now the audit family.** Census and live-fire over everything check-shaped that fires outside the test suite: git hooks, Claude Code hooks (including ones disabled by env or config — a control that had to be turned off is a census row, not an omission), CLI validators, ambient reminders. Per control, four slots re-derived from current code — fires-via, guarded-by, retirement-condition, disclosed-uncontrolled-edges — each marked derived or transcribed, with "nothing" in a slot as the reportable finding. Live-fire is mandatory for controls nothing watches and dispatches to `adversarial-verify`, under the safety protocol from the design note: scratch branch, visibly-fake violations, never `--no-verify`, a green counts only with its needle shown, cleanup verified before reporting. Report-only, no standing meta-checks, headers re-derived not trusted — a run, not an artifact, so there is no new layer to drift. Plugin description widens from retrospectives to the audit family per the packaging decision in `docs/internals/control_audit_design.md`.
- **`skill-maintainer` 0.18.1 → 0.19.0 — controls audit listed as maintenance phase 5.** Per the control-audit cadence decision (on-demand plus a listed step, nothing automatic): the maintain skill now names the periodic controls audit where the postmortem plugin is installed, so the cadence has an owner without a scheduler.

## 1.10.0

### added
- **`postmortem` 0.6.1 → 0.7.0 — the adversarial primitive, shipped once instead of restated three times.** The plugin now carries a portable `control-builder` agent (state the claim precisely enough to be wrong, describe the positive result first, remove exactly one variable, verify the control actually ran, measure both sides) and an `adversarial-verify` skill stating the two-step protocol as two separate judgments: construct the refutation, then have a fresh pass — not the constructor — verify the needle was threaded before either outcome counts. A fourth verdict, vacuous, covers the green that never reached its subject. The agent ships mechanism and failure shapes only; the originating repo's evidence section stays local per the priors-rot rule, and installing repos are told to grow their own specimen record. `test-audit`'s spot-mutation step is now a dispatch to this primitive rather than parallel prose. Built from `docs/internals/control_audit_design.md`, which records why the primitive ships before the control-audit skill that needs it.

## 1.9.3

### fixed
- **`readwise-reader` 1.1.1 → 1.1.2 — content-triage reviewed against its source; the 124-day staleness red cleared honestly.** The review, not just the stamp: the skill's lifecycle (new → later / archive / delete) was checked against `tools/triage.py` (`triage_get_inbox` reads `location='new'`; the accepted actions are exactly `later`/`archive`/`delete`, single and batch) and `api/models.py`. It matches. The API model also carries `feed`, which the triage tools deliberately do not touch, so the skill's silence about it is correct scope, not drift; the rest of the file is decision-framework opinion with no code claims to drift. `last_verified` bumped to today per invariant 1 (written only after an actual review — this was one), and `review_interval_days` widened 90 → 365: the skill's source is this plugin's own triage tools, which change through this repo where the cascade already prompts a review, not on an external cadence worth a quarterly alarm.

## 1.9.2

### fixed
- **`skill-maintain` 0.25.1 → 0.25.2 — the two filed tests.py refactors, plus the window defects they were hiding.** Both changelog checks now share one fence-aware section extractor (`_top_changelog_section` over `_mask_fences`, fence rules as the path-privacy 0.16.x work settled them), which closed two real escapes in `check_changelog_claims` on the way: a `## ` line inside a fenced code block used to end the top section early — so a real claim below the fence escaped unaudited while a claim-shaped string *inside* the quoted example was audited and could false-fire — and an `[Unreleased]` section on top used to *become* the window, so the newest release's claims were never read. The window is now the newest release section by shape, fences blanked. Both defects recorded red first; four new arms, tool suite at 152. And `_version_candidates` no longer parses each pyproject twice behind differently-spelled exception tuples: `_pyproject_project` is the single reader, with `_pyproject_version` folded on top. CLI-only release — the skill-maintainer plugin carries no code from `tools/`, so no plugin bump (invariant 1).

## 1.9.1

### fixed
- **`gemini-bridge` 0.7.0 → 0.7.1 — the three low-severity items from the 2026-08-03 review, closed.** `--allow-prompt-secrets` now waives the block, not the look: the scan still runs and prints its findings, followed by an explicit "sending despite the finding(s) above" line — the flag used to skip scanning entirely, which removed the one moment a real secret could still be stopped on exactly the runs that needed it. The config route (`scan_prompt = false`) still skips the scan altogether: it is a standing project opt-out, not a false-positive claim, and the distinction is now pinned by a test each way. The ledger's `prompt_scanned` field keeps its value semantics (False = the scan did not gate the send, either route) so existing audit filters keep working; its comment and the README paragraph now say "did not gate" rather than "never checked", which the flag route made untrue. `ledger.jsonl` is now chmod 0o600 like every run file beside it — it carries model, recipe, session id, and interaction ids, and default umask left it as the one world-readable record of all that. And `probe.py`'s header no longer claims it "deletes every interaction it stores": probe 8's own settled finding is that the delete returns 501, so the header now says what the cleanup actually achieves — files removed, interactions permanent. Two new arms recorded red first plus one pin; suite at 228.

## 1.9.0

### removed
- **`apps/heylook-monitor` deleted.** The MCP App dashboard for the external heylookitsanllm server, frozen since 2026-02-13 — every touch since was sweep collateral, no tests, TypeScript outside the workspace so no repo check ever exercised it. It was never a marketplace plugin (README row only, clone-and-build distribution), so no installed copies exist, no `renames` mapping is needed, and this is not a breaking change for any plugin user. Its deletion also closes the 2026-08-03 egress-sweep follow-up by removal rather than patch: the `0.0.0.0` bind with open CORS and unvalidated `HEYLOOK_URL` is gone instead of fixed. Recoverable from git history if the heylookitsanllm repo ever wants it. Deliberately left in place: the historical changelog entries describing its addition and lockfile migration, and the `skill-maintain tune --project heylook` CLI example, which names the external server repo, not this app.

## 1.8.0

### added
- **`claim-audit` 0.1.0 — new plugin: the added prose of a diff audited as untrusted claims.** Built from `docs/internals/claim_audit_design.md`, one session after the spec was captured, per the deliberate defer. The procedure that survived field contact in the sibling repo: extract counts, statuses, and attributions from added lines by reading (a regex scanner measured above 85% false positives at this); name the deriving command *before* running anything; run and record both sides so a reader can disagree with the verdict; label the unsourceable (`(memory)`/`(local)`/`(reported)`, past-tensing, or deletion) rather than failing it; end every report with its own scope — lines read, claims extracted, claims derived — because a green report indistinguishable from a run that read nothing is the class the skill exists to catch. Three conditional arms: adversarial-input construction when the diff touches executable behavior (the entire difference in finding the only true code defects in both motivating samples), control-vs-reimplementation reading when the diff mirrors logic living elsewhere (highest measured yield), and the invalidation grep when a decision just landed (stem variants, case-insensitive). Report, don't rewrite — auditor findings shrank on caller verification often enough that the weigh-it-yourself step is load-bearing. Decisions against the design note's open questions: own plugin (runs pre-commit on any repo, couples to nothing here), no shipped agent (subagent briefings carry shapes, not state), and portability via citing the installing repo's own drift record, with a report-only first run where none exists. The skill carries the spec's scope caveat verbatim: the yield ordering was measured in a green-by-default corpus and is not universalized.

### added
- **`gemini-bridge` 0.6.1 → 0.7.0 — recipe-free calls, every parameter a flag.** `-r` is now optional: a call without it runs as `adhoc` — labeled that way in the run directory and ledger — and sends no `system_instruction` at all unless one is supplied (an empty stance field is omitted from the request rather than sent as `""`, since the field is interaction-scoped and billed). Every parameter a recipe could set is now a CLI flag with CLI > recipe > default precedence: `--thinking-level`, `--seed`, `--max-output-tokens`, `--service-tier`, `--schema-file`, `--label k=v`, `--store`, plus `--system`/`--system-file` for an ad-hoc stance. Thinking still defaults to `minimal` on the recipe-free path — the probed cost finding stands, so raising it stays an explicit act. Two refusals are design, not accident: `--system*` does not combine with `-r` (the run is labeled with the recipe's name, and swapping the stance under that name would mislabel the record), and `--continue-from` still requires storage (`--store` is the ad-hoc opt-in; stored interactions cannot be deleted). Also closed while in the file: the 2026-08-03 follow-up gap where the prompt scan skipped schema descriptions and labels — the scan now covers every outgoing text channel (prompt, system instruction from any route, serialized schema, label values), recipe-provided or CLI-provided alike. Eighteen new test arms — seventeen recorded red first; the eighteenth (a typo'd recipe name still errors rather than silently going ad-hoc) pinned a guard that already held, and was green from the start. Suite at 225.

### fixed
- **`dev-conventions` 0.15.3 → 0.15.4 — `--explain` discloses what its count does not measure.** The consumer's follow-up on the count feature, an hour after it shipped: the count measures redundancy, not independence — a rule and a sentence *about* the rule count alike, so "+1 more" can be two rules or one rule plus its epitaph. No positional discriminator separates those the way fences separated commands from rules, and chasing it lexically is the whack-a-mole this arc already refused twice; per the control-authoring checklist's what-it-does-not-do discipline, the limit is stated in the output itself — one footer line on every explain run, pinned by the count test. First-match understated robustness; the count could overstate it, for the mirror-image reason; the disclosure closes the pair.

## 1.6.3

### fixed
- **`dev-conventions` 0.15.2 → 0.15.3 — `--explain` now prints a matching-line count with the first match.** The consumer's first real run surfaced the founding specimen one level up: the diagnostic can point at a real match that isn't the reason. Their tdd coverage displayed a meta-sentence *describing the silence* as the match, making a reader reasonably suspect the gate was silencing off its own epitaph — when the load-bearing rule independently held it, provable only by a hand-run counterfactual. The explain line now appends "+N more matching line(s) — deleting the shown line does not open the gate" whenever coverage rests on more than one line, so deletion-robustness is legible without the counterfactual. Pinned both ways: two covering lines must show the count, one must not. Display-only; the silent path is untouched.

## 1.6.2

### fixed
- **`dev-conventions` 0.15.1 → 0.15.2 — consumer-measured fixes to the coverage machinery, same day as its first field deployment.** Three changes, each driven by the consumer repo's measurements rather than argument. **Coverage now greps prose only**: fenced code blocks are blanked before matching (line numbers stay true; inline code spans still count — "use `bun add`, never `npm install`" is a rule with code in it). The rule-vs-command discriminator is positional, not lexical: the consumer measured a fenced `bun run` parity command silencing the javascript block in a repo with no npm prohibition and no pinning policy anywhere — a wrong verdict, in the unrecoverable direction. The strip can only remove coverage, so it errs toward a block loading, which mute already recovers; the one regression class (conventions stated inside a fenced block) fails the same safe way. **Force now overrides both gates**: the consumer verified that the trigger match short-circuited before the directive state was ever read, so `"javascript": true` could not recover a block whose markers were gitignored or below scan depth — force existed to make wrongful silence recoverable and recovered only one of the two ways it happens. State is now read first (still a pure-bash no-op for config-less repos). **`--explain <dir>` narrates the gates**: three causes of silence (trigger never fired, muted, ground covered) were byte-identical, and the founding specimen took a manual `bash -x` dig to diagnose; the mode shares `directive_state`/`ground_match` with the silent path so the explanation cannot drift from the behavior, prints the exact matched line per directive, and doubles as the specimen-accumulation instrument without which any "tune after N specimens" trigger stays unreachable by construction. Configure's `show` now includes the table. Pinned by four new arms (fenced-commands-don't-cover recorded red first, inline-spans-still-cover, force-overrides-trigger-miss, explain-names-the-gate); suite at 147. Filed, not built, in plugin-patterns.md: the gitignored-marker limit (a prose trigger can be true on one machine and false on every clone — bounded blast radius, noted), and the 0.16.0 strategic step — init declaring coverage so the regex demotes to a fallback. A second consumer specimen (the two hooks "disagree" about JS-ness) was withdrawn after proper measurement: the enforcement guard walks up from cwd and resolves the managing lockfile per directory, so detection-scans-down and enforcement-walks-up are both correct for their consequence profiles; the withdrawal is recorded because the confident false inconsistency came from testing at the wrong cwd.

## 1.6.1

### fixed
- **Pre-push review of the unpushed day: ten findings, eight fixed, two filed.** A code review over the day's seven local commits, applied before anything left the machine.
- **`dev-conventions` 0.15.0 → 0.15.1 — the ground patterns matched token mentions, not stated rules.** Verified specimens: `last.updated` matched the bare `last updated:` freshness stamp the doc-conventions directive itself mandates; `test.first` matched "ordered latest first"; `\buv\b` under `-i` matched "UV mapping"; `internal/log` substring-matched "internal/logging"; `\bnpm\b` matched "distributed via npm". Wrong-direction failure: a wrongly-silenced block was unrecoverable, since mute can only force silence. Patterns now demand rule-shaped context ("never use npm" covers ground, "distributed via npm" does not) with all five specimens pinned as test arms — and the missing escape exists: an explicit `true` in the `directives` map force-loads a block past coverage, `unmute` now removes the key (back to coverage-decided), and `force` is a first-class configure action. Also fixed from the same review: metadata is handled as a head-only class (ground honored anywhere in the leading metadata run, body lines that merely look like metadata survive into output, future metadata keys neither leak nor eat content), the trigger match runs before any jq/grep spawn, and the live-repo silence claim in gotchas.md is now actually pinned by `test_this_repo_stays_fully_covered` — the arm existed only as prose, which is this repo's most-documented failure class, committed by the session that spent the day documenting it.
- **`skill-maintain` 0.25.0 → 0.25.1 — the changelog-claims resolution map was machine-dependent and could double-report.** `_version_candidates` globbed `*/*/pyproject.toml` with no skip filter, so gitignored `coderef/` reference clones entered the map at whatever version the local checkout holds, and the repo's own root pyproject was invisible via `--dir` on single-package repos. Now filtered through `_skipped` with the root pyproject included. And a run with failing claim rows no longer also appends a passing summary row under the same check name — the scope count rides the failing row instead.
- **`skill-maintainer` 0.18.0 → 0.18.1, `postmortem` 0.6.0 → 0.6.1 — doc hygiene from the same review.** The best-practices directive contract now documents the `# ground:` line (it still said trigger-only, so a fresh `skill-maintain init` elsewhere would have taught the pre-0.15.0 contract); the postmortem README now describes 0.6.0's absent-artifact marking and carries a current date; stale `last updated` stamps refreshed where this diff had already violated the rule it ships. Filed, not fixed (follow-ups in the session log): unifying the two top-section extractors in `tests.py`, and collapsing its triple manifest parse.

## 1.6.0

### added
- **`dev-conventions` 0.14.0 → 0.15.0 — scaffolder, not broadcaster.** The load-bearing fact: scaffolded text reaches every collaborator's Claude through normal context loading; broadcast only ever reached installers. So the ambient tier inverts. New `/dev-conventions:init` scaffolds tailored convention lines into the repo's own files, once — detects the stack, skips ground the repo already covers, applies the would-the-model-do-it-anyway exclusion to every line, tailors to the repo's actual state (an npm repo gets offered the migration, not a rule contradicting its lockfile), shows the diff, never auto-commits. And the SessionStart hook now silences each block automatically wherever the repo's own files cover that block's *ground* — per block, not per file: each directive declares its ground as a regex on line 2, and the hook greps root CLAUDE.md, `.claude/rules/*.md`, and config `rules[]` before injecting. The granularity was the one substantive review flag from the consumer repo, and it is what keeps 0.14.0's guardrail: an architecture-only CLAUDE.md silences nothing (pinned by a test arm), while a repo stating its own package-manager rule silences exactly that block. Coverage gates prose only — the PreToolUse enforcement hook never consults it. Muting (0.14.0) remains as the manual override for ground the pattern cannot see. Bracketed per the pattern this repo canonized yesterday: nine pytest arms in the repo suite, including metadata-never-leaks and every-shipped-directive-declares-ground. Broadcast remains the default for repos with no coverage at all; the arc's next step (a one-line self-extinguishing pointer for bare repos) is deliberately not in this release.

## 1.5.0

### added
- **`skill-maintain` 0.24.0 → 0.25.0 — the changelog's version claims are now checked against the manifests.** `check_version_alignment` proves `plugin.json`, `marketplace.json` and `pyproject.toml` agree with *each other*; nothing proved they agree with what the changelog SAYS shipped. Those are different guarantees with different consumers — the changelog is what a reader trusts to know a fix landed, while `marketplace update` resolves the manifest — and the gap produced a specimen the same day it was named: two sessions committing in parallel landed a 1.4.0 entry claiming `postmortem` 0.6.0 while both manifests still read 0.5.0. Internally consistent, therefore green, and 241 tests passed on it.

  `check_changelog_claims` parses ``name X.Y.Z → A.B.C`` out of the **top section only** and requires the target to match a version that name actually carries. Scoping is the whole design: every one of the 85 claims in this repo's history would fire against today's manifests, because an old entry describing an old state is correct, and a check that reds permanently is a check that gets disabled. Names resolve through plugin manifests, `*/*/pyproject.toml`, and console-script aliases, and a name may legitimately hold two versions at once — `skill-maintainer` is a plugin at 0.18.0 and a CLI at 0.25.0 that version independently by design, so a claim matching either passes rather than the check guessing which was meant.

  Measured before shipping: 78 of 85 historical claims resolve, and all 7 misses name retired units (`agent-state`, `agent-state-mcp`, `env-forge`, `tui-design`), which take the report-don't-fail path — observed false failure rate 0. Recorded red against the live defect first (manifests reverted to `HEAD`, check fired, naming both numbers), then green. The header carries what it does not do — top section only, so a claim unsatisfied until the next section lands escapes permanently; the pre-arrow version is unread — and its retirement trigger: a generated changelog drops the claim form, the resolved count falls toward 0/N, and the green goes vacuous while still reading green, at which point delete it rather than teaching the regex new shapes.

## 1.4.0

### added
- **`postmortem` 0.5.0 → 0.6.0 — the `artifacts` list is now resolved at write time and marked at read time.** `filing.md` has always asserted that `artifacts` is a projection of the body's citations and "it is checkable: if the two sets disagree, one of them is wrong" — and nothing checked it, at either end. A repo running the plugin caught the specimen in vivo: a path written into a postmortem's frontmatter from working memory, hours after the file it named was created, landing one directory off. It was caught by a human resolving each entry by hand while assembling the list, and that repo's own escape analysis recorded the gap plainly — the check that should catch it mechanically does not exist.

  The failure is quiet in both directions and it lands on the one view `artifacts` exists to serve: a by-artifact index gains a row for a file nobody examined, while the file that *was* examined shows nothing written about it. That is the silent-undercount shape — a reader cannot distinguish "nothing was written" from "the tool did not understand it", which is the exact failure `postmortem-index` already refuses to commit for missing frontmatter, reached by a path it did not defend.

  Two halves, no new machinery. `filing.md` now says to resolve each path against the tree while assembling the list rather than writing it from memory, and to decide the ambiguous case rather than leave it — the field also admits commits and command names, which are not paths and are not checkable that way. `postmortem-index` checks path-shaped entries against the working tree and **marks** the ones that do not resolve instead of dropping them: the mark reads *not in the tree today*, because a postmortem is historical and a file examined a year ago may simply have been renamed since. That makes the same mark do double duty as a staleness signal on the artifact list. `references/index-page.md` gains the `.absent` rendering in both views and a check that an unresolved artifact still gets a by-artifact row — an absent artifact missing from that view is indistinguishable from one nobody ever wrote about, which would rebuild the defect one level down.

## 1.3.0

### added
- **`dev-conventions` 0.13.0 → 0.14.0 — ambient directive blocks are now mutable per repo.** Field report from a repo running the plugin alongside its own mature conventions: the generic TDD block's letter ("one line on what breaks if it is deleted") differed from the repo's sharper local rule (header claim plus per-case rationale, enforced by its own checks), and the repo paid reconciliation cost on every test it wrote — twice disclosing a "shortfall" against a form its own stronger rule doesn't use. The only prior escape was disabling the whole plugin, which is exactly how this repo itself runs it (invariant 6) — all-or-nothing where the wanted operation was a trim. `.dev-conventions.json` gains a `directives` map keyed by directive filename (`python`, `javascript`, `tdd`, `doc-conventions`); the SessionStart hook skips muted blocks with the same explicit `has()` guard the PreToolUse hook uses for `enforce.*`, and the configure skill gains `mute`/`unmute` actions that require naming the superseding local rule before muting — muting a block nothing replaces is losing the convention, not trimming a duplicate. Fixed in the same pass: a repo muting every shipped directive kept losing its own `rules[]`, because the empty-context exit ran before rules were appended — caught by testing the all-muted arm before shipping, moved the append above the exit.

- **`skill-maintainer` 0.17.1 → 0.18.0 — best-practices reference gains a "control authoring" section.** Distilled from a sibling repo's field-tested claims-reminder apparatus: anything check-shaped a plugin ships (hook, validator, reminder) carries a four-section header (why not the obvious alternative, measured false-positive rate with its sample, what it does not do, a retirement trigger named at install), a subordination rule for classes that become mechanically checkable, deduplicated and measured reminder output, factual-statement phrasing for model-facing text (imperatives can trip injection defenses and silently reroute the message to the terminal), scope-stating greens, collision-proof fixtures over probably-won't-collide ones, and a bracket over the control itself. The companion bracket-the-hook pattern — the arms that pin each rot mode, plus the PreToolUse delivery semantics verified against the upstream snapshot — landed in `docs/internals/plugin-patterns.md` (repo docs, not plugin content).

### changed
- **Two directive rules restated as properties instead of forms.** The TDD claim-per-test line now names the property (every test's claim must be recoverable) with the one-line comment as default form and a file-level header convention as an accepted alternative. The doc block's "every doc" dating rule now respects classes a repo deliberately exempts (changelogs, dated records), and the filename rule defers separator choice to the repo's existing convention. Both changes came from the same field report: a generic rule stating a form turns a repo's deliberate, better-guarded practice into an apparent violation. The injected block also now opens with a standing supersession line — a repo-local rule covering the same ground wins — so the escape is stated once instead of reconciled per block.

## 1.2.7

### fixed
- **`path-privacy` 0.16.0 → 0.16.1 — a NUL byte could forge a closing fence to the shell engine.** Found by an adversarial review of 1.2.6, whose 4,000-body differential fuzz otherwise confirmed the two engines agree. BSD awk ends its *record* at a NUL, so a ` ``` ` line with a NUL tail reached the fence function as a bare run — a valid closer — while the Python twin saw the non-blank tail and kept the fence open: the split-engine class 1.2.6 existed to eliminate, reopened through bytes no honestly-authored text file carries. A `tr '\000' '\001'` in front of the awk keeps the forged tail visible, which is both the agreeing and the fail-closed direction. Scoping note recorded in the test: the *scanner* never reaches fence logic for NUL-bearing files — they take its pre-existing binary detour ("not scanned, check by hand", exit 0) — so the fix and its test live at the library level, where the PreToolUse hook and the scrub call directly. Mutation-checked: removing the `tr` turns the new fixture red — after the first mutation run was itself caught being a no-op (a quoting layer swallowed the needle; the retry asserts the needle exists before claiming anything).

- **`gemini-bridge` 0.6.0 → 0.6.1 — `ledger.record`'s `prompt_scanned` default flipped to False.** Same review: defaulting the new field to True rebuilds 0.6.0's bug one forgotten kwarg from now — a future call site omitting it would mislabel an unscanned run as scanned, hiding it from the exact audit filter the README points at. Absent now means "assume not scanned"; a caller that did scan says so explicitly. Both call sites already pass it, so nothing was live.

## 1.2.6

### fixed
- **`path-privacy` 0.15.0 → 0.16.0, `skill-maintain` 0.23.0 → 0.24.0 — the fence pass 1.2.5 shipped was not markdown, and the difference was two working bypasses.** Found by an adversarial review of that release. Both engines toggled fence state on ` ``` ` *or* `~~~` interchangeably, but markdown closes a fence only with the character that opened it — so a `~~~` line inside a ` ``` ` block flipped the state off, and a marker that renders as a code example to every renderer and every human was live to the scanner. The exact class 1.2.5 claimed closed, reachable again by adding one line to the example. Run length was ignored the same way, so an inner ` ``` ` closed an outer ` ```` ` demonstrating it.

  The second bypass was worse because it split the engines. The shell's fence indent was `[[:space:]]` under `LC_ALL=C` — ASCII-only — while the Python twin used `\s`, which matches U+00A0 and friends. A NBSP-prefixed fence was therefore a fence to Python and not to the shell: the commit gate treated the marker as live and exempted the file, while `_has_skip_marker` returned False, which kept `check_marker_denylist` — the loud-recurrence backstop the whole design leans on — silent about a file the gate was waving through. The locale pin that fixed 1.2.4's grep skew had introduced the inverse skew one function over.

  Fences now follow markdown's own rules in both engines: a fence opens after at most three ASCII spaces with a run of three or more backticks or tildes, and closes only with a blank-tailed run of the *same character, at least as long*. Closing is strict and opening liberal deliberately — an over-eager open hides a marker and costs a loud false positive, an over-eager close un-hides one and costs a silent exemption — and an unclosed fence swallows to the end of the window for the same reason. The awk is procedural rather than regex because interval expressions are missing from older mawk, and this library runs on whatever awk the host has.

  Pinned by five new fenced fixtures (mismatched characters both directions, shorter-run-inside-longer, unclosed at EOF, info-string on a would-be closer), three closing-rule tests, and a cross-engine agreement test over NBSP, LINE SEPARATOR and IDEOGRAPHIC SPACE prefixed fences — the divergence class directly. Mutation-checked in both engines: restoring the toggle turns five shell tests red, and dropping the same-character/length rule from the Python copy turns three red including the agreement test. Neither bypass was live in tracked content.

- **`gemini-bridge` 0.5.3 → 0.6.0 — the ledger positively mislabelled unscanned runs as scanned.** `allow_prompt_secrets` records only the CLI flag, but the prompt scan can also be off via `scan_prompt = false` in project config — and the README pointed auditors at that flag field as *the only way to find* unscanned runs. So every config-route run produced a row saying `allow_prompt_secrets: false`: the audit field pointing away from exactly the runs it exists to find, for text that is plaintext on disk locally and undeletable at Google. The ledger now records `prompt_scanned`, the effective per-run state whatever the route; the flag field stays, because a deliberate one-off bypass and a standing config opt-out are different facts about a run. Rows older than the field carry no `prompt_scanned` key — the README now warns they predate the fix and cannot be read as scanned. Pinned by a test that sets the config off, sends secret-shaped text, and asserts the row says unscanned.

### fixed
- **`path-privacy` 0.14.0 → 0.15.0, `skill-maintain` 0.22.0 → 0.23.0 — a marker shown as an example inside a fenced code block was still a working opt-out, and 1.2.4 argued that was unavoidable.** It is not. The argument was that a marker and a quotation of one are the same string, so no pattern separates them — true, and irrelevant, because fence state is not a property of a line. It is a property of what came before it. That takes a scan rather than a better regex, and the scan is four lines of awk. Shipping an argument for why a hole must stay open, in the release notes of the change that narrowed it, is the failure worth naming here: the reasoning was sound about patterns and simply never asked whether a pattern was the right tool.

  Both engines now drop fenced blocks before looking, so a doc can demonstrate the marker the way a doc should. Strictly fail-closed: skipping lines can only ever remove matches, so this turns exempt files into audited ones and never the reverse — a stray fence above a genuine marker costs a visible false positive rather than a silent exemption.

  **Discovered while verifying it: the fence pass made the scanner noisy on binary files.** Under a UTF-8 locale, macOS awk writes `towc: multibyte conversion failure` to stderr for every undecodable record, the scanner runs over whole trees, and the PreToolUse hook captures its stderr into the block message — so every binary in the repo would have become noise inside an unrelated diagnostic. `LC_ALL=C` on the awk, matching the greps, which makes it treat input as bytes and stay silent. Caught by running the census over the real tree rather than over fixtures.

  **`check_marker_denylist` now covers plugin READMEs**, not just changelogs and skill docs, and matches path-privacy's sanctioned exception on the whole path rather than the parent directory name. A README describing the escape hatch is exactly as likely as a skill doc doing it.

  Pinned by six new tests across both engines and mutation-checked in each: neutering the fence pass turns the four fenced forms red plus the cross-engine agreement test, and a marker following a *closed* fence must still exempt — the obvious way to get fence tracking wrong. The cross-engine test now compares whole file bodies rather than single lines, since neither fence state nor the 30-line window is a property of one line.

## 1.2.4

### fixed
- **`path-privacy` 0.13.0 → 0.14.0, `skill-maintain` 0.21.0 → 0.22.0 — 1.2.3 did not close the hole it claimed to close, and opened three new ones closing it.** Two independent review passes found it. `## path-privacy: skip-file` — an ordinary markdown H2 — was a working file-level opt-out, as were a `*` bullet and a four-space-indented code sample. Proven the way it deserved to be proven: a fresh repo, the real installed pre-commit hook, and a `git commit` carrying a home path that **landed**. The introducer set admitted `#+` and `*`, which are markdown *display* forms, not comments. So the release that narrowed the rule to stop documents from exempting themselves shipped a rule that let any document with a section heading do exactly that — and the fenced example 1.2.3 added to `SKILL.md`, recommending that very form, was itself a live marker.

  The pattern is now `^ {0,3}(<!--|#|//|--|;)?[[:blank:]]*`: a single `#`, no `*`, and at most three spaces of indent, which is markdown's own boundary for "not a code block". Each restriction is documented against the bypass that reached it, because the next person to widen this will have a good-sounding reason too.

  **Three regressions came from the shared library that 1.2.3 introduced, all from one mistake: guarding with `[ -r ]`, which tests readability, not definition.** A truncated or syntactically broken library passes it, the fallback never installs, and the undefined function exits 127 — which every call site reads as "not exempt". Verified: with the library emptied, `scrub-paths.sh` rewrote a marker-protected file, which is the precise outcome its abort was written to prevent. Worse, the SessionStart hook set `PP_SKIP_MARKER_RE='$^'` as its "matches nothing" fallback; under BSD grep that matches every *empty* line and silently stripped the blank lines out of the injected directive, and when the library was broken rather than absent the variable stayed unset, `grep -vE ""` matched everything, and **the privacy directive stopped loading in every repo, invisibly**. All four consumers now source with stderr discarded and then verify what got defined; the hook's degraded path is a passthrough *function*, never a pattern, because a function cannot fail that way on any platform.

  **And it leaked a path, from inside the tool whose only job is not leaking paths.** Sourcing a broken library makes bash print its own diagnostic quoting `$0` — an absolute path under the plugin root, carrying the username. The PreToolUse hook captures the scanner with `2>&1` and re-emits it, so that landed in the block message and the transcript. Nothing was sourced before 1.2.3, so this was new. A test now asserts the diagnostics contain no absolute path.

  **The real fix is the one that stops trying to out-regex prose.** `check_marker_denylist` fails the suite if `CHANGELOG.md` or any skill doc outside path-privacy carries a file-level opt-out. A fenced code block is not indented, so a document quoting the marker inside one is still a working marker, and no pattern can distinguish them — they are the same string. The rule narrows the hole; asserting the outcome on the file classes this keeps happening to is what closes it. Controlled by planting the exact recurrence at the top of this changelog and watching it go red.

  **Comment-less formats get no file-level opt-out, deliberately.** JSON and CSV cannot put the marker at the head of a line, and admitting a JSON key prefix would reopen the rule to every YAML value and config string — the same widening-for-convenience that caused this. They use the per-line marker or belong in `.gitignore`. The block message now names the syntax actually legal in the file it just blocked instead of suggesting HTML comments in Python, and says plainly when there is none.

  **Correcting 1.2.3's own entry: it claimed "thirteen shell probes" pinned the behaviour. There were none.** The probes were run by hand in one session and never committed, so every test of a rule consumed by three shell programs went through the Python copy — meaning the pattern could be edited and all three shell consumers broken with the suite still green. That claim is corrected in place rather than left standing, because it was false when written, not superseded. `test_skip_marker_shell.py` is now those probes: 25 tests driving the real scripts as subprocesses, including a cross-engine test asserting the shell ERE and the Python duplicate accept the same corpus — the only thing that makes a deliberate copy safe. Mutation-checked against the old pattern: five go red, four of them the exact bypasses.

  Also corrected: `test_marker_is_honoured_in_html_comment_and_indented_forms`, added in 1.2.3, asserted the four-space-indent bug *as intended behaviour*; `SKILL.md` contradicted that same test on indentation, claimed "any comment syntax works" (false for JSON), and said "three consumers" when there are four; the README stopped naming the token at all, documenting an escape hatch a reader could not use. `--help` on both scripts emitted a marker as its first line, so redirecting help into a file silently exempted it — and `usage` runs on any unknown argument, so that needed no deliberate act. Both now start below the marker and end at the first non-comment line rather than a hardcoded range, which a header edit in 1.2.3 had already shifted. The shell greps pin `LC_ALL=C` and the Python audit uses `split("\n")` rather than `splitlines()`, closing two ways the two engines disagreed about which lines were in the 30-line window.

## 1.2.3

### fixed
- **`path-privacy` 0.12.0 → 0.13.0, `skill-maintain` 0.20.0 → 0.21.0 — a file could switch the leak gate off for itself just by describing how to switch it off.** The file-level opt-out matched its token *anywhere* on a line, so any document that discussed the escape hatch exempted itself from the entire audit. 0.48.0 narrowed this once, from "anywhere in the file" to "anywhere in the first 30 lines", and 1.2.2 walked straight back into it: an entry documenting the marker put the token in the window and silently un-gated the changelog. Two encounters with the same defect, the second while writing about the first, is the argument for fixing the class instead of the instance.

  The rule is now anchored. A marker counts when it is a line's **leading content** — optional indentation, an optional comment introducer, then the token — and anything after it on that line is free text, so `marker -- why this file is exempt` keeps working and is the form to prefer. Prose cannot reach it, because a sentence always has words before the token. Head-scoping stays; anchoring is what makes it hold for the files most likely to discuss the marker, which are skill docs and changelogs, and which grow from the top straight into the window.

  **One definition, in `scripts/_skip_marker.sh`, for the same reason `_version_compare.sh` exists.** The check was written out separately at all four call sites — scanner, scrub, PreToolUse hook, and the whole-tree audit — which is how a defect in it survived being "fixed" once already: repairing one copy looks exactly like repairing the rule. The three shell consumers now source it. The Python audit keeps a deliberate copy, because it has to run in repos where path-privacy is not installed at all; that copy has a consumer beyond the check that confirms it is a copy, which is the test this repo applies to every duplicated field.

  **Degradation is per-consumer, chosen by what the caller does with the answer.** A missing library makes the scanner and the write blocker fail CLOSED — nothing is exempt, everything is scanned — because a false positive is loud and a silent exemption is the whole defect. `scrub-paths.sh` instead aborts: it rewrites files, so failing closed there means scrubbing the pattern catalogs the marker protects. That abort was first placed next to its call site, below the "no config, nothing to do" early exit, which made it unreachable in the common case; it now sits with the other hard dependency check at the top.

  **Behaviour change for anyone with an existing marker.** A marker buried mid-sentence stops exempting its file, so a repo relying on the loose match will start seeing findings it did not see before. That is the fail-closed direction and it is visible, but it is a change. The only such file here was the config template, whose exemption turned out never to have been load-bearing — it contains nothing but the `USERNAME` placeholder, which both checks already treat as clean — so the marker was removed rather than the rule bent to fit it.

  Pinned by three new Python tests. **Correction (1.2.4):** this sentence originally also claimed "thirteen shell probes". Those probes were run by hand and never committed, so no shell coverage existed; the rule's three shell consumers were untested. Corrected here rather than in place because the claim was false when written. The real shell suite arrived in 1.2.4.

## 1.2.2

### fixed
- **`path-privacy` 0.11.1 → 0.12.0 — the plugin's own file-level opt-out marker was riding into every session's context.** It was the first line of every block the SessionStart hook injected, in every git repo, since 0.1.0. The source file has to carry that marker: the directive defines a leak by naming the home-directory variable in prose, so without it the scanner flags the directive and the plugin blocks its own rule from loading — verified by stripping the marker and rescanning, which exits 1. The emission needs nothing of the kind. `tail -n +2` stripped the `# trigger:` line above the marker and nothing else, so the marker rode along as a stray comment nobody wrote on purpose.

  Now filtered on the way out, anchored so only a line consisting of *nothing but* the marker is dropped. A future directive that documents the escape hatch in prose keeps its sentence — the naive `grep -vF` would have deleted it silently, which is the kind of removal that gets noticed a release later.

  **The marker was doing a second job by accident, and that job is now stated outright.** `hook_additional_context` records carry only the event name, so an injected block cannot be traced to the plugin that produced it — the reason SessionStart emissions grew an attribution first line in 0.89.0. path-privacy never got an explicit one, because the stray marker already served as a de facto signature; 0.89.0 recorded that coincidence and kept it. So removing the stray comment would have silently cost attribution, which is why the two changes ship together rather than as a one-line cleanup. It now emits `[plugin:path-privacy]`, the same bracket form `dev-conventions` uses, so both are greppable with one pattern.

  Four probes pin it: the marker dropped in both comment syntaxes including an indented one, a prose mention preserved, a directive that filters to empty producing no attribution-only block, and a non-git cwd still silent.

  **Writing this entry re-triggered a defect 0.48.0 thought it had closed.** The first draft quoted the marker token literally, which put it inside the changelog's first 30 lines and silently exempted the entire file from the leak gate. 0.48.0 narrowed exactly this — a file merely *quoting* the token anywhere was exempt — by limiting the search to the first 30 lines. That window is not a fix for the one file guaranteed to keep discussing the marker and to grow from the top; it only moves the trigger to "documented recently". Entry rewritten descriptively so the gate stays live. Left standing as a known hazard rather than patched under this bump: **the exemption matches the token anywhere on a line**, where the same anchoring now used by the SessionStart filter — the line must be *nothing but* the marker — would make prose incapable of disabling the audit. Both the shell scanner and the Python whole-tree check would need it, so it is its own change. The failure mode is the bad one: an exemption that works looks exactly like a file with nothing to hide.

## 1.2.1

### fixed
- **`dangling-refs` 0.1.0 → 0.1.1 — the sweep the skill is built around only searched the current directory.** A code review caught it within an hour of shipping. `git ls-files` lists files under the cwd, not the repo, and **the single most likely place to run a pre-deletion sweep is inside the unit being deleted** — where it returns a tidy handful of self-references and reports clean. Measured here: sweeping for `gemini-bridge` from inside `apps/gemini-bridge/` found 12 hits; from the root, 26. The 14 it missed are the non-local references the skill exists to find. A skill whose one job is catching what edit-time tools cannot see, shipping with a command that cannot see them either.

  All four snippets moved to `git grep -- :/`, which fixes three more defects in the same change. `git ls-files | xargs` splits on whitespace, so a tracked path containing a space was silently skipped — and since every snippet ended in `2>/dev/null`, the resulting errors were swallowed and the sweep still looked clean. On GNU systems `xargs` with no matches runs the utility with no file operands, so the import check blocked reading stdin instead of reporting clean; it would have passed on macOS and hung on Linux. And the name was interpolated as a regex, so a unit called `foo.js` matched loosely while one starting with `-` was parsed as an option — now `-F`.

  Two coverage gaps fixed alongside. The import check hand-listed `*.py *.ts *.js`, missing `.tsx`, `.mjs`, `.jsx`, `.pyi`, `.cjs` — 21 tracked files in this repo the check never opened. The link check matched only inline `](…)` links in `*.md`, missing reference-style definitions, `href=`, and any non-markdown file — which is where a registry entry naming a removed path actually lives.

  Also corrected a contradiction the review spotted: the skill said a removal is done when "the sweep is quiet", while its own cascade requires a changelog entry naming the retired unit. The sweep will never go quiet, and should not. It now says every remaining hit must fall in the historical or third-party bucket.

- **Two plugins were missing from the README install block.** `dangling-refs` and — pre-existing — `gemini-bridge`. Someone copy-pasting the documented install list never got either. Both added, along with their slash commands. This is exactly the "indexes, tables of contents, any file whose job is to enumerate what exists" bucket the new skill declares must-change, missed on the commit that introduced the skill.

## 1.2.0

### added
- **New plugin: `dangling-refs` 0.1.0.** One skill, `retire`: remove a unit — plugin, package, module, directory, dependency — without leaving references behind.

  It exists because of a failure this repo hit hours earlier and could not have caught with any of its existing machinery. Retiring `agent-state` left five references in shipped content, and they were found by a manual sweep run *after* the deletion was committed. **Deletion-induced breakage is non-local**: the files that broke were never edited, so nothing fired. A language server sees open files, a `PostToolUse` hook sees edited files, a pre-commit check sees the diff — every one of them is scoped to what changed, and what changed is not where the damage is.

  Shipped as a procedure rather than a linter, deliberately. Of those five references exactly one was mechanically detectable as a path that no longer resolved; the other four were sentences naming a concept, which no path checker catches. A link check had passed cleanly the entire time, which is the useful lesson: *"no broken links" is a strictly weaker property than "nothing names a thing that no longer exists."*

  The judgment the skill encodes is the sorting, and two of its four buckets are **do not touch**. Changelogs and design records describe what was true when written, and rewriting them destroys the record of what was tried — the reason `model_routing_flywheel.md` kept its dead commands behind a status header this morning instead of being cleaned up. Instructions about what may still sit in *someone else's* repo stay correct after your removal and strand their audience if deleted. Getting those two wrong costs more than missing a stale reference.

  It also names the parts of a removal that are easy to forget: the deprecation mapping so installed copies get cleaned up rather than silently orphaned, the distribution boundary as a separate and higher bar because shipped content reaches other people, and the fact that removing anything published is a major version bump.

  Complementary to a whole-tree consistency check rather than a replacement — a check can answer "does this path resolve", never "should this sentence still exist". The check half stays unbuilt until it earns it.

## 1.1.1

### fixed
- **Shipped content no longer names a package that was deleted.** Retiring `agent-state` left five references behind in plugins that users install, and the sweep that found them ran only after the retirement had already been committed — a reminder that "no broken markdown links" is a weaker check than "nothing points at a thing that no longer exists".

  `path-privacy` 0.11.0 → 0.11.1: two teaching examples used "the agent-state DB" and a path under the user's Claude config directory to illustrate naming an external dependency generically. The lesson was never about agent-state, so the examples now use a neutral name and nobody goes looking for a package that isn't there.

  `skill-maintainer` 0.17.0 → 0.17.1: the finish-session workflow listed `apps/agent-state-mcp/` among example directories a session might touch. Now `apps/gemini-bridge/`.

  `model-routing` 0.5.0 → 0.5.1: its README and SKILL.md explain why the delegation feedback layer was removed, and the argument rested partly on "nothing has written to that database since 2026-03-12". Still true, and now stronger — both note the package was retired outright. The instructions to delete the section from an installed rule stay exactly as they were: those describe what may still be sitting in someone else's repo, which is unaffected by what we ship.

### changed
- **The repo version is 1.0.0.** Removing two published plugins is a breaking change for anyone who installed them, and the `renames` map exists precisely because that breakage has to be handled rather than absorbed. Numbering it 0.100.0 would have understated it. The two entries below are renumbered accordingly; nothing about their content changed.

## 1.1.0

### added
- **`skill-maintain test` now blocks tracked content from citing gitignored files.** The failure it catches had two live instances and one of them was shipping: `CLAUDE.md` and `gemini_bridge_design.md` both instructed every reader to run `internal/scratch/gemini_probe.py`, and `gemini-bridge`'s SKILL.md carried *measured* resolution guidance produced by `internal/scratch/diff_control.py`. Neither file exists for anyone who clones the repo. A measurement whose instrument is untracked is an assertion wearing a measurement's clothes.

  The rule is "resolves to an existing **file** under `internal/`", not "mentions `internal/`", and that distinction is what makes it mechanical rather than a judgment call. `internal/log/log_YYYY-MM-DD.md` is a naming convention and passes; `internal/log/` and `internal/postmortems/` are directories — places to write to, which is the entire point of having the directory — and pass; `internal/api/`, `internal/service/` in the MCP analysis describe Go's project layout and pass. Only a path that really is a file sitting there right now, being cited as a source, fails. `CHANGELOG.md` is exempt because it is a record of the past.

- **`gemini-bridge` 0.5.2 → 0.5.3 — both instruments promoted out of scratch.** `scripts/probe.py` is the live API probe, tracked because every static source about this API was wrong about something material and only a live call settles a new parameter. `scripts/diff_control.py` is the control harness SKILL.md already tells you to run against a null pair before trusting a new comparison recipe. Both had `Throwaway.` in their docstrings; both now say what they are and why they are tracked. Bodies are unchanged.

- **`skill-maintainer` CLI 0.19.0 → 0.20.0 — `scripts/trigger_eval.py` and `scripts/make_evals.py`.** The trigger-rate harness, adapted from `skill-creator`'s `run_eval.py` with two deliberate fixes: a "real" mode so an installed twin cannot steal a trigger and be miscounted as a miss, and a full-turn scan, because stock `run_eval.py` returns False at the first tool call that is not Skill/Read — scoring a natural Read → Skill → Edit sequence as a miss. Improvements to the sanctioned measurement tool should not live in gitignored scratch, particularly in the same session that retired a package for pretending to measure skills.

## 1.0.0

### removed
- **`agent-state` and `agent-state-mcp` are retired.** Both packages deleted, `agent-state-mcp` added to the marketplace `renames` map so installed copies are cleaned up. This closes a question `docs/internals/agent_state_population.md` opened on 2026-07-26 and had been carrying since: populate the schema, or retire the package, because "empty but documented" is the one state that should not persist.

  Its own recommendation was to populate `dim_skill_version` first and retire only if that had not happened in a reasonable window. What closed the window was not the calendar but three findings, each killing one candidate population. **`fact_watermark` duplicates files** — `.skill-maintainer/state/upstream_hashes.json` holds current values, `changes.jsonl` holds the history of what changed and when, and between them they carry what `WatermarkRecord` normalizes. **`dim_skill_version` duplicates git**, which already stores every SKILL.md version, with token count and validity computed from the files on demand. **`fact_delegation`** was already ruled out by the flywheel analysis, and the `changes.jsonl` importer feeding `fact_run` was deleted earlier the same day for being lossy in the wrong direction.

  That left run lineage, which has no producer. And the question the whole thing existed to answer — *is this skill any good* — needs a different instrument. `v_flywheel` could only ever have offered observational correlation from production: which runs consumed which skill version, and whether those runs happened to succeed. A skill version shipped in the same week as three other changes would take credit for all of them.

  The Claude Code docs are explicit that this is the wrong shape: *"Seeing a skill trigger tells you Claude found it, not that it did what you intended."* They point at `skill-creator`, which runs the same prompt with and without the skill **in the same turn**, uses the previous version as the baseline when iterating, and reports mean, stddev, and the delta between configurations. A controlled A/B beats production correlation for this question, and one already exists — this repo has even adapted its eval runner, with two fixes for miscounted triggers.

  `VISION.md` cited agent-state as an exemplar of "nothing else reads it, so a database is the store" — twice today, narrowing it once before removing it. The cautionary note stays in its place, because it is worth more than the example was: **run the test on your own units before citing them as exemplars.** A principle illustrated by something that fails it ships with a counterexample built in.

  Docs that discussed it are updated rather than rewritten. `model_routing_flywheel.md` and `agent_state_population.md` keep their `agent-state` commands and table names with a status header, because the reasoning is the point and erasing it would destroy the record of what was tried.

## 0.99.5

### fixed
- **`agent-state-mcp` 0.2.3 → 0.2.4 — angle brackets removed from the skill description.** It named the database as `(<HOME>/.claude/agent_state.duckdb)`. That form is correct everywhere in this repo *except* a description: `skill-creator`'s validator rejects angle brackets in frontmatter outright, while `skill-maintain validate` only warns, so this would have failed hard the first time the skill met the stricter tool. It was the only such description in the repo.

  The location is now named in prose, and the exact path stays in the body where the `<HOME>/` convention is legal. That is the better place for it anyway: a description loads on every session, a body loads only when the skill activates, so the path moved from L1 to L2 at no cost to anyone trying to find the file.

## 0.99.4

### removed
- **`agent-state` 0.3.1 → 0.4.0 — the `changes.jsonl` importer is gone**, along with `migration.py`, its tests, and the `agent-state migrate` command. `agent-state-mcp` 0.2.2 → 0.2.3 for the two docs that advertised it.

  It had never been run, and the decisive part is not that it was unused but that it was **lossy in the wrong direction.** Three structurally different event types collapsed into one `fact_run` shape with the distinguishing payload buried in an opaque `metadata` blob, so a `quality_report` lost `skills`, `valid`, `over_budget` and `stale` as queryable columns. The imported copy answered *fewer* questions than `read_json` over the original JSONL. A second copy that is strictly worse than the original is the clearest possible case for not keeping it — the same test [VISION.md](VISION.md) now states as "substrate follows from consumers", and the one CLAUDE.md invariant 1b applies to duplicated versions.

  `docs/internals/agent_state_population.md` already argued this from the other direction: "either adopt the schema or delete the importer; maintaining both formats is the actual cost." That resolves item 3 of that document. The wider populate-or-retire question for `agent-state` remains open and is unaffected — watermark staging and run lineage are instrumented facts with no file behind them, and stay correctly in a database.

## 0.99.3

### added
- **`gemini-bridge` 0.5.1 → 0.5.2 — the ledger now keeps the interaction id, so a run directory can be deleted without losing the only handle to what is stored.** Cleaning up `.gemini-runs/` looked like a housekeeping question and was not. `stored` reads `interaction.id` out of each run directory; the ledger did not record it; the API has no `list` to rebuild the set and `delete` returns 501. So deleting old run directories would have silently blinded the only disclosure surface a user has, permanently, with no error and no way to recover the handles.

  It matters less than it sounds today, because every shipped recipe is `stateful: false` and stores nothing — but `client.py` deliberately captures the id *whenever the server returns one*, precisely in case `store` was misreported. Naive pruning would have reintroduced exactly the risk that code was written to guard.

  Recorded as present-and-null rather than omitted when nothing was stored, for the same reason as the scan-bypass flag: a query for stored interactions must not have to distinguish "no id" from "this row predates the field". The id is not a secret — an opaque pointer to data already sent, already sitting in plaintext in the run directory.

  This is the piece that had to land before pruning could be built at all, and the one piece that cannot be backfilled: runs made without it never get their handles into the ledger.

### fixed
- **The repo path-privacy audit had a standing false positive.** It flagged two fixtures reading `/Users/somebody/...` and `/home/somebody/...` as leaked home paths. They are deliberately shaped like the thing the scanner exists to notice, so they cannot be rewritten as `<user>` placeholders without testing something else, and `somebody` is not a real account — the audit's allowlist covers substitution syntax and a fixed set of system accounts, and simply does not know the word. Annotated with the sanctioned per-line `path-privacy: ignore` rather than by widening the allowlist, which would have been making a check pass by editing what it measures.

  206 tests, up from 204. The repo board is now 244 green with one deliberate red — `content-triage`, which has real unfixed drift.

## 0.99.2

### changed
- **`readwise-reader` 1.1.0 → 1.1.1 — two skills were on a freshness window their content cannot justify.** `library-search` and `knowledge-retrieval` moved from `review_interval_days: "90"` to `"365"`. `content-triage` deliberately stays at 90.

  The 90-day tier was assigned to all three in bulk, by a commit whose own stated rule is "30d for content derived from the Claude Code docs, 90d for skills tracking a third-party SDK or API, 365d for methodology and for our own code." Only one of the three meets the middle condition. `library-search` depends on this repo's `tools/search.py` and `tools/tags.py` — all four tool signatures it cites were checked and match — and `knowledge-retrieval` cites no tool, no API surface, and no URL at all. It was authored methodology. A window on it could never have detected anything; it was a recurring alarm with no signal behind it. Both were tiered at 90 because they live in a plugin whose *name* contains a third-party product.

  **`last_verified` was not touched, deliberately.** Under a corrected window neither is stale, and moving the date would assert a review that did not happen. That matters more than usual here: the existing 2026-04-02 date is itself a mechanical bump — the commit that set it changed only the date across 21 skills, with no body change — so the true last-review date for all three is unknown. Re-tiering is the sanctioned response to a wrong window; bumping the date is the one edit that makes the signal lie, which the quality skill says in as many words.

- **`content-triage` needs a real review, and it is not just the skill.** Its lifecycle diagram declares the Readwise location set as `new → later → archive`, but the live API also carries `shortlist`, and our own code is behind in the same direction: `tools/triage.py` accepts only `later`/`archive`/`delete` while `api/models.py`'s enum comment already names `feed`. Skill and implementation drifted together, away from the API, so fixing the skill alone would create a new inconsistency. Left for a human against the live API rather than guessed at here.

- **`doc-claim-auditor` now writes long audits to a file and returns a path.** A subagent's final text lands in the caller's context and stays for the rest of their session whether or not it gets acted on, so a full audit of a long doc can cost more attention than the drift it found. Past roughly 400 words it writes a file and returns the path plus a map — FALSE count, worst offenders, section headings — because a path with no map is worse than no file. Short audits still come back inline; a round trip through disk for three findings is overhead, not discipline.

  This is the first application of the return-a-path invariant from [docs/internals/foreign_capability_bridge.md](docs/internals/foreign_capability_bridge.md) to something other than a foreign capability. It fits exactly one of this repo's four local agents — the rest are narrow executors whose reports are short by design — which places the real cost in the built-in exploratory agent types, where there is no definition to edit.

## 0.99.1

### fixed
- **`gemini-bridge` 0.5.0 → 0.5.1 — the interaction id was read at write time, not at check time.** The guard tested `result.interaction_id`, then a closure read that attribute again when the deferred write actually ran, so the value written was not provably the value that passed the check. Harmless in practice — nothing mutates the result between the two — but this is the one field a re-run cannot regenerate and the only handle on a stored interaction, which makes "provably the same value" worth having. Bound to a local before the guard.

  Version bumped for a change with no user-visible behaviour because the alternative is worse: leaving it unbumped means the copy in an installed marketplace cache and the copy in this repo both claim to be 0.5.0 while differing. Two artifacts with one version is the drift the cascade exists to prevent.

## 0.99.0

### added
- **`gemini-bridge` 0.4.0 → 0.5.0 — a `general` recipe, because until now the tool could not be asked an arbitrary question.** `-r/--recipe` is required and exactly one recipe shipped, so every call was a perceptual diff or nothing. That is backwards for a bridge whose realistic use is mostly ad hoc: the one analysis anyone had written down was the specialised one, and the general case had no path at all.

  The fix is a recipe, not an optional flag. Making `--recipe` optional would have meant a call whose analytical stance came from however the question happened to be phrased that session, which is the failure the recipe format exists to prevent. A `general` recipe keeps the stance versioned and diffable while leaving the question free, and it gives ad-hoc calls a name in the ledger instead of a null — so the corpus that a future recipe would be promoted *from* starts accumulating under a label rather than evaporating.

  It ships without a schema, deliberately. A schema would force arbitrary questions into one verdict shape, and not knowing the question in advance is the entire point of the bucket.

- **The prompt-scan bypass is now recorded.** `--allow-prompt-secrets` skips the outgoing-text scan, so the run directory keeps text nobody checked, in plaintext, while the interaction at Google cannot be deleted. Those are the runs most worth finding later and there was no way to find them: the ledger did not record the flag, so locating them meant grepping every `prompt.md` — reading the very content the flag was used to send. Recorded on the failure path too, since a failed call still transmitted the prompt.

  The field is written as `false` on ordinary calls rather than omitted. A filter for risky runs must not depend on a key that exists only on the risky ones.

### fixed
- **Run trees relied on a single file to stay out of git.** The tool writes a `*` gitignore inside `.gemini-runs/` at creation, and a project's own `.gitignore` knows nothing about the tool. Delete that one file and prompts and responses are stageable by `git add .` until the next call rewrites it, with nothing announcing the window. `doctor` now reports whether the marker is in place, this repo's root `.gitignore` covers the tree as a second layer, and the README says to do the same in any project using it. The tool still does not edit anyone's `.gitignore` for it — a marker that reappears silently is the failure mode being fixed, not the fix.

- **Shipped recipes are now validated as a set rather than by name.** The suite tested one recipe by path, so the recipe most likely to be malformed — a newly added one — was the one nothing covered. It now parametrises over the directory and asserts the invariants that hold for every shipped recipe: no recipe opts into storage without argument, and every one resolves a valid thinking level.

  204 tests, up from 198.

## 0.98.0

### fixed
- **`path-privacy` 0.10.0 → 0.11.0 — one staged binary silently disabled the leak scan for every file after it.** A red-team pass found and reproduced this; it is the most serious defect in the repo's privacy enforcement to date, and it was reachable without doing anything unusual.

  When ripgrep is handed a file directly and that file is binary *and* matches, it does not emit `file:line:match` — it emits a diagnostic: `path: binary file matches (found "\0" byte around offset 0)`. The scanner fed the middle field of that line into an arithmetic expansion to index the source array. Bash treats the bare word `matches` inside `$(( ))` as a variable reference, `set -u` makes that fatal, and bash 3.2 — which is what `env bash` resolves to on a stock Mac — **terminated the script while still exiting 0**. The pre-commit hook read that as "scan passed".

  The consequence was not "binaries are not scanned", which is documented and expected. It was that one binary aborted the scan for **every file after it in the same commit**, so unrelated plain-text leaks went through unreported, with the only symptom a stderr line that reads like a random bash bug. Reproduced end to end: a plain-text leak alone is correctly blocked; the same leak with a compiled binary staged alongside it commits successfully. Staging a build artifact with an embedded absolute path is entirely ordinary.

  Scope was precisely the `--staged` mode — the pre-commit hook, the authoritative gate — and single-file audits. The whole-tree audit was immune, because directory mode filters binaries out before this code runs, which is why the audit kept reporting clean while the commit path stayed open.

  Anything that is not a plain line number is now handled explicitly instead of reaching arithmetic, and files that cannot be line-scanned are reported by name rather than dropped silently. `references/patterns.md`'s claim that ripgrep skips binaries was true of the audit path and false of the gate that matters.

### changed
- **`gemini-bridge` 0.3.0 → 0.4.0 — closes what two red-team passes found.** The most serious: a recipe's `system_instruction` was sent verbatim on every call and scanned by nothing. Recipes are files, `--recipe` accepts an arbitrary path, and no flag could even opt that path into scanning. Both halves of the outgoing text are checked now.

  The secret patterns missed the modern form of the very keys they were named for. `sk-[A-Za-z0-9]{20,}` excludes the hyphen, so OpenAI's current `sk-proj-`, `sk-svcacct-` and `sk-admin-` keys produced no finding at all; likewise GitHub's recommended `github_pat_` format, Stripe's underscore-separated keys, npm and SendGrid tokens, and connection strings carrying an inline password — the shape people paste most often while debugging.

  Path matching now normalises Unicode. macOS stores accented filenames decomposed while a config file is composed; the two are the same text to a person and different bytes to `fnmatch`, so an accented directory name silently failed to match with no deliberate evasion involved.

  Redaction now scales with input length. The fixed head-and-tail formula looked safe on long matches and revealed 10 of 15 characters on a short one, leaving five to brute force.

  Also: run directories are created owner-only, because the prompt-scan override writes the secret it was overridden for to local disk in plaintext with no retention window, and default umask left that world-readable; `--dry-run` withholds a prompt containing secret-shaped content rather than printing it, since stdout persists in the calling agent's context; and a key command the kernel refuses to exec raises a clean error instead of a raw traceback.

  Two limitations are now documented rather than left to inference: neither guard reads the *contents* of an attachment, and a hardlink under an innocuous name defeats path matching entirely. These are guards against mistakes, not against determined evasion.

  198 tests, up from 183.

## 0.97.0

### changed
- **`gemini-bridge` 0.2.0 → 0.3.0 — the privacy guard now covers what is actually transmitted, and it is on by default.** Asked whether the security posture was good, the honest answer was "mostly, with one hole", and the hole was structural rather than a bug: `privacy.is_sensitive` inspected which *files* were attached and said nothing about the *prompt* — which is composed by Claude, after Claude has spent a session reading the user's files. A secret pasted into a question went out unchecked, while a configured `sensitive_paths` implied the tool was vetting what it sent. A misleading guard is worse than an absent one.

  Outgoing text is now scanned for secret-shaped content before the call, using patterns adapted from this repo's own `scan-for-secrets` so the two agree on what a secret looks like. High-confidence shapes block; lower-confidence ones (an email address, an absolute home path) warn. Findings are redacted before display — a message naming what it found must not reproduce it, or the secret simply relocates into a terminal and a session transcript.

  The path guard also **defaulted to empty**, which meant that out of the box it blocked nothing and the real protection was "the user chose which files to name". It now ships a deliberately narrow default set covering shapes that are secrets or nothing, opt-out rather than opt-in.

  **The guard also ran too late to work.** Ordered after media inspection, a file it exists to block — `id_rsa`, something `.pem` — was rejected first for having an unrecognised mime type, so most default patterns could never fire. Found by a test written for something else. It now runs on the raw arguments, because whether a file should be sent has nothing to do with whether its type is supported.

  `doctor` reports both guards and states plainly that sent interactions cannot be deleted through the API.

### fixed
- **Correction to an earlier claim: bulk deletion does exist.** `interactions.delete` returning 501 stands, and there is still no programmatic or per-interaction purge. But AI Studio's log dialog has a project-wide **Delete project logs** button, so the accurate statement is "cannot be deleted *via the API*". Different mitigation, different ergonomics — manual and all-or-nothing, but immediate rather than waiting out the retention window. That dialog also carries a per-API storage toggle whose default the per-request `store` value overrides.

### added
- **Generative tests for the path guard**, motivated by a bad track record rather than a hunch: the function was rewritten three times in one session and each fix revealed the previous one broken in a way that looked correct. Hand-picked cases kept passing while it leaked, because they were chosen by whoever held the wrong mental model. The new tests generate paths, derive the patterns a person would expect to block each one, and assert the guard never under-blocks — 360 assertions across forms that all silently failed at some point.
- **Fault injection for the post-call path**, which existed to handle failures that had never happened. Confirms that a write failure after a billed call still records the interaction id first, still writes the ledger, and surfaces the answer rather than losing it.

  183 tests, up from 83.

## 0.96.0

### added
- **`gemini-bridge` 0.2.0 — a new plugin for handing a perceptual task to a Gemini model when Claude cannot do it directly.** The motivating case: comparing two renders of the same 3D scene, where Claude could measure the images with numpy but could not see the difference, and answered a visual question with pixel statistics. That substitution is the trigger phrase the skill actually keys on, not "there is an image here".

  Shape is a thin CLI plus recipes as data. A recipe is YAML frontmatter for parameters and a markdown body that becomes the `system_instruction`, so a new kind of analysis is a new file rather than new code. Keeping the analytical stance in a versioned file is what makes results reproducible: composing the prompt fresh each session makes the answer depend on how the question happened to be phrased that day.

  Every call writes a run directory — prompt, media manifest, response, structured verdict, token usage — and stdout stays deliberately small, because tool output persists in a session's context for the rest of that session and a full scene description printed there is thousands of tokens that cannot be reclaimed.

  **The API surface was established by live probing, not documentation, and that turned out to be necessary rather than fastidious.** Every static source was wrong about something material: the OpenAPI spec omits video input entirely, the generated SDK omits a parameter the API accepts and ships a `delete` the server does not implement, and the docs are wrong about both while giving three mutually contradictory video token rates. A drift check validating the CLI's flags against the OpenAPI spec was designed and then abandoned — it would have failed video input as invalid and sent us chasing a bug that does not exist.

  What the probe established, all of it load-bearing: `temperature` is accepted and **silently ignored** (at 0.0 the same prompt returns varying answers, and 0.0 versus 2.0 produce identical answer sets), so recipes reject it and `seed` is the determinism knob. Thinking runs by **default** and bills at the output rate — 195 thought tokens for "17 * 23" at `high` against 0 at `minimal` — so an unset `thinking_level` is the expensive path, not the cheap one. `interactions.delete` returns **HTTP 501**, so stored interactions cannot be purged at all and `stateful: false` is the only privacy lever that exists.

  Resolution guidance is measured rather than assumed. A control harness over four real image pairs, two runs each, at both resolutions: `low` is sufficient for storyboards and contact sheets — it found *more* differences than `high` on two of them — and `high` earns its cost only on full-frame renders, where it found five or six differences to `low`'s one. The same harness measured the failure mode that actually matters for the use case, comparing images against themselves, with zero false positives across every case. `confidence` returned `high` in all 32 runs, so nothing routes on it and the escalation mechanism designed around it was dropped rather than shipped unexercised.

  Credentials are secret-manager agnostic by construction: the tool runs any command that prints a key, with a plain environment variable as the zero-setup fallback, so nobody is required to install anything. The first version hard-coded one vendor and had to be rewritten.

### fixed
- **`gemini-bridge` 0.1.0 → 0.2.0 — findings from a code review and a privacy audit, run as independent passes over the initial commit.** The serious ones clustered into two themes.

  Losing something irreplaceable after a call that had already been paid for. `call` raised on a truncated or unparseable response, discarding the interaction id into a local variable — and since delete returns 501, that leaves a permanent, billed, untracked interaction with no record anywhere. Separately, any write failure after a successful call lost the answer, the usage record and the id together, with nothing on disk to show the call had happened. `call` no longer raises once the API has responded, the id is written first because it is the only thing a re-run cannot regenerate, and an answer that cannot reach disk is printed rather than dropped.

  A safety guard that did not guard. The sensitive-path check expanded the candidate path but not the pattern, so home-relative and variable-prefixed patterns — the forms this repo's own conventions teach people to write — matched nothing at all. Both reviews found it independently.

  **Three bugs surfaced while fixing that one, each of which made the fix look like it worked**, which is the part worth remembering: normalising an empty pattern produced `"."`, matching every file with an extension; `os.path.normcase` is a no-op on POSIX, so the first attempt at case folding changed nothing while appearing correct; and a test passed for the wrong reason, because macOS temp directories sit under a `private` prefix, so that pattern matched the temp path rather than the directory under test. A green test that is not testing anything is worse than a red one.

  Also: status handling now covers the full set the SDK defines rather than the two the docs mention — a `failed` interaction returns empty output, which was parsed as JSON and reported as a malformed reply, blaming the parser for an API failure and burying the only signal that explained it. Attachment paths are recorded relative to the project, so an absolute argument no longer writes a username into a run directory that can be copied or shared. `background` is rejected outright rather than validated and never sent. A `stored` command lists what exists server-side, which is the only thing a user can act on given it cannot be deleted.

  Tests went from 28 to 83, concentrated on the modules where the critical bugs lived and had no coverage at all.

## 0.95.0

### fixed
- **`advisor` 0.2.0 → 0.3.0 — the spend gate had a total bypass, and it was a copied idiom.** Two Sonnet reviewers, one on correctness and one on privacy, found six real defects between them. The worst: `advisor-pre-tool-use.sh` opened with a blanket `command -v jq || exit 0`, lifted from `path-privacy`'s hook where failing open is correct. Here `exit 0` means *allow the spend*, so on any machine without `jq` on the hook's PATH the gate silently became a no-op — no authorization check, no model check, no trace. No hostile actor required, just a missing dependency.

  The lesson generalises past this bug: **a defensive idiom is only defensive relative to what failure means in that script.** The same line is right in the mint hook (no jq → no token → nothing authorized) and catastrophic in the gate. Failure policy is now stated per-job rather than at the top of the file, and when `jq` is absent the gate falls back to a crude substring match and *refuses* an advisor spawn rather than waving it through.

  Also fixed: **the one-authorization-one-spawn guarantee did not hold under concurrency.** Validation read the token and only then deleted it, so two parallel `Agent` calls — a supported and encouraged pattern — could both pass every check against the same file. The token is now claimed with an atomic `mv` *before* validation, so only the winner proceeds. Verified with 10 rounds of two concurrent spawns against one authorization: exactly 10 allowed, 10 denied. An empty `session_id` also used to skip the gate entirely; it now denies, since a spawn that cannot be verified must not be funded.

  Three defects in `digest.py`, two of them silent-data-loss:
  - **The `AskUserQuestion` promotion was order-dependent.** A user-role message batching an `AskUserQuestion` result with an ordinary tool result would flip back to `tool_output` and drop the whole event — the user's answer included. The same failure class as the bug that shipped in 0.1.0, one ordering away, and the existing regression test used a single block so it did not catch it. Promotion is now sticky.
  - **A non-dict `message` raised instead of degrading.** Valid JSON, unexpected shape, uncaught `AttributeError`, whole digest aborted, consult blocked.
  - **`NotebookEdit` never appeared under "Files written or edited"** — it names its target `notebook_path`, and the collector checked only `file_path` while the trajectory summary checked all three. Two copies of one key list that disagreed; now one shared helper.

  Privacy fixes from the second reviewer: state is written under `umask 077` with `chmod 700`, where it previously inherited the default umask and landed `0644` in a `0755` directory. On macOS `TMPDIR` is per-user so this was contained, but the `${TMPDIR:-/tmp}` fallback is a shared world-readable `/tmp` on Linux — and that directory holds a digest of the session transcript. Digests are now cleared when a new consult is authorized, and session directories older than seven days are swept.

  The README now states plainly what the digest contains and does not filter. Your own messages are preserved verbatim by design, so anything pasted into the chat is in there. That sends nothing new to the model — it was already in the conversation — but it does write a second copy to disk, which is the part worth knowing. `scan-for-secrets` is named as the tool to point at a digest if the payload needs screening; wiring it in automatically is deliberately not done.

  Three tests added, one per data-loss defect. 25 for the digest, 100 across the repo.

### added
- **`advisor` 0.1.1 → 0.2.0 — 22 tests for `digest.py`, the component that already failed silently once.** The digest reconstructs a session from its transcript so a stronger model can read it. Its failure mode is the dangerous kind: it does not crash, it just hands the advisor a session with something missing, and the advice comes back confident and uninformed.

  The suite is built around the bug that shipped in 0.1.0 and was caught by eye rather than by any check — `AskUserQuestion` results were classified as tool output, so every constraint stated through that channel was dropped. `test_ask_user_question_result_is_promoted_to_human` pins it, with a sibling asserting ordinary tool results are *not* promoted, since the naive fix files every Bash result as user steering.

  Also covered: user messages surviving an absurdly small character budget (a stated constraint must never be a compression casualty), sidechain exclusion, error attribution to the originating tool, file paths captured without inlining file bodies, a malformed trailing JSONL line degrading rather than raising (the transcript is written asynchronously and may be mid-write), harness-injected `<system-reminder>` blocks stripped, and the CLI exit codes.

  Test-harness note worth keeping: loading a PEP 723 script by path needs the module registered in `sys.modules` *before* `exec_module`, or `@dataclass` fails with an unhelpful `'NoneType' object has no attribute '__dict__'` — it resolves its own module through `sys.modules[cls.__module__]`.

### fixed
- **`advisor` 0.1.0 → 0.1.1 — the mint hook glob-expanded the arguments you typed.** `set -- $ARGS` performs pathname expansion as well as word splitting, so `/advisor --model *` run in a directory containing files became `--model <filename> <filename>`. The model validation coerced the unrecognised value back to the default, so it failed safe rather than spawning an unexpected tier — but it silently discarded what was asked for, which is the wrong behaviour for the one component whose whole job is honouring the user's stated bounds.

  Fixed with `set -f` around the split rather than `read -ra`: the array form needs bash 4.4+ to be safe under `set -u` when empty, and macOS still ships bash 3.2.

  Found while scoping a code review, and the first attempt to reproduce it was itself wrong — the check ran in this environment's zsh, which does not word-split unquoted expansions, and reported no bug. Re-run under `bash -c`, the expansion produced three positional parameters from two. Shell-behaviour claims need the shell the script actually declares.

### removed
- **`model-routing` 0.4.0 → 0.5.0 — the agent-state feedback layer is gone.** It appended an outcome-recording section to the installed rule, telling Claude to run `agent-state delegation record` after verifying each delegation. Three independent reasons it had to go: the table it wrote to (`fact_delegation`) has never existed in the live database, nothing has written to that database since 2026-03-12, and the outcome it captured was the orchestrator grading its own delegation — the signal shape both design notes now say should not be built. It was also always-loaded text in every project that opted in.

  Superseded rather than merely deleted: `ccutils` recovers 947 delegations from session transcripts observationally, needing no cooperation from the party being measured and backfilling five months retroactively.

  This also caught two claims that expired when installation was paused. Both plugin READMEs argued the pair must stay separate because `model-routing` needs to be discoverable while `advisor` must not be — an argument that died the moment `model-routing` took `disable-model-invocation` too. Rewritten to the reason that still holds (shape and lifecycle: an installer with no runtime footprint versus three hook events and a spend gate; a paused thing versus one tracking a moving upstream beta), with the expiry noted rather than silently patched.

### changed
- **`skill-maintainer` 0.18.1 → 0.19.0 — the description check no longer demands a trigger phrase from skills that cannot be triggered.** `disable-model-invocation: true` keeps a description out of Claude's context entirely, so it is never matched against a user's phrasing. Requiring a WHEN trigger there asks for text that provably cannot fire, and the only way to satisfy it is to write one that never will — passing a check by touching what it measures. `validate`, `quality`, and `test` now skip that check when the flag is set. The WHAT check still applies: the description is what a person reads in the slash-command menu. Default stays strict, so an exemption has to be declared rather than inferred.

  While measuring this, the WHAT check turned out to be broken in a way nothing had surfaced. Its verb list held ten entries; the repo's 32 descriptions lead with 32 distinct verbs, of which the list contained four. It passed almost everything anyway because `"use when"` was in **both** the WHAT and WHEN lists — so a description with a trigger phrase satisfied both, and the WHAT check had no independent signal. Its failures were identical to the WHEN check's across all 32 skills. Widened to the verbs actually in use, and it now checks the leading word rather than scanning for any of ten substrings.

  A cautionary note on the measurement itself: the first pass at this used a regex to pull descriptions out of frontmatter and reported 17 of 32 skills failing, which read as a badly-calibrated check. The regex was capturing `>-` from YAML folded scalars. Parsed properly, the real answer was 2 of 32 — exactly the two `disable-model-invocation` skills, i.e. every failure the check produced was a false positive of one kind. The wrong number argued for redesigning the check; the right number argued for one exemption.

- **`model-routing` 0.3.5 → 0.4.0 — installation paused, and the skill is now user-invoked only.** The rule was removed from all eight repos carrying it, so the thing to prevent is it coming back on its own. `disable-model-invocation: true` keeps the description out of Claude's context entirely, which means phrases like "set up model delegation here" no longer reach it — only an explicit slash command does, and the skill then explains the pause and confirms before writing. Removal needs no confirmation and is unaffected.

  Deliberately *not* a hook. The advisor gate exists because its failure mode is spending money on a frontier model, which is invisible until the bill. Here the failure is a file appearing in `.claude/rules/` — cheap, visible, and deleted in one command. Blocking the eager path is proportionate; a `PreToolUse` gate would be machinery a paused feature has not earned. The tier test from invariant 1c cuts both ways, and this is the side where it argues for less.

  Second skill in the repo to trip `skill-maintain validate`'s "missing WHEN trigger" warning, for the same reason as `advisor`: a description that never enters context cannot carry a trigger phrase. Two instances is enough to say the check should exempt `disable-model-invocation` skills rather than have both of them documented as accepted warnings.

- **`model-routing` 0.3.4 → 0.3.5 — the rule now tells Claude to check `.claude/agents/` instead of trusting the agent names printed in the rule itself.** Found by surveying the eight repos that have the rule installed: one had hand-edited this exact line, and the edit was a bug report. It read *"An earlier version of this line named `fast-executor` and `task-coder`, neither of which has ever existed here — a dispatch to a nonexistent agent name is the failure to avoid."*

  The rule is copied verbatim into projects, but the agents layer is opt-in, so any install that skipped it got a rule confidently naming two agents that were not there. Someone hit that, diagnosed it, and fixed their local copy — where the fix was invisible to everyone else and would have been overwritten by the next install. The template now states the general form: list the directory, use what is actually in it, do not trust a name written here.

  Worth noting how this surfaced. The verbatim-copy install makes a local edit the only place a lesson can land, and nothing carries it back. That is the same one-way-drift shape as 0.3.4's fix, in the other direction.

- **`agent-state` 0.3.0 → 0.3.1 — documented as not currently workable, with the evidence.** The live database has not been written to since 2026-03-12: `dim_skill_version` is empty, `fact_delegation` does not exist, and the schema sits at v2 while the README documented v3. That last one is not a migration bug — the DDL is `CREATE TABLE IF NOT EXISTS` and runs on every connect, so a v2 database is direct evidence that **no process has opened it since v3 shipped**. A third source of truth, `SCHEMA_VERSION = 2` in `database.py`, is defined once and read nowhere; per invariant 1b it should be deleted rather than corrected.

  The root problem is that the package has no producers, and the table this repo intended to use — `fact_delegation` — was superseded before it ever ran. `ccutils` now recovers delegations from transcripts observationally, which beats asking an agent to self-report the outcome of its own work. What survives is the half transcripts structurally cannot hold: watermarks, runs that are not Claude Code sessions, and skill content versions. New design note at [docs/internals/agent_state_population.md](docs/internals/agent_state_population.md) covers the population plan and the observation that `v_flywheel` returns nothing because agent-state owns producer-run and skill-version while ccutils owns consumer-run — the join key being the skill content hash, which both sides can compute independently. Docs only; no schema or code changed.

- **`model-routing` 0.3.3 → 0.3.4 — cross-links with `advisor`, and the shipped rule template reconciled with the copy this repo actually runs.** They read as a pair — one routes down, one routes up — but they cannot merge on a technicality that matters: `model-routing` must stay discoverable, so its description sits in the always-loaded skill listing, while `advisor` sets `disable-model-invocation` precisely to stay out of it. One plugin cannot hold both settings. Their autonomy policies are also opposites: delegate downward on your own judgment, never spend upward without a keystroke.

  The template had drifted from `.claude/rules/model-delegation.md` here, in the direction that mattered: it ended "keep it in the main loop **or spawn Opus**" and listed opus among the delegation tiers. That is a bug in a rule whose thesis is "route to the cheapest capable model" — it pointed the uncertainty fallback at the most expensive tier, and with `advisor` now in the repo it would have authorized exactly the autonomous up-tier spawn that plugin exists to prevent. Fresh installs got the drifted copy; this repo never did, so nothing here misbehaved and nothing revealed the gap. Same shape as invariant 3's `best_practices.md` duality: two copies, and the one nobody reads is the one that rots. Found by diffing them rather than by either copy failing.

### added
- **`advisor` 0.1.0 — a higher-tier consult for the current session, with the spend decision moved from the model to the user.** Emulates the Claude API's [advisor tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool) inside Claude Code. The API version pairs a cheap executor with a stronger advisor that reads the full transcript mid-generation; Claude Code cannot do that, because its `Agent` tool forces a choice — `subagent_type: "fork"` inherits full context but ignores the model override, and any other subagent takes the override but starts empty. Neither yields a stronger model that has seen your work.

  `skills/advisor/scripts/digest.py` bridges that gap by reconstructing the session from its transcript JSONL into a bounded digest. It is lossy on purpose: one transcript in this repo reached 13 MB, far more than the live window it came from ever held, because tool results are truncated in-session but written to disk in full. Allocation is deliberate rather than proportional — the task statement and every human message survive uncompressed, because losing a constraint the user stated is the one failure mode that makes advice actively harmful.

  **The inversion.** The API tool's premise is that the executor knows when it needs help, which is reasonable when you have set a budget in advance and wrong for an interactive session, where an autonomous frontier-model spawn is a surprise charge against someone watching their own bill. So typing `/advisor` is the only thing that authorizes a spend.

  **Where the authorization is minted decides whether that is true.** The first cut had `prepare-consult.sh` mint it, which quietly defeated the gate: that script runs under Bash, so the agent could call it and satisfy the constraint it was supposed to be bound by. The hook checked that *a* token existed, not that a human made one. Minting now happens only in a `UserPromptExpansion` hook, an event that fires solely when a user-typed command expands — upstream is explicit that this is the path `PreToolUse` misses, because Claude invoking a skill goes through the `Skill` tool while typing `/advisor` does not. The agent cannot reach it. Tokens carry `origin: user_typed_command`, and both the script and the spawn gate refuse anything without it.

  Three independent gates, since the failure is a surprise charge: `disable-model-invocation: true` keeps the skill out of Claude's context entirely; the mint hook is unreachable from the agentic loop; and `PreToolUse` denies spawns whose authorization is missing, expired, replayed, lacking provenance, or naming a model other than the one typed — which closes "approve sonnet, spawn fable". Bounds are captured at mint time, so nothing downstream can substitute a value.

  The honest limit, stated rather than papered over: the token is a file, so anything holding Write or Bash can fabricate one. This is defense against an *eager* agent, which is the actual risk, not against a hostile one. No file-based scheme can promise the latter.

  Neither hook job can spawn a model — they detect and refuse, nothing else. That is why block messages terminate in a human decision: telling Claude to "consult the advisor first" would have the main loop helpfully do exactly that, restoring the surprise spend the hook exists to prevent.

  The optional pre-write checkpoint (the upstream "hard rule") ships **off**. Anthropic's own numbers have it raising Haiku coding pass rates ~7.5pp while costing ~4pp on retrieval-heavy workloads and pushing Opus to over-call — a real tradeoff, not a free win, and defaulting it on would misrepresent it as one.

  Mirror image of `model-routing`, which routes *down* to cheaper models for mechanical work. Same axis, opposite direction; they compose.

## 0.94.1

### fixed
- **`path-privacy` 0.10.2 → 0.10.3 — its description was invalid, and it was the one skill that could least afford to be.** Descriptions cannot contain `<` or `>`; upstream `skill-creator` rejects them outright and `skill-maintain validate` warns. `path-privacy`'s description demonstrated the leak forms it blocks using the placeholder convention itself, so it carried three angle-bracket pairs and was the only description in the repo doing so. The skill whose entire job is teaching that convention was the one place the convention is illegal.

  It went unnoticed because validation runs on *changed* skills at commit time, so a rule nobody trips stays unenforced until someone edits the file. Found by tripping it on an unrelated skill and checking whether the rule was real rather than working around the warning. The placeholder form stays correct everywhere else — bodies, references, docs, commit messages — and the rule now lives in `.claude/rules/skills.md` so the next description does not rediscover it at commit time.

  Wording only. The scanner, the hooks, and what counts as a leak are unchanged.

## 0.94.0

### changed
- **`writing` 0.4.1 → 0.5.0 and `dev-conventions` 0.12.4 → 0.13.0 — four descriptions rewritten against measured trigger rates rather than intuition.** Each skill was run against 16 held-out prompts (10 should-trigger, 6 near-miss should-not-trigger), three runs per prompt, detecting whether the installed skill actually fired. The rewrites target the specific prompts that measured dead.

  **The theory the measurement killed.** The prior round of rewrites assumed that leading with "the words a request would actually contain" raises the trigger rate. `voice-match` was the clean test: its description enumerated "in my voice", "sound like me", and "in my style", and prompts containing those exact strings triggered it 0 times out of 3, each. Listing the phrase does not buy the trigger. What separates the descriptions that fire from the ones that do not is whether they name a concrete artifact, symptom, or output the model cannot produce unaided — `reportCallIssue` and a wall of "Arguments missing for parameters" fire at 100%, "write in the user's voice" reads as an ordinary instruction the model simply follows. Descriptions now lead with the thing that cannot be guessed.

  `plain-language-us` (40%) fired on the remedy's vocabulary and went dark on the complaint's: "apply house style" triggered 3 of 3 while "make this summary readable" and "clean up the prose, it has that AI-ish bolded-phrase thing" triggered 0 of 3. It now leads with the symptoms a request actually describes. `voice-match` (10%) now leads with the saved profile it reads and the reason generic drafting fails. `dep-audit` (43%, and five prompts stuck at exactly 1 of 3 — matching, then losing to "I will just run `uv audit` myself") now leads with the report it produces, severity and fixed version and transitive coverage included. `python-tooling` (73%) drops its dependency-pinning clause: the pinning prompts measured 0 of 3 with the SessionStart hook active and 3 of 3 with it silent, because `directives/python.md` already answers them in context. A description should not advertise a trigger the plugin's own hook pre-empts.

  **Precision was never the constraint.** Across 198 runs against deliberate near-misses — "configure pyright for this repo" against `configure`, "run a maintenance pass" against `init-maintenance`, "scan this repo for hardcoded api keys" against `dep-audit` — there was not one false trigger. The descriptions were tuned narrow and were paying for it in recall, which inverts the priority the vision document states.

  **Two harness corrections worth recording.** Measuring an installed skill with a synthetic stand-in scores a miss whenever the real twin wins the trigger, which reads as a broken description and is not one. And a detector that early-exits on the first non-Skill tool call scores a natural Read → Skill → Edit sequence as a miss. Both bias results downward; both were corrected before any number here was believed.

## 0.93.0

### added
- **`postmortem` 0.4.0 → 0.5.0 — `postmortem-index`, a generated browsable view over a repo's postmortems.** Third skill in the plugin, because its trigger surface is genuinely different: "what have we written about X" has nothing to do with running a postmortem, and burying those phrases in an analysis skill's description would cost the trigger.

  **This is not the index file that filing rejected, and the distinction is the whole justification.** What 0.3.0 rejected was a committed `postmortems/README.md`: a copy whose only consumer is the check that it matches the directory, drifting the moment someone adds a file. This page is rebuilt from the files on every invocation and deleting it loses nothing. That is the test — if deleting a file loses information it was truth, and if not it is a view. The one thing that turns a view back into a copy is committing it, so the skill offers to gitignore the generated file when the postmortem directory is tracked. A generated artifact that cannot be committed cannot be mistaken for truth.

  **Frontmatter only, never the body.** This is the payoff of two earlier decisions landing where they should: filing specified frontmatter strictly and rendering deliberately declined to make the *body* a parse contract. The index reads `mode`, `scope`, `date`, `summary`, `artifacts` and `supersedes` without ever touching prose, so a section written differently cannot break it.

  **Nothing is hidden.** Superseded postmortems dim and carry a badge rather than disappearing — a stale conclusion a reader can see is stale is useful, and one that has been hidden is a trap. Files predating 0.3.0 have no frontmatter at all; they still appear, with date, mode and scope recovered from the filename (the portable half of the naming rule) and a "partially indexed" badge. Silently dropping them is what makes an index untrustworthy, because a reader cannot distinguish "nothing was written" from "the tool did not understand it". An empty directory renders the page with a zero count and says where it looked.

  **JavaScript, in this one place.** The document rules it out because a record that needs a script to be readable is less durable than the markdown it came from; an index is a tool that gets rebuilt, so the rule does not carry. The script is inline, dependency-free, and strictly an accelerator: nothing starts hidden, so with scripting off the page loses filtering and keeps everything else. Terms AND together, matching runs against one `data-search` attribute rather than rendered text so behaviour cannot drift from styling, clicking an artifact filters to it, and the superseded toggle exists because it is the one filter a reader cannot type.

  Verified in a real browser rather than by inspection, since the interactive half is the part that inspection cannot check: initial 4 of 4, single term 2, two terms narrowing to 1, artifact click populating the filter, superseded toggle 3 of 4, a no-match state reporting 0 of 4 honestly, and a full restore on clear. A first pass shipped a dangling `.empty` class that no code path emitted — caught on screenshot, now wired to the no-match state.

### changed
- **`postmortem` frontmatter gains a required `summary`.** One sentence carrying a *finding*, not a topic: "looked at the lint tooling" is a subject line, "Ruff and Pyright diagnostics did not overlap, so the LSP collision was the real constraint" is a summary. A reader scanning a directory decides what to open from this field alone, so restating the slug wastes the slot the slug already fills. A postmortem whose sections are all "Nothing." says that here too — the work was clean is a finding, and it saves opening the file.

  It is also **the one field an annotation may change.** Annotate-don't-rewrite protects findings, because a silently edited conclusion is worse than a wrong one left standing; it does not protect metadata. A stale summary sends readers to the wrong file, which is the failure the field exists to prevent.


## 0.92.0

### added
- **`postmortem` 0.3.0 → 0.4.0 — `--html` renders a self-contained human-readable file beside the markdown.** New `references/html-render.md`, read only when the flag is passed, so a markdown-only run pays nothing for it.

  **The design collapsed once the owner answered one question.** [docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) built its whole argument on a fear that N renderers would each re-derive the findings and then disagree, and concluded that a structured intermediate was "the whole design decision. Everything else follows from it." That premise does not hold here: there are no separate renderers, there is one model in one turn, and HTML is only ever produced in the run that writes the markdown. So the guarantee comes from a *rule* — render the markdown you just wrote, never re-analyse — and a rule is sufficient when there is one implementer. No intermediate, no sidecar, no parse contract. The doc's two heaviest sections were answering a question the shipped feature does not ask.

  **A flag, not a format list.** The doc proposed `--format=md,html` and argued positional arguments could not carry a third dimension. Markdown is always written — filing made it load-bearing, since `supersedes` names a `.md`, the `artifacts` grep hits the `.md`, and annotate-don't-rewrite edits the `.md` — so the "list" has exactly one optional member, and a list implies a choice that does not exist. `--html` and `--out=<dir>` compose with positional mode and scope, so the argument interface never had to break.

  **No styler, no `--style`, no availability ladder.** The doc spent a section on composing with `impeccable` without depending on it; the answer is that one built-in stylesheet is the whole design, and the hook gets added if a different look is ever actually wanted. A soft dependency that no one exercises is still a section of instructions to maintain.

  Self-contained by constraint: no external requests of any kind, no JavaScript, embedded CSS, light and dark. Both stated uses — reading your own in a browser, sending one to someone who will not clone the repo — need portability and neither needs interactivity. Empty sections render visibly rather than being collapsed or dropped, citations are never trimmed for tidiness, and annotations render distinctly from the findings they correct, since an append-correction that reads like original text defeats append-correcting.

  Rendering a postmortem from an *earlier* run is explicitly not a designed capability: `report-format.md` is a house style, not a parse contract, so nothing guarantees an old file is machine-readable. Asked anyway, transform what the file says including later annotations, and never re-derive from fresh evidence.

  Verified on the filing fixture: no `http(s)://`, `@import`, `<script>`, `<link>` or `src=`; all five sections present including the empty one; citation counts identical between the markdown and the HTML; same stem, same directory. `test-audit` deliberately unchanged — its tabular verdicts may want different treatment than narrative prose, and one consumer is enough to learn from.


## 0.91.0

### changed
- **`postmortem` 0.2.1 → 0.3.0 — postmortems are filed, not buried.** The filing half of [docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) is implemented; rendering is deliberately still not started. New `references/filing.md` carries the whole procedure and `references/report-format.md`'s location section shrinks to a pointer, since it held an abbreviated copy of the same ladder.

  **The directory is resolved, never hardcoded, and the run says which rung it landed on.** `--out=<dir>` or a location named in the request, then a root-level `.postmortem.json`, then inference from where the repo already keeps prose about itself, then propose-and-remember. Only the last rung blocks. Inference picks the *parent* and the leaf is always `postmortems/`, so a repo with `internal/log/` gets `internal/postmortems/` and inherits that parent's tracked-ness — gitignored parent means the postmortems are local scratch, which is an answer rather than an oversight. Config is the plugin's own `.postmortem.json`, following the "Per-repo plugin config" convention in `plugin-patterns.md`; the design doc's open question leaned toward a shared per-repo config and that was rejected. One shared file would couple plugins that release independently, and there is exactly one consumer.

  **`artifacts` is a projection of the citations, not free metadata.** Every entry in the frontmatter list must be cited in the body and every artifact cited in the body must appear in the list, which makes the field checkable rather than decorative — the two sets disagreeing means one of them is wrong. It also gives the no-citation-no-finding rule a mechanical consequence at file level: a findings-bearing postmortem with an empty `artifacts` list is a contradiction. That field is the reason the whole scheme needs no index file: "has anything been written about this plugin" is one grep, and an index would be a copy whose only consumer is the check that it matches the directory.

  Frontmatter also carries `mode` / `scope` / `date`, `range` for spans, and an optional single-valued `supersedes`. A span's *filename* date is the start of its range, not the day it was written, so lexical sort stays chronological by subject; the write date lives in `date:`. Annotate-versus-supersede got the test it lacked: if the old document's verdicts still stand and one is now wrong, annotate it; if its whole framing has been overtaken, write a new file that supersedes it. Cross-linking is one direction only — a plan doc gets a pointer to the postmortem, and nothing links back, because `artifacts` already records everything the run examined.

  Tested by running the ladder against two repo shapes. A repo with a session-log directory resolved at rung 3 and wrote beside it; a repo with no prose anywhere blocked at rung 4 and created nothing, which is the correct output. The second fixture found a gap in the first draft: rung 4 now has to state whether the proposed location would be tracked or gitignored, because rung 3 reads that off a sibling directory and rung 4 has no sibling to read.

  `argument-hint` gains `[--out=<dir>]` and keeps its positional mode and scope; the design doc's full switch to flags belongs with the format work, since `--format` is what positional arguments actually cannot carry.


## 0.90.0

### changed
- **`model-routing` 0.3.2 → 0.3.3 — reviewed by the owner.** `metadata.last_verified` moved 2026-07-05 → 2026-07-26. This is the one case where that field should move: a human actually read the skill against its source. It stays out of every mechanical cascade precisely so that when it does move, it means something.

- **`skill-maintainer` 0.16.4 → 0.17.0 — `tune` runs as Phase 4 of the maintenance pass, not on a schedule.** The other phases check what this repo *says*; this one checks what its plugins actually *do*, in every project they run in. Folding it into `maintain` rather than scheduling it is deliberate: neither built-in scheduler fits — `CronCreate` jobs are session-only and expire after seven days, and cloud routines cannot read the local transcripts `tune` depends on — and a cron that quietly stops is the same never-zero-channel failure the rest of this tooling exists to remove. Running it where maintenance already happens has no way to silently stop working.

  The phase says what to act on, in the terms the measurements established: read the emission *rate* rather than the count, treat an `ambiguous(...)` plugin column as a filename collision to rename, question an LSP channel above ~3 diagnostics per push, and do **not** delete a zero-invocation skill on that evidence alone — not-needed and not-discoverable look identical there and the remedies are opposite, so `skill-creator`'s description-tuning harness settles it first.


## 0.89.0

### added
- **`ruff-diagnostics` 0.1.0 — Ruff findings reach Claude after every Python edit, via a hook, because an LSP cannot work here.** Ruff ships a language server and Astral's guidance is to run it *alongside* a type checker, not instead of one: "the server is intended to be used alongside another Python Language Server in order to support features like navigation and autocompletion." That is how it works in VS Code and Neovim. Claude Code cannot express it — it registers one language server per file extension, and "the first server registered handles files with that extension and the others never start." `pyright-lsp` claims `.py` and `.pyi`, so a Ruff LSP would lose the race silently, decided by registration order. The hook reconstructs the intended split from outside the LSP layer: Pyright owns types and navigation, Ruff owns lint. Astral reached the same conclusion independently — their own Claude Code plugin ships a `ty` server and deliberately does not register Ruff as one. (That plugin also claims `.py`/`.pyi`, so installing it collides with `pyright-lsp`; noted in the README because the failure is silent.)

  **Three constraints, each of which cost something to learn.** `uv run ruff` syncs the project environment before running — observed installing 24 packages into a project that merely lacked Ruff — so every probe uses `uv run --no-sync`, which fails cleanly instead. Ruff reports an unreadable path as a single `E902` io-error, so a naive count of a broken invocation returns a plausible-looking `1` rather than crashing; any `E902` aborts silently rather than reporting fiction. And a clean file emits nothing at all, because an always-on hook that narrates its own success is pure token cost.

  **No rule-set opinion, no fixing, no config writes.** It runs bare `ruff check`: config-less projects get Ruff's defaults, configured projects get their own config. `ruff check --fix` is offered as text and never executed — fixes are edits, and edits are the user's call. Unlike `pyright-autoconfig`, which can drop a git-excluded `pyrightconfig.json`, Ruff's config lives in tracked files, so there is no untracked place to put settings and the hook only ever reads.

  Pairs with `pyright-autoconfig` without overlapping it: measured Pyright/Ruff diagnostic overlap across this repo was **zero at line level**, and 11 of 2,429 (0.5%) even with Pyright forced to strict. The duplicate pair that intuition suggests — `F821` against `reportUndefinedVariable` — never fires at all; the real duplicates are `F401`/`reportUnusedImport` and `F841`/`reportUnusedVariable`, and both Pyright rules are off in the configuration actually in use.

- **`dev-conventions` 0.8.1 → 0.9.0 — ruff guidance, in the pull-based tier only.** The `select`-versus-`extend-select` trap goes in the `python-tooling` skill, where there is room for the reasoning — and deliberately **not** in the `python.md` SessionStart directive. It was briefly added there during this session and removed before release: the rule now has an evidence-triggered carrier in `ruff-diagnostics`, which fires only on a project that actually sets `select`, and an always-loaded copy of a rule that a hook already raises on demand is exactly the sediment the ambient tier accumulates. Nothing about ruff is now paid for by sessions that never touch ruff. The skill also carries the invocation ladder (`uv run ruff` > `uvx ruff` > global `ruff`, preferring the project's pinned version) and two restraints taken from Astral's own skill: don't run `ruff format` on a project that isn't ruff-formatted, because reformatting buries the actual change; and scope fixes to the code being edited rather than the whole tree. Both tiers say to raise a narrow `select` list with the user rather than rewriting their lint config unprompted.

### added
- **[docs/internals/postmortem_output_formats.md](docs/internals/postmortem_output_formats.md) — design for postmortem multi-format output and filing. Not started; design only.** Two separable problems, deliverable independently.

  **Rendering**: markdown by default because the primary reader is often the next model, with HTML or HTML/JS on request in a style of the user's choosing. The design's one real decision is to split analysis from rendering — a structured intermediate that renderers consume — because bolting formats onto today's shape means each renderer re-derives the findings and two renderings of the same postmortem can then disagree. Styling is pluggable and explicitly optional: `impeccable` is named only as an example, and the rule is that a complete readable HTML file must be produced with no styler installed at all. Also switches the argument interface from positional to flags, since format is orthogonal to mode and scope.

  **Filing**: today's rule — append a `## Postmortem` section to the plan doc — optimises for proximity to the work and against ever finding it again. Standalone files named `YYYY-MM-DD_<mode>_<slug>.md` — date first so lexical sort is chronological, slug from the scope because that is what a grep months later will match. The *directory* is resolved rather than hardcoded: an explicit flag or per-repo config, else inferred from where that repo already keeps prose about itself, else proposed once and remembered. `internal/` is this repo's answer and is gitignored here; whether postmortems are local scratch or a tracked shared record is the repo owner's call, and a plugin shipping to other repos cannot assume either. Flat directory, organised by scope rather than session since sessions are already indexed by the logs. Deliberately **no index file**: that would be a copy whose only consumer is the check that it matches the directory, which is the same reasoning that removed SKILL.md versions and the per-unit changelogs. The naming convention is the index; frontmatter carries an `artifacts` list so "has anything been written about this file" is one grep.

  `postmortem` 0.1.3 → 0.1.4 for the README pointer to the design; the skill itself is unchanged.

  Records the constraints that are load-bearing today and easy to lose in a rewrite: no citation no finding, empty sections are valid output, a file always, annotate rather than duplicate, and finding-routing runs once rather than per renderer.

### changed
- **Docs swept to match what actually ships.** `ruff-diagnostics` was missing from the README plugin table entirely. `dev-conventions`, `dimensional-modeling` and `writing` still carried descriptions of behaviour they no longer have — a SessionStart hook that was removed, a directive tier that shrank, monoliths that were split. Six plugin READMEs pointed at hook scripts by their pre-rename names, so every "run it yourself" snippet in them was broken; `plugin-patterns.md` did too, in the example it holds up as the correct exec form. `pyright-autoconfig`'s README had a guarantee bullet stranded below a code block by an earlier edit. Last-updated dates refreshed on the seven plugin READMEs whose plugins changed this release. All eight touched plugins patch-bumped, since a README is plugin content and the pre-commit gate says so.

- **`/simplify` — four cleanup agents; the branch was red and neither test suite told me.** `test_path_privacy.py` reads the path-privacy hook scripts by name, and the rename to `<plugin>-<purpose>.sh` earlier in this release broke it outright: **1 failed, 19 passed**. `skill-maintain test` does not run pytest, so a suite I had been quoting as green all session was measuring the other half of the tests.

  **The guard it broke exists to prevent the bare version inequality that has now recurred five times, and it had already been defeated twice over.** It matched on the whole file body rather than the line, and the injected no-op fallback stub contains the comparator's name — so the assertion passed vacuously for `install-git-hooks.sh` forever. It also named `pp_version_is_newer`, which after the `tN` move has no production call sites at all: the guard was protecting a dead function. It now globs the hook scripts instead of naming one (the rename in this very branch is the proof that a hardcoded filename does not survive refactors), checks the line rather than the file, accepts either shared comparator, and measures the distance to the direction test in **code** lines so a rationale comment between them does not read as a missing test. Mutation-verified: replacing the direction test with `false` turns it red.

  Also from the review: `_version_tuple` and `_installed_version` in `tune.py` were dead — orphaned when `artifact_drift` moved to template stamps. The transcript pre-filter now matches only the four attachment kinds the loop branches on, rather than every attachment, before paying for `orjson.loads` across a ~1.1GB corpus. `dev-conventions`' PreToolUse hook parsed its stdin with three `jq` spawns where one `@tsv` call does; on a hook measured at ~5,000 fires per project that is ~10,000 subprocesses saved. `ruff-diagnostics` spawned `uv run` twice per Python edit — once to probe availability, once to work — and now stats `.venv/bin/ruff` first, keeping the probe only as the fallback. The command-head parser duplicated verbatim across both rule blocks is extracted; the **rule blocks themselves stay hand-rolled**, because they are not instances of one pattern and a table of glob patterns in POSIX sh becomes `eval`.

  `path-privacy`'s SessionStart hook contradicted its own policy statement: the header said it "deliberately does NOT rewrite the hook", citing four repo-damaging bugs, while the code refreshes it in place. The reversal is deliberate and the caveat is now answered rather than withdrawn. A comment also still credited `pp_version_is_newer` for a guard that `pp_template_is_newer` performs.

  Two doc gaps the altitude pass found: the tier model had no slot for a **silent actuator** — a `SessionStart` hook that writes something and emits only on state change, which is what `pyright-autoconfig` and `path-privacy` both are — so the next reader would have put an actuator's explanation in the ambient tier. And the per-repo config question is now a written convention (`.<plugin-name>.json`, root-level, tracked, omitted keys mean default) rather than an open question, deliberately **not** a shared mechanism: one shared file would couple plugins that release independently, and there is exactly one consumer.

- **Code review found eleven defects; the worst was a fix that never reached the repo.** `path-privacy` 0.9.1 → 0.10.0, `dev-conventions` 0.12.1 → 0.12.2, `ruff-diagnostics` 0.1.1 → 0.1.2, `skill-maintainer` plugin 0.16.2 → 0.16.3 and CLI 0.17.0 → 0.18.0.

  **The wrapper's runtime staleness check was still comparing a `tN` stamp against a plugin version**, so it would have printed "re-run install-git-hooks.sh" on every commit in every repo, unfixably — the exact cry-wolf failure the template-version change existed to remove, made worse. A commit claimed to fix it; the file is not in that commit. The edit was uncommitted when a verification block ran `git commit --allow-empty` followed by `git reset --hard HEAD~1`, which discarded it. The test that "confirmed" the fix passed because it read `.git/hooks/`, which is untracked and had kept the good wrapper. A test that reads a generated artifact cannot verify the generator.

  **The same comparison was wrong in two more places**, and for the same underlying reason as the original: `--doctor` still called `pp_version_is_newer` on `tN` stamps, and would have told an ahead wrapper to regenerate itself from an older plugin. `skill-maintain tune` compared stamps against `plugin.json`, so every healthy gate reported "cannot compare -- reinstall". `pp_template_is_newer` now lives in `_version_compare.sh` — the one authored source already injected into every wrapper and sourced by the installer and the SessionStart hook — rather than being written out separately in each, which is how the numeric version of this bug survived three sweeps. Both fallback stubs define it too, so a wrapper built without the library degrades instead of calling an undefined function.

  **`dev-conventions` blocked on substrings.** `rg "pip install" README.md` and `git commit -m "stop using pip install"` were both blocked in any repo with a `uv.lock`, in a file whose own header argues a false block is worse than a directive. Matching now runs per command-head, splitting on `;|&` and stripping env-var prefixes, with the `uv pip` shim check evaluated on the same head. The first attempt at this broke the real blocks while fixing the false ones and was caught by the matrix, not by reading the diff.

  Also: `rules[]` in `.dev-conventions.json` never loaded in a repo with no Python or JS marker, because the language guard returned first — the `configure` skill documents those as generic house rules and promises they load next session. `ruff-diagnostics` checked `pyproject.toml` before `ruff.toml`, inverting ruff's own precedence, so a project whose `select` lives in `ruff.toml` never got the note it exists to give. Five dangling references to the deleted `sync-bundled-ref` skill, one of them a live instruction in `finish-session`'s workflow. A dangling pointer to the deleted `bun-tooling` skill in the always-loaded JavaScript directive. Stale `_deprecated` claims in `maintenance.md`.

- **Hardcoded repo layouts removed from the live skills, not just documented as a future fix.** The design doc written moments earlier said the location must be resolved rather than assumed — while every skill that actually writes a file went on hardcoding `internal/log/`. A README pointer and a plan change nothing: the model reads `SKILL.md` and `references/`, and that is where the behaviour lives.

  Audited every skill and reference in the repo. Three categories came out. Legitimate: `skill-maintainer` naming `.skill-maintainer/`, which is its own directory that it creates rather than a layout it assumes. A preference, now labelled as one: `dev-conventions:doc-conventions` prescribing `./internal/` — prescribing is a conventions plugin's job, but it now says outright that a repo with its own arrangement keeps it. And two genuine defects.

  **`postmortem` 0.1.4 → 0.2.0** now resolves where to write: an explicitly named location, else beside wherever the repo already keeps prose about itself, else propose and get agreement. It also stops burying reports inside plan docs — cross-link instead, because a postmortem filed inside a plan doc is findable only by someone who already knows which plan doc to open — and adopts the `YYYY-MM-DD_<mode>_<slug>.md` name so a search months later matches on scope.

  **`skill-maintainer` 0.16.1 → 0.16.2** was the worse one: `finish-session` *writes* a session log, and did so to a hardcoded `internal/log/log_YYYY-MM-DD.md` in whatever repo it ran in. It now matches an existing log directory's layout and filename pattern, and proposes rather than creates when there is none.

  `path-privacy` 0.9.1 for one example line that read as a requirement.

- **Every hook script renamed to `hooks/<plugin>-<purpose>.sh`, because a shared filename made hooks unattributable.** Transcripts store the plugin-root variable unexpanded, so five of our plugins shipping `hooks/session-start.sh` — and two shipping `hooks/pre-tool-use.sh`, a collision introduced hours earlier in this same release — were indistinguishable to any tool reading them back. `skill-maintain tune` reported them as one `ambiguous(...)` bucket, which was honest and useless. Eleven scripts renamed; zero collisions remain. This also improves `/hooks` and `claude --debug hooks`, which show the same command strings.

- **SessionStart emissions now carry a `<!-- plugin: NAME -->` first line.** The other half of the same problem: `hook_additional_context` records carry only the *event* name, so an injected block could not be traced to the plugin that produced it — 201,144 bytes of it in one project, filed under `context via SessionStart`. Roughly 24 characters buys exact attribution. `path-privacy` already did this by accident with its `skip-file` marker; it is now a convention rather than a coincidence.

- **`dev-conventions` 0.11.0 → 0.12.0 — `tdd-workflow` deleted; red/green is not a house rule.** The skill taught the cycle and a list of standard practices — one behavior per test, descriptive names, never write implementation first — all of which Claude does without being told. Exactly one rule in it was non-derivable: every test records a one-line claim of what breaks if it is deleted. That already lives in the 500-char ambient directive, and the depth belongs to `postmortem:test-audit`, which exists to recover those claims. `postmortem` 0.1.0 → 0.1.1 for the cross-reference that pointed at the deleted skill.

- **`dev-conventions` 0.10.1 → 0.11.0 — rebuilt around what Claude cannot derive, plus per-repo overrides.** The plugin had drifted into teaching tooling. `bun-tooling` opened with a table mapping `npm install` to `bun add`; `python-tooling` described itself as a "conversion reference" whose core was "auto-loaded via SessionStart hook". Claude already knows uv and bun. Upstream's exclude list names this exactly — "anything inferable from code, standard conventions, detailed API docs" — with the test "Would removing this cause Claude to make mistakes? If not, cut it", and the Claude 5 post reporting **80% of Claude Code's own system prompt removed with no measurable loss**.

  What this plugin actually carries is a *preference*: that this owner uses uv and bun, how things get pinned, and a handful of house rules. `bun-tooling` is deleted outright — after cutting standard knowledge nothing remained that the 435-char directive did not already say. `python-tooling` 4,259 → 1,657 chars, refocused on the one genuinely non-derivable thing: the two mechanical mistakes that produce hundreds of Pydantic/Pyright diagnostics reading as unfixable noise, moved to `references/type-checking.md` with the measured 698 → 264 result behind them. Ruff guidance is gone from it entirely; `ruff-diagnostics` owns that, and the duplication was the only real conflict between the two plugins.

  **Per-repo customisation, because the defaults are preferences and repos differ.** A tracked `.dev-conventions.json` at the repo root overrides them: `enforce.*` turns an individual block off (the honest way to say "this repo really does use npm", rather than `DEV_CONVENTIONS_ALLOW=1` disabling everything everywhere for one call), and `rules[]` appends house rules to the SessionStart directive for that repo only. Both hooks read it. `/dev-conventions:configure` manages it with `$ARGUMENTS`, and pushes back before writing: a mechanically checkable rule should be a hook, and a rule the model already follows should not be added.

  The first implementation of the override silently did nothing, because `.enforce[$k] // empty` in jq treats `false` as absent — the alternative fired on exactly the value the check exists to read. Caught by testing the override rather than the code path. Five cases pinned: no config, python override, unrelated key, lockfile override, and an injected repo rule.

- **`path-privacy` 0.8.1 → 0.9.0 — commit messages and branch names are now enforced, and the directive shrank by 40%.** `PreToolUse` matched only `Write|Edit`, so a leaky `git commit -m` or `git checkout -b` passed straight through and was caught only by the commit-msg hook: correct, but one step too late — the commit fails and has to be retried. The matcher now includes `Bash`, and `-m`/`--message` values plus `-b`/`-B`/`-c` branch names are scanned with the same scanner before the command runs.

  Narrow on purpose: only cleanly-parseable forms are extracted, anything else falls through untouched, and the commit-msg hook remains the real backstop. Upstream is explicit that hook matching "fails open... when the Bash command can't be parsed", so this must never pretend to be exhaustive. Seven cases pinned, weighted to false-positive guards: a clean commit message, non-git Bash, `git status`, and ordinary edits all pass; a leaky message, a leaky branch name, and a leaky edit all block with exit 2.

  **With that enforced, the always-loaded directive stopped needing to explain it.** 1,540 → 926 chars; the plugin's whole SessionStart emission 2,065 → 1,439. What was cut is what the block message already says better, naming the actual offending path instead of listing hypothetical examples. What stayed is the rule itself and the one thing no hook can catch: if you fix a leak, do not say so — not in commit titles, branch names, or the changelog. Ambient cost across all remaining SessionStart hooks in this repo is now 3,918 chars, from 5,667 when this work started, with three hooks deleted outright on top of that.

- **`path-privacy` 0.7.4 → 0.8.1 — the frozen git hooks now refresh themselves, and stop crying wolf.** Two defects, one visible and one structural.

  **Nobody should run a shell script to update a plugin.** The wrapper is frozen at install time by necessity — a git hook cannot source from a plugin that may not be installed — so every template change meant a manual `install-git-hooks.sh` in every repo, and the notice saying so was the plugin's most-repeated output. The SessionStart hook already runs in every repo and already detects the staleness; it now just fixes it, re-running the installer in place and reporting "no action needed". It falls back to the old notice only when the rewrite actually fails (read-only `.git`, a `core.hooksPath` pointing elsewhere, a missing installer).

  **The stamp was tracking the wrong thing.** It carried the *plugin* version, so any unrelated bump — a renamed script, a doc fix — marked every installed wrapper in every repo stale. Measured across this plugin's history: **22 version bumps against 10 template changes**, so more than half of every staleness notice ever shown was false, including one this release generated an hour before this fix. Wrappers now carry `WRAPPER_TEMPLATE_VERSION` (`t1`), hand-incremented only when the generated wrapper actually changes.

  **The format change immediately broke the direction guard, and the test caught it.** `pp_version_is_newer` only understands plainly numeric versions, so it answered "not newer" for both `t9` and `t1` — sending an *ahead* wrapper into the refresh branch and downgrading it. That is the third appearance of this same defect class in one release. A `tN`-aware integer comparison now guards it, verified across four stamp forms: `t9` left alone, `t1`/`0.7.2`/`unknown` refreshed. Ownership is unchanged and still exact — a hand-written hook without our stamp is never touched, confirmed by checksum.

  **The generated wrapper carried a second copy of the same defect, and it kept firing after the first fix.** Each wrapper runs its own staleness check at commit time, and that copy compared its stamp against the resolved plugin's *version* — guaranteed to differ on every unrelated release, so the notice printed on every commit forever. It now compares template version to template version, reading `WRAPPER_TEMPLATE_VERSION` from the resolved plugin's installer, and its remedy line no longer names a command: "Open a Claude Code session in this repo and it refreshes itself." Wrapper template bumped to `t2`; verified by committing and getting silence.

- **`mece-decomposer` 0.5.2 → 0.6.0 — SessionStart hook removed, same reasoning as `dimensional-modeling`.** MECE decomposition is a method you reach for when decomposing something, not a convention you need before your first action. The skill is unchanged.

- **`dimensional-modeling` 0.4.2 → 0.5.0 — SessionStart hook removed; it is a skill you invoke, not a convention you need before acting.** It fired on any `.duckdb` file within three levels, `CREATE TABLE ... fact_/dim_` in SQL, **or `import duckdb` in any `.py`** — which is true of this repo's own `agent-state` and of `readwise-reader`, neither of which is designing a star schema. 906 bytes per session, in any project that touches duckdb, and the payload's own last line was "For full methodology... invoke /dimensional-modeling:dimensional-modeling": an always-loaded advertisement for a skill that already exists.

  **This corrects the tier test recorded earlier in this release.** Detection-gating makes a hook *cheaper*, not *justified*; the question is whether the content must arrive **unprompted**. "Always use uv" must — you would run `pip` before thinking to check. "Grain first, facts are append-only" must not — the model can recognise that it is designing a schema, which is exactly what a skill description is for. The skill is unchanged and keeps the full methodology.

- **The SessionStart attribution marker briefly broke three hooks, caught by testing the output rather than the diff.** The marker was first emitted as an HTML comment *before* the JSON envelope, which made stdout unparseable — silently killing the entire injection for `dev-conventions`, `dimensional-modeling`, and `mece-decomposer` rather than failing loudly. It now rides inside the `additionalContext` value as `[plugin:NAME]`, applied where the content is assembled rather than by pattern-matching the emit site, and all three are verified to parse.

- **`explainer-video` and `screenwright` retired from this repo.** Both were superseded — explainer-video frozen in favour of its successor, which was then renamed and migrated to its own repo — and neither had been invoked once across 200 transcripts. Together they were ~75,000 characters of skill body and references, including this repo's only token-budget failure (6,760 against a 4,000 limit).

  **Archived rather than deleted**, at the owner's request: both plugin trees and their five planning documents were copied into the successor repo's own archive area and byte-compared before removal here, so nothing depends on git history alone. Dropped from `marketplace.json` with `renames` entries to `null`, and swept from the README, CLAUDE.md's index, and `docs/README.md`. The `film-reviewer` agent went with them — it existed only to review explainer-video scenes and referenced files that no longer exist. `physics_bake_proposal.md` moved too, being entirely successor-Phase-4 work.

### removed
- **`cogapp-markdown` deleted.** Never invoked across 200 transcripts, no arguments, no references — a 4,692-character monolith wrapping a tool Claude can drive directly. Dropped from `marketplace.json` with a `renames` entry, and swept from the README including its credit line, since there is no longer anything here to attribute. Two stale credits went with it: the MCP Apps SDK entry, whose plugin was removed earlier this release, and `env-forge`'s pointer to `apps/_deprecated/`, a directory that no longer exists.

- **`mcp-apps` deleted.** Both skills (`create-mcp-app` 11,873 chars, `migrate-oai-app` 8,633) were 117 days stale and never invoked once across 200 transcripts. Dropped from `marketplace.json` with a `renames` entry to `null`, and swept from the README and CLAUDE.md. The README's generic "MCP Apps" section stays: `mece-decomposer` and `skill-dashboard` still ship MCP Apps, and that section describes theirs, not the deleted plugin's.

- **`plugin-toolkit/skills/plugin-toolkit.backup/` deleted.** An untracked stray carrying its own `SKILL.md`. `discover_skills` skipped it correctly so it cost nothing measurable, but it was a second copy of a skill sitting next to the real one.

### removed
- **`tui-design` deleted.** Old, unused, and its skills were never invoked once across 200 transcripts. Dropped from `marketplace.json` with a `renames` entry to `null`, and swept out of the README, four skill-maintainer docs that used it as their worked example, and the drift backlog.

- **`apps/_deprecated/` deleted, and the deprecation rule with it.** (A first pass left three untracked `__pycache__` files behind, so the tree survived on disk after `git rm` removed it from the index; cleaned.) The convention was to move withdrawn plugins there rather than delete them; in practice it was a second tree to maintain whose contents were never read, and it required a `SKIP_DIRS` entry precisely because everything in it would otherwise sit permanently red. Removal is now a deletion — git history is the archive. `.claude/rules/plugins.md` rewritten accordingly, with the full sweep the old rule omitted (README, docs, and any SKILL.md using the plugin as an example), and the `SKIP_DIRS` entry dropped rather than kept "just in case", so a directory reappearing under that name is scanned like any other.

### added
- **`skill-maintain tune` (skill-maintainer 0.15.3 → 0.16.0) — how plugins actually behave, across every repo you use them in.** Reads session transcripts and reports, per project: how often each hook *fired* versus *spoke*, bytes emitted by channel, block counts, ms/firing, LSP diagnostic density, and skill invocations per transcript. Plus a cross-repo section for the one thing that can genuinely drift — files a plugin wrote *into* a repo.

  **Scoped by what Claude Code already does.** `claude plugin details` reports per-plugin always-on vs on-invoke token cost, `/context` breaks down the window, `/doctor` estimates skill-listing cost, `/hooks` lists registrations, `claude --debug hooks` shows firings, `--safe-mode` isolates culprits. Three planned sections were dropped as redundant with those. What none of them show is behaviour *over time and across projects*, which is all this computes. The module docstring lists the built-ins so the next person checks before adding a section.

  **Four measurement traps are handled and documented in-module**, each having produced plausible-looking wrong numbers first: `{}` is silence, not speech (count it and every silent hook reads as a 100% emitter); `hook_success.stdout` and `hook_additional_context` are separate channels and summing them yields rates above 100%; `session-start.sh` cannot be attributed by command string because several plugins ship that filename and the plugin-root variable is stored unexpanded, so attribution resolves against the installed plugin registry and reports genuinely-shared paths as `ambiguous(...)` rather than guessing; and everything is date-filtered, because transcripts span months and mix in since-disabled plugins.

  **The artifact-drift section caught its own author reintroducing a fixed bug.** The first version compared wrapper stamp to plugin version with a bare `!=` — the exact defect `path-privacy` 0.7.2 and 0.7.3 exist to fix, which fires in both directions and calls both "stale". It reported this repo's own 0.7.3 wrapper as stale against an installed 0.7.1 plugin and advised re-running the installer, which would have regenerated the wrapper *from the older plugin*: the advertised fix as a downgrade. Direction is now established rather than assumed, non-numeric stamps are reported as un-comparable rather than guessed at, and an ahead wrapper is told the gate is fine and explicitly warned not to re-run the installer.

  First real run found live drift: `heylookitsanllm` carries an unstamped pre-0.6.0 `path-privacy` wrapper, and its LSP channel runs at 6.9 diagnostics per push against 1.6 here.

- **`dev-conventions` 0.9.0 → 0.10.0 — an enforcement tier, so the rules that can be checked stop being paid for as prose.** Upstream is blunt that prose is advisory: "Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook instead." A new `PreToolUse` hook blocks `pip`/`pip3`/`python -m pip` install and uninstall, `npm`/`yarn`/`pnpm` install/add/remove, and hand-edits to `uv.lock`/`bun.lock`. The two directives shrink accordingly — `python.md` 1,013 → 722 chars across this session, `javascript.md` 441 → 491 (it grew slightly, because the surviving line now explains what is enforced and what is not).

  **Detection gating is the whole safety story**, because a false block is far more disruptive than a directive the model can weigh in context. Every rule requires positive evidence from the project: pip is blocked only where `uv.lock` exists (a `pyproject.toml` alone is not evidence — plenty of pip projects have one), and npm only where `bun.lock` exists *and* no `package-lock.json`/`yarn.lock`/`pnpm-lock.yaml` competes. `uv pip install` is explicitly allowed as uv's own shim. `DEV_CONVENTIONS_ALLOW=1` disables every block.

  **The `if` filter is an optimisation, not the boundary.** Upstream warns it "fails open, running your hook regardless of pattern, when the Bash command can't be parsed", and advises the permission system over a hook matcher for hard allow/deny. So `if` only decides whether to spawn; every decision is made in-script from parsed `tool_input`. Twelve cases pinned, weighted toward false-positive guards rather than blocks: pip in a non-uv project, npm where both lockfiles exist, a repo with no project markers, `uv pip install`, `uv add`, and ordinary file edits all pass untouched.

- **[docs/internals/context-cost.md](docs/internals/context-cost.md) — where context cost actually goes, measured rather than assumed.** Across 27 transcripts in this repo, `PreToolUse` fired 5,109 times and emitted **zero bytes**, while `SessionStart` fired 54 times and emitted **77,582** — 53% of all hook output. Cost is emission, not invocation; the real per-edit cost is latency (~58ms/firing), not context. Upstream independently singles out the same event: "SessionStart runs on every session, so keep these hooks fast... For static context that doesn't require a script, use CLAUDE.md instead." It is worse than one-per-session, too — `SessionStart` re-fires on resume, fork, clear *and* compact.

  Also records the per-project variance that makes any abstract judgement of a plugin useless: one third-party plugin emitted 0 bytes across ~3,700–10,400 firings in three projects and **2,055,910 bytes** in a fourth, where a configured rule injected a suppression essay on every edit to four hot files — the largest context consumer in that repo by ~20x.

  Carries the resulting tier test (detectable violation → `PreToolUse` block; detectable condition → `PostToolUse` notice; neither → one ambient line pointing at a skill), how DRY resolves across tiers without paying for it, the eight built-in introspection commands that should not be re-implemented (`claude plugin details`, `/context`, `/doctor`, `/hooks`, `claude --debug hooks`, `--safe-mode`, `InstructionsLoaded`, `skill-creator`'s eval harness), and four transcript-mining traps that each produced plausible-looking wrong numbers before being caught.

### fixed
- **`pyright-autoconfig` 0.2.2 → 0.3.0 — declining to write was a one-way door; it now hands the project back.** The hook already refused to write when a project declared its own `[tool.pyright]`. That was necessary and not sufficient, because of a Pyright rule the plugin never accounted for: "a `pyrightconfig.json` file always takes precedent over `pyproject.toml` if both are present." So a file dropped *before* a project grew a `[tool.pyright]` block went on silently outranking it, forever, and the user had no reason to suspect a git-excluded file they never created was why their config had no effect. Found live in another repo, where an entire `[tool.pyright]` block would have been dead on arrival.

  When the project now declares its own config, the hook **removes the file it wrote** rather than merely leaving it. It also drops its own `.git/info/exclude` line, which would otherwise hide a `pyrightconfig.json` the project later wants tracked. Ownership discipline is unchanged and now covers deletion too: it retracts only its own byte-for-byte output, so a file anyone has edited stays untouched exactly as before. This is the one case where the hook emits context — a retraction the user did not ask for and cannot see in `git status` has to announce itself, and the notice reminds them to carry `venvPath`/`venv` into the new block.

  Seven behaviours pinned against real git repos: writes on a fresh project, retracts on handoff, cleans the exclude line, stays silent on the second run, preserves a hand-written config *and* stays quiet about it, no-ops on a `[tool.pyright.<subtable>]`-only project with nothing of ours to retract, and retracts without crashing outside a git repo.

### removed
- **`apps/readwise-reader/CHANGELOG.md` deleted — this repo has exactly one changelog, at the root.** It was the only first-party per-unit changelog in the tree (every other `CHANGELOG.md` is vendored, under `node_modules/` or `coderef/`), which is precisely why it rotted: a convention with a single instance has no habit maintaining it. Its latest heading was `0.3.0` while `pyproject.toml` had reached `1.0.2` — five versions of silent drift, in a file whose own package `CLAUDE.md` instructed keeping it updated. That instruction now points at the root changelog instead.

  This applies the same test that removed `metadata.version` from every SKILL.md: **does the copy have a consumer other than the check that confirms it is a copy?** `plugin.json` has one (Claude Code's `marketplace update`) and `marketplace.json` has one (the listing), and those two are already machine-checked against each other. Per-unit changelog headings had no consumer at all, and proved it by drifting five versions without a single failure anywhere.

### changed
- **`ruff-diagnostics` warns when a project's `select` list silently narrows it.** Ruff 0.16 (2026-07-23) raised the default rule set from 59 rules to 413, on the stated grounds that "many of these rules catch severe issues, including syntax errors and immediate runtime errors but were not previously enabled by default." The consequence is easy to miss: `select` **replaces** the default set while `extend-select` **extends** it, so any curated `select` written before 0.16 now enables fewer checks than having no Ruff config at all. Measured on this repo's `readwise-reader`: under its own seven-group `select` the package reports `All checks passed!`, while Ruff's defaults find seven real issues in the same tree — four blind-`except` handlers among them. The notice fires once per session per project root and, deliberately, fires even when the edited file is clean, since a narrow `select` reporting everything clean is exactly the state being warned about. It never edits lint config.

- **`readwise-reader` 1.0.2 → 1.1.0 — `select` → `extend-select`, and the seven findings that surfaced.** The package reported `All checks passed!` under its own seven-group `select` while Ruff's defaults found seven real issues in the same tree; converting to `extend-select` keeps every group the project already chose and restores the 413 defaults on top. No new noise came with them — `E501` does not fire at this line length, and the deliberate `B905` ignore still applies — so the change is purely additive: 7 findings, then 0.

  Three were mechanical and are fixed: a redundant `global webhook_handler` in `create_app()` whose only real assignment happens in the nested route handler that declares its own `global`; a `startswith` pair collapsed to a tuple; and a nested `async with` combined in the e2e fixture.

  **The four `BLE001` blind-`except` handlers are narrowed to what their bodies can actually raise**, read out of starlette 1.3.1 rather than guessed. `Request.json()` is `json.loads` over `body()`, so malformed JSON and bad encodings arrive as `JSONDecodeError` and `UnicodeDecodeError` — both `ValueError` — and a client vanishing mid-body raises `ClientDisconnect`; the two JSON parse sites catch exactly those. The form site needs one more: starlette converts form-parser failures into `HTTPException(400)`, whose default handler returns **plain text**, so letting it propagate would have broken this endpoint's contract to answer in RFC 6749 JSON. The batch collector in `triage.py` catches `httpx.HTTPError` (transport and status), `ValueError` (pydantic `ValidationError`, response `JSONDecodeError`), and `duckdb.Error` (the audit write). Every subclass relationship above was verified in the installed environment, not assumed.

  What this buys: a bug in our own dispatch now surfaces as a 500 instead of being disguised as the caller's malformed request, or silently recorded as a per-document failure the user is told to retry.

  **Ten tests added, because three of the four narrowed handlers had no coverage at all** — only the webhook's `test_malformed_json` already existed, so passing tests would otherwise have proved nothing about the change. Four e2e tests pin the OAuth bodies (malformed JSON, invalid UTF-8, unparseable multipart, empty form) including the assertion that the token endpoint still answers in JSON rather than starlette's plain text. Six unit tests pin the batch collector across all four reachable exception types, plus batch continuation, plus the new guarantee that an unexpected `TypeError` propagates. That last one is **mutation-verified**: restoring the bare `except Exception` turns exactly it red and leaves the other five green.

  Suite: 111 passing, up from 101. Dev-dependency floor moved `ruff>=0.9.0` → `ruff>=0.16`, since the reasoning above only holds from 0.16 on.

- **Workspace ruff floor `>=0.8.0` → `>=0.16`, `uv.lock` relocked 0.15.5 → 0.16.0.** Found by the new hook rather than by inspection: it reported nothing on a file with three known findings, because it had correctly preferred the workspace's *pinned* ruff, and 0.15.5's 59-rule default set does not include `ISC004` or `BLE001`. The hook was working as designed; the repo was the stale thing. The root `pyproject.toml` is a virtual workspace root with no version, so this carries no cascade of its own.

  **`uv run` works in this package again.** It had been failing outright with `skill-maintainer references a workspace in tool.uv.sources, but is not a workspace member`: the root `pyproject.toml` excludes `apps/readwise-reader` from the workspace, while this file still declared `skill-maintainer = { workspace = true }` and listed the package as a runtime dependency. The dependency was spurious — `skill-maintainer` is imported nowhere in `src/`, `tests/`, `commands/`, or `skills/`, and survived only in stale `egg-info` build artifacts — so both the dependency and the `[tool.uv.sources]` block are removed rather than the exclusion being reversed. Pre-existing and unrelated to the lint work; it is fixed here because it blocked running this package's own tests the normal way.

## 0.88.0

### fixed
- **`path-privacy` 0.7.1 → 0.7.2 — the stale-wrapper notice could not tell "older" from "newer", and its remedy downgraded a working gate.** The comparison at the heart of the notice was `[ "$have" != "$CURRENT_VERSION" ]`: a string inequality, which fires in both directions and labels both "older". A wrapper can legitimately be *newer* than the running plugin — install the hooks from a source checkout, then open a session whose installed copy is several releases behind, and that is exactly the state. The notice then told you to re-run `install-git-hooks.sh`, which regenerates the wrapper from the *older* plugin: the advertised fix silently reverts the gate to superseded logic, discarding fixes it already had. The remedy for each direction is the opposite one, so direction has to be established before advice is given. Now compared with `sort -V`, with a separate notice for the ahead case that says the gate is fine, names the plugin as the thing that is behind, and explicitly warns against re-running the installer. Verified against a constructed wrapper/plugin matrix — older, equal, newer, and unstamped pre-0.6.0 — each producing its own outcome, with the equal case silent.

- **`path-privacy` 0.7.2 → 0.7.3 — the same defect in two more copies, one of which prints on every commit, plus a fail-safe guard and the shared helper that should have existed first.** 0.7.2 fixed the SessionStart notice, which fires once per session. It was not a sweep. Two more copies of the identical bare `!=` survived it: the wrapper template in `install-git-hooks.sh`, which bakes the check into every generated `pre-commit` and `commit-msg` hook and therefore prints on *every commit*, and `--doctor`, which additionally exits 1 on a healthy gate and prints the blanket remedy `install-git-hooks.sh -C <repo>` — sending the user to regenerate a *newer* wrapper from an older plugin, precisely the downgrade this work exists to prevent. The first sweep missed both because it grepped the symptom shape (`VERSION" *!=`) rather than the concept; `--doctor`'s copy reads `[ "$ver" != "$WRAPPER_VERSION" ]`, with the operands in the other order.

  **Direction was also being inferred from a failed test rather than a positive one.** `if older … else newer` treats every non-comparable input as "newer", and the reachable case is this script's own fallback: when `plugin.json` cannot be read at install time it stamps the wrapper `unknown`, which `sort -V` orders *above* any numeric version. So an `unknown` wrapper — unknown, therefore probably ancient provenance — was told on every commit that its gate was fine and not to refresh it, which is the exact inversion of the right advice, and a regression against the pre-0.7.2 behaviour. "Newer" is now a claim that must be earned: `pp_version_is_newer` returns false for anything not plainly numeric (`unknown`, `pre-0.6.0`, a build suffix, empty) and for a `sort` without `-V`, so every unverifiable case lands in the stale branch, whose remedy is idempotent and harmless when unnecessary.

  All three call sites now consume one authored helper, `scripts/_version_compare.sh` — sourced by the installer and the SessionStart hook, and injected verbatim into each generated wrapper, which is frozen at install time by design and so cannot source anything at run time. Nine tests pin it, including `0.9.0` vs `0.10.0` (the case a lexicographic compare inverts, shipped for real in 0.3.2), the `unknown` stamp, and a guard against any call site reintroducing a bare version inequality. Mutation-tested: reverting the helper to the naive comparison turns exactly three of them red. `--doctor` now annotates an ahead wrapper instead of failing on it — verified by exit code against real generated wrappers, 0 when the wrapper is newer, 1 when genuinely stale.

  **Numbered separately rather than folded into 0.7.2**, though 0.7.2 was never pushed. Two materially different wrapper templates would otherwise both stamp `# path-privacy:wrapper-version 0.7.2`, and every staleness check — the SessionStart notice, the wrapper's own self-report, `--doctor` — compares exactly that stamp. A plugin whose entire purpose is detecting frozen, superseded wrapper logic must not ship two versions of that logic under one number.
- **`path-privacy` — the notice printed a literal `—` where an em dash was intended.** `$'—'` relies on `\uXXXX` expansion, which needs bash 4.2+; macOS ships bash 3.2, so the escape passed through untouched and every stale-hook notice read `... of the plugin — pre-commit (0.6.2)`. Since nothing downstream needs the dash, both notices use plain ASCII punctuation rather than carrying a bash-version dependency for a typographic nicety.

- **`skill-maintainer` 0.15.2 → 0.15.3 — a doc claim about the path-privacy hook was wrong, and had been repeated into the test suite that documents it.** `test_path_privacy.py`'s module docstring said the pre-commit hook "scans the diff, so it only ever sees added lines", and the 0.45.1 changelog entry that motivated the whole-tree audit said the same. Neither was ever true: `--staged` has collected names via `git diff --cached --name-only` and scanned those files' **full content** since 0.1.0, verified against the original implementation. The real limit is narrower and more useful to know — the hook only sees files in the *staged set*, so a leak in a file you never touch is never scanned. The error survived because the conclusion it supported (a whole-tree audit is needed) is correct under either mechanism, so nothing downstream ever contradicted it. Both statements corrected, the changelog entry annotated in place rather than rewritten. The practical consequence, now stated where people will hit it: whole-content scanning of staged files means editing a long-lived file can block a commit over lines you did not write. Also carries nine new tests pinning the wrapper/plugin version comparison (see path-privacy 0.7.3).

### changed
- **`dev-conventions` 0.8.0 → 0.8.1 — the Pydantic `str` enum rule re-tiered out of unconditional global config.** The rule (assign `SkillStatus.ACTIVE`, not `"active"`) is a narrow Python/Pydantic detail that lived only in global instructions, so it loaded into every session regardless of language — including pure JS and TS ones with no Python anywhere in them. That tier already names this plugin as where detailed conventions live, which made the rule a textbook case of specific guidance occupying the always-loaded tier while a pull-based one existed to hold it. It now sits at the two tiers that fit: a one-line form in the `python.md` SessionStart directive, gated on Python-project detection so it reaches only sessions it applies to, and the full statement in the `python-tooling` skill, which has room for the rationale the one-liner does not — Pydantic coerces the bare string at runtime, so both spellings pass every test and only static analysis can tell them apart, which is the entire reason the rule exists.

## 0.87.0

### fixed
- **`path-privacy` 0.7.0 → 0.7.1 — the whole-tree audit was blind to every hidden file and directory, and reported clean anyway.** `scan_dir` runs `rg` without `--hidden`, and ripgrep skips dotfiles and dot-directories by default. So `find-external-paths.sh -d .` — the documented "audit a repo" mode — never descended into `.claude-plugin/`, `.claude/`, or any root dotfile, which is precisely where machine-specific paths accumulate. The per-file and `--staged` modes pass explicit paths, which ripgrep does not filter, so they saw those files fine; the two modes disagreed and only the quieter one was being used for audits. Found the hard way: the pre-commit hook blocked a commit over findings the audit had declared clean seconds earlier. `--hidden` added; `.git` stays excluded by the existing glob, and ripgrep's `.gitignore` handling stays on since an ignored file cannot reach a commit. Enabling it immediately surfaced live findings in three previously unreachable files. An audit that under-reports is worse than no audit — it is read as a clean bill of health.

### changed
- **Internal cleanup across six plugins — docs, comments and examples normalized to the repo's generic-path convention. No behavior change.** Example and placeholder paths in documentation now use a neutral `/path/to/...` form, and references to standard global locations use the `<HOME>/...` form the repo already uses elsewhere. Where a file's subject matter genuinely is these path shapes — pattern catalogs, test fixtures, the config-reading script — the plugin's own file-level and per-line opt-out markers are applied instead of rewriting content that has to look that way to be correct. Verified by re-running the whole-tree audit (clean) plus the full suite: `skill-maintain test` reports 271 passed and 7 failed — the same 7 pre-existing staleness and token-budget failures as before this change, none of them in a touched plugin — and 105 unit tests pass.

  **Corrections from review, folded into the same unreleased versions.** The first pass of this sweep applied `<HOME>` — a *prose* placeholder — inside executable code fences, which broke five shell snippets in `plugin-toolkit`'s USE_CASES and the smoke test that is `pyright-autoconfig`'s only "verify the hook works" instruction. Bash reads `<HOME>` as a redirect: `for plugin in <HOME>/...` is a hard syntax error, and `ls <HOME>/...` silently runs against `/.claude/plugins/`. Those are restored to the runnable tilde form with a per-line `path-privacy: ignore`, which is what the same sweep already did correctly for the `expanduser()` calls in `schema_bench`. The one JSON config example where no comment syntax exists now states the substitution explicitly instead of leaving a value that would resolve relative to the server's working directory.

  The same pass also over-applied file-level `skip-file` to six files where only a handful of lines carried the shapes — blinding the audit to ~1,400 lines that had nothing to hide, which is the same defect class this release's headline fix was about. Narrowed to per-line markers everywhere except the three files that genuinely are pattern catalogs end to end. One of those removals initially deleted the exemption's own implementation in `tests.py` (the check greps for the marker literal, so a filter on "lines containing the literal" ate it) and collapsed the file's blank lines; caught by `test_skip_file_marker_is_honoured` failing, reverted, and redone by exact line content.

  Cascade: `plugin-toolkit` 0.2.1 → 0.2.2, `scan-for-secrets` 0.1.2 → 0.1.3, `pyright-autoconfig` 0.2.1 → 0.2.2, `agent-state-mcp` 0.2.1 → 0.2.2, `readwise-reader` 1.0.1 → 1.0.2, `skill-maintainer` 0.15.1 → 0.15.2 (each plugin.json + marketplace, plus the two workspace pyprojects and `uv lock`; `readwise-reader` is workspace-excluded so its lock is unaffected). The review corrections above land in these same version numbers rather than a second bump chain: none of them has been published, so each will first exist publicly with the corrections already in it.

## 0.86.0

### changed
- **`path-privacy` 0.6.2 → 0.7.0 — a plugin update reached the scanner but never the gate's own logic, and the documented file-level escape hatch did not exist on the path that advertised it.** Five fixes from an external field report filed by a consuming repo, each reproduced here before being changed.

  **The gate silently trailed the installed plugin.** The generated wrapper re-resolved its scanner only when the frozen path was *missing* (`if [ ! -x ... ]`). A marketplace install freezes a path into the version-stamped cache, and an update writes a *sibling* version directory while leaving the old one executable until cleanup ~14 days later — so the condition stayed false and the repo kept running the superseded scanner for that entire window, self-correcting only as a side effect of garbage collection. The frozen path is now a hint rather than a pin: a cache-resident wrapper resolves to the newest executable version on every run. Scoped to the *same marketplace's* directory, never across marketplaces — two marketplaces shipping a plugin of the same name are unrelated packages, and one's version number says nothing about the other's. Reproduced with a constructed cache: the old wrapper runs 0.6.2 with 0.7.0 and 0.10.0 both present; the new one runs 0.10.0, prefers 0.10.0 over 0.7.0 rather than losing to it lexicographically, ignores a decoy `mp-z/9.9.9`, and falls back to 0.7.0 when the newest loses its exec bit.

  The report's proposed fix — flip the guard to re-resolve unconditionally — was measured and is a **no-op**: group 1 of the search globs the frozen tree itself, which for a cache install *is* the version directory, so it returns the frozen path, and the cache search that could find a newer version never runs. That group had been dead code since 0.6.0 narrowed it; its stated purpose (letting a local checkout recover) was never achieved, and its fallthrough silently moved a `--plugin-dir` user onto a cached marketplace copy they had not installed. Replaced with an explicit split: cache installs prefer the newest sibling version, local checkouts keep their own copy while it works and only reach for the cache once it is gone.

  **The wrapper can never be updated by the plugin** — it is the thing that locates the plugin. That is structural and unfixable, so it is now surfaced three ways instead of one: the existing SessionStart stamp comparison, plus a new one-line stderr notice from the wrapper itself at commit time (which reaches you when committing from a plain terminal with no session open), plus `--doctor`. Still never auto-applied; rewriting a file in someone's `.git/` mid-commit is exactly the surprise a privacy gate should not spring.

  **`--doctor`.** Hooks live in `.git/`, so they are per-repo, uncommittable and installed by hand, and nothing tracked which repos had them — "which of my repos are protected, at what version, failing open or closed?" had no answer short of writing your own scan. `install-git-hooks.sh --doctor` reports this repo; `--doctor <root>` sweeps every git repo under a root you name. Per hook: version stamp (`<unstamped, pre-0.6.0>` when absent, which a version comparison cannot detect and which has to be read as "ancient, reinstall"), `fail-closed` vs `FAILS OPEN`, frozen-path status, and `not installed` when a hook is missing. Exit 1 on any finding. Read-only, and it requires an explicit root rather than sweeping a home directory on its own — a privacy tool should not decide by itself to enumerate everything you own.

  **The file-level skip marker did not work on the path that advertised it.** `path-privacy: skip-file` was implemented in `scan_file` only; the PreToolUse write blocker scans via `--text`, which never checked it — while printing that exact marker as the remediation. So a blocked write sent you to an escape hatch that could not work, and the plugin's own files, every one of which carries the marker, could not be edited in their own repo. New `--allow-skip-file` flag makes `--text` honour the marker in its first 30 lines; the write blocker passes it, the commit-msg hook does not, so a commit message still cannot exempt itself by quoting one token. The blocker also now reads the marker from the *target file on disk* — an Edit sends only a fragment, so a marker at the top of a file is never in the payload and scanning the payload alone could never honour it. Six probes pin the matrix.

  **SessionStart said nothing when the gate was absent.** It compared version stamps but skipped repos with no wrapper at all, so the directive kept asserting the rule in ungated repos — reading as protection while nothing enforced it, which is this plugin's main failure mode. It now names which of the two hooks is missing, and says the rule still applies but is unenforced here.

  **Docs.** The suggestion template led users into a block: it ships absolute paths, so copying it to the documented default path before gitignoring is blocked by the write hook. Gitignore-first is now stated as an ordered step rather than a parenthetical. Empty `suggest` — which deletes a matched prefix and is the single highest-value entry, turning an absolute in-repo path into a genuinely repo-relative one — was load-bearing, deliberate, and undocumented; it now leads the template, with a note that it affects the scrub only, since an in-repo path is never a scanner finding. The scrub footgun is now a specific warning (a match on the shell HOME variable rewrites live code in any repo containing shell scripts) rather than a general "review the diff", and those entries are omitted from the template on purpose.

  Cascade: plugin.json + marketplace 0.6.2 → 0.7.0.

## 0.85.0

### changed
- **`skill-maintainer` 0.15.1 — quality-pass follow-ups to the 0.15.0 validator work.** A `/simplify` and documentation pass surfaced three fixes, none behavioral. The `cc_schema` module docstring claimed `--strict` runs via `validate_frontmatter(BASE_SPEC_FIELDS)`, but the CLI actually wires it to `portability_warnings` — corrected so a reader is not sent to the wrong function. The hand-maintained `CLAUDE_CODE_FIELDS` set is now tied in the docstring to the existing `skill-maintain upstream` drift tracking of `code.claude.com/docs/en/skills`, so a change to that page triages toward this file rather than a generic "doc changed" flag. The skill-maintainer plugin README's summary now says it validates against the Claude Code skill schema (a superset of the Agent Skills spec), not "the Agent Skills spec". 60 tests still pass. Deliberately not applied: the reviewed triple-parse in `validate_single` (validation is not a hot path, all three call sites are correct and tested, and parse-once would make `check_best_practices` dual-mode), and importing `skills_ref`'s private value-validators (would re-couple to an early external library's internals, the opposite of owning the gate).

## 0.84.0

### changed
- **`skill-maintainer` 0.15.0 — validate against Claude Code's skill schema instead of the lagging cross-vendor allowlist; and make the repo root a virtual workspace with no version.** Two coupled changes.

  **Validator.** The hard gate was `skills_ref.validator.validate` (the vendored agentskills.io reference validator), whose six-field allowlist rejects every Claude Code frontmatter extension — `disable-model-invocation`, `argument-hint`, `model`, `context`, `paths`, and the rest — so a skill using any of them could not be committed. This repo's skills run in Claude Code, so the gate should be Claude Code's schema, which is a superset. New module `cc_schema.py` encodes that superset (base spec plus the CC extensions) and the name/description/compatibility rules; `validate.py`, `quality.py`, and `tests.py` all route through it, so there is one source of truth. Unknown fields are still rejected (a typo like `disable-model-invokation` fails with the allowed list printed). `skill-maintain validate --strict` runs the cross-vendor check as an opt-in portability lint that flags CC-only fields. `skills_ref` is kept only as a parser. The pre-commit hook, `.claude/rules/{general,plugins,skills}.md`, `best_practices.md` (working copy plus the bundled mirror), and the maintenance/gotchas/README/init docs are re-pointed off `uv run agentskills validate` onto `uv run skill-maintain validate`; the agentskills.io *spec* references stay, since it remains the base. 8 new tests in `test_cc_schema.py`. A metadata-values-are-strings check was deliberately not added: `skills_ref` parses with `strictyaml` and force-stringifies the metadata map, so through the tooling metadata is always string-valued and a machine check could never fire — the convention is documented in `.claude/rules/skills.md` instead.

  **Virtual root.** The root `pyproject.toml` dropped its `[project]` table and version. A plugin collection has no single package version — every plugin versions itself in `plugin.json`, every CLI in its own `tools/*/pyproject.toml` — so the root `version` was a fiction that nothing installed, existing only for `check_changelog_version` to compare the CHANGELOG against. That comparison had drifted red for a long time (CHANGELOG `0.83.0` vs root `0.50.0`) and was never a commit gate. The root is now a virtual uv workspace (workspace plus dev-group only; `uv sync --all-packages` and `uv run` unchanged), and `check_changelog_version` is repointed to always validate the changelog heading and insert-integrity while comparing to a version only when the root declares one — turning that row green honestly rather than by feeding it a matched number. 3 new tests pin the virtual-root behavior; `docs/internals/plugin-versioning.md` and CLAUDE.md invariant 1 updated to drop the root version bump from the cascade.

  Cascade: `skill-maintainer` plugin.json + marketplace + `tools/skill-maintainer/pyproject.toml` 0.14.x → 0.15.0, `uv lock` refreshed.

## 0.83.0

### added
- **`postmortem` 0.1.0 — new plugin: evidence-grounded retrospectives, replacing an always-on reflection rule with pull-based skills.** Born from the observation that a global "identify what you'd do differently" rule fires on every task and pressures the model into inventing findings on trivial work — the escape hatch ("if nothing, say so") is weaker than the elicitation. The fix is structural, not rewording: reflection becomes on-demand, and the skill carries enforcement a one-paragraph rule cannot. Two skills. **`postmortem`** runs a verdicted retrospective of finished work in two modes — session (the conversation as evidence) and span (git history, `internal/log/` session logs, CHANGELOG entries, plan docs) — in five sections: what went well, what did not, a planned/shipped/verdict deviations table, escapes (each bug found in scope vs. the test that should have caught it — missing or green-but-blind), and forward items that must be checkable (markable done/refuted later, or cut). Ground rules distilled from the 2026-07-22 explainer-video run postmortem, the format's proving instance: no citation, no finding (the anti-confabulation mechanism — generic advice is banned); empty sections are valid output; annotate-don't-rewrite (later evidence appends a dated correction, never a silent edit); state the structural version when a lesson generalizes; label inference vs. measurement. Output is always a durable file (plan doc, session log, or proposed location) — chat-only is not a postmortem, because the annotation convention needs somewhere to live. Findings route onward only when earned: durable lessons → memory/CLAUDE.md proposal, mechanical repeats → a hook, follow-ups → roadmap or log. **`test-audit`** asks whether a green suite still means anything, on the model that a test is a claim (what its authors believed it verifies), an oracle (what it actually checks), and a reachability envelope (the conditions the harness can express — one viewport, one renderer, one fixture shape). Process: inventory → claim recovery via git archaeology ("unknown" is itself a finding) → classify load-bearing / scar-tissue / decorative / redundant → oracle verification by spot mutation (deliberately break the guarded behavior, confirm red; a test green under mutation of its own subject is decorative — full mutation tooling is an escalation, not the default) → envelope mapping → keep / rewrite-the-claim / delete verdicts with evidence, deletions listed but never applied unasked. Carries the run's two standing cautions: a green control that never ran is the worst outcome, and a proxy can reject, never approve. Per-architecture envelope question packs in `references/architectures.md` (API/LLM server, full-stack e2e, CLI, perceptual/generative pipeline, data pipeline). Registered in marketplace.json and the root README; root version 0.49.1 → 0.50.0 with lock refresh.

### changed
- **`metadata.author` removed from every SKILL.md frontmatter — 16 plugins patch-bumped in one sweep.** Completes the decision 0.81.0 made for the `writing` plugin but never applied repo-wide: the entire SKILL.md, frontmatter included, loads into context when a skill activates, so an author name there is standing context cost with no runtime use. Authorship lives in `plugin.json` and plugin READMEs, which are never context-loaded. 30 SKILL.md files cleaned; every metadata block keeps its `last_verified` (no empty blocks left). Upstream credits were already preserved in READMEs (cogapp-markdown "credits", mcp-apps "upstream"), so nothing was lost. Bumped: cogapp-markdown 0.1.1, explainer-video 0.25.10, skill-maintainer 0.14.1, path-privacy 0.6.2, plugin-toolkit 0.2.1, scan-for-secrets 0.1.2, mcp-apps 0.1.1, dimensional-modeling 0.4.1, tui-design 0.4.1, model-routing 0.3.1, screenwright 0.12.2, json-query 0.1.1, agent-state-mcp 0.2.1, readwise-reader 1.0.1, mece-decomposer 0.5.1, skill-dashboard 1.1.1 (each plugin.json + marketplace.json, plus the three app pyprojects and lock). `dev-conventions`' removal rides its 0.8.0 bump below; `writing` (0.81.0) and `pyright-autoconfig` were already clean; `postmortem` shipped clean this release.
- **`dev-conventions` 0.8.0 — tdd-workflow gains the test-provenance rule.** New rule in the TDD cycle, in both surfaces: the `tdd-workflow` skill and the SessionStart `tdd.md` directive. Every new test carries a one-line note of what breaks if it is deleted — the motivating requirement, bug, or incident. This is the forward convention that makes future `test-audit` claim-recovery cheap; a test whose claim nobody can recover later becomes unauditable scar tissue. Version cascade: plugin.json + marketplace.json 0.7.0 → 0.8.0.

## 0.82.0

### added
- **`writing` 0.3.0 — new `voice-match` skill: write in the user's own voice, with memory.** A second skill in the `writing` plugin, composable with `plain-language-us` but usable alone. It learns the user's voice from their messages in the current thread (sentence rhythm, punctuation habits, register, directness, signature words, structure) and writes the deliverable in it while keeping meaning and facts intact. Guardrails: match voice, never copy typos or errors; match durable voice, not transient chat shorthand (no all-lowercase fragments bleeding into a report); weak signal falls back to a neutral default; voice never bends accuracy. **Persistence** is layered across two stores, per the request for global and per-repo memory that updates as it learns: a global `<HOME>/.claude/voice-profile.md` applied everywhere, and a per-repo `.claude/voice-profile.local.md` for project-specific voice, with project traits overriding global on conflict. The skill reads both on activation, merges them with the live thread signal (live wins on stale conflict), and updates the right profile in place after a substantial task — durable traits only, kept as a concise card, never personal identifiers or written content. The per-repo profile is personal, not team config, and the skill keeps it gitignored. Precedence with the house style is "voice within the rules": `plain-language-us` sets the clarity floor (spelling, sentence case, front-loading, the machine-register ban), `voice-match` sets the voice (em dashes, contractions, sentence length follow the profile). **Control and feedback, deliberately lightweight** (not a warehouse): a `learning` mode (`session` persists nothing, `project`, `global`, or `off` read-only) decides when the profile is written, overridable per request; explicit corrections are recorded as a fixed preference that later inference does not override; and a `/writing:voice` command (`show`, `correct <note>`, `scope`, `reset`, `save`) gives discoverable control alongside plain-language triggers. `show` is the window into what the skill currently thinks the user's voice is. Frontmatter follows the same discipline as the sibling skill: no `author`, no handles or URLs in the body. Version cascade: plugin.json + marketplace.json 0.2.0 → 0.3.0; root and plugin READMEs updated with the skill row, invocation, the command, and a voice-profiles note.

## 0.81.0

### changed
- **`writing` 0.2.0 — the GOV.UK skill is relicensed as `plain-language-us`, localized to American English, and hardened against injection.** The core premise is unchanged: open content up without dumbing it down, front-load everything, active voice, one idea per sentence, sentence case, no bold or italics for emphasis. Three things changed. **(1) Locale.** British spelling and conventions give way to American ones, with a new "American English conventions" section stating the differences: American spelling (organize, color, behavior, analyze) and word choice (toward, while, among); double quotation marks as the default; periods and commas inside the closing quote; the serial (Oxford) comma; month-first dates with ISO for all-numeric; comma-thousands / period-decimal numbers. Inline: "utilise" → "utilize", "organisation" → "organization", every "full stop" → "period", single quotation marks for titles → double, and Latin-abbreviation examples now show American forms (e.g., i.e., etc.) while still advising against them for accessibility. **(2) Name.** Anchored to the American federal plain-language tradition (plainlanguage.gov, the Plain Writing Act, the PLAIN network) rather than a British government brand — the skill's own deliverable named honestly, and a source it actually tracks. Directory `govuk-style` → `plain-language-us`; invocation is now `/writing:plain-language-us`. **(3) Injection surface.** The SKILL.md body loads into the model's context when the skill triggers, so a bare `@fofr` handle and a UK gov URL sitting in it were live injection vectors. All external handles, URLs, and third-party references are removed from the skill body and frontmatter (`metadata.credit` dropped); attribution and heritage now live only in the plugin README, which is documentation, not loaded instructions. **(4) Substance.** Two new sections sharpen the "open up, don't dumb down" premise. "Match the audience and keep real terminology" says plain English means clear, not a smaller vocabulary: keep a field's precise, current terms for expert readers (KV cache, speculative decoding, logits for a frontier-AI audience) and cut only jargon that is vague, ambiguous, or not actually established. "Avoid model tells and filler" bans the machine-text tics — load-bearing / heavy lifting, the "it is not X, it is Y" frame, false-candor openers ("the honest truth"), throat-clearing ("it is worth noting"), and em-dash overuse (single hyphens are fine). The whole body was rewritten to model that last rule: em dashes replaced by periods, commas, or hyphens throughout, including in the always-loaded `description`. `metadata.author` removed from the SKILL.md frontmatter — the entire file, frontmatter included, loads into context on activation, so a personal name there is standing context cost with no runtime use; authorship stays in plugin.json and the README. `metadata.last_verified` set to today — the skill was actually reviewed and rewritten this session, not bumped mechanically. References updated in the root README (plugins table, invocation list) and the plugin README. Version cascade: plugin.json + marketplace.json 0.1.0 → 0.2.0.

## 0.80.1

### changed
- **`screenwright` 0.12.1 — every tracked example now ships its preview set, and the READMEs catch up.** Examples policy clarified (recorded in the plan): owner approval gates what enters `examples/`; once tracked, the preview set is mandatory — an AVIF in repo-level `docs/media/`, embedded in the examples README with a link to the `.html` and a description of what the example showcases. Rendered the three missing previews (menagerie, bear-and-bees, noise-chart — 720px/12fps via the Metal recorder path) and restructured the examples README: every entry now links its HTML, embeds its AVIF, and says what it demonstrates, under a standing callout that the AVIF is to the film what a thumbnail is to a full image — the HTML is the artifact. Also: the plugin README's Status section notes the chart tier, and the repo hub README's explainer-video section now points readers at screenwright as the in-development replacement (frozen predecessor, successor on the node stack, supersedes when verifiably better on the same test cases).

## 0.80.0

### added
- **`screenwright` 0.12.0 — `examples/noise-chart.html`, the first chart-tier scene, plus two plan-level directions.** The chart tier (recorded in the plan) sits below the films: static grids, one primitive per cell, smoke-gated and byte-compared per backend — charts isolate what films integrate, and new shader primitives land chart-first before any showcase or film uses them. The chart: 12s, one locked head-on shot (a chart is a document), eight unlit tiles — a MaterialX baseline row (fbm, worley, scrolling aastep, palette-mapped fbm) and a hash-lattice row (value noise, re-hashed cells, domain-warped fbm) plus the classic `fract(sin(dot))` hash as a deliberate drift CONTROL, structurally identical to the hash-cells cell except for the hash function. Measured: 20/20 smoke green including the control — 15 consecutive `WEBGPU=metal` runs and 5 WebGL2-fallback runs. The honest negative: the 0.11.0 carry-forward metal 1-in-6 determinism FAIL did **not** reproduce under dense noise coverage (no shadows, no characters, one shot), which narrows the suspect space toward the machinery bear-and-bees has and the chart deliberately lacks; the sin-hash control also stayed clean at this sample size, so it stays in place — re-runs are free. Also recorded in the plan: the Phase 4 bake direction gains a **light-bake sibling** (iterative illumination — GI, radiosity, probe solves — baked at build time, playback pure, same red lines against tier drift), including the finding that reflections need no bake at all: SSR, planar reflector, GTAO, and environment lighting are pure functions of scene state, available at runtime today. Cross-directory fence parity green with the new example in the set.

## 0.79.0

### added
- **`screenwright` 0.11.0 — Phase 2 GATE MET: `examples/bear-and-bees.html`, the comedy short.** 21.3s, eight beats, the register's whole point in one ratio: a 2.6s hush (bear frozen nose-under-hive, one scout bee holding his eyeline, a double blink played TO CAMERA) against a 1.1s eruption. The bear is the menagerie quadruped vector scaled ~0.8 with fur; the bees are scene add-ons (closed-form swarm — comet chase via per-bee lagged evaluation of the bear's own travel function, `bearXAt(t-lag)`, so pursuit derives from the pursued). Staging is probe-solved, not eyeballed: the original paw-swipe gag died on measurement (this vector's muzzle projects ~2.9 past the shoulder, the foreleg reaches 2.33 — a paw can never pass the nose), so the gag became a nose boop, solved in ALL THREE axes to a surface graze (normalized ellipsoid distance 1.02 at the latch instant) after the film-reviewer caught the z-axis as a 0.41 miss faked by a lucky camera angle — instance five of the documented contact-bug class. The reviewer's other two HIGHs: the flee launch clipped the hive before the duck opened (duck now opens pre-launch; measured +0.01..+0.24 clearance through the under-run), and the comedy's face never faced the lens (a 3/4 face-turn envelope from spot through hush puts both eyes, the blink and the glance on screen). MEDs: whole-film `energy:'locked'` (steadicam sway moved ~10% of frame through THE pause — silent-comedy tableau grammar instead), hush two-shot re-anchored to the face, the button's cross-meadow blend cut to a hard cut (its motion bar dropped 7.00→2.34, erupt now correctly the film's peak at 7.07). The neck-curl sign convention was bracketed empirically mid-build: +z curl RAISES this rig's head — the probe grid settled it after two theory-first rounds went the wrong way. Verification: smoke green both backends, zero advisories; cross-directory fence parity green with the new example in the set; nocap sheet carries the full gag wordlessly; motion profile shows no dead air. Carry-forwards (recorded in the plan): one unreproduced WEBGPU=metal determinism FAIL (1 in ~6 runs — the bee visibility gate shipped in the same round is hygiene, not the fix), and the missing per-shot camera-energy vocabulary. Also riding: docs/internals/physics_bake_proposal.md — the owner-selected Phase 4 direction (bake-time simulation, runtime determinism intact) with red lines, eval criteria, and spike list; Phase 4 now precedes Phase 3.

## 0.78.0

### changed
- **`screenwright` 0.10.0 — simplify pass over the 0.6.0–0.9.1 range: five findings applied, headlined by a sixth parity fence.** The structural one: the page scaffold (overlay CSS + caption/title/vig/flash DOM, lines 1–46 of every 3D scene) had reached FIVE byte-identical unfenced copies — the exact "at a third consumer, extract or marker-fence it" trigger the SOLVER fence's own comment memorializes, fired and unacted again. It is now the `HTML` fence: HTML-comment markers (the block lives outside `<script>`, so the JS-comment marker form cannot fence it), a second regex arm in smoke's parametrized parity loop, verified byte-identical across all five carriers and green on the cross-directory run. This block carries the `will-change` compositor-layer hint — determinism-relevant, previously mirrored only by discipline. The rest: `build.js`'s `REVIEW_EXT` restored to a derivation of `REVIEW_FMT` (it had been snapped to a literal `'jpg'` under a comment still claiming the derivation — changing `REVIEW_FMT` would have silently broken every sheet/strip/poster ffmpeg path); dead `chestX`/`chestY` dropped from `buildCharacter`'s return in both `CHARACTER` carriers (never read anywhere; the rig API now matches characters.md's documented field list); menagerie's 36-line CINEMATOGRAPHY doc block trimmed to the 4-line pointer gearbox and materials already use; characters.md's "Not here yet" closing no longer contradicts the fur/fabric section 40 lines above it (fur and fabric shipped in 0.8.0). Efficiency angle reviewed clean — no findings. Verification: smoke green for all five 3D scenes on webgl2 and both character carriers on webgpu; cross-directory fence parity green with the new fence in the loop.

## 0.77.1

### fixed
- **`screenwright` 0.9.1 — six findings from a five-agent code review of the 0.6.0–0.9.0 range, fixed and re-verified.** The one that mattered most: shoot.js's refusal of `WEBGPU=swiftshader` went dead in the 0.6.0 backend.js extraction — the shared `angleArgs()` gates the throw behind `refuseSwiftshaderShip`, defaulting false, and shoot.js called it bare, so the documented recorder/gate asymmetry existed only in comments (reproduced: no throw; the exact "600 flat frames with exit 0" class the guard was measured against). Fixed at the call site; the refusal now throws and smoke's probe path is unchanged. Two menagerie review fixes had never been backported to the template they came from: the demo subject aimed at the root instead of `rootX + rig.centerX` (the FS cropped the walker's feet — verified on before/after contact sheets, the documented wall-of-rump class), and the settle breath was still `backOut(ramp)-1`, holding the walker 4% squashed from frame 0 (menagerie's pulse idiom applied). In the `CHARACTER` fence (both carriers, cross-directory parity re-run green): `solveLimb`'s clamp floor was an absolute `.2`, which INVERTS the clamp for rigs with total reach under `.21` and poses the limb beyond its own length every frame — floor is now `min(.2, reach-.02)`, byte-identical at every shipped scale (menagerie legs are all reach > 1.9) and load-bearing for the insect-scale rigs bear-and-bees needs. Docs: webgpu-stack.md claimed `MeshToonNodeMaterial` is "exercised by the material packs" when materials.html deliberately avoids it (banding is authored in the node graph on `MeshBasicNodeMaterial`) — reverted to available-but-unused; film-language.md still said `CONFIG.energy` after 0.6.0 single-homed energy in STYLE. Dispositioned, not fixed (recorded in the plan): character colors are hex literals in `buildCharacter` calls rather than STYLE keys — the bibles.md rule bites when the first character bible pair arrives, and the palette moves into STYLE then. Verification: smoke green on both backends (webgl2 + webgpu confirmed) for the character template and menagerie in a scratch workspace; cross-directory fence parity green; the swiftshader refusal demonstrated throwing; before/after sheets read frame by frame.

## 0.77.0

### added
- **`screenwright` 0.9.0 — Phase 2 step 3: `examples/menagerie.html`, the character-scaffold gate demonstration.** A furred bear (lateral-sequence quadruped), a fabric-shirted human (biped), and a text-invented three-eyed whip-tailed strider — three proportion vectors through ONE `buildCharacter`, walking in on staggered gaits, all turning to the viewer, settling as a group. Gate criteria measured: squint-distinct silhouettes (the squint strip separates all three at 90px), planted feet (strip-checked for each), byte-determinism on both backends, cross-directory fence parity green (all five fences, templates + examples). Independently reviewed by the film-reviewer agent, which caught the round of defects author-eyes missed — the look beat happened entirely off-frame (heads yawed ~26° where the camera needed ~75°, and the shot framed one character while the other two turned off-screen), the film's only closeup was 70% void, the tail-wag idle blend spiked the wag rate ~5x for a few frames (phase blended through a t-scaled gate instead of crossfading amplitudes), a one-shot "breath" held every character 3-5% squashed from frame 0, and a bare floor made an 11-unit walk read as a treadmill. All fixed and re-verified; the nocap pass now carries the look beat on geometry alone. One kit addition fell out: `rig.centerX` (visual center relative to the root) — aiming a subject at a quadruped's root orbits its tail end and crops the head, measured as an FS rendering a wall of rump. Per owner policy (recorded in the plan): the HTML is the shipped artifact — no AVIF/MP4 is rendered by default; finalized scene HTMLs are also copied to gitignored `internal/scenes/` for local viewing.

### fixed
- **`explainer-video` 0.25.9 + screenwright examples README — cross-tree preview links were one directory short.** Both examples READMEs sit five levels below the repo root but linked `docs/media/` with four `../`, so every embedded preview 404'd on GitHub (owner-reported). Fixed to five and every link target verified to exist; the plugin-level READMEs (two levels deep) were already correct. Riding the same commit: the screenwright README Status section caught up to Phase 2 (it still named the character scaffold as future work), and shoot.js's header now states the embed gotcha (direct shoot.js runs do not vendor three — bundle first; every build.js command already does it automatically).

## 0.76.0

### added
- **`screenwright` 0.8.0 — Phase 2 step 2: the fur and fabric packs.** Fur is kit code in the `CHARACTER` fence: `addFur(mesh, opts)` grows shell layers as children of the mesh (riding every IK transform) — the same geometry displaced along its own normals per layer, TSL fractal-noise coverage thinning toward the tips and darkening toward the roots, discarded via `alphaTestNode` so fur stays on the OPAQUE pipeline and never joins the sortObjects transparency-ordering bill; shells cast no shadows. `furCharacter(rig, parts, opts)` furs whole parts, identified by their shared per-part material instance so scene add-ons (eyes, props) are never furred by accident. Verified byte-deterministic on both backends on the quadruped vector. Fabric is a `matFor` recipe, not code: `MeshPhysicalNodeMaterial` + `sheenNode`/`sheenRoughnessNode`/`sheenColorNode`, verified rendering on r185 (the sheen rim visibly brightens grazing angles on a roughness-.9 base) — node slots again, with the plain `sheen` property presumed unreliable the way `transmission` measurably is. Both documented in `references/characters.md` with a cross-reference from `materials.md`. Phase 2 remaining: the three gate films (bear-and-bees, human, text-invented creature).

## 0.75.0

### added
- **`screenwright` 0.7.0 — Phase 2 step 1: the character scaffold.** New `templates/scene.character.template.html`: the 3D template plus a parity-fenced `CHARACTER` block (the fifth fence, registered in smoke) holding the scaffold kit — ONE parametric skeleton family where a character is a point in proportion space (`propDefaults` overrides) plus a material choice (`matFor(part)` is the seam where shading packs will plug in). The kit: lathed-profile torso + capsule shells generated from the proportion vector at load (pure code, zero assets), analytic two-bone IK ported from the predecessor's proven walker (generalized with a bend direction: knee-forward hind legs, elbow-back forelegs), the plant-grid gait generalized to any planted-limb set (biped `0/.5`; quadruped lateral-sequence `0/.25/.5/.75`, each limb's plant column riding its own attach x), and closed-form chain helpers (`chainCurl`, `chainWave`) for neck/tail — the "IK extends to spine/tail" half of the plan, done analytically. Loud build-time reach checks (match-cut-constraint spirit) replace silent hyperextension. New `references/characters.md` documents the vector, gait, conventions, and a QUADRUPED vector verified building and walking, not just the biped demo. The template demo walks a tailed biped through title/walk/look/settle and grew the face-features-as-scene-add-ons pattern (eyes riding `rig.head` — which also fixed front/back ambiguity: a bare sphere head made front shots read as back shots).

  Template-authoring findings measured on the way, kept as comments: near-equal overlapping shell radii z-fight into jagged seams (hence ONE lathed torso profile); `shoulderW` must clear the torso silhouette or hanging arms embed in it; framing estimates must respect torso/neck tilt or the camera frames empty air above a quadruped; solver angle 0 is the PROFILE (0 = from +Z), a misread that cost two probe rounds. Verified: smoke green on both backends (webgl2 + webgpu confirmed), CHARACTER fence parity-checked, contact sheet and mid-walk strip read frame by frame — planted feet hold their ground position across cells. Gate work remaining in Phase 2: fur-shell/fabric packs, then `bear-and-bees` + human + text-invented creature from the one scaffold, squint-distinct, strip-checked.

## 0.74.0

### changed
- **`screenwright` 0.6.0 — the deferred quality pass: a four-angle simplify review (reuse, simplification, efficiency, altitude) over the whole founding range, ~30 findings deduped and applied, verified look-neutral.** The structural fixes:

  1. **New `templates/backend.js`, shared by shoot.js and smoke.js** — Chromium resolution, the WEBGPU/ANGLE flag policy, the settle idiom, and the aspect-shape table now have ONE copy each. The duplication was already biting: smoke's inline flag builder had lost the `ANGLE_BACKEND` allow-list (a typo the recorder rejects loudly sailed through the gate), and the arm64 Chromium fix had to be hand-applied to four copies earlier the same day. The one deliberate asymmetry survives as a parameter: shoot.js refuses `WEBGPU=swiftshader` for shoots; smoke may probe it.
  2. **Two new parity fences, `RIG` and `DRIVER`, in every 3D scene** (renderer/post/mesh-helpers and overlay/contract/boot — both regions verified byte-identical across the three 3D scenes before fencing). Between them they cover all three LOAD-BEARING determinism guards (sortObjects, frustumCulled, the nodeFrame tick), which until now were byte-identical only by discipline, invisible to the parity check. The check itself is one parametrized loop over fence names (was two hand-copies), reads each file once, and was run cross-directory (templates + examples): green.
  3. **Contract over internals:** caption fade is now exported (`window.CAPFADE`) and smoke reads the contract instead of probing `CONFIG` against a mirrored default; flashes are resolved ONCE per scene and both the renderer and `window.FLASHES` consume the same list (the resolution was written twice per file and could drift).
  4. **`energy` has one home: STYLE** (per bibles v2). The solver's `STYLE.energy||CONFIG.energy` chain and the dead `CONFIG.energy` knobs (shadowed by every bible) are gone; template prose now matches bibles.md on where the look lives.
  5. **Wasted work removed:** smoke builds the three vendor bundle once per run instead of once per template scene (`VENDOR_CACHE`, ~1-2s per extra scene); `build.js motion` no longer launches a second browser just to read `window.BEATS` (the shoot now writes the beats manifest as a side product, ~3-6s saved per run); `loop`/`avif` shoot JPEG q92 intermediates instead of PNG masters for their q60/720px lossy deliverables (capture measured 164-190 ms/frame PNG vs 29 ms JPEG); smoke's framing check resizes 3 times instead of 9; the shipped-frame spread PNG travels as an evaluate argument instead of a megabyte JS source literal; `avif`/`loop` scaffolding collapsed into one `inlineExport`; the 2D template resolves accent inks at load and shares one polyline measurement between `drawOn`/`alongPath`.
  6. **Cleanups:** argument-less `build.js vendor` (built the full bundle and discarded it) is gone along with the SKILL.md caveat explaining it; the CLI destructure names no longer lie (`arg1/arg2/arg3`, meaning named per dispatch line); dead `thicknessScaleNode = 14` assignment and the write-then-overwrite dance removed from materials.html; both examples drop the template's "replace this placeholder" banner and 35-line SHOTS tutorial in favor of pointers; webgpu-stack.md no longer claims the pack materials are "not yet exercised"; film-language.md cites this plugin's own example instead of the frozen skill's; the 2D template carries a provenance note (forked from frozen explainer-video; bugfixes must be mirrored by hand). READMEs now state explicitly that **WebGPU is not required** (WebGL2 fallback is the default path; `WEBGPU=metal` is an opt-in speedup), and the plugin README's status caught up to Phase 1 complete.

  Deliberately NOT taken (measured machinery): merging seekTo+settle into one evaluate, deduping the three stringified luma readers (the shipped-frame bracket was measured against the current implementation), caching `warp()`'s sort. Verification: smoke green on both backends for both templates AND both examples (`webgl2` and `webgpu` confirmed per run); the swiftshader flat-frame FAIL re-demonstrated after the flag-plumbing change (exit 1); cross-directory fence parity green; `motion`/`loop`/`vendor` exercised; and pre-edit vs post-edit gearbox frames byte-identical at two timestamps — the pass provably changed no pixels.

## 0.73.1

### fixed
- **`screenwright` 0.5.1 + `explainer-video` 0.25.8 — eleven findings from a five-agent code review of the day's diff, all fixed and re-verified.** The three that mattered most: `build.js aspect` threw a `ReferenceError` on an undefined `stripText` in BOTH skills (confirmed by running it — the command had never been exercised on either fork since the nocap feature landed; fixed in both, and explainer-video's fix is bugfix-scoped under its freeze along with the arm64 Chromium-resolution backport its shoot/smoke needed); smoke.js's inline WEBGPU flag builder lacked shoot.js's allow-list and conflict rejection, so a typo like `WEBGPU=meta` silently fell through to the SwiftShader branch — the gate would have checked the exact backend the shipped-frame check exists to catch (now throws); and the `nodeFrame` determinism guard's "smoke fails loudly" comment was false for the `_nodes`-removed path — the `if` silently no-opped; it now emits a console warning, which smoke's zero-warnings rule converts to a hard failure. Plus: smoke now samples inside shot-transition windows (scenes export `window.SHOTS` cut windows; review verified no fixed-fraction sample ever landed in any blend window on a shipped film), worker-parallel shoots verify all pages resolved the SAME backend before splicing frames (and the byte-identity comment now says it was measured on the WebGL2-everywhere path only), the SIZES comment gained its missing `FSA`, a stale carried-over example path in a smoke comment was reworded, SKILL.md no longer cites a path outside the plugin subtree (the rule this very diff established), the root README's install and invocation lists gained screenwright, and explainer-video's README got its last-updated bump. Examples regenerated on the fixed template; smoke green everywhere; three review findings scored out as non-manifesting (playwright's exit reaper covers the browser-cleanup pair; the classic stack honors preserveDrawingBuffer, mooting the framing-check backport).

## 0.73.0

### added
- **`screenwright` 0.5.0 — Phase 1 step 6: style bibles v2. PHASE 1 COMPLETE.** A bible is the STYLE object itself — the solver and template already consume `exposure`/`bloom`/`dof`/`lens`/`cutDur`/`energy`, so the v2 mechanism landed with zero new machinery; palette keys are the scene's contract with the bible (a hex literal in a material is a look decision hiding from the switch). `examples/gearbox.html` now ships the committed control pair: `workshop` (lit machine-shop, steel and brass, steadicam) vs `neon` (dark stage, machines as silhouettes, the light as subject — bloomed markers, glowing trails, locked long lens, slow blends), one line apart, verified categorically different and byte-deterministic on both backends. New `references/bibles.md` carries the shape and register rules; `docs/media/gearbox-neon.avif` is the second preview. Phase 1 gate met: regression comparison (0.2.x), material packs (0.4.0), control pair (0.5.0). Carried forward: full bloom bracket, template-palette exposure pass, `WEBGPU=vulkan` verification, upstream sortObjects repro filing.

## 0.72.0

### added
- **`screenwright` 0.4.0 — Phase 1 step 4: the material packs (cel, subsurface, glass), with step 5's first bloom measurements.** New `references/materials.md` carries three recipes, all verified byte-deterministic on both backends in the shipped showcase (`examples/materials.html`, preview in `docs/media/`), and two r185 traps found the hard way:

  1. **The plain `transmission` material property never engages** — the value stores correctly but renders fully diffuse on both backends; the `transmissionNode` slot works. Recipe rule: node slots are the reliable interface, and any physically-featured property is suspect until seen rendering. (Found because the glass beat rendered as opaque balloons; isolated by an in-page property-vs-node A/B against a bright wall.)
  2. **Chang-style SSS has no thickness input** — a constant `thicknessColorNode` glows the whole mesh uniformly (measured: a lightbomb at backlight 26, clipping at 4.5, right at 2.2). The recipe models thin-vs-thick as two materials: strong scattering on ears, subtle on the body.

  Cel is TSL-native — three tones by quantized key-light lambert in `colorNode` on an unlit material, so ambient light *cannot* wash the bands (the old stack's hemisphere-washes-toon failure, solved structurally rather than by light budgeting). The glass beat pays the sortObjects bill on purpose: emissive core, glow disc, far orb, near orb created farther-first composite correctly under unsorted drawing, per the plan's ordering-discipline requirement. Bloom: first honest observations recorded (monotone threshold, no cliff at 1.0 — appears pre-tone-map; emissives behind transmission barely feed it; palette-conditional as ever) — a rule waits for a film that leans on bloom.

## 0.71.0

### added
- **`screenwright` 0.3.0 — Phase 1 step 3: the post pipeline is always on.** Every 3D scene now renders through `RenderPipeline`, pass-through by default — the look is unchanged (identical exposure statistics to direct rendering), but smoke's determinism and shipped-frame checks exercise the post path on every scene, closing the last "present in the bundle, exercised nowhere" gap. Effects are `STYLE` flags, both verified byte-deterministic on both backends and visually confirmed: `STYLE.bloom` (TSL bloom — thresholds deliberately unmeasured until the pack work brackets them; the old `UnrealBloomPass` numbers do not transfer) and `STYLE.dof`, whose focus distance rides the cinematography solver's `shotFocus` through a uniform — the `SHOTS[]` `focus` property is functional for the first time on this stack (the doc audit had flagged it inert), so two adjacent shots differing only in focus, joined by `cut:'blend'`, are a rack focus. gearbox regenerated on the post-path template and re-shipped (example + docs/media recording).

## 0.70.3

### changed
- **`explainer-video` 0.25.7 (frozen; plumbing-scoped) — the six rendered `.avif` recordings move to repo-level `docs/media/`,** matching the policy screenwright 0.2.2 established: recordings are human-browsing artifacts the skill never uses, and the plugin subtree (copied per retained version into every install cache — measured at 3 retained versions ≈ 3 copies of 8.4 MB, now ≈ 3 copies of 4 MB) carries only what the skill needs. All README embeds rewritten to cross-tree relative paths; the `bibles.md` and `delivery.md` prose mentions updated so no in-plugin doc implies the recordings sit beside the examples. The teaching `.html` films are untouched and stay in-plugin. delivery.md's evidence chain ("GitHub serves `.avif` as `image/avif`") is unaffected — the file is still served from the same repo, from a different directory.

## 0.70.2

### changed
- **`screenwright` 0.2.2 — rendered previews move out of the plugin subtree.** Decided on measured install mechanics (an opus agent verified both steps on a live install): `marketplace add` shallow-clones the whole repo either way, but `plugin install` copies the plugin subtree into a per-version cache — so binary previews in the plugin dir get duplicated per retained version while contributing nothing to the skill (Claude never reads an AVIF; only the HTML baselines teach, and `examples/` never auto-loads into context per the Agent Skills spec). `gearbox.avif` now lives in repo-level `docs/media/`, embedded by the new `examples/README.md` via cross-tree relative path (GitHub resolves it; no release-asset uploads needed). New standing rule, recorded in the plan: **SKILL.md never cites paths outside the plugin subtree** — the install cache lacks `docs/`, so such pointers would dangle for every installed user. Teaching HTML files stay in-plugin and bundled: self-containment is doctrinal, and there is no way to avoid embedding three without reopening the shipped-broken-example class.

## 0.70.1

### changed
- **`screenwright` 0.2.1 — four subagent reports folded in: two review passes fixed, two investigations closed.**

  The independent film review found what the author's own review missed, with measured evidence: the mesh-beat highlight ring was parked 0.17 world units off the interlock midpoint (~45% of its radius framing blank face); the ratio beat's trails swept EQUAL arcs while caption and in-source comment promised 3:1 (the comment described code that did not exist); and the HTML loop seam was a naked triple discontinuity (camera FSA→WS jump + both markers mid-arc). All fixed in the example: ring centered on the measured interlock midpoint with a pulsed fill light (the meshing teeth sat in the key's shadow), trails rewritten as a TIME HISTORY (dot i sits where the marker was at t−(i+1)·DT, so arc lengths show the true 3:1 sweep), a motor block with a breathing lamp gives "input" actual geometry, and the loop is now seamless BY CONSTRUCTION — `SPIN = 12π/TOTAL` puts both gears at whole revolutions per film and the final shot matches the opening shot. Two LOW findings (marker passes near the caption zone; title mass sits left) accepted as register choices.

  The minimal-repro agent CONFIRMED the sortObjects defect outside the pipeline (3 meshes, no shadows, both backends; 39/40 wrong with sorting, 40/40 clean without; stale object's shadow correct while its beauty pass lags) and refined the story: the trigger is a REVISITED state after a depth-order change — object motion suffices, camera cuts are just the common case — and it is 100% deterministic on revisit; the "~12% flaky" was sampling structure. Rule #5 and the template comment now state the confirmed mechanism. New caution recorded: a one-time WebGPU first-render warmup difference exists even with sorting off; the boot's pre-`sceneReady` render absorbs it.

  The framing-delta agent MEASURED AWAY the "~3% zoom" between stacks: at equal viewport, rendered geometry is sub-pixel identical (±0.7 px / 14 silhouette probes) across all three renderer configurations — the original A/B had a ~33 px effective-viewport mismatch. The SIZES ladder calibration is safe; the real cross-stack difference is tone/shading (~9% of pixels), which the eye reads as zoom.

  The doc audit caught three drifts, all fixed: SKILL.md's scaffold step invoked argument-less `build.js vendor` (builds and discards — inert; now names the scene), the shared-contract paragraph claimed `SHOTS[]` and `window.BACKEND` for the 2D template (scoped to 3D), and webgpu-stack.md named a nonexistent `mx_perlin_noise_float` (the export is `mx_noise_float`). Plus: smoke now prints which backend each scene verified (`ok scene.html [source, webgl2]`), making `window.BACKEND` consumed rather than decorative.

## 0.70.0

### added
- **`screenwright` 0.2.0 — Phase 1 steps 1–2: the sampling helper and the `gearbox` regression film.** The film shipped as the skill's first example (`examples/gearbox.html` + `.avif`), built from ONE scene body injected into both screenwright's and frozen explainer-video's templates and judged side-by-side: composition and read match cell for cell, both stacks smoke-green. It also did exactly what running the regression FIRST was for — it caught the biggest node-stack defect so far:

  **With `renderer.sortObjects` on, a camera cut corrupts per-object uniform state.** The depth sort reorders the draw list and objects render at a *previous seek's* pose — sticky across re-renders, immune to settle time (0.5s changed nothing), on both backends, ~12% of determinism checks on a 25-mesh multi-shot scene. The proven template never hit it (4 meshes, stable order). Isolated by ascending bisection after seven descending bisects each refuted a suspect (settle length, frustum culling, transparency, nesting, the internal animation loop, fog, rim light): the same world under one static shot was clean, multiple shots broke it, `sortObjects=false` fixed it 16/16. Now a template default and determinism rule #5; per-mesh `frustumCulled=false` (a smaller cousin, measured separately) is rule #6. Consequence documented: overlapping transparent objects must be created farther-first.

  Also: `sampleAt()` in smoke.js — THE one way to read scene pixels in-page (render + read in a single task), with the framing and exposure checks refactored onto it; a scene-rig lesson from the twin comparison (`key.shadow.normalBias = .035` kills extruded-face shadow acne in both stacks); and one parked honest residual — a ~3% constant framing delta between the stacks at identical `t`, visible only in direct A/B, unexplained.

## 0.69.0

### added
- **`screenwright` 0.1.0 — a new plugin: the explainer-video successor on the three.js node stack.** Phase 0 (foundation) of `docs/internals/screenwright_plan.md`: the templates, recorder, and instruments ported from explainer-video to `WebGPURenderer` (transparent WebGL2 fallback) + TSL node materials, gated green on both backends. `explainer-video` is now frozen — published, bugfix-only — per the plan's founding decisions.

  Phase 0 shipped four measured findings, each now encoded in the tools rather than in prose:

  1. **Shadow maps update at most once per `nodeFrame.frameId`, and `render()` never advances it** — only the renderer's internal rAF loop does. Two `seekTo` calls in one browser tick left the second rendering with the first's shadow map: a flaky byte-determinism failure whose pixel diff was confined to shadowed regions. `seekTo` now ticks `renderer._nodes.nodeFrame.update()` before rendering (private API, pinned at `three@0.185.1`; smoke fails loudly on rename).
  2. **The compositor can present a frame late** relative to the queued render, so the recorder settles one double-rAF between seek and screenshot — without it, screenshot hashes flaked over byte-identical canvas content.
  3. **A half-dead WebGPU adapter ships the flat clear color with exit 0** — deterministic, caption crisp on top, four existing checks green. New hard check in `smoke.js`: a caption-stripped cold page must ship frames that change across sampled `t` and whose richest frame clears a measured luma-spread floor (broken 1.7 / healthy 3D 161.3 / flat 2D register 120.9; floor 12). Demonstrated firing on the real failure (playwright headless-shell + `WEBGPU=swiftshader`), not assumed. `shoot.js` refuses that adapter outright without `WEBGPU_UNSAFE_SHIP=1`.
  4. **The Chromium cache scan matched nothing on Apple Silicon** (missing `-arm64` layouts) and silently fell through to system Chrome — an auto-updating build that disagreed with playwright's pinned one about WebGPU, which is how finding 3 hid. Both tools now scan both layouts.

  Also: `WEBGPU=off|auto|metal|vulkan|swiftshader` recorder policy with conflict rejection (the wrong flag combination is how the silent black-frame configuration happens); `compileAsync` pre-warm before `sceneReady`; `window.BACKEND` export; the demo scene's material is a TSL MaterialX node graph driven by the sanctioned `uTime` uniform, proving the pattern under byte-determinism. New reference `references/webgpu-stack.md` carries the backend policy, the four node-stack determinism rules, and every measured bracket.

## 0.68.6

### removed
- The `Stop` parity hook and its `.claude/settings.json` entry. **Its own justification stopped being true in 0.68.5.**

  The hook existed because "`smoke.js` catches drift but costs a multi-minute Chromium launch." Adding `--parity-only` made that check 0.2s on demand, which removed the reason for a session-level mechanism. What remained was a hook firing on every turn end in this repo — including sessions touching `readwise-reader` or docs and never opening a scene — to guard a rare, deliberate operation (editing a marked shared block) whose failure is a recoverable source inconsistency the release gate already hard-fails on. The one thing that made it selective, a dirty-tree precondition, was itself broken and had to be removed.

  The refactor earned its place; the hook did not. Recorded because the sequence is the useful part: a check was duplicated into its caller, the duplicate diverged immediately, fixing that properly produced a fast shared implementation, and the fast implementation made the caller redundant. **The right fix for "this check is too slow to run often" was to make the check fast, not to build a second place that runs it.**

### changed
- `smoke.js`'s usage block documents `--parity-only`, and points callers at it rather than at reimplementing the check.

## 0.68.5

### fixed
- **explainer-video 0.25.4 -> 0.25.5**: a code review found ten real defects, including two in the guard added to prevent them.

  **The parity hook had reimplemented the check instead of calling it.** Verified: a scene whose marker was mangled to `KERNEL-STARTX` dropped out of the comparison in total silence — the exact self-exemption fixed in 0.25.1, reintroduced in bash, diverged from `smoke.js` on day one. `smoke.js` gains `--parity-only`: marker parity plus template integrity with no browser launch, and the hook is now a wrapper around it. One implementation. **A check duplicated into its caller is subject to the rule it enforces**, recorded in `instruments.md`.

  **The hook's own frugality defeated it.** It only ran when scene files were dirty. This repo commits at the end of a turn, so the tree was clean exactly when the check mattered and it never fired — verified by committing real drift and watching it pass. It now runs every stop; measured cost is 0.2s.

  **The self-containment assertion still knew one spelling.** HTML permits unquoted attribute values, so `<script src=./evil.js>` passed as self-contained — the 0.25.3 defect one level down. It was also `<script>`-only while the changelog claimed "is anything external referenced" and promised the Canvas2D backend a guarantee, which is the backend likeliest to pull a font or stylesheet rather than a script. Now covers `script`/`link`/`img`/`iframe`/`video`/`audio`/`source`/`track`/`embed`, quoted or not, with `data:`/`blob:` allowed and `<a href>` deliberately excluded. Ten controls both directions; all six shipped examples still pass.

  **`smoke.js` paid for a build it threw away.** The pre-flight `build.js vendor` had no target, and `vendor()` deletes its own output, so every run built a full minified three.js bundle that was immediately discarded and an `existsSync` guard that could never short-circuit. Removed; the real embed happens per-scene during bundling.

  Also: `.smoke-*` scratch copies are gitignored and excluded from scene discovery (an interrupted run left one behind, and the next run adopted it as a real scene — joining the parity set and being rendered); the half-fence message pointed at the END marker when a mangled START reads identically; and the vestigial single-element `variants` loop is gone, so the cleanup `finally` scope is legible.

### changed
- `doc-claim-auditor` pinned to `model: sonnet` — grep-and-classify against code is what `.claude/rules/model-delegation.md` calls well-specified, mechanical and verifiable. `film-reviewer` and `control-builder` now state in-file why they deliberately inherit the session model instead.
- Dropped the `CLAUDE.md` invariant added in 0.68.4 for the `Stop` hook. It did not bite on first edit, which is that section's bar; the hook is discoverable from `settings.json` and self-documented, and the lesson worth keeping lives in `instruments.md`.

## 0.68.4

### added
- **explainer-video 0.25.3 -> 0.25.4**: `references/instruments.md` gains "Where a check belongs: the tool path or the artifact".

  The 0.25.2 fix left its reasoning unrecorded, which is the more valuable half. A guard on the code path holds only for callers who take that path — `ensureVendor` now refuses to embed into a template, but a hand edit, a bad merge, or a future command writing the file directly all reproduce the broken artifact past it. A guard on the artifact's own invariant catches every route, including ones nobody has written yet.

  It also records **the instrument deliberately not built**, which this file treats as worth as much as the ones that were. "Assert the working tree is clean after `smoke.js` runs" is the obvious move and is wrong: `smoke.js` runs mostly in an author's scratch directory that is usually not a repository, where writing files is the entire point. The assertion would be false in the tool's primary use case and would need suppressing there — the standard route by which a check becomes noise and then gets bypassed. An invariant belonging to a repository gets enforced where repositories are enforced.

- `CLAUDE.md` invariant 7 records the repo-local `Stop` hook and, like invariant 5, that resetting `.claude/settings.json` silently removes it — the checks it runs exist nowhere else at that cadence.

## 0.68.3

### fixed
- **explainer-video 0.25.2 -> 0.25.3**: the self-contained assertion knew one spelling of one tag.

  Swept for more guards asking a weaker question than the operation they protect — the root cause behind 0.25.1 and 0.25.2 — and found the inverse form. `bundle()` asserted self-containment by testing `VENDOR_TAG`, anchored on exactly `<script src="./three.global.js"></script>`. A scene referencing anything external under any other spelling — single quotes, a CDN, a differently-named bundle — **passed** the assertion while carrying a reference that would not travel with the file. That is the failure the surrounding comment records as already having shipped: a committed 3D example with a dangling reference that rendered nothing.

  It now asserts the property: no external `<script src>` remains, `data:` URIs excepted. This also **removes** a three.js assumption rather than adding one — the question is no longer "is the three tag gone" but "is anything external referenced", so the Canvas2D backend and any future SVG one get the same guarantee without the vendoring machinery being involved. Controlled: a normal scene still bundles, single-quoted and CDN references are now caught.

  Swept clean otherwise. `motion`'s `f%05d.png` assumption holds because `frames()` pins `SHOOT_FORMAT: 'png'` rather than inheriting it. Noted but not changed: `build.js` keeps the command list, `USAGE`, and the dispatch chain as three parallel lists that must be edited together, and the `sway:` advisory parses scene source with a regex that a reformatting would silently defeat.

### added
- The `Stop` hook also flags a shipped template that has been inflated with an embedded library. `ensureVendor`'s refusal guards the tool path; this guards the artifact, so a hand edit, a merge, or a future command that never calls `ensureVendor` is caught the same way. Bracketed by observation in both directions: intact templates are 32 KB and 24 KB, an inflated one measured 802 KB, and nothing legitimate sits near the 200 KB threshold.

## 0.68.2

### fixed
- **explainer-video 0.25.1 -> 0.25.2**: running the verification gate destroyed the thing it was verifying.

  `smoke.js` asserts each scene is self-contained by running `build.js bundle` on it, and `bundle()` embeds three.js **in place**. That is correct for an authored film — embedding is what makes it self-contained — but `templates/` holds the shipped 32 KB starting points, so every gate run silently rewrote `scene.template.html` with 0.77 MB of inlined three.js. The result is idempotent, which is why nothing ever flagged it; it reached `git add` before a post-commit `git status` caught it.

  Two changes, because the hazard has two halves. `ensureVendor()` now **refuses** to embed into any `*.template.html` with an explanatory error, which protects every `build.js` command rather than just this one path — `sheet`, `motion` and `strip` had the same effect on a template and nobody had noticed. And `smoke.js` verifies a template through a throwaway copy beside it, since a template must keep its vendor tag yet can only be rendered with three embedded. The copy is deliberately not named `*.template.html`, or the new refusal fires on it and the template becomes uncheckable — which is what the first attempt did.

  Controls both ways: a template now errors and is byte-identical afterwards; an authored scene still embeds normally (31,899 -> 802,292 bytes, tag consumed).

## 0.68.1

### fixed
- **explainer-video 0.25.0 -> 0.25.1**: a scene could exempt itself from the kernel/solver parity check.

  `smoke.js` extracts each shared block with a regex anchored on the full `/* ==== KERNEL-END ==== */` marker, but its half-fence guard asked the loose `txt.includes('KERNEL-END')`. A mangled marker — `KERNEL-ENDX` — satisfies the loose form as a substring while the anchored extraction stops matching, so the file **dropped silently out of the parity set with no failure reported**. That is precisely the self-exemption the guard was written to prevent; only outright deleting the marker was caught. Both guards now derive from the same regex that builds the parity set, so any broken fence, however broken, fails loudly.

  Found by building a positive control for a new parity hook rather than by the gate itself, which is the recurring lesson here: the check that has never fired is indistinguishable from the check that cannot fire.

### added
- Repo-local `Stop` hook (`.claude/hooks/kernel-parity.sh`) reporting kernel/solver drift across explainer-video scenes at end of turn, and three delegation agents (`film-reviewer`, `doc-claim-auditor`, `control-builder`) in `.claude/agents/`.

## 0.68.0

### added
- **explainer-video 0.24.0 -> 0.25.0**: the most repeated authoring bug in this skill's history finally has a name and a technique.

  **Two things that must touch: measure the contact, do not infer it** (`references/method.md`). Four independent films had already hit this and each was written off as a one-off — a payload dot that arrived at empty space, a hammer head hanging 0.6 units clear of the plank it was meant to strike, a domino that swept *between* the paddles, a body that descended offset from the gate that opened it. A two-character fight scene made it a pattern: neither combatant's blow ever reached the other.

  The cause is a vocabulary trap rather than carelessness. **`h`/`w` describe the FRAMING extent; the contact point is a different number that nothing records.** A pelican declaring `h:6.6, w:4.2` gives no hint that its beak tip sits +4.37 from its origin, so authors use the number that is written down. The section gives the measurement technique (`Box3` through `page.evaluate` — the same probe the cross-section film used for its front-face check), and shows solving the staging from the measured offsets rather than tuning a coefficient: the fight's two separations fell out as exactly 5.83 and 3.23. It also covers the two ways the check goes wrong — testing only one axis (one swing measured an x-overlap of −1.66 with a **y-overlap of 0.01**, arcing clean over its target) and ignoring whether the reach exists at all (a 1.72-unit arm cannot touch something 2.9 away).

  **Geometric contact is not legible contact.** Overlapping bounding boxes mean the objects touch; they do not mean the viewer sees a hit. The contact point can sit behind a body, or the two interpenetrate and read as clipping. This is the interaction form of the existing "subject versus apparatus" rule.

  Deliberately **not** built: a `build.js contact` checker. Four films hit the bug and none was *blocked* — each was fixed by hand once someone measured. Documenting the rule and the technique is the earned response; an instrument waits for a film that cannot proceed without one.

## 0.67.0

### added
- **explainer-video 0.23.0 -> 0.24.0**: two rules learned by building a two-character scene, plus docs for the pass-three primitives.

  **Every character owns its own physics and state** (`references/method.md`). The moment a second figure enters a scene, "cyclic motion derives from progress" acquires a second half: from *that* character's progress, on *that* character's grid. This shipped and looked exactly like a broken rig — a fight scene handed the second character foot targets computed on the *first* character's plant grid, anchored at the first one's start and stepping at the first one's stride. The IK solved faithfully for targets that meant nothing, so the legs splayed and it read as broken geometry rather than a maths error. Nothing detected it; a human looked at a frame and said "the robot walks weird". The section tabulates what each character must own (start, direction, stride, limb lengths, travel expression) and what borrowing each one costs, with the structural fix: parameterise the gait instead of copying it, and hand the solver an offset from that character's own hip. Shared constants are for the *world* — gravity, wind, the beat grid — never for anatomy.

  **Union subjects take wide rungs only** (`references/film-language.md`). `MS`/`MCU`/`CU` carry human-figure meanings and a union box of two fighters has no waist; asking for `MS` on a 9-unit-wide pair jams the camera into the gap between them.

  `SKILL.md` and `method.md` now document the pass-three kit — `rampE`, `latch`, `warp`, `txt()` — and the `nocap` semantics sheet, which had shipped in 0.23.0 with only inline comments.

## 0.66.0

### added
- **explainer-video 0.22.0 -> 0.23.0**: hardening pass three — the kit gains time-shaping and a real text layer. Scoped by what actually blocked a film, not by what the plan listed: three planned primitives (`cyc`, `progress`, and initially `warp`) were **deliberately not built**, because every film that wanted them shipped without them. Building all nine would have repeated the mistake two reviews had just corrected — shipping surface with no callers.

  **`rampE(t, beat, a, b, ease)`** returns `{u, e}` — the raw gate and the eased value together. The kernel warns "gate on the raw ramp, never on an eased value" because `backOut(0)` carries positive floating-point residue; **three separate authors gated on the eased value having read that warning**, because the idiom the kit offered was a single composed expression and gating correctly meant splitting it. Making the correct path the easy path beats warning louder.

  **`latch(t, at)`** answers "when did the previous link hand over", which `ramp`/`pulse`/`during` cannot — they all answer "where am I inside this beat". This matters more than it sounds: driving B from A's own expression is right for a *sustained* coupling and wrong for an *impulsive* one. Measured on a domino chain, a hammer's post-impact ringdown retracted the driver by 54% of a contact width and **the entire fallen row stood back up and fell again**. Derivation propagates onset; it does not propagate persistence.

  **`warp(t, segments)`** — a monotone reparameterisation of `t`, so a window of real seconds can run slow or fast while the beats keep their real-time pacing. This was explicitly deferred as unearned an hour before a film needed genuine slow-motion; it ships now because that film exists, which is the earn-in rule working rather than an exception to it. Verified monotone and pure.

  **`txt()` / `txtWidth()`** replace a `label()` that was centre-align only, fixed weight, and unmeasurable — every 2D film rewrote it within minutes, and the blueprint pack documents primitives the template never shipped. `label()` is kept as the centred shortcut.

  **`?strip=text` — the semantics instrument.** "Cover everything except the geometry" was the test and had no tool: an author hand-edited a copy of the scene to run it. Every draw routed through `txt()` becomes a no-op, and the DOM overlay hides too, so `build.js sheet <scene> 480 0.6 nocap` renders the same beats with every word removed on both backends. It works *because* the text helper is worth using — hand-rolled `fillText` opts out of it. Verified: the 2D example's sheet comes back wordless, and is markedly harder to read, which is exactly the finding the instrument exists to surface.

### changed
- **explainer-video: flash width is a parameter** (`CONFIG.flashWidth`, or per-flash `w`), was hardcoded at ±0.25s — so the shortest expressible flash was 0.5s, longer than an entire beat in one film whose author reimplemented the flash in scene code to get a 0.20s snap. `window.FLASHES` now carries each flash's width, and `smoke.js`'s sampler avoids the declared interval rather than an assumed constant that would have gone stale the moment flashes became parameterised.

## 0.65.0

### fixed
- **explainer-video 0.21.1 -> 0.22.0**: nine defects found by an adversarial code review of the hardening work, every one reproduced before being fixed. Three were introduced by this run.

  **`vendor` destructively rewrote every `.html` in the scene's directory.** `embedInto` walked `readdirSync` and embedded three.js into any file carrying the vendor tag, and `ensureVendor` runs before *every* command that opens a scene. Reproduced: `build.js bundle a.html` in a directory holding a work-in-progress scene and a copy of `scene.template.html` rewrote all three from 26,934 to 797,327 bytes — the shipped template silently lost its placeholder and grew 30x, and the result looks idempotent so nothing would ever flag it. This is the most damaging thing the branch introduced. It now embeds into the target only, verified with a bystander file.

  **The gate hard-required a canvas with `id="c"`, which the contract does not.** A scene satisfying the full contract, deterministic, correctly contained, but naming its canvas `stage`, **failed** with an unactionable `Cannot read properties of null`. Worse, the `>=99%` near-black hard-fail never ran for it — putting any such scene back in exactly the state that let a 342-frame all-black film report `all scenes pass`. Now queries `document.querySelector('canvas')` and tolerates canvas-less backends, which the file's own comment always promised.

  **`motion`'s provenance assertion sat 75 lines *below* a silent no-op.** An early return printed "no frames captured, nothing to report" and exited 0 — the outcome strictly worse than the partial profile the assertion was written to prevent. The assertion now runs first, and its `0.9` heuristic is replaced by an exact count: `tblend` emits one delta per adjacent pair, so N frames must yield N−1. The old constant was wrong in both directions — `N−1 < 0.9N` holds for every `N < 10`, so short films threw spuriously, while 25 frames could vanish from a 254-frame render undetected. Relatedly, `slice(1)` was discarding a real sample on a false premise: `tblend` has *already* dropped the unpaired first input, so the film's first inter-frame delta was invisible by construction and every dead-air timestamp was reported one frame early.

  **`anchorX` offset along world X, not camera-right** — so at `angle: 90` it moved the target straight toward the camera and produced no horizontal movement at all, which is precisely the framing problem it was added to solve.

  **`SHOOT_FORMAT` wrote JPEG bytes into `.png` filenames**, and `range` (documented for hand use) honoured it from ambient env — so exporting it to speed up reviews and then re-shooting a range would splice lossy frames into a lossless master, with every downstream check matching on the extension and seeing nothing wrong. The extension now follows the format.

  Also: the kernel/solver parity check silently exempted a file carrying `START` without `END` (delete one line and a scene becomes invisible to the drift check that justifies the duplicated-block pattern); `samplePlan`'s flash avoidance could move a sample *into* an adjacent flash — reproduced at 95% white on an ordinary 0.4s cut-in/cut-out pair — and depended on the order flashes were authored in, now fixed with merged intervals; and an invalid `ANGLE_BACKEND` was silently accepted, handing you hardware GL while you believed you were reproducing a software-GL regression.

### changed
- **explainer-video: the camera floor is now opt-in (`CONFIG.cameraFloor`), off by default.** The review argued it was the one change on the branch that narrowed expressiveness against the branch's own rule, and it was right: it clamped `p[1]` only, so the camera left the sphere the solver placed it on and the declared rung stopped producing the framing it promised — an author asking for a hero low angle silently got a higher one. A bare `0.35` world-unit default also baked a world scale into a skill whose claim is any subject at any scale: at `h ~ 0.2` (a circuit board, a molecule) *every* shot would clamp. Default behaviour is now identical to before the floor existed.

## 0.64.1

### fixed
- **explainer-video 0.21.0 -> 0.21.1**: two real bugs and a round of simplification, from a review of the hardening work.

  **`poster` was broken by this run's own `sample` rename.** `shoot.js` now writes `<scene>_sample_<t>.png` into `FRAMES_DIR`; `poster` still read `sample_<t>.png` from the CWD and would fail at the ffmpeg step. It now owns a workspace and asserts the file exists rather than guessing a name. **`build.js aspect` with no scene** reached `path.resolve(undefined)` and died instead of printing usage — it was added to `USAGE` and the dispatch but not the missing-target guard.

  **`SHOOT_FORMAT` was dead configuration for `aspect`.** `aspects` mode bypassed the shared `shot()` helper and called `page.screenshot()` directly, so the review-capture format never applied and `aspect` paid full PNG cost while `sheet` and `strip` got the measured ~6x. Now 2s.

  **The two Chromium resolvers had diverged on this branch.** `shoot.js` gained a numeric build-number sort; `smoke.js` kept a lexicographic one, which puts `chromium-1099` above `chromium-1223` — so the gate and the recorder could resolve different browsers on the same machine. Synced.

### changed
- **explainer-video: the sampling layer was over-built and is now the size of its job.** It shipped with `beats`/`peaks` modes and `frac`/`avoid` options, of which exactly one caller used one mode — the other branches were unreachable, written for a `peaks` mode never implemented. Earn-in applies to tooling too. It is now `samplePlan(dur, flashes, n)`, keeping the two behaviours that carry their weight: interior-only points (t=0 is a title card in essentially every scene, which is how the old single-sample check came to look at the one moment a broken scene was clean) and flash avoidance. Verified: all three determinism controls still caught, all six examples and both templates still pass.

  Also removed: a `bundleName` helper orphaned when `bundle()` became an assertion, an `expectFrames` helper superseded by `motion`'s two inline checks, a `_wrote` alias of a variable in the same scope, a dead `shots[0]` binding, a `variants` loop that always had one element after the source/bundled pair collapsed, entry-time `clean()` calls deleting directories `workspace()` had just created, and seven copies of the output-basename regex. The framing check's sample constant was renamed off `EXPOSURE_SAMPLE_TIMES`, so re-bracketing exposure can no longer silently move framing's sample points.

## 0.64.0

### added
- **explainer-video 0.20.0 -> 0.21.0**: `references/instruments.md` — a consolidated ledger of what every check can and cannot see, with its measured bracket. This is the modularisation the test run actually earned: the limits were real, measured, and scattered across `method.md`, code comments and a postmortem, which is the shape knowledge takes right before it gets forgotten. It leads with the rule they all serve — **a proxy can reject, it cannot approve** — and records what has *no* instrument (watching the loop, semantics, whether a beat is funny, cross-machine reproducibility) as plainly as what does.

### changed
- **explainer-video: docs corrected where they were actively misleading.** `style-3d.md`'s SwiftShader note read as "PMREM is broken"; bisected, PMREM works for LDR and HDR on both backends, and only `Sky` into a **half-float** target fails — poisoning *direct* lighting on every `MeshStandardMaterial`, with a fallback that agrees across backends to 0.2%. The bloom-threshold rule now reads "above the **sky-lit** luminance of your brightest material", bracketed at 3.2 (blown) / 8.0 (right) / 14.0 (no-op).

  `film-language.md` documents the vocabulary added in 0.20.0 (union subjects, `d`, `anchorX`, the `FSA` rung) and stops promising what the renderer cannot do: **`whip` is a fast cut, not a whip pan** — it differs from `blend` only in duration, and `focus` requires a `BokehPass` the base template does not have, so a scaffolded scene that sets it gets silence. `h` is now documented as "the extent that must stay in frame", not "the subject's height" — three films cropped their own payoff on that distinction.

  `method.md`'s semantics axis is restated as **"cover everything except the geometry"**. The old "cover the caption" degenerates to a silent pass with no captions, removes the film when text is the subject, and cannot see canvas text — in one film built from an external document, 5 of 8 beats survived hiding the DOM caption and only **2 of 8** survived hiding the drawn labels too. The pacing floor is rescoped to the window in which a *mechanism* must be read, with the undocumented converse recorded: a physical event is often **faster** than a beat wants to be (a domino falls in 0.30s while beats want 3-4s).

## 0.63.0

### changed
- **explainer-video 0.19.0 -> 0.20.0**: hardening pass two — the framing vocabulary now measures what it promises, and the solver is fenced.

  **The solver had reached SIX copies.** The generalization plan's postmortem set the trigger at "a third consumer, extract or marker-fence it"; it fired long ago and nothing acted. It is now inside `SOLVER-START`/`SOLVER-END` markers with a `smoke.js` parity check that hard-fails on drift, exactly like the deterministic kernel. Editing the solver is one edit again.

  With the fence in place, the solver gained what the run showed it was missing: **union subjects** (`subject: ['plank','hammer']` solves the bounding box of both — every causal beat is two objects and the space between them, and hand-authoring a composite subject with an invented centre is the "coordinates were never the author's intent" the vocabulary exists to abolish); **projected fitting** when a subject declares depth (`d`), because an axis-aligned width is non-monotonic in camera angle — measured, a box that fitted at 0 and -45 degrees clipped at -26; a **horizontal anchor** (`anchorX`), the absence of which is why framing a named subject put its most important feature at the frame edge and authors fell back to framing regions; an **`FSA` rung** at f=.70 between `WS` (.50) and `FS` (.95), the workhorse "full body with a little air" framing that did not exist; and a **floor guard** so a low elevation at long distance can no longer put the camera underground. All optional and defaulting to prior behaviour: a subject declaring only `h` frames exactly as before.

  **`window.FLASHES` joins the contract.** The new sampling layer's flash-avoidance was silently avoiding nothing, because `CONFIG` is a `const` in a classic script and never becomes a window property — so a legitimate film failed the blank check *inside its own world-cut flash*. Same shape as why `window.BEATS` exists: when a tool is tempted to parse scene internals, the contract is missing an export.

  Regression: all six examples and both templates pass, with solver and kernel parity enforced across all of them.

## 0.62.0

### fixed
- **explainer-video 0.18.0 -> 0.19.0**: hardening pass one, from a batched test run of eleven films. Full analysis in [docs/internals/explainer_video_hardening_plan.md](docs/internals/explainer_video_hardening_plan.md); the run's ~51 findings collapse into two root causes, and each gets a structural fix rather than a patch per symptom.

  **Root cause 1 — instruments that generalise from a single sample.** `smoke.js:147` was `const t = Math.min(1, dur/3)`, which for any film over 3s is the *constant 1.0s* — inside the title card the workflow tells you to write first. Three controls on one scene proved the consequence: a provably non-deterministic scene reported **`all scenes pass`, 0 warnings**, because t=1.0 was the only timestamp where that scene was clean. The skill's central guarantee could report green on a scene that violated it.

  Fixed structurally with a **sampling layer** every check draws from — it knows the duration, the beat table and the flash windows, offers `uniform`/`beats`/`peaks` modes, avoids `CONFIG.flashes` windows (which blind exactly the beats bracketing a world cut), and reports which points it used so a green result is auditable. Determinism and blankness are now **ALL-quantified** over a 4-point plan rather than spot-checked at one arbitrary second. Verified against all three controls: previously 1 of 3 caught, now 3 of 3, with the good scene still clean.

  **Root cause 1, second half — runs were not isolated and nothing verified provenance.** Five agents independently hit fixed scratch directories; the worst measured case encoded 3 frames from one film and 70 from another, silently. Rather than suffix six hardcoded names with a pid (the seventh command would hardcode a seventh name), all scratch space now goes through one `workspace(scene, tag)` helper, and `motion` asserts that the frames it parses match the frames it wrote — which generalises to any future desync, including the stale-tail class. Verified with concurrent runs in one directory.

  **Bandaids, labelled as such because they genuinely are:** a >=99% near-black frame is now a failure rather than an advisory (a 342-frame all-black render previously reported `all scenes pass`, because the caption pill kept the frame from being technically empty); `shoot.js sample` honours `FRAMES_DIR` and prefixes filenames by scene; `shoot.js` self-heals its vendor step like `build.js`.

### changed
- **explainer-video: renders are much faster, and the reason was measured, not guessed.** GL backend is now selectable and defaults to **hardware** (`ANGLE_BACKEND=swiftshader` forces software) — it was hardcoded to SwiftShader, which cost 55x on the GL draw for a post-chain scene and let a Sky/PMREM scene render 342 black frames with exit 0. Review passes (`sheet`/`strip`/`aspect`) now capture **JPEG q92** instead of PNG over the identical readback path; they already emit `.jpg`, so no deliverable changes. Measurements (`motion`) and masters (`frames`/`all`) stay PNG.

  Measured: a review pass on the heaviest scene went **7s -> 1s**; a full 30fps render **38.5s -> 21.5s**. Benchmarked at 1920x1080: PNG 185.6 ms/frame, JPEG q92 30.9 ms, JPEG q80 29.5 ms — size nearly halves between q92 and q80 while time barely moves, which locates the remaining cost in CDP pixel readback rather than compression. WebP was tested and **is not available**: Playwright rejects it (`type: expected one of (png|jpeg)`), and it would land in the same ~30 ms band regardless.

### added
- **explainer-video: `examples/README.md`** describing each of the six films and stating plainly that the `.html` is the film — full resolution at display refresh — while the `.avif` beside it is a heavily compressed 960px/15fps recording that exists only because github.com cannot run a script tag. Judge a film by opening the HTML.
- Root README now leads with explainer-video and links to the examples folder.

## 0.61.0

### added
- **explainer-video 0.17.0 -> 0.18.0**: four new committed examples, and every example is now a genuinely self-contained single file.

  **Examples.** The plugin previously shipped two films, both self-referential — the pipeline explaining itself, and a demo character. Added: **`heat-pump`** (36.6s, 10 beats, three worlds joined by four hard cuts under flashes, every cut verified at flash 0.980 on the exact frame the world changes), **`chain-reaction`** (16s, a six-link Rube Goldberg where each link's trigger time is derived from the previous link's own curve), **`pelican-walk`** (17.8s, no explanation — 1600 instanced rain streaks whose height is `mod(t)` and lightning as three exponential decays at fixed offsets, both pure functions of `t`), and **`toybot-dance`** (12.6s, no captions at all). That gives the examples cross-world walkthrough, causal-chain, and two non-explainer registers for the first time. `skill-retrieval` removed at the owner's request; `toybot-walk.midnight.avif` removed — `midnight` is a one-line render, which holds the control-pair claim more honestly than a committed artifact that can go stale against the scene.

  **Vendoring is now structural, not a convention.** `build.js vendor` builds three as an IIFE, splices it directly into the HTML, and deletes the intermediate file — there is no `three.global.js` to ship and no `.bundled.html`. `ensureVendor` runs before every command that opens a scene, so a scene cannot reach a render, a review, or a commit still pointing at a library that is not inside it, and `smoke.js` fails any scene that is not self-contained (`bundle` is now an idempotent assertion rather than a transform). This closes a real defect: the committed 3D example shipped as un-bundled source with a dangling `./three.global.js` reference and **rendered nothing when opened**, because bundling was an optional manual last step. The old source-vs-bundled artifact pair collapses into one file, and with it the whole "the bundled copy drifted from the source" failure class.

  Verified: all six examples self-contained, smoke green (contract, determinism, kernel parity, framing invariance), and byte-identical renders before and after embedding. AVIFs standardised at 960px/15fps.

## 0.60.0

### fixed
- **explainer-video 0.15.0 -> 0.16.0**: two defects found by *running* the pipeline rather than reading it, both invisible from inside the recorded outputs.

  **The HTML artifact and the recorded formats disagreed on framing.** SKILL.md's headline claim is that one scene file drives the live HTML loop and the frame-exact render alike. They were identical in *time* and not in *framing*. The 2D template scaled by `canvas.height/VIEW_H` alone, so visible world **width** was a function of the viewport's aspect ratio; the 3D solver pins the *vertical* extent (`dist = h/f/(2·tan(fov/2))`), so horizontal extent is vertical × aspect. Either way a window narrower than 16:9 silently cropped the sides. Measured on a fixed world point at `(3,3,0)` in the 3D template: `ndc.x` went **0.913 → 1.161** (off-frame) from aspect 1.78 → 1.40, while `ndc.y` held constant to four decimals.

  It was invisible to the entire test surface **by construction** — no tool in the chain ever opens a non-16:9 viewport (`shoot.js` pins 1920x1080, `smoke.js` uses 640x360 and 1920x1080, `build.js` opens no browser). Only a human resizing a window could see it, and one did. Worst hit was the shipped `toybot-walk`: at 1.40 the sign was cut out of the rack-focus shot — the exact failure that scene's own comment ("both subjects must be visible") exists to prevent. Crop thresholds measured per example: `toybot-walk` 1.66 (only 7% margin at 16:9), `scene2d.template` 1.45, `skill-retrieval` 1.30, `one-scene-every-format` 1.07.

  Both backends now compose against a fixed 16:9 **design frame** and contain it: 2D scales by `min(W/VIEW_W, H/VIEW_H)`; 3D widens the vertical fov below the design ratio while the shot solver keeps the **authored** lens for framing distance — the split that makes it contain rather than zoom out. Applied to both templates and all three examples. **Both are the identity at 16:9, verified byte-identical across all five shipped scenes at two timestamps**, so no committed artifact needed re-rendering and the match-cut constraint is untouched (it is a load-time pass over authored fields; `fitFov` is a uniform post-solver transform, so two shots with equal authored fov render equal fov at every aspect). `references/method.md` gains a "Framing rules" section as a sibling to the determinism rules, which were entirely temporal and had no home for this.

  **`build.js all` could silently encode the wrong frames.** `frames()` declared `dir='frames'` as a default parameter and passed it as `FRAMES_DIR` to `shoot.js`, overriding any ambient value, while `video()` reads `process.env.FRAMES_DIR`. So `FRAMES_DIR=X build.js all` shot fresh frames into `frames/` and encoded from `X/` — the same ship-the-wrong-film failure the comment inside `video()` already describes and claims to have closed, reintroduced through the other half of the pair. Silent whenever `X` already held frames: measured, one stale frame produced a **0.0 MB one-frame mp4 and exit 0**, printed as success. Fixed by defaulting `frames()`'s `dir` to the same expression `video()` uses; callers that own a scratch dir (`sheet`/`loop`/`avif`/`strip`) pass one explicitly and are unaffected.

  Known and still open, recorded in `method.md`: captions are fixed CSS px so they size against the window rather than the design frame, and `smoke.js` measures caption overflow at 1920 wide — a caption can pass there and still clip in a narrow window. The durable guard against the whole class is a smoke check at a second aspect ratio; not yet built.

## 0.59.0

### added
- **explainer-video 0.14.0 -> 0.15.0**: Phase 4 (style bibles) — gate met, and with it the generalization plan's back-to-back run (Phases 0-4) completes. A style bible is one object constraining every register layer — palette, lights, post, glass (`STYLE.lens`, the solver's default), cut pace (`STYLE.cutDur`), camera energy — while `BEATS`, cast, world, and the shot list stay content, untouched.

  The gate is the committed control pair: `examples/toybot-walk.html` carries a `BIBLES` table and a one-line switch. `toybox` (default) is the daylight paper-cutout film; `midnight` (`toybot-walk.midnight.avif`, 0.15 MB) is the same eight shots, same beats, zero geometry edits — as a low-key neon noir: 30° lens, locked tripod, 1.3s dollies, magenta rim, bloom threshold at .55 so glow carries the frame. The crush lint fires at 84% on midnight and that is the register by intent, judged by looking — precisely the hazard the neon-dark pack predicted when it was written, two phases before this film existed. If the swap had NOT categorically changed the film, the layers would not actually be separated; the pair is the standing proof they are.

  `references/styles/bibles.md` holds the spec (every key annotated as register), the pair's summary table, and the bible-writing recipe. Descriptions caught up with the run: plugin.json, marketplace.json, the root README's plugin row, and SKILL.md's retrieval description now state the two-backend/packs/bibles reality; CLAUDE.md's where-to-find table gains the generalization plan + roadmap row. Full regression green: three examples + both templates, source and bundled, kernel parity holding. Cast/set modules stay deliberately informal (no second film reuses a character yet — the plan's own rule); cut-rhythm-as-average-shot-length stays unbuilt with `cutDur` as the pace lever until a film needs more.

## 0.58.0

### added
- **explainer-video 0.13.0 -> 0.14.0**: Phase 3 (film language) — shots as data, gate met and phase closed. The 3D template's raw camera keyframes are GONE, replaced by a cinematography system: `SUBJECTS` (positions as pure functions of t — tracking shots for free), a calibrated size ladder (EWS→ECU), a framing solver (`dist = h/f/(2·tan(fov/2))`), moves as eased end-values (`size2`/`angle2`), cuts as entry vocabulary (`hard`/`whip`/`blend`), **the match-cut constraint checked at load** (identical framing vocabulary or throw), focus as a per-shot subject with racks expressed as two shots differing only in `focus`, and camera energy profiles (`locked`/`steadicam`/`handheld`) driven by seeded noise — closing the Phase 1 flag on `noise1`.

  Gate: `examples/toybot-walk.html` re-authored as an eight-shot list with zero hand-written keyframes — a compiler-verified match cut (MS on the sign plate, hard cut, MS on the bot's torso: the frames rhyme because they must), a whip into the finale, and the rack rebuilt as focus-only shot changes. Two calibration lessons recorded in `references/film-language.md`: the first size ladder shipped MS at full-shot framing (sizes are conventions with meanings, not free parameters — FS added, ladder recalibrated), and a rack to an off-screen subject explains nothing (both subjects must be visible at different depths, which set the rack triplet's size and anchor).

  Deliberately not built, per the earn-in rule, recorded with reasons: dissolve/wipe, ffmpeg edit lists, cut rhythm (belongs to Phase 4's style bibles), the 2D solver analog. Exit checkpoint: harvest in film-language.md + SKILL.md contract, release cut, regression green (all examples + both templates), prune reviewed (unused ladder sizes kept — the ladder is one conventional table, not speculative machinery).

## 0.57.0

### added
- **explainer-video 0.12.0 -> 0.13.0**: Phase 2 (cinematic 3D) closes. The toybot film gains its world — a 46-tree instanced forest (one draw call, plus one more for the whole field's inverted-hull outlines via a second `InstancedMesh` sharing the same seeded matrices), a `LatheGeometry` urn, a chrome `MeshPhysicalMaterial` pod, and a matcap boulder whose shading is painted at load on a canvas (zero lights, zero files). Re-encoded at 0.22 MB AVIF; smoke, motion profile, and the full-example regression all green.

  Two negative results, both bisected against controls and recorded in `style-3d.md` rather than shipped around silently: **`PMREMGenerator.fromScene` renders every subsequent frame black on SwiftShader** (software GL) — the IBL recipe is documented, expected to work on hardware GL, honestly marked unverified there, with the measured consolation that a metal physical material reads convincingly from the directional rig alone; and **the visible Sky dome, though it works, lost to the flat-background control on this film's low-horizon composition** — HDR-bright, fighting ACES at any exposure. `THREE.Sky` stays bundled for the compositions it suits (open sky, high angles, exposure ~0.5-0.6, bloom threshold above sky luminance).

  Phase 2 exit checkpoint: harvest done (instanced-field recipe moves from "not yet built" sketch to built-with-a-trick; Sky/IBL status section; matcap recipe), release cut (this one), regression green (three examples + both templates, source and bundled, kernels byte-identical), prune reviewed (Sky bundled-but-unused-by-a-film is kept: it was built, measured, and rejected *for this composition* with the rationale recorded — that is used knowledge, not speculation; quality tiers remain unbuilt by design with their rule pre-decided). Phase 3 — film language — is next.

## 0.56.0

### added
- **explainer-video 0.11.0 -> 0.12.0**: Phase 2 (cinematic 3D) opens and its spike gate is met — `examples/toybot-walk.html`, a cel-shaded character with an analytic IK walk, rack-focus depth of field, and bloom, rendered through a post-processing chain that **passes the byte-determinism check with the chain enabled**, source and bundled.

  `build.js vendor` now bundles the composer classes onto the THREE namespace (`EffectComposer`, `RenderPass`, `UnrealBloomPass`, `BokehPass`, `OutputPass`) — always included, one bundle, no second vendor file to drift. The hard rule ships in the vendor comment and the new "cinematic kit" section of `references/style-3d.md`: **no temporal passes, ever** — TAA and accumulation blur carry state across frames and break the seekTo contract; every bundled pass is per-frame pure, and smoke.js is the enforcement.

  The spike earned four recorded lessons the docs now carry: the gait's plant grid must anchor at the walk's START (anchored at the origin, the first frame's target sat 16 units ahead and the IK swung both legs horizontal — the contact sheet caught it); hemisphere light washes toon bands out (toon quantizes directional light only — measured, energy shifted to the key); the inverted-hull outline shell exposes every geometry intersection seam (clear the joins); and a payoff beat's events must be sequenced, not simultaneous (the first cut ran the hop and the orb glow together and neither read — now anticipation → hop → land → settle → glow). Rack focus is computed per frame from live camera distances and lerped between subjects under a bump — pure, and the cheapest big "filmed" win in the kit.

  Committed as a 0.13 MB animated AVIF (moving camera — WebP's punishing case), embedded in the README where it doubles as the second observation the animated-AVIF-inline evidence chain has been waiting for. Roadmap item 10 (committed character/moving-camera example) closes with this. Quality tiers deliberately deferred with the rule pre-decided (determinism and shipping run at FINAL); remaining in phase: procedural-sky IBL, matcap/physical packs, instanced geometry.

## 0.55.0

### added
- **explainer-video 0.10.0 -> 0.11.0**: the Phase 1 proving film ships, and Phase 1 of the generalization plan closes at its gate.

  `examples/one-scene-every-format.html` — the plugin explaining its own pipeline on the Canvas2D backend in the paper-cutout pack: 20.8s, six beats of varied duration, held camera, committed as a 0.96 MB WebP and a 0.10 MB AVIF (verified animated, 250 frames). Every beat carries its idea in geometry: the beats table draws itself in and *retimes on screen* (stretch one duration, the downstream segment shifts — accumulation shown, not asserted); one scrubber spanning two beats drives the mini-scene, the ruler dot, and the capture row from a single expression; captured frames each hold the sun pose from their capture instant; the frames become the four delivery chips; the retime makes the chips answer.

  The film went through the full method and the method caught things: the contact sheet flagged a middle-third violation (the table is beat 2's subject and sat on the top rail during its own beat — it now owns the center, then migrates), a false color pairing (chip four wrapped onto chip one's accent; it is now a paper chip), and a timid title motif; the consecutive-frame strip caught the table migration tangled with the stage's entrance (now sequenced: clear first, enter second); the motion profile shows varied per-beat energy and zero dead air; the spanning scrub crosses its beat boundary without a stall by construction.

  One bracket upgraded from artifact to observation: with the sampling race fixed, the dynamic-range lint's 0.0 reading on this film is a genuine known-good-below-the-floor case — flat paper-and-ink design sits below a floor bracketed on 3D renders while reading perfectly. The threshold note and the paper-cutout pack record it as the measured fact it now is.

  Phase 1 exit checkpoint: harvest done (threshold note, pack hazards, kernel-comment rules), release cut (this one), regression green (`skill-retrieval.html` passes smoke untouched, 0 warnings; template kernels byte-identical), prune reviewed (`noise1` is consumed by the 2D camera's sway path rather than any proving film yet — kept as part of the camera-energy mechanism, flagged for Phase 3, which formalizes camera energy).

## 0.54.0

### added
- **explainer-video 0.9.0 -> 0.10.0**: style packs, the kernel made drift-proof, and the STYLE split completed on both backends.

  `references/styles/` ships three packs — `paper-cutout` (the 2D default, now documented as a choice), `blueprint`, `neon-dark` — each a swappable `STYLE` block plus the register rules that make a look coherent (easing temperament, camera energy, fill/line vocabulary, per-pack hazards). The mechanism is verified, not assumed: applying the blueprint block to the placeholder scene's unchanged beats produced a categorically different film, reviewed frame by frame. The swap also caught a real bug — `contrastOn()` assumed dark-ink-on-light-paper, so the first dark pack got light text on its amber fill; it now picks whichever of ink/bg sits farther in luminance from the fill, which is polarity-safe. The blueprint pack's predicted lint hazard became a recorded observation on the same run (dynamic-range 10.2, frames legible).

  The shared kit + beat addressing in both templates is now a marked KERNEL block, byte-identical by construction, and `smoke.js` **hard-fails** when two checked files carry different kernels — the repo family's mirrored-copies-plus-drift-test pattern applied to scene templates. The check's positive control was run: a one-character kernel mutation fails the suite; restored, it passes. The 3D template gains the `STYLE` split (bg, exposure) to match the 2D one, and renders byte-identically after the refactor, verified by frame compare.

## 0.53.0

### added
- **explainer-video 0.8.0 -> 0.9.0**: the second backend. `templates/scene2d.template.html` is a Canvas2D scene on the identical window contract — flat vector, paper-and-ink, born self-contained (no vendor step; `build.js bundle` correctly reports nothing to inline). Every tool ran unchanged against it on the first try: shoot, smoke (contract + byte-determinism + lints), sample review. It carries the first `STYLE` block split out of `CONFIG` — palette, linework, type in one place; timing in `BEATS`; camera energy in `CONFIG` — and a camera rail (`{x,y,zoom}` keyframes anchored to beats) that is the 3D `KEYS[]` convention minus one dimension.

  The deterministic kit gains four easing personalities, identical in both templates (deliberately — they are part of the shared kernel a later extraction pulls out): `backOut` (overshoot-and-settle), `elasticOut` (rings down; budget for payoffs), `quant` (stop-motion — quantize TIME per object, still a pure function of t), `noise1` (seeded 1-D value noise from the frozen R pool, for handheld/idle wobble). The 3D template's rendered output after the kit addition is byte-identical to before it, verified frame-compare.

  Two bugs shipped in the 2D template's first render and were fixed by looking at frames: `backOut(0)` carries positive floating-point residue (~2e-16), so a `pop<=0` gate leaked one frame where the box was invisible but its unscaled label rendered full-size (with `arcTo` spray from a radius wider than the box) — **gate on the raw ramp u, never on an eased value**, and clamp rrect radius; and a white label on the yellow accent — label ink is now picked by the fill's luminance (`contrastOn`), which is a STYLE-layer decision, not a call-site one.

  And one instrument bug, found because its two symptoms looked like scene findings: the dynamic-range lint read **0.0** on the 2D template, and — once, unreproducibly — the crush lint read **100% near black** on the known-good pale 3D template. Neither was an observation. `smoke.js` ran `seekTo` and the pixel sample in separate `evaluate` calls, and the caption-overflow check ends with an async viewport restore whose resize event lands between them — sampling a cleared or stale-sized canvas. Fixed structurally (seek+sample in one JS task, plus waiting for the canvas buffer to settle to the viewport); four consecutive full runs now agree at zero warnings. The near-miss is recorded in the threshold note: the 0.0 reading briefly stood as "flat design measures below the floor," which is exactly the "green control you did not really run" failure — whether a legitimate flat design can sit below the floor is plausible and now honestly marked unmeasured.

## 0.52.0

### added
- **explainer-video 0.7.0 -> 0.8.0**: parallel frame capture — `shoot.js <scene> full 30 --workers N`, or `SHOOT_WORKERS=N` which `build.js` callers inherit. N pages in one browser, each shooting a **contiguous** 1/N chunk so a dead worker leaves one obvious gap instead of a comb the encoder would hide. Phase 1 of the generalization plan opens here (back-to-back mode pulls capture infrastructure forward).

  Both halves measured before trusting, and one refutes the design note that motivated the feature. Correctness: 4-worker output is byte-identical to 1-worker output on the template scene, 48/48 frames. Speed: on a 4-core software-GL container — the exact case roadmap item 5 predicted this would matter for — 25.1s single vs 26.1s with 4 workers, ~1.0x, because SwiftShader already multithreads a single page's rasterization across the cores and extra pages only contend. The remaining win case (many-core, or hardware GL where one page cannot saturate the machine) is plausible and unmeasured; the docs say so instead of promising a speedup that was not observed.

## 0.51.0

### changed
- **explainer-video 0.6.0 -> 0.7.0**: `references/method.md` is re-layered by audience, with no rule changed and no observation dropped — Phase 0 of [docs/internals/explainer_video_generalization_plan.md](docs/internals/explainer_video_generalization_plan.md).

  The file conflated three documents: the universal method, a three.js cookbook, and delivery forensics — which made renderer-specific rules read as universal law (the wash rule shipped exactly that way and was refuted by one dark-palette scene). The split makes the boundary structural: `method.md` keeps what holds for any backend implementing the window contract (the three failure axes, beats and controls discipline, continuity source shapes, semantics tests, the iteration loop, determinism rules — the shared-material purity block moves here from the cookbook, since `smoke.js` enforces it for every backend); `style-3d.md` takes the three.js half (camera rail, lighting wash/crush, texture labels, procedural-asset cookbook, r185 notes, performance envelope) and is explicitly the *first* style reference, not the only possible one; `delivery.md` takes the GitHub forensics (format tradeoffs, encoder settings, the content-type evidence chain). SKILL.md, the plugin README, and one `build.js` comment re-point at the new homes.

## 0.50.0

### added
- **explainer-video 0.5.1 -> 0.6.0**: the review loop gains an instrument for the failure it was blind to, and loses one it could not actually measure.

  The skill's whole method was "render frames and look at them", which only covers failures visible *within* a frame. Two other axes were undocumented: continuity (defects between frames) and semantics (every frame correct and the film still explains nothing). `references/method.md` is restructured around the three axes — the reorganisation is what made the gap visible.

  `build.js sheet` tiles one frame per beat into a contact sheet plus a `.squint.jpg` thumbnail strip. It exists because sampling one frame per beat hides *systematic* error: reviewing a real scene one frame at a time read as six small framing problems, and the same frames tiled read immediately as one bad camera formula generated by a `.map()`. The squint strip finally operationalises the silhouette rule the docs have carried for months with no instrument. `smoke.js` gains advisory caption and exposure lints, and scenes now expose `window.BEATS` so tooling can label frames by beat.

  `build.js motion` was built to flag pops and stalls and **does not**, which is recorded rather than hidden. Measured against a scene with a known discontinuity: whole-frame statistics put it at 1.00x its own local baseline, a step-halving probe exploiting `seekTo` purity gave 1.60 against a 1.69 control, and the stall detector fired at every beat boundary of a *known-good* film because films are supposed to settle between beats. The command was cut back to a per-beat motion profile and dead-air report, which is what those statistics genuinely measure. Continuity review stays a watch-the-loop activity against three documented source shapes. A check reporting "0 pops" on a scene that has one is worse than no check.

  `build.js strip` tiles **consecutive** frames from one narrow window — the partial replacement, and the only pixel-level continuity check that survived bracketing. It exists because the reviewer is usually an agent, which cannot play a film, so "watch the loop" was an instruction the primary user could not follow. Bracketed both ways on a moving-camera scene: a 1.2-unit whole-body jump injected as a positive control is obvious between adjacent cells; the 0.35 rad limb rotation is invisible. It reaches world- and object-level breaks and stops short of limb-level ones, and the range is written into the code rather than implied.

  `build.js sheet` gains a sampling-fraction argument (`sheet <scene> 480 0.95`), which puts every beat at its *end* — where an effect that parks at the end of its ramp and never leaves becomes visible. Both instances of that bug in a real scene were found by accident, on a later frame.

  `build.js avif` adds a much smaller inline output, with a tradeoff the size table does not show. Re-measuring the file's own benchmark: the 12s moving-camera template gives webp 15.16 MB (reproducing the recorded 15.56) against **AVIF 0.28 MB** — 54x — and the held-camera example gives webp 0.195 MB against **AVIF 0.029 MB**. AVIF beats the mp4 on both, because it is an AV1 keyframe-plus-deltas stream rather than a format that collapses when every pixel moves. But an animated AVIF is an AV1 *still-image sequence*, decoded in software frame by frame with no hardware video path, so it costs decode CPU at playback — the repo owner watched it stutter, worse in macOS Preview than Chrome, and decode load scales with the viewer's machine. Bytes-on-disk and decode-cost-at-playback are different costs, and the size measurement was blind to the second. HTML+JS scene, MP4, AVIF, and WebP are presented as **equal peer outputs with no forced default** — each wins on a different axis (interactivity, audio+smooth-everywhere playback, size, best-verified inline rendering), and the choice is the user's per context until the open questions (chiefly whether animated AVIF stays smooth on low-end hardware) are settled. `method.md` carries the full comparison. The encoder `-s` knob is encode-time only; resolution, not `-s`, is the AVIF decode lever.

  Two verification notes, because both could have produced a confident wrong answer. `ffprobe` reports an animated AVIF as a **single frame**, which reads exactly like "the encoder silently wrote a still" and would have invalidated every number above; `avifdec --info` reports the true 132/288 frames and infinite repeat, and a single 960px still of the same scene is 7.3 KB against 290 KB for the 288-frame sequence, so a collapsed sequence would have been off by 40x. Separately, GitHub serving `.avif` as `image/avif` with nosniff is verified by fetch — the same allowlist mechanism the docs already prove makes WebP render and mp4 fail — but that check was against a *still*, and animated-AVIF rendering in a real README currently rests on a single real-world observation, recorded as such rather than as a bracket.

  `build.js video` now reports its output size and, past the 10MB issue/PR attachment ceiling, prints the re-encode command. crf 17 puts anything past ~20s over that ceiling, so the pipeline's own output could not be delivered the way `poster` instructs — a 39s film came out at 19MB and needed a hand-rolled crf 24 pass.

### changed
- **explainer-video**: "budget 3-4 rounds" now says what more rounds do *not* buy. A real scene got four thorough rounds — which converged composition cleanly, catching six genuine defects — and two continuity defects rode through untouched to a confident all-clear. Rounds of looking converge the axis stills can show and do nothing for the other two.
- **explainer-video**: the wash rule was stated as universal law ("every first render comes out overexposed") and is palette-conditional — a dark-palette scene refuted it, and following the doc would have made that film worse. Exposure guidance and the new lint now cover both tails. The caption reading-speed figure was stated in three inconsistent places (25, ~35, and a 27/37 bracket); it is now one number everywhere, warning at 30, on the confirmed-good side of a gap no observation narrows.

## 0.49.1

### added
- **skill-maintainer**: 14 regression tests pinning behaviors fixed earlier today that had **no test at all** — Poetry-layout pyproject, `[tool.*]` tables above `[project]`, populated `## [Unreleased]` sections, keep-a-changelog headings, non-dict marketplace entries, object-form sources, sources escaping the repo root, nameless plugin manifests, bare home paths without a trailing slash, the sanctioned `<HOME>/.claude/...` form, the `skip-file` marker quoted deep in a file, and system account names.

  Six behaviors were changed and none were pinned, so every one could have silently regressed — the exact failure this suite exists to prevent, in the commit that fixed six instances of it elsewhere. Suite goes 29 -> 43 tests. Mutation-checked: reverting the Poetry fallback turns one red, so the new tests are load-bearing rather than decorative.

## 0.49.0

### added
- **path-privacy 0.6.0 -> 0.6.1**: installed git hooks now announce when they are out of date, so the one manual step after a plugin update stops depending on anyone remembering it.

  A plugin update refreshes the scanner the wrapper *calls* but not the wrapper *itself* — its logic is frozen at install time. Before this there was no way to tell an old wrapper from a current one by inspection, so a repo could carry logic fixed several releases ago with nothing to reveal it. The generated wrapper now carries a `# path-privacy:wrapper-version` stamp, and the existing SessionStart hook compares it against the installed plugin, emitting one notice in the repo where it matters. Pre-0.6.0 wrappers have no stamp and are reported as `pre-0.6.0`.

  It deliberately does **not** rewrite the hook. Silently editing a file in someone's `.git/hooks` at session start is the kind of surprise a privacy gate should never spring, and 0.6.0 fixed four ways that installer could damage a repo. Verified across five states: current wrapper silent, unstamped detected, older stamp reported with its version, repo with no hooks silent, and a third party's own pre-commit hook left unclaimed. The directive the hook already injects is unaffected; total cost 47ms.

## 0.48.1

### changed
- **CLAUDE.md**: invariant 2 corrected. It said every path "must resolve under the repo root", which reads as permission for `/Users/<name>/<this-repo>/x` — and that is exactly how five paths carrying a username survived 157 days and a full docs triage. The hooks do permit that shape by design; it still leaks the username. The invariant now says so and points at the whole-tree audit that catches the second class. Invariant 1 gains the clause that editing `tools/<plugin>/src/` *triggers* the cascade — it previously listed `tools/<plugin>/pyproject.toml` as a target without saying what causes one, and skill-maintainer shipped two commits at 0.13.0 through that gap.
- **CLAUDE.md**: fixed three self-contradictions and a stale date. The working agreements listed `env-forge` among the disabled SessionStart hooks while invariant 6 correctly calls it deprecated; the "Where to find what" table advertised captured upstream docs two rows above a row stating nothing upstream is copied in; the SKILL.md count was wrong. Last-updated moved from 2026-05-04 despite same-day rewrites.
- **README.md**: `skill-dashboard` was listed in two plugin tables and missing from the install block entirely despite shipping in the marketplace — all 18 plugins are now installable from the README. Removed references to the deleted `docs/reports/` synthesis, and rewrote the `docs/analysis/` description, which still advertised a tagged wiki of domain reports rather than the three files that survived triage.

### added
- **docs/internals/gotchas.md**: two operational hazards that cost real time. `/code-review ultra` with no argument diffs against `origin/main`, so pushing first empties the review target; it also caps at 8,000 lines, which this repo exceeds routinely. Splitting a diff across branches to fit that cap manufactures false positives — reviewers report content as missing when it only lives in the half they cannot see, which accounted for four findings in the 2026-07-21 review. Also: `git add -A` with two sessions in one worktree, which swept work three times and permanently detached two changelog entries from their commits.

## 0.48.0

A nine-angle max-effort review of the previous seven commits returned 26 verified findings, all in code written that day and most of them inside *fixes*. They collapsed to six root causes; fixing the roots rather than the symptoms is what this release does.

### fixed
- **path-privacy 0.5.0 -> 0.6.0**: the installer no longer assembles the hooks path by hand. One `git rev-parse --git-path hooks` call replaces four separate defects: installing into a repo *subdirectory* fabricated a dead `.git/hooks` and reported success; worktrees and submodules crashed with `mkdir: Not a directory` while the changelog claimed they were supported; and a `core.hooksPath` of `<HOME>/hooks` created a directory literally named `~` inside the work tree. It now also **refuses** when `core.hooksPath` comes from global config (a per-repo install would have gated every repo on the machine, and `--uninstall` anywhere would have removed it everywhere) and when the hooks directory is tracked (the wrapper embeds a machine-specific absolute path, so committing it would plant the leak class this plugin polices and hand teammates a path that fails closed).
- **path-privacy**: the fail-closed guarantee was defeated one delegation level down. The wrapper carefully selects an *executable* entry script; that script then found its own scanner missing and exited 0 — `# fail open by design` — so a leak committed with rc=0. Both entry scripts now fail closed, matching the wrapper.
- **path-privacy**: the recovery search reached every neighbouring project on disk. A broken checkout at a checkout in one sibling project directory silently ran another sibling project's scanner — arbitrary sibling code, or on a shared machine another user's, executed as a commit gate. It also matched `<plugin>.backup` snapshots, which sort *above* the real directory. Group 1 is now the frozen tree itself, and the cache group sorts by the version component alone rather than by whole path (where the marketplace directory outranked the version, so `mp-z/0.0.1` beat `mp-a/9.9.9`).
- **explainer-video 0.5.0 -> 0.5.1**: `shoot.js full` recursively deleted its output directory, and that directory comes from `FRAMES_DIR` — so `FRAMES_DIR=. shoot.js scene.html full` erased the scene file and everything beside it. Reproduced independently by three reviewers. It now deletes only `f#####.png`, which is all the stale-tail bug ever required; verified the stale tail is still cleared and a non-frame file in the same directory survives.
- **explainer-video**: `range 0 60` — re-shooting the opening beat, the documented purpose of the mode — threw `invalid start frame: "0"`, because the new validator conflated "not a number" with "zero" on a 0-based index. And `sample` was left out of that validation entirely, still writing `sample_NaN.png` with exit 0 on the exact typo cited as the validator's motivation.
- **explainer-video**: `video()` read `frames/` while `shoot.js` honoured `FRAMES_DIR`, so a hand-run reshoot wrote one place and the encoder read another — silently shipping the previous film.
- **skill-maintainer 0.13.0 -> 0.14.0**: `check_path_privacy` was **built on a wrong diagnosis**, stated as fact in three places. The scanner does not "only see added lines" — `--staged` reads whole files. The 157-day leak survived because `find-external-paths.sh` exempts paths resolving *inside* the repo root, which is exactly what its documented rule says. The two checks enforce genuinely different rules — resolves-outside-root versus carries-a-real-username — and the docstring now says so instead of claiming a parity that never existed.
- **skill-maintainer**: the audit missed a bare `/Users/<name>` with no trailing slash; exempted any file merely *quoting* the `skip-file` marker anywhere (including this CHANGELOG and path-privacy's own SKILL.md); dropped non-ASCII filenames by splitting `git ls-files` on newlines instead of NUL; and returned `[]` on git failure, emitting no row at all so the check silently vanished from the suite.
- **skill-maintainer**: `check_changelog_version` hard-failed Poetry-shaped repos that the regex it replaced handled, and still failed a *populated* `## [Unreleased]` section — only an empty one passed, defeating the exemption's stated purpose. `check_version_alignment` dereferenced marketplace sources that escape the repo root (verified reading `/etc` via a traversal source).
- **skill-maintainer**: the version cascade was never run for this plugin — `plugin.json`, the marketplace entry and `pyproject.toml` all sat at 0.13.0 while its source changed across two commits, so `marketplace update` would not have refreshed installed users at all. The omission is listed in the common-mistakes section of the document being edited in the same branch.

## 0.47.0

### removed
- **docs/analysis**: deleted the seven bannered survivors and `docs/reports/claude_ecosystem_synthesis.md`. `docs/` is now 184K across the essentials.

  This reverses the compromise reached earlier the same day, and the reasoning is recorded in `docs/analysis/log.md` rather than left to look like churn. **The banners did not work.** Retrieval here is frequently grep-based, and a grep hit lands mid-file, below the banner, on unbannered stale prose — the mitigation only protects a whole-file read, which is not how these are consumed. `subagents_and_agent_teams.md` still asserted "subagents cannot spawn other subagents" as a key constraint in its body, which is false and load-bearing for anyone designing delegation.

  Everything durable in the deleted cohort is superseded by `.skill-maintainer/best_practices.md` (which is *maintained*), duplicated by tracked upstream snapshots, shipped in `skills/mcp-apps/references/`, or describes in-repo code that is its own source of truth. The synthesis report went too: 13 of its 15 analysis links were dead, and a 706-line synthesis of documents that no longer exist is worse than none.

  **Kept:** `data_centric_agent_state_research.md` — the one irreplaceable file, holding the comparative survey and DuckDB rationale behind `tools/agent-state`, where `VISION.md` asserts the conclusion but not the comparison. Plus `mcp_protocol_and_servers.md` (verified current) and the log.

### added
- **docs/internals/plugin-patterns.md**: a hook anti-pattern section salvaged before deletion — but only the items that are environmental or that we verified independently. Importing the unverified remainder into a maintained document would have moved the problem rather than solved it. Includes the lesson from this session's own leak: a diff-scoped check cannot enforce a whole-tree invariant.

### fixed
- **branches**: removed two stale local review branches and their worktrees. Verified first that neither held unmerged content — both were squashed snapshots strictly behind `main`. Also confirmed `origin/claude/romantic-brattain` (Feb 2026) is fully landed: its `mcp-app` sources are byte-identical to `main`'s copies under `apps/`, and its `commands/` became `main`'s `skills/`. It reads as unmerged only because the `apps/` restructure moved the paths.

## 0.46.0

### added
- **skill-maintainer**: `check_path_privacy` — a whole-tree audit for absolute home paths carrying a real username, wired into `test_repo_hygiene`.

  *(Correction, 0.88.0: the mechanism stated below is wrong and was wrong when written. `--staged` has collected file names via `git diff --cached --name-only` and scanned those files' **full content** since 0.1.0 — it has never been a diff scan. The real limit is narrower: the hook only sees files in the staged set, so a leak in a file you never touch is never scanned. The conclusion — that a whole-tree audit was needed — holds either way, which is why the error survived review. Verified against the 0.1.0 implementation.)*

  The path-privacy pre-commit hook scans the **diff**, so it only ever sees added lines. A leak introduced before the hook existed, or in a file since touched only elsewhere, survives indefinitely. That is not hypothetical: five absolute paths carrying a username sat in a tracked doc for **157 days** and through a full docs triage, because every commit that touched the file added lines somewhere else. The hook was working exactly as designed; the invariant it claims to enforce ("every path in repo content") is broader than what a diff scan can reach.

  This audits content rather than changes, so a pre-existing leak cannot hide behind a clean diff. It honours the same `path-privacy: skip-file` and `path-privacy: ignore` markers the plugin's scanner uses, so the plugins that legitimately contain these patterns stay silent, and treats `/Users/Shared`, regex/substitution syntax, and conventional stand-in names as non-leaks — a check that cries wolf gets bypassed, and this one is meant to gate.

  Seven regression tests, both directions, and mutation-tested: neutering the check turns two of them red.

## 0.45.1

### fixed
- **docs**: reconciled repo documentation with the repo's actual state, from a parallel consistency review.
  - `CLAUDE.md` and `docs/internals/gotchas.md` both said **four** plugins are disabled via `enabledPlugins`; `settings.json` has three. Corrected to three, with the reason recorded: `env-forge` is *deprecated*, not disabled — the `renames` map handles its removal, and an `enabledPlugins` entry for it would be auto-deleted by Claude Code, mutating a tracked file.
  - `README.md` listed `explainer-video` twice in the plugins table with conflicting descriptions, twice in the install block, and twice in the invocation list. It also still advertised an "environment synthesis" grouping whose section was removed with env-forge, and omitted `pyright-autoconfig` entirely despite it shipping in the marketplace.
  - `docs/internals/plugin-versioning.md` contradicted itself: the header still described a four-source cascade, and the worked example walked the reader through adding `metadata.version` and `metadata.last_verified` to six SKILL.md files — twenty lines after the document says the field was removed and must not be re-added. A reader skimming for the procedure would have landed on step-by-step instructions to do the forbidden thing. The example is now seven files with no SKILL.md, and the common-mistakes list reflects the checks that actually exist.
  - `docs/internals/upstream_drift_backlog.md` still listed `renames` as absent and the hook-entry count as 9; both were resolved or wrong.

## 0.45.0

### fixed
- **skill-maintainer**: discovery matched `SKIP_DIRS` against the **absolute** path, so a repo checked out beneath any directory named `internal`, `coderef`, `.venv`, `node_modules` or `_deprecated` found zero skills and zero plugins and the suite reported green having scanned nothing — the worst failure available to a checker, since it looks exactly like success. Matching is now relative to the repo root. Verified both ways: a nested repo under `internal/` is now visible, and this repo still excludes its own `internal/` and `_deprecated/`.
- **skill-maintainer**: restored the `.backup` **suffix** rule, which the above refactor dropped — `plugin-toolkit.backup` is a snapshot directory, not a unit to check. Both rules now live in one place instead of one of them getting lost in a refactor, which is precisely what happened.
- **skill-maintainer**: `check_version_alignment` no longer aborts the entire run on a malformed marketplace entry. A non-dict entry, or the object-form `source` the official schema allows (`{"source": "github", ...}`), raised out of the function and killed every later check in `test_repo_hygiene` with no summary printed. External sources are skipped (no local manifest to compare); malformed entries are reported.
- **skill-maintainer**: a plugin whose `plugin.json` parses but has no `name` was silently invisible to the reverse sweep — contradicting the "do NOT skip" reasoning one branch above, in the check whose whole purpose is finding plugins nobody can install.
- **skill-maintainer**: `check_changelog_version` parsed pyproject with a regex that took the first `version = "..."` anywhere in the file, so a `[tool.*]` table above `[project]` won; and single quotes, missing spaces, or a dynamic version made it return success while unable to run at all. Now uses `tomllib`, fails loudly on an unparseable file, and treats declared-dynamic versioning as the legitimate shape it is.
- **skill-maintainer**: the changelog check rejected keep-a-changelog headings (`## [1.2.3] - 2024-01-01`), prerelease suffixes, and a conventional `## Unreleased` section above the top version. This tool runs against arbitrary repos via `--dir`, where all three are standard — a false positive on a correct changelog is how a gate gets ignored.

Each change was verified against a constructed instance of the failure it addresses, and against a legitimate configuration it must not fire on.

## 0.44.0

### fixed
- **path-privacy 0.4.0 -> 0.5.0**: five installer defects found by the parallel review, two of which could affect a user's own repository and shipped in 0.4.0.
  - **`core.hooksPath` repos got a successful-looking no-op.** The installer wrote to `.git/hooks` regardless, so every husky/lefthook repo printed "installed" and git never ran the hooks — the plugin promised a gate it never installed. Same fail-open class as the wrapper bug 0.4.0 fixed, one level up, and it would have shipped alongside that fix. Now honours `core.hooksPath` and says where it installed.
  - **The installer wrote through symlinked hooks.** `.git/hooks/pre-commit` symlinked into the work tree (`ln -s ../../scripts/pre-commit.sh`) meant `cat >` followed the link and overwrote the user's *tracked source file* with the wrapper, which they could then commit. The link is now replaced, never written through.
  - **Discovery picked a candidate before testing executability**, so a newest copy with the exec bit lost blocked every commit while a working older copy sat beside it. And `sort -V` over a merged list compares the marketplace directory before the version, so a stale copy from another marketplace outranked a newer one from your own tree. Groups are now tried in order, newest-executable-first within each.
  - Install refuses rather than silently overwriting when a `.local` already exists and the live hook is not ours; uninstall no longer restores over a hook the user wrote themselves.
  - Worktrees and submodules (`.git` is a file, not a directory) are no longer rejected with a misleading "not a git repo".

Verified by control in throwaway repos: the user's tracked source survives a symlinked-hook install, the wrapper lands in `.husky` and not `.git/hooks`, a real leak is still blocked, clean content still commits, and discovery falls through to an executable older copy rather than failing closed.

## 0.43.0

### fixed
- **explainer-video 0.4.3 -> 0.5.0**: findings from a parallel review pass, most of them defects that shipped.
  - **The committed inline demo was corrupt.** `examples/skill-retrieval.webp` played 22.8s of animation for an 11.0s scene — it contained frames from an unrelated render. Root cause: `shoot.js full` never cleared its output directory, so a re-render producing fewer frames left the previous run's tail in place and the encoder appended it. `full` now clears (`range` deliberately does not — partial re-shooting is its purpose). Artifact rebuilt: 204 KB, 11.0s. The size and beat-count claims in README/SKILL.md/method.md described the corrupt file and are corrected.
  - **`bundle` could destroy the source scene.** `bundleName` returns its input unchanged when the name does not end in exactly `.html`, so `bundle scene.htm` wrote the inlined output over the source and reported success. Now refuses.
  - **A highlight was fully lit before its beat began.** Widening the sweep to ±0.9 to fix a flicker put slab 0 at `bump(0,-0.9,0.9)` = 1.0 for the entire title card. The sweep now starts off the left end. A regression introduced by an earlier fix.
  - **Frame determinism was violated by text antialiasing.** Chrome re-rasterized the DOM overlay with a different AA mode after opacity round-tripped through 0, so the same `t` differed by a few pixels depending on seek *order* — breaking the frames-in-any-order guarantee for any frame with overlay text. `will-change:opacity` pins the layer.
  - Bad numeric args reported success while doing nothing (`full 3O` printed "done: NaN frames", exit 0); `loop` leaked temp dirs on error paths; `file://` URLs broke on `#`/`%` in a path; `ss`/`bump` returned NaN for a zero-width span; `during`/`secAt` bypassed the unknown-beat guard; Chromium build directories sorted lexicographically.
  - Corrected a comment claiming the explicit file list dodges `ARG_MAX` — `execFileSync` argv goes through the same `execve` limit. What it actually buys is deterministic ordering and a loud empty-match failure.

## 0.42.1

### added
- **explainer-video 0.4.2 -> 0.4.3**: `method.md`'s "Build the control" section gains "Verify the control actually ran". The rule as shipped had its own failure mode and did not warn about it: a control testing the wrong thing still returns a number, and the number looks like evidence. Three real instances across today's work — a blank-scene check that never modified the scene, a does-it-fail-without-X run where X was still present, and a summarizing fetch whose silence was read as absence. A green control you did not really run is worse than no control, because it converts an open question into a settled one that nobody revisits.

## 0.42.0

### fixed
- **path-privacy 0.3.2 -> 0.4.0: three defects in the fail-closed wrapper, all found by cross-review, all landing before the push because the marketplace update is what arms the fuse.**
  - **The `rm` remediation destroyed the user's own hook.** The wrapper also *chains* `<hook>.local`, which is where an existing pre-commit hook is preserved at install time. Telling a blocked user to `rm` the wrapper silently took their previous hook with it — our gate fails loudly, theirs died quietly. The message is now conditional: with a `.local` present it says `mv <hook>.local <hook>` and states that this restores what they had before path-privacy.
  - **Discovery assumed a marketplace-cache install.** A local checkout or `--plugin-dir` install has a frozen path that never lived under `<HOME>/.claude/plugins/cache/`, so once it broke the glob found nothing and the user was hard-blocked by a message naming a directory their install was never in. Discovery now searches the frozen path's own tree first (sibling version dirs, then the tree itself) before falling back to the cache, and the error names both locations.
  - **The message had no "why now."** It fires roughly 14 days after a plugin update, on an unrelated commit. It now leads with the cause — the plugin updated and the old cached copy was cleaned up — which turns a mystery block into a recognisable event.
- Verified by control across four paths: `.local` present (user hook runs, `mv` advice shown), local-checkout frozen path with a sibling version (recovers and still blocks a real leak), no `.local` with every discovery source neutered (fails closed, `rm` advice), and the ordinary valid-path case. Two of those controls were wrong on the first attempt — one committed clean content so the exit code proved nothing, and one left the real cache glob intact so the hook legitimately recovered — and were re-run before being recorded.

## 0.41.1

### fixed
- **path-privacy 0.3.1 -> 0.3.2: the wrapper's fallback picked the lexicographically last cached version, not the newest.** Found by cross-review. Glob order is lexicographic, so with `0.1.9` and `0.1.10` both cached the last-wins loop selected `0.1.9` — the older scanner. Verified against a constructed cache: last-wins picks `0.2.0` from `{0.1.6, 0.1.9, 0.1.10, 0.2.0, 0.10.0}` while `sort -V` correctly orders `0.1.6 -> 0.1.9 -> 0.1.10 -> 0.2.0 -> 0.10.0` and picks `0.10.0`. Now uses `sort -V | tail -1`. Narrow — the fallback only runs once the frozen path is gone, which usually leaves one version — but it is reachable when two updates land inside the 14-day orphan window, and "newest" has to mean newest. All three controls re-run after the change: frozen path valid passes, frozen path broken self-heals and still blocks a real leak, nothing found fails closed with the full diagnostic.

## 0.41.0

### added
- **`check_changelog_version`**, proposed by the concurrent session during cross-review: the top `## X.Y.Z` heading in `CHANGELOG.md` must equal the root `pyproject.toml` version. Both of their changelog failures — an insert that matched `# changelog` instead of the version heading, leaving an entry with no version, and the repo version left unbumped — violate that single comparison. Nothing in the repo would have caught either: `check_version_alignment` compares plugin manifests, and the pre-commit only warns when content changes with no version file staged, and version files *were* staged. It is exact rather than heuristic, so it can legitimately gate, and it returns no findings when either file is absent. Verified by reconstructing both historical failures against the real repo, not just synthetic fixtures: each is caught with a specific message, and the tree goes green again on restore. Five regression tests, written red-first.

## 0.40.5

### fixed
- **`check_version_alignment`: two defects found by cross-review, both in the newest logic in my half.**
  - `lstrip("./")` strips a character *set*, not a prefix. A marketplace `source` of `./.claude/thing` became `claude/thing`, so the check would report "plugin.json does not exist" while pointing at a path that was never right — sending someone to hunt a missing file rather than a mangled one. Every current entry happens to be safe, so it passed today and would have broken the first time a plugin lived under a dot-directory. `removeprefix("./")` is the fix. Same class as the `$&` bug in the bundler: a string method doing something adjacent to what it reads like.
  - The reverse sweep swallowed unreadable manifests with `except Exception: continue`. The forward loop reports them. So a corrupt `plugin.json` made a plugin invisible to the exact check meant to catch plugins nobody can install, and the check reported green — the same silent-drift failure the function exists to prevent. It now reports the unreadable manifest.
- Both covered by regression tests written red-first (17 tests, all green).

## 0.40.4

### fixed
- **explainer-video 0.4.1 -> 0.4.2**: three instances of post-refactor staleness, all documentation that never caught up with the 0.2.0 beats change.
  - `references/audio.md` told you to "slow the beat down in `CONFIG`" — but `CONFIG` has held no timing since 0.2.0, and the same file says four lines later that the beats table is the single source of timing truth. Following it literally sent you to the wrong file to find nothing.
  - `references/audio.md` also keyed narration by numeric beat index (`{beat: 1}`) when beats have been named since 0.2.0. Rewritten around named beats and aligned with the roadmap's `narration-drives-timing` design, which is implementable only *because* beats are named data — a measured clip duration cannot be written back into a positional index.
  - `docs/internals/explainer_video_roadmap.md` still specified the addressing helper as `u()` in four places. It was renamed to `ramp()` during the refactor itself, to avoid shadowing the local `u` in `setCamera`.

The first was found by cross-review, the other two by sweeping for the same class afterwards — including one in a file the original sweep had looked at and passed. A sweep scoped to the symptom rather than the class.

## 0.40.3

### fixed
- **explainer-video 0.4.0 -> 0.4.1**: two defects found by cross-review, both in the newest code.
  - **`loop` and `poster` failed on a fresh checkout.** Neither ensured `three.global.js` existed before rendering, so a clean directory produced `THREE is not defined` — loud, but pointing at the scene contract when the cause was a missing build step. `bundle()` had auto-vendored since the start and `smoke.js` gained a conditional version later; the two newest entry points never got it. Now share an `ensureVendor` guard using the same needs-three test, so a non-three backend is still never forced to build a bundle it will not load.
  - **`FRAMES_DIR` was honoured by `shoot.js full` but ignored by `range`.** `range` is the mode a user runs by hand to re-shoot a few seconds after an edit, so the override added in 0.4.0 to stop `loop` clobbering `frames/` silently did not apply in the one case someone drives manually. Both modes now use it.

Both verified by control from clean directories: `poster` and `loop` complete with no vendored bundle present, and `FRAMES_DIR=alt shoot.js range` writes 5 files to `alt/` and 0 to `frames/`.

## 0.40.2

### changed
- **Sharpened the summarising-fetch caveat into a categorical rule.** It read as a caution about large pages losing a sentence. The stronger and correct form, from the concurrent session: **a summary can never source a claim that the docs do not say something**, because absence is precisely what summarisation discards — its silence is not evidence. Not a caveat, a category error. Both sessions made it the same way on the same day: one summarising query against the 230KB hooks page returned "not stated for any hook type" for a sentence that appears three times in the raw text. Recorded in `plugin-patterns.md` and `best_practices.md`.

## 0.40.1

### changed
- **Timeout citations are now verbatim quotes plus a URL, not line numbers into a gitignored snapshot.** The concurrent session could not reproduce the Agent SDK callback sentence via a summarising fetch of the hooks page and said so rather than accepting the correction — the right call. It does reproduce: the sentence sits under `### PreToolUse` in the raw page at <https://code.claude.com/docs/en/hooks>, which is over 230KB, and a single sentence is easy to lose in summarisation. But the citation form was the real problem: the snapshots are gitignored and renumber on every fetch, so a line number is unverifiable by exactly the person who most needs to check it. Both quotes are now inline, and the guidance notes to grep the raw text rather than trust a summary.
- **Corrected an overstatement of my own.** I described the Agent SDK callback case as "the one directly-analogous documented case". It is the same *event* (`PreToolUse`) on a different *mechanism* — an SDK callback, not a `command` hook in `hooks.json`. That makes it weak evidence, not an analogy, and the guidance now says so. The conclusion is unchanged: command-hook timeout behaviour is unspecified, and the 30s value was chosen so that the unknown cannot matter.

## 0.40.0

### fixed
- **Corrected an inference I had written into guidance as documented fact.** The previous entry claimed a canceled `PreToolUse` hook "reports no decision, so the call proceeds and the check fails open". That is not documented for `command` hooks. It was generalized from the HTTP-hook section, which fails open but opens with "Error handling differs from command hooks" and closes with "Unlike command hooks" — a passage that explicitly excludes the case I applied it to. The one directly-analogous documented case says the **opposite**: an Agent SDK callback hook on `PreToolUse` that exceeds its timeout *blocks* the tool call. Command-hook timeout behaviour is genuinely unspecified, and `plugin-patterns.md` and `best_practices.md` now say so and name both conflicting passages. Caught by the concurrent session; it is the same failure the docs triage existed to remove — reading an adjacent section and treating it as the source.
- **path-privacy 0.3.0 -> 0.3.1: `PreToolUse` timeout 3s -> 30s.** With the failure mode unknown, the value should be chosen so it cannot matter. Crossing {fails open, fails closed} against {too short, too long} leaves exactly one catastrophic cell — too-short *and* fails-open, a silent bypass where the gate skips and the write proceeds with no message. Every other outcome is a visible stall or a loud block. So for anything that gates, err long: 30s is ~120x headroom over the measured 0.25s, still diagnosable inside one turn, and 20x below upstream's own 600s default. The earlier 3s bet on a failure mode we cannot confirm. `pyright-autoconfig` deliberately stays at 5s — it gates nothing, has no silent-bypass mode, and its only real risk is stalling session start.
- Also corrects the framing in 0.38.0: upstream's default is 600s, so `3000` was five times the default rather than an obvious outlier, which is part of why it read as plausible through review and a version cascade.

## 0.39.0

### fixed
- **path-privacy 0.2.1 -> 0.3.0: the git-hook wrapper died on a 14-day fuse after every plugin update, and failed open when it did.** `install-git-hooks.sh` froze an absolute path to the scanner at install time, pointing into the **version-stamped** plugin cache (`.../path-privacy/0.1.6/...`). Updating the plugin writes a new version directory and orphans the old one, which Claude Code deletes 14 days later (plugins-reference: "removed automatically 14 days later"). For those 14 days the hook silently ran the *old* scanner, so a fix to the scanner never reached the repo; after 14 days the guard `if [ -x "$PATH_PRIVACY_SCRIPT" ]` went false and the wrapper `exit 0`'d — the leak gate silently doing nothing, in every repo it had ever been installed into. Verified by constructing the pruned state: the old wrapper exits 0 with no output.
- The generated wrapper now re-resolves to the newest installed copy when the frozen path is gone, and if it still cannot find the scanner it **fails closed** with a message naming what it looked for and how to reinstall or remove it. A leak gate that cannot run must not let the commit through quietly. Verified across three cases: frozen path valid (passes), frozen path broken (self-heals via discovery and still blocks a real leak), no copy anywhere (exits 1 with remediation).

### note
- **Existing installs are not self-correcting.** Any repo where `install-git-hooks.sh` was run before this release still has the old frozen-path wrapper. Re-run the installer there to pick up the hardened version.

## 0.38.0

### fixed
- **Two hook timeouts were wrong by 1000x and would have gone live with the next marketplace update.** Upstream documents `timeout` as *seconds*; `path-privacy` had `3000` (fifty minutes) on its `PreToolUse` hook and `pyright-autoconfig` had `5000` (eighty-three minutes) on `SessionStart`. Both were wrong from the commit that introduced them, survived review and a version cascade, and were spotted only because the exec-form conversion moved the field next to `args` in a diff. Corrected to 3 and 5. The `PreToolUse` one had the real blast radius: it gates every Write and Edit, so a hung hook stalls the session for the whole window — and a canceled hook reports no decision, so the call proceeds and the check fails open. A wrong timeout does not make the gate stricter, only the stall longer. Values were measured before being set: the path-privacy scan runs 0.25s against a deliberately extreme 1.4MB/20,000-line payload (12x headroom at 3s), pyright-autoconfig 0.03s (~170x at 5s).

### added
- **The seconds unit is now stated in `plugin-patterns.md` and `best_practices.md`.** Milliseconds are the instinct from every other JS API in this repo, which is why it needed saying — and this was a documented field nobody had checked against its own documentation.

## 0.37.3

### changed
- **The exec-form rule in `plugin-patterns.md` now covers plugin scripts, not just `hooks.json`.** It described a `hooks.json` convention when the underlying problem is spawning a subprocess with an interpolated path, which plugin scripts do too via `execSync`. The rule addressed one surface of a two-surface bug; explainer-video's scripts were living proof of the other. Adds the `execSync` -> `execFileSync` array-argument form, notes that quoting fixes the space case but leaves `;`/`$`/backticks, and records two traps in the same family: a shell-expanded glob silently caps out at `ARG_MAX`, and a derived output written into a source directory destroys the source (a preview build overwriting the full-resolution frames behind an mp4).

## 0.37.2

### fixed
- **explainer-video 0.3.4 -> 0.4.0**: fixed the four defects that were about to be handed to a code review as known-but-unfixed, which is the wrong trade — a review's value is finding what you do not already know.
  - **Shell-free process calls.** Every `execSync` with an interpolated path became `execFileSync` with an argument array. A directory containing a space broke the build outright. This is the same class as the exec-form hook rule added to `plugin-patterns.md` today; that rule covers `hooks.json` and says nothing about plugin scripts, so the guidance addressed one surface of a two-surface bug.
  - **`build.js loop` no longer destroys `frames/`.** It reused the shared directory, so producing a README loop silently overwrote the full-resolution frames a previous `build.js all` had shot — deleting the source of your mp4 with no warning. It now shoots into its own `.loopsrc`, via a new `FRAMES_DIR` override in `shoot.js`.
  - **No shell glob in the WebP encode.** `img2webp ${tmp}/*.png` was never tested past ~100 frames; a 60s film at 12fps is 720 files and can exceed `ARG_MAX`. Now an explicit file list, which also fails loudly when scaling produced nothing.
  - **`smoke.js`'s blank-frame floor derives from the viewport** instead of a hardcoded 6000 bytes, which silently mis-calibrated the moment the viewport changed.

All four verified by control, per the rule added in 0.3.4: `frames/` confirmed intact at 275 files across a `loop` run, a build run to completion from a directory with spaces in its name, and the blank-scene check confirmed still failing (1453 bytes against a derived floor of 5760).

## 0.37.1

### changed
- **The staleness banners added in 0.37.0 were reframed after review from the concurrent session.** They read "Stale -- not re-derived", which describes pending work; in three months that becomes furniture nobody reads. All eight documents are the same case -- wrong in places, still the best available, no rewrite scheduled -- so the banner now says exactly that and states it is permanent rather than a to-do. `data_centric_agent_state_research.md` is reframed as a historical record of what was considered, in the same spirit as `log.md`. The critique was correct and self-directed: a banner with nothing forcing action on it is the same pattern as the permanently-red board.

### added
- **`maintenance.md` records the availability-vs-staleness trade** behind deleting the local upstream copies, rather than leaving it implied. An absent doc announces itself; a stale undated doc teaches something false with confidence. The section says plainly not to quietly re-add local copies on a fetch failure, and what to do instead.
- **`maintenance.md` gains "Designing a new check"**, from two rules earned in the concurrent session. *A proxy can reject but cannot approve*: give a heuristic authority only over its confident region and stay **silent** elsewhere, because a warning band over the uncertain region trains people to skim past the loud case too. *Build the control*: a technique needs a without-it comparison, a check needs a constructed failing case, a threshold needs bracketing by a confirmed-bad and a confirmed-fine observation.
- **A fourth instance of the decayed-signal pattern is recorded** in the drift backlog: freshness checks detect drift over time and catch nothing that was wrong on the day it was written. `method.md` has always specified 3-4 seconds per beat while the example shipped at 2.4/2.4/3.2, under its own floor. Nothing was stale; the doc and the artifact disagreed from the start. We have no general consistency check for a documented threshold against the artifact it governs.

## 0.36.4

### added
- **explainer-video 0.3.3 -> 0.3.4**: `method.md` gains "Build the control", generalizing a discipline that had appeared three times as separate instances. For any claim that a technique improves something, build the version without it and confirm that one is worse — otherwise you have measured your own effort rather than the effect. Three forms tabulated (technique needs a without-it render, check needs a constructed failing case, threshold needs bracketing above and below), each with the worked instance that changed an outcome: the blank-frame check verified against a deliberately blank scene, the caption floor bracketed by a watched-bad 37 CPS and a watched-fine 27 CPS, and phase-locking flagged as claimed-but-uncontrolled. Names the seductive failure it prevents — applying a technique, seeing a good result, and concluding the technique caused it when the result would have looked fine anyway.

### changed
- **roadmap**: recorded that the ~35 CPS caption floor is bracketed by observation on both sides, which the original 17-21 threshold never was, but is still one viewer and two data points. Tighten as more scenes get watched rather than treating it as settled.

## 0.37.0

### removed
- **`docs/` triaged: 26 files deleted, 972K -> 400K.** All 20 of `docs/claude-docs/` -- frozen 2026-02-19 copies of upstream Claude Code docs that had become roughly a third of current content (hooks 64KB -> 235KB, plugins-reference 24KB -> 88KB) while carrying **no date header**, so nothing signalled their staleness. They were wrong in load-bearing ways: `allowed-tools` described as restricting when it grants, hook exit 0 described as success when it reports no decision. Plus six analysis reports: three were the same Anthropic skills-guide PDF restated three times (superseded by `.skill-maintainer/best_practices.md`), `self_updating_system_design.md` described a CDC pipeline never built, and two were point-in-time snapshots pinned to a pre-reorg layout.

### changed
- **Upstream docs are no longer copied into the repo.** `settings`, `permissions` and `mcp` -- the three deleted pages that had no live tracking -- were added to `upstream_urls`, bringing tracked pages to twelve. `skill-maintain upstream` fetches them into gitignored state with per-page deltas. A stale copy is worse than no copy: a clone can refetch in seconds but cannot know that what it is reading is five months old.
- **Eight surviving analysis reports gained staleness banners** naming their specific false claims rather than a generic warning. They share one shape -- durable original synthesis (anti-pattern catalogs, design checklists, comparison matrices) sitting on rotted API specifics. `subagents_and_agent_teams.md` is the sharpest: it asserts three times that subagents cannot spawn subagents, which current docs reverse, and that is load-bearing for delegation design.

### fixed
- **Two documents linked from `CLAUDE.md` as live references were wrong.** `cross_surface_compatibility.md` claimed PreToolUse "exit 0 = approve" (it reports no decision; approval needs `permissionDecision: "allow"`). `mcp_apps_and_ui_development.md` cited `coderef/ext-apps/` and `coderef/mcp-ui/`, neither of which exists -- the real paths are under `coderef/mcp/`. Both corrected in place.
- Link-rot from the deletions repaired across eight files, including relative-path breakage introduced during the redirect; `skill-maintain lint` is clean.

## 0.36.3

### added
- **explainer-video 0.3.2 -> 0.3.3**: `method.md` gains "Where you will be tempted to break this" under the determinism rules. The closed-form requirement is easy to keep until the subject *is* a physical process — any scene depicting momentum, decay, accumulation, charge, wear, growth or trails pulls toward integrating from the previous frame, which breaks `seekTo` purity and beat independence at once. Gives the closed-form replacements (`ω0*exp(-k*(t-t0))` for a coast-down, `count*ramp(...)` for accumulation, N samples of the position function for a trail) and says plainly that physical-metaphor scenes are both the most likely to reach for a simulator and the most likely to expose the divergence on a loop's second pass.
- **explainer-video**: `method.md` gains "Motion that reads vs causality that reads". A sweep only has to be perceived as motion; a beat whose job is "A drives B" fails if the viewer perceives A moving and B moving. The lever is phase and derivation rather than duration — drive B from A's expression, not independently from `t` — and the verification is a control: break the phase relationship deliberately and confirm the broken version reads differently. Marked untested.

### changed
- **roadmap**: the caption lint is redesigned rather than dropped. The surviving rule is general — **a proxy can reject, it cannot approve**. Characters-per-second correctly identified a 37 CPS caption as unreadable and was wrong at 27, so the error was granting its whole range decision authority when it has a confident region and an uncertain one. The lint that earns its place is a floor (~35+ CPS), silent below it with no warning band, reporting the effective window rather than "too long". Not built yet: the JS is stable pending review and this adds to it.

## 0.36.2

### fixed
- **explainer-video 0.3.1 -> 0.3.2**: two items found by the cold run (following `SKILL.md` literally in a clean directory rather than editing files already understood). Step 2's scaffold command used bare `${CLAUDE_SKILL_DIR}`, which expands to empty in a shell and yields `cp: /templates/...: No such file or directory` if an agent copies it verbatim; it is now quoted and annotated as a load-time substitution rather than a shell variable. Step 1's caption guidance was `<70 chars` -- a character count cannot reference beat duration, so the same line is comfortable over 4s and impossible over 1.5s. Replaced with a per-second budget against the caption's *effective* window (beat duration minus fade, minus any `capEnd` trim), marked as observed rather than derived.

## 0.36.1

### fixed
- **explainer-video 0.3.0 -> 0.3.1**: overlay fades now complete **inside** their own beat rather than straddling the boundary. The title fade was centred on `t1`, so title pixels bled 0.3s into the next beat and retiming the title silently moved content into its neighbour. Fixed in the template and the worked example.
- **explainer-video**: retimed the worked example after watching it. It ran 2.4 / 2.4 / 3.2s against `method.md`'s own stated 3-4s-per-beat guidance, and the sweep read as a flicker. Now 3.2 / 4.2 / 3.6, with the sweep highlight widened from ±0.55 to ±0.9 slab-units. Width mattered more than duration — lengthening the beat alone just spaced the flickers further apart.

### added
- **explainer-video**: a "Dwell: measured, not derived" section in `method.md`, recording the two values above as observations rather than rules. Also records that a beat can pass a caption reading-speed check and still be too fast to follow, so motion pacing and caption pacing are separate problems.

### changed
- **explainer-video**: the caption reading-speed lint proposed for a future release is **not** shipping as designed. Its threshold came from arithmetic (17-21 CPS) and was contradicted by one person watching three seconds of video: a 27 CPS caption read fine. If it ships at all it should guard only the egregious case, not act as a pacing tool.

## 0.36.1

### changed
- **docs reconciled with the 0.35.0 process changes.** `CLAUDE.md`, `.claude/rules/plugins.md`, `docs/internals/{maintenance,gotchas,plugin-versioning,plugin-patterns}.md`, and both skill-maintainer READMEs now describe the three-file cascade, `review_interval_days`, the `last_verified` semantics, `_deprecated`, `check_version_alignment`, the `--strict` pre-commit gate, and hook exec form. `docs/analysis/`, `docs/claude-docs/` and `docs/reports/` were deliberately left alone -- they are captured upstream documentation and point-in-time reports, not statements of our conventions.
- **`.claude/rules/plugins.md`** gains the version-cascade, deprecation, and exec-form rules, and now says plainly that upstream requires only `name` in `plugin.json` -- the other four fields are this repo's convention, enforced by our own test suite.

### fixed
- **`CLAUDE.md` had been truncated.** The 0.35.0 edit replaced from invariant 5 to end-of-file, silently deleting the "Where to find what", "State", and "Cross-repo" sections. Recovered from `9bbb7e1` and updated: the doc table gains rows for the versioning doc and the upstream drift backlog, and "State" now describes `review_interval_days` and `apps/_deprecated/`.

### added
- **model-routing installed into this repo**: `.claude/rules/model-delegation.md` plus the `fast-executor` and `task-coder` agents. The feedback layer was deliberately skipped -- it appends always-loaded text that only pays off with the `agent-state` CLI in active use.

## 0.36.0

### changed
- **explainer-video 0.2.0 -> 0.3.0**: generalized the skill beyond the single domain its first build happened to come from. The procedural-asset cookbook in `method.md` is now organized by **shape problem** rather than by subject, and leads with a derivable method (decompose to primitives, silhouette first, oversize the signature feature ~30%, costume beats anatomy, signal over realism) so an uncovered domain can be handled without a matching recipe. Recipes are split into ones actually built versus sketched, so the earned material stays distinguishable. `SKILL.md` gains a `domain` field in the spec, a third style mode (cross-section), and an explicit statement that only geometry and caption register vary by field — never the contract, beats or pipeline.
- **explainer-video**: widened the skill description, which is the retrieval surface. It previously read software- and character-flavoured and would not have triggered on "animate how a heat pump works" or "show how our approval process flows". Now spans process, mechanism, system, organism, market, supply chain, building and policy, and mentions the WebP inline-in-README output that 0.1.2 added.
- **explainer-video**: replaced the longer worked example. It is no longer bundled; `skill-retrieval.html` remains as the diagrammatic reference. The playful/moving-camera style now ships without an example — the template scaffold plus the `method.md` recipes are the starting point. Worth replacing with a neutral-subject example when one is needed.

## 0.35.0

### changed
- **version cascade is now three files, not 3+N.** `metadata.version` removed from all 39 SKILL.md. It duplicated `plugin.json`, and the only thing that ever read it was the check confirming the duplicate still matched — storing a value in N places so a hook can verify all N agree is work that produces no information. A `skill-maintainer` bump used to force 6 SKILL.md edits; `dev-conventions`, `mece-decomposer` and `env-forge` 5 each. Now: `plugin.json` + `marketplace.json` + `CHANGELOG.md`. Both consumers already treated the field as optional (`[ -n "$sk_ver" ]` in the pre-commit, `if (meta?.version)` in skill-dashboard), so a stray re-addition is still caught rather than silently drifting. One code change *was* needed and I initially missed it: the pre-commit's *extraction* is a pipeline (`sed | grep '^ *version:' | head | sed`), and under `set -euo pipefail` a grep that matches nothing aborts the entire hook with a silent exit 1. Tolerating absence in the comparison is not the same as tolerating it in the extraction. Fixed with `|| true`.
- **`metadata.last_verified` is out of the cascade too.** It asserts a human reviewed the skill against its source, which a version bump does not establish. Documented in CLAUDE.md invariant 1, `docs/internals/plugin-versioning.md`, the `sync-versions` skill, and best_practices.
- **`dev-conventions`, `dimensional-modeling`, `mece-decomposer` disabled in this repo** via `enabledPlugins: false`. Their SessionStart hooks inject ~3,500 chars of convention text every session, and those conventions are already stated twice here — `.claude/rules/general.md` and the user's global CLAUDE.md. The hooks stay in the plugins because they are the entire point for a repo with nothing written down; they are redundant only *here*.

### added
- **skill-maintainer 0.10.0 -> 0.11.0**: `_deprecated` added to `SKIP_DIRS`, so units kept for reference but no longer published stop producing permanently-red rows (an unpublished plugin legitimately fails "listed in marketplace.json", and its skills legitimately go stale).
- **pre-commit**: `claude plugin validate . --strict` gates any staged `marketplace.json`. Unknown top-level fields are warnings by default so a manifest can double as `package.json`; `--strict` promotes them to errors, which is what a hand-edited manifest wants. Verified by injecting `keywords` as a string — the commit is blocked. Skipped when the CLI is absent, so the hook still works without Claude Code installed.

### removed
- **env-forge deprecated.** Moved to `apps/_deprecated/env-forge/`, dropped from `marketplace.json` `plugins[]` and the uv workspace, removed from the README. Code kept, not deleted. `marketplace.json` gains `"renames": {"env-forge": null}` — the documented graceful-removal path, so existing installs get a "removed from the marketplace" notice instead of `plugin-not-found`. That map is append-only. Staleness failures 11 -> 6.

## 0.35.0

### changed
- **explainer-video 0.1.3 -> 0.2.0**: beat timing is now data. A named `BEATS` array is the single source of timing truth; captions, camera keyframes and `DURATION` all derive from it, and `animate()` addresses beats by name. `SKILL.md` has claimed since 0.1.0 that "retiming a beat is a one-line edit" -- it was false, because timing lived in `CONFIG.captions`, in `ss(t, 5.0, 6.9)` literals scattered through `animate()`, and again in the camera rail. It is now true. Durations accumulate rather than being absolute, so lengthening a beat shifts every later beat instead of silently overlapping it.
- **explainer-video**: two addressing forms, and the distinction is load-bearing. `ramp`/`pulse` take **fractions of a beat** and stretch when the beat is retimed; `rampS`/`pulseS`/`secAt` take **seconds from the beat start** and do not. A rise across half a beat should stretch; a 0.25s flash or a 0.06s world cut must not, because stretching a cut window uncovers the cut -- the one bug `method.md` says already cost a re-render.
- **explainer-video**: both worked examples migrated. Verified behavior-preserving by shooting identical timestamps before and after and comparing with `ffmpeg psnr`: 7 of 12 frames byte-identical on the longer scene, the rest 61-97 dB (imperceptible), and **the world-cut transition byte-identical at every sampled frame through it**. The only sub-70 dB frames were caption-fade boundaries, confirmed via difference images to be localized to the caption pill and the title -- a consequence of captions now spanning their beat instead of a hand-kept gap. A `capEnd` field covers the case that genuinely needs an early-ending caption, where it must clear a flash.

### added
- **explainer-video**: `method.md` gains "Beats are data, not comments" (including how to verify a migration with psnr and difference images) and "Spike the hostile beat first" -- build the beat that is both load-bearing and compression-hostile before committing to the full table, since it answers "does it read" and "does it encode small enough" in a few seconds of work.

### fixed
- **explainer-video**: `smoke.js` no longer vendors three unconditionally; it only does so if a scene actually references the bundle. The script tests the contract, not the renderer, so a 2D or SVG backend should not be forced to materialize a three bundle it never uses.

## 0.34.0

### fixed
- **explainer-video 0.1.2 -> 0.1.3**: corrected the mechanism given for why a repo-relative mp4 does not render as a player. 0.33.0 said `raw` serves video as `application/octet-stream`; it actually serves it as `text/plain; charset=utf-8` with `X-Content-Type-Options: nosniff`. Verified by fetching both formats from the URL a repo-relative reference resolves to. The conclusion was right and the reason was wrong, which matters because the real reason is a **content-type allowlist** -- `.webp` comes back as `image/webp` while video does not -- and that is exactly why the WebP loop path works at all. Independent verification also confirmed the animation chunks survive byte-intact.

### added
- **explainer-video**: two traps documented in `method.md` and `SKILL.md`. Never track the loop under Git LFS -- `raw` returns the pointer file, not the image, and the README shows a broken image; this catches most repos that ship demo media. And no format gives inline motion *with audio*: GIF, WebP and APNG are all silent, so the narration path and the inline path are necessarily different artifacts. APNG is flagged unverified rather than assumed.

## 0.34.0

### added
- **skill-maintainer 0.9.1 -> 0.10.0**: `check_version_alignment` in the repo-hygiene suite compares every `plugin.json` against its `marketplace.json` entry, in both directions -- a marketplace entry pointing at a plugin that does not exist, and a plugin on disk nobody can install. The pre-commit hook only ever inspected plugins a given commit happened to touch, which is why `path-privacy` drifted five releases before anything noticed. Verified by re-injecting that exact drift: it fails, and goes green when restored.

### changed
- **all 8 hook-shipping plugins**: hooks converted from shell form to **exec form** (`"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]`). Shell form hands the whole string to `sh -c`, so a plugin root containing a space -- a user account named `First Last` -- splits at the space and the hook dies with `sh: /Users/First: No such file or directory`. Demonstrated the failure and the fix before converting; output and exit codes are byte-identical for the path-privacy blocker. `bash` is named as the executable with the script in `args` rather than making the script path the `command`, because a `.sh` file is not spawnable on Windows -- the same reason the upstream docs recommend `node` plus a script path.  <!-- path-privacy: ignore -->
- Affected: `dev-conventions` 0.6.0 -> 0.7.0, `dimensional-modeling` 0.3.2 -> 0.4.0, `env-forge` 0.3.1 -> 0.4.0, `mece-decomposer` 0.4.1 -> 0.5.0, `path-privacy` 0.1.6 -> 0.2.0, `pyright-autoconfig` 0.1.2 -> 0.2.0, `skill-maintainer` 0.9.1 -> 0.10.0, `tui-design` 0.3.1 -> 0.4.0.
- **best_practices.md / plugin-patterns.md**: document exec vs shell form, including the Windows constraint and the `${user_config.*}` shell-form rejection (v2.1.207+).

### fixed
- **version cascade convention**: the cascade re-dates `metadata.last_verified` alongside `metadata.version`, which conflates "this file changed" with "someone checked this is still correct". Bumping eight plugins for a hook-invocation change would have silently marked 17 unreviewed skills as freshly verified and dropped staleness failures 11 -> 5 on no evidence. Those dates were restored. The two plugins that kept today's date are the ones actually exercised. Worth reconsidering whether `last_verified` belongs in the cascade at all -- see docs/internals/upstream_drift_backlog.md.

## 0.33.1

### added
- **docs**: `docs/internals/explainer_video_roadmap.md` — design for the queued explainer-video work. The headline item is replacing scattered literal timings with a named-beats table as the single source of timing truth: `SKILL.md` currently claims "retiming a beat is a one-line edit" and that is false, since beat timing lives in `CONFIG.captions`, in `ss(t, 5.0, 6.9)` literals through `animate()`, and again in the camera rail. The doc argues the ordering (the refactor blocks the contact sheet, narration-driven audio, and the lint; only parallel capture is independent) and records what we are deliberately not building.
- **docs/README.md**: indexed `upstream_drift_backlog.md` and the new roadmap, neither of which appeared in the internals table.

## 0.33.0

### added
- **explainer-video 0.1.1 -> 0.1.2**: two new delivery outputs and a second worked example, driven by verifying how GitHub actually renders things. `build.js loop` produces an animated WebP (the one motion format GitHub renders inline in markdown); `build.js poster` produces a still plus the markdown snippet to paste. `examples/skill-retrieval.html` is an 8s held-camera diagrammatic scene, and its 175 KB WebP is committed and embedded in the plugin README -- the inline story, demonstrated rather than asserted.
- **explainer-video**: `CONFIG.sway` is now a config value rather than a hardcoded `0.06`, so holding the camera is a one-line edit.

### changed
- **explainer-video**: delivery is now a step-1 decision, not an encode-time one, because it constrains the camera and therefore the beats. Measured: the 12s template scene at 960px/24fps encodes to 0.52 MB as mp4 but **15.56 MB** as WebP (worse than GIF's 12.08 MB), because the default sway moves every pixel every frame and defeats inter-frame compression. The same pipeline on an 8s held-camera scene yields a 175 KB WebP -- smaller than its own mp4. So the rule is by scene type, not by squeezing under the 10 MB cap: held camera -> inline loop; moving camera -> poster still linking to an attached mp4; authored diagram -> hand-written animated SVG.
- **explainer-video**: documented that a repo-relative mp4 does **not** render as a player on GitHub (`<video>` is stripped from GFM, and raw serves video as `application/octet-stream`); the working path is an issue/PR attachment URL. Also that `img2webp` is required for loops, since Homebrew's ffmpeg ships without libwebp.
- **explainer-video**: corrected the render-speed figure in `method.md`. It claimed ~1 fps at 1080p, which is true for software GL in a cloud container but read as universal; measured 5.3 fps on local hardware GL (288 frames in 54s). Both cases are now tabulated, and the parallel-capture opportunity that falls out of determinism is noted.

### fixed
- **explainer-video**: `smoke.js` asserted `window.THREE` and read pixels from a WebGL context, which would have failed any non-three backend. The contract (`seekTo`/`DURATION`/`stopPlayback`/`sceneReady`) is the actual product -- three.js is one backend, and a 2D canvas or SVG/CSS timeline implementing those four globals should get frame-exact MP4s from the same pipeline. The renderer assertion is gone and the blank-frame check now measures the screenshot instead of the canvas. Verified with a negative control.
- **README**: `explainer-video` was missing from the root plugins table, install list, and invocation examples -- step 5 of the plugin checklist was skipped when it was added in 0.31.0.

## 0.32.0

### fixed
- **marketplace.json**: `path-privacy` was pinned at 0.1.1 while its `plugin.json` and SKILL.md had moved to 0.1.6 -- the marketplace entry was never updated during those five bumps, so installs resolved a stale version. Caught by the pre-commit version check once an unrelated edit touched the plugin. Reconciled against `plugin.json`, which is the source of truth.

### added
- **skill-maintainer 0.8.1 -> 0.9.0**: per-skill review intervals via `metadata.review_interval_days`, honoured by `test`, `quality`, and `freshness` (falling back to the global 30-day default; `freshness --threshold` still overrides everything). A single global window was the wrong instrument for a repo tracking sources of very different volatility -- the Claude Code docs move weekly, Kimball dimensional modeling has not moved in decades. Forcing both to 30 days kept 31 of 39 skills permanently red, which is how a signal stops being read.
- **all skills**: tiered into 30d (content derived from Claude Code docs), 90d (tracks a third-party SDK/API), and 365d (methodology, or our own code -- we update the skill when the code changes and the date is only a backstop). Staleness failures dropped from 31 to 13, and the remaining 13 are genuine: they track moving surfaces and are past their own declared window.

## 0.31.1

### added
- **explainer-video**: `templates/smoke.js` — a contract and determinism check that renders one frame of every scene, source and bundled, and fails on any console error, missing contract member, blank canvas, or non-deterministic `seekTo`. It found two real bugs in the shipped example on its first run.

### fixed
- **explainer-video**: the worked example never set `window.DURATION`, violating the documented recorder contract. `shoot.js` masked it with a `|| 20` fallback that coincidentally matched the example's length — a 30-second scene would have silently rendered only its first 20 seconds. The example now sets it and the fallback is gone, so a missing `DURATION` fails loudly.
- **explainer-video**: the worked example broke the skill's core determinism invariant. `browL/browR.rotation.z` were set at build time and mutated only inside the finale branch, so nothing reset them for `t < 17.7`. The MP4 renders 0->N once and looked correct, but the HTML loop's second pass showed finale brows during the early beats — the exact HTML/MP4 divergence the architecture claims is impossible. Brows are now restated every frame.
- **explainer-video**: reframed one beat of a worked example. The subject sat in the upper third against `method.md`'s own middle-third rule; it now centers.

## 0.31.0

### added
- **explainer-video 0.1.0**: new plugin for deterministic animated explainer sequences (3D or diagrammatic), delivered as a self-contained looping HTML page, a frame-exact MP4, or both. The whole film is a pure function of time `t`, so one scene file drives both the live HTML loop and the headless render — no second copy to keep in sync. Ships a runnable scaffold, a headless frame shooter, a vendor/bundle/frames/video pipeline, a design-method reference, and a worked 20s example.

### changed
- **explainer-video**: promoted from a bare skill directory to a plugin (`.claude-plugin/plugin.json`, README, `skills/explainer-video/`), added `metadata.version`/`last_verified`, renamed `reference/` -> `references/`, and converted the toolchain from npm/node to bun.
- **explainer-video**: pinned `three@0.185.1` and `playwright-core@1.61.1` (from `three@0.149.0`, unpinned playwright). This was a migration, not a bump — three removed its UMD build after 0.160, and `outputEncoding`, `sRGBEncoding` and `useLegacyLights` are gone in r185. Because `THREE.<removed>` evaluates to `undefined` rather than throwing, the old code would have rendered with silently wrong colors. three is now vendored locally as an IIFE bundle (`build.js vendor`) instead of loaded from a CDN, so renders never touch the network.

### fixed
- **explainer-video**: `build.js bundle` corrupted every bundled artifact. The inline step used a string replacement, where `$&` is a substitution pattern, and minified three contains `if($&$.isStackTrace)` — splicing the matched script tag into the middle of the library. Now uses a function replacement. This bug predated the version migration.
- **explainer-video**: the vendored bundle must be IIFE format. An ESM bundle loaded as a classic script leaks top-level identifiers into global scope, where a minified `MW` collided with a scene variable and broke the worked example.
- **explainer-video**: `shoot.js` now surfaces page and console errors and fails fast when a scene never becomes ready, instead of silently shooting hundreds of broken frames. Playwright's Chromium cache is scanned by build rather than pinned to a stale build number.

## 0.30.2

### changed
- **pyright-autoconfig 0.1.1 -> 0.1.2**: code-review fix for a config-overwrite regression. 0.1.1's "is this config ours?" test was a loose `grep reportMissingModuleSource`, so a user's OWN hand-written `pyrightconfig.json` that set that key would be misclassified as ours and silently overwritten (losing their other settings). Ownership is now **exact**: the hook only ever recognizes/rewrites its own byte-for-byte template output (venv or venv-less), and self-heals only its exact venv-less template once `.venv` appears. Any other config is left completely untouched. Verified: a user config containing `reportMissingModuleSource` is now preserved; self-heal + idempotency still pass. (Unrelated but same session: hardened the user-scope `block-network-exfil.sh` PreToolUse hook against full-path curl and `<(curl)`/`$(curl)`/`| xargs sh` bypasses -- that hook is a personal `<HOME>/.claude/hooks/` file, not part of this repo.)

## 0.30.1

### changed
- **pyright-autoconfig 0.1.0 -> 0.1.1**: post-review hardening of the SessionStart hook.
  - **Self-healing venv pointer (real bug fix)**: previously, a config written before `.venv` existed (the clone-then-`uv sync` order) was venv-less and the idempotent early-exit meant it never gained `venvPath`/`venv` -- so imports never resolved, defeating the plugin's main purpose. The hook now rewrites its own config once `.venv` appears (verified: venv-less on first run, venv pointer added on the next).
  - **Subtable-aware config detection**: the "respect an existing pyright config" guard now matches a bare `[tool.pyright]` header OR any `[tool.pyright.<subtable>]` (e.g. `executionEnvironments`) -- a subtable alone is valid TOML and a written `pyrightconfig.json` would otherwise shadow it.
  - **Write-gated exclude**: `.git/info/exclude` is only touched after the config write actually succeeds (no more orphan exclude entry on a failed write).
  - **jq-missing signal**: a missing `jq` now emits one stderr line instead of a fully silent no-op.
  - **De-duplicated the config builder** (single `desired` string, was two near-identical heredocs). SessionStart matcher intentionally omitted (repo convention is no-matcher; the hook is idempotent + cheap, and an unverified matcher risks the hook never firing).

## 0.30.0

### added
- **pyright-autoconfig 0.1.0** (new plugin): a one-hook plugin that makes the Claude Code Pyright LSP quiet and useful across all Python projects without per-repo setup. On SessionStart, if cwd is a Python project (`pyproject.toml`/`setup.py`/`setup.cfg`/`.venv`) with no existing Pyright config, it drops a personal `pyrightconfig.json` pointing Pyright at the uv `.venv` (`venvPath`/`venv` -> imports resolve -> real cross-file type intel) and setting `reportMissingImports`/`reportMissingModuleSource` to `none` (kills the dominant noise; Claude Code surfaces all severities, so only `none` actually removes a diagnostic). Registers the file in the repo's `.git/info/exclude` so it never commits and never shows in `git status` -- no global git config, nothing to replicate by hand on other machines. Idempotent (exits once a config exists), non-destructive (never overwrites an existing `pyrightconfig.json` or `[tool.pyright]` block), silent (no injected context), and a fast no-op outside Python projects. Solves the flood that pyright-lsp produces when it can't find the venv (worst on files it can't root: sibling repos, `/tmp` scratch). Prerequisite: the official `pyright-lsp` plugin + `pyright-langserver` on PATH.

## 0.29.2

### changed
- **README**: added an `### updating` section under installation — how to pull plugin updates (`claude plugin marketplace update` + `claude plugin update`), the startup auto-update behavior, and a note on scripting a one-command sweep across machines. Closes the gap where install/uninstall were documented but keeping plugins current was not.

## 0.29.1

### changed
- **README plugins section**: regrouped the flat 17-row plugin table into six purpose-based categories (development conventions & authoring; decomposition & model routing; plugin & skill maintenance; MCP servers & apps; privacy & pre-share safety; environment synthesis). Every plugin preserved verbatim; project-scoped and package sections unchanged.
- **VISION.md restructure**: reordered so the concrete loading model leads — retrieval problem, then "what gets loaded and when", then principles, then the architecture worldview (was architecture-first). Intro rewritten to match. Validated the L1/L2/L3 loading table against the captured `docs/analysis/memory_and_rules_system.md` and upstream docs: all existing rows accurate (incl. the "~2% of context" SKILL.md frontmatter figure); added a note on three L1 sources present in Claude Code but unused here (managed-policy CLAUDE.md, `CLAUDE.local.md`, user-level `<HOME>/.claude/rules/`). Added an ASCII tree-topology diagram to the architecture section; fixed a now-stale "below" -> "above" cross-reference. Both edits produced by down-tier subagents (sonnet) and verified in the main loop — a dogfood of the model-routing pattern.

### changed
- **model-routing 0.2.0 -> 0.3.0**: made the base rule genuinely standalone and split the agent-state coupling into an opt-in layer. The `agent-state` recording block moved out of `references/model-delegation.md` into a new `references/feedback-addon.md`, which the installer appends only when the user asks for it ("with feedback" / "with agent-state"). The base `.claude/rules/model-delegation.md` now has zero external-tool references — it loads into every session of every project where it's installed, so the feedback text (which only pays off when the CLI is present) shouldn't ride along by default. Three independent install layers now: base rule (always), agents (opt-in), feedback (opt-in). SKILL.md, plugin/marketplace descriptions, and READMEs updated; no change to `fast-executor` / `task-coder`.

## 0.28.1

### changed
- **Path-privacy cleanup** ahead of a repo push: replaced a few external path references with generic forms across `tools/agent-state/BACKLOG.md`, `apps/readwise-reader/.../enrichment/pipeline.py` (stub comment), and `skills/scan-for-secrets/.../SKILL.md` (References list). Functional behavior unchanged.
- **scan-for-secrets 0.1.0 -> 0.1.1**: version cascade for the SKILL.md content change above (plugin.json, marketplace entry, sub-skill `metadata.version`, `last_verified`). No functional change.

## 0.28.0

### changed
- **dev-conventions 0.5.0 -> 0.6.0**: refresh for current tooling and scope.
  - **Lock file fix**: `bun.lockb` -> `bun.lock` everywhere (javascript directive, `bun-tooling` and `doc-conventions` skills, README, and the hook's marker detection). Bun switched to the text-based `bun.lock` in 1.2 (default since); every bun project in this repo already uses it, so the plugin now matches reality. The hook detects both `bun.lock` and legacy `bun.lockb`.
  - **Slimmed directives to policy**: the `python.md` and `javascript.md` SessionStart directives no longer teach `uv add`/`uv run`/`bun add`/`bunx` command mappings (current models default to these unprompted). They now carry only the non-inferable policy: which manager is mandated, the pinning strategy, no-auto-lint, and don't-hand-edit-lockfiles, plus a pointer to the L2 skill for full tables.
  - **Dropped orjson from the plugin**: `python-tooling` no longer mandates `orjson` over stdlib `json`, and the plugin/marketplace descriptions drop it from the injected list. JSON-library choice is a per-project preference, not a near-universal default like uv/bun/TDD; the skill now says so and points to the project's own `CLAUDE.md`/`.claude/rules/`. This repo keeps its orjson rule in `.claude/rules/general.md`, where it belongs and is genuinely used.
  - All five sub-skills bumped to 0.6.0 / `last_verified` 2026-07-05.

## 0.27.0

### added
- **agent-state 0.2.1 -> 0.3.0**: delegation feedback loop. Schema v3 adds `fact_delegation` (append-only; grain: one row per delegated subagent task, recorded when the orchestrator verifies the result; deterministic MD5 surrogate key so re-recording identical inputs is a no-op) and `v_delegation_stats` (acceptance rate per model/domain). New `delegations.py` module (`record_delegation`, `get_delegation_stats`, `get_recent_delegations`), `DelegationOutcome` enum (accepted / revised / redone / escalated), and `agent-state delegation record|stats|list` CLI. TDD: 10 new tests in `test_delegations.py`; existing schema-version assertions updated to v3; suite at 45 passing.

### changed
- **model-routing 0.1.0 -> 0.2.0**: the installer now optionally copies pre-shaped agent definitions into the target project's `.claude/agents/` — `fast-executor` (haiku, mechanical execute-to-spec) and `task-coder` (sonnet, implement-to-spec with verification), both templated verbatim in the skill's `references/agents/`. The installed rule prefers those agents when present and, when the `agent-state` CLI is on PATH, records each verified delegation outcome (`agent-state delegation record ...`) so acceptance rates can tune delegation criteria from data; recording is optional and never blocks work.
- **agent-state BACKLOG**: captured follow-up to expose `fact_delegation` through agent-state-mcp's read-only tools.

## 0.26.0

### added
- **model-routing 0.1.0** (new plugin): opt-in per-project model delegation. One skill, `model-routing`, installs `.claude/rules/model-delegation.md` into the current project by verbatim copy from the skill's `references/model-delegation.md` template (diff-and-confirm if a local copy exists; removal is deleting the file). The rule routes well-specified, mechanical, verifiable data/coding tasks to the cheapest capable model in a subagent and keeps design, ambiguity, user interaction, and verification of returned work in the main loop; model tiers appear only as examples so the rule survives lineup changes. Pure markdown skill, stays out of the uv workspace. Registered in `marketplace.json` and the root README plugins table, install list, and invocation examples.

### changed
- **VISION.md**: new architecture subsection "route to the cheapest capable model" — routing has two axes (context a subagent sees, model tier that executes it); decomposition quality and model tiering are complements; delegation rules should be stated as task properties with tiers as examples. Matching bullet in "what this means for this repo" pointing at the model-routing plugin as the implementation. The L1/L2/L3 loading table gains a `Type` column (Instructions / Memory / Rule / Skill / Settings / Reference / Script) so each loaded artifact is named by kind, not just by path.

## 0.25.0

### added
- **writing 0.1.0** (new plugin): the repo's first writing-skills bundle. Ships one skill, `govuk-style`, which applies the GOV.UK / Government Digital Service house style — plain English, active voice, front-loaded content, sentence case, and no bold or italics for emphasis. Pure markdown skill (no Python), so it stays out of the uv workspace. Registered in `marketplace.json` and the root README plugins table, install list, and invocation examples. Adapted from a skill shared by [@fofr](https://twitter.com/fofr); credited in the SKILL.md `metadata.credit` field, the skill body, and the README.

## 0.24.8

### changed
- **skill-maintainer 0.8.0 -> 0.8.1**: `/simplify` follow-up pass on the three commits that landed today.
  - `lint.py`: extracted `_count_analysis_reports` and `_count_captured_docs` named functions, replacing two byte-identical lambdas in `COUNT_PATTERNS`. Drift surface eliminated -- if the exclusion set changes (e.g., `_index.md` is added later), only one place to update.
  - `lint.py`: added `_safe_read(path)` helper that returns `None` on `OSError` / `UnicodeDecodeError`. `find_count_drift` and `find_broken_links` use it instead of bare `path.read_text()`. Honors the documented "exit 0 always" contract -- a dangling symlink or non-UTF-8 file in the doc tree no longer crashes the pass.
  - `lint.py`: `find_count_drift` memoizes counter results per call (`actual_cache: dict[int, int]` keyed by `id(counter)`). A file with multiple lines matching the same pattern now triggers one filesystem glob, not N. Real concern only on duplicated prose in long files; cheap fix.
  - `pre-commit.sample` (and the live `.git/hooks/pre-commit`): inline comment in `claude_md_size_check` documenting that the `4000`-token threshold mirrors `shared.TOKEN_BUDGET_WARN`. The shell can't import Python; the comment is the only available drift signal.
- **README.md**: skill-maintainer plugin row gains the new `lint` capability and the tracked pre-commit hook scaffolding (both shipped today). agent-state-mcp row scrubbed of `<HOME>/.claude/...` path leak (now `<HOME>/.claude/...`). The `docs/internals/` line in the documentation highlights was wrong -- said "API reference, DuckDB schema, troubleshooting"; replaced with the actual contents (versioning cascade, plugin patterns, maintenance commands, gotchas) plus a new pointer to `docs/analysis/index.md` since that's now a real wiki-style index. The skill-maintainer CLI section gains the new `init` hook-scaffolding behavior and `lint` in the example commands.
- **CLAUDE.md**: added missing `last updated:` line at top. Caught by the docs-staleness sweep -- root CLAUDE.md was the only file in the active doc tree without one.

### notes
- The staleness sweep across the doc tree (38 files with `last updated:` dates older than 30 days) found **no date-vs-content drift** -- every file's commit date aligns with its stated `last updated:` line within 7 days. The dates are accurate signals of when content was last touched. Did not blind-bump the 36 stable analysis/reference files; doing so would make the dates *less* accurate as audit signals. The two real audit candidates (`apps/readwise-reader/CLAUDE.md` and `README.md`, 88 days) remain deferred -- they need someone with that codebase's context.

## 0.24.7

### added
- **skill-maintainer 0.7.0 -> 0.8.0**: two new capabilities, both closing real gaps surfaced by the hub-and-spoke restructure.

  **(1) Pre-commit hook is now a tracked, installable artifact.** The hook source moved from `.git/hooks/pre-commit` (untracked, lost on every fresh clone) to `tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample` (bundled with the Python package). New `scaffold.py` module exposes `install_pre_commit_hook(root, force)`. `skill-maintain init` now calls it on every run: idempotent (skip if up-to-date), refuses to clobber a divergent existing hook unless `--force-hook` is passed (which preserves the prior hook as `.git/hooks/pre-commit.local` first), and degrades gracefully (`skipped: not a git repository`) outside git repos. The bundled hook is portable: version-alignment checks no-op in repos without `.claude-plugin/plugin.json`, the CLAUDE.md size guard no-ops if CLAUDE.md isn't staged. Replaces the brittle "copy from a teammate's clone" instruction in `docs/internals/gotchas.md`. The `init-maintenance` SKILL is refactored to delegate to `skill-maintain init` instead of writing its own minimal hook.

  **(2) Lint v2 -- markdown link-rot detection.** `skill-maintain lint` gains a third pass: scans `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/internals/*.md`, `docs/analysis/*.md`, and `VISION.md` for `[text](path)` links resolving to files that don't exist. Skips `http(s)://`, `mailto:`, and pure anchor (`#section`) links. Anchor fragments are stripped before existence checks. Links escaping the repo root are skipped (don't flag legitimate sibling-repo references). Caught one real broken link on its first run -- `docs/analysis/cross_surface_compatibility.md:401` pointed at `abstraction_analogies.md` which lives in sibling repo `star-schema-llm-context`, not here. Replaced with a path-privacy-clean prose reference.

- `docs/analysis/log.md` seeded with two real entries (the wiki layer bootstrap and the 2026-05-04 upstream delta); accumulates forward from here. Historical operational events stay in `.skill-maintainer/state/changes.jsonl` (machine-readable) and are not backfilled into the narrative.

## 0.24.6

### added
- **skill-maintainer 0.6.5 -> 0.7.0**: new `skill-maintain lint` subcommand (wiki-sanity pass) plus the wiki layer it operates on.
  - `skill_maintainer/lint.py` implements two checks today: (1) **orphan detection** in `docs/analysis/` — files on disk not linked from `docs/README.md` or `docs/analysis/index.md`; (2) **count drift** — scans `README.md`, `CLAUDE.md`, `docs/README.md`, and `docs/internals/*.md` for assertions matching `\b\d+\s+(domain reports|reports covering|captured docs)\b` and compares each claim to the filesystem. Soft findings (exit 0); not a CI block. Cross-reference and stale-claim heuristics deferred to a future minor.
  - `docs/analysis/index.md` (new): wiki-style index tagged by kind (entity / concept / audit / synthesis). Complements `docs/README.md`'s umbrella index by retrieving by intent.
  - `docs/analysis/log.md` (new): append-only narrative log of ingests, updates, and audits with verb-prefixed `H2` headers (`ingest | update | audit`). Complements `.skill-maintainer/state/changes.jsonl` (operational, machine-readable) with the human-readable why behind significant updates.
  - `docs/internals/maintenance.md` gains a `skill-maintain lint` row in the on-demand commands table.
  - `cli.py` registers `lint` in `COMMANDS`, lists it in `--help`.
  - Inspired by [Karpathy's LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the model is appropriate specifically for `docs/analysis/` (an accumulating knowledge corpus about external systems) and not for CLAUDE.md / READMEs / SKILL.md (which have other purposes).
- The lint pass paid for itself on its first run: caught a "16 domain reports" example I'd written into `docs/internals/gotchas.md` while documenting the rule that prose shouldn't include hardcoded counts. Rephrased without a count.

## 0.24.5

### changed
- **CLAUDE.md restructured to hub-and-spoke.** Trimmed root `CLAUDE.md` from ~270 lines to ~60 by lifting four content domains into `docs/internals/` spokes loaded by reference:
  - `docs/internals/plugin-versioning.md` — full version cascade, sync-versions coverage gaps, sub-skill alignment block, worked example using the most recent skill-maintainer 0.6.4 bump.
  - `docs/internals/plugin-patterns.md` — required structure, hooks-vs-skills, composable directives, agents, catalog-as-exemplar, bash 3.2 portability, greenfield-vs-production schema evolution.
  - `docs/internals/maintenance.md` — full keep-fresh table, on-demand commands, state files, workspace member table.
  - `docs/internals/gotchas.md` — best_practices.md duality, security-guidance hook disable, pre-commit hook re-installation, path-privacy interaction, CLAUDE.md size creep rule, count-drift rule.
- The new CLAUDE.md is a hub: identity + working agreements + 5 repo invariants (the rules that bite on first edit) + a "Where to find what" index pointing at the spokes + state + cross-repo. Path leaks scrubbed (`<HOME>/.claude/...` → `<HOME>/.claude/...`; a local clone of the Agent Skills spec description genericized).
- Companion fix: the `last updated` date on `docs/README.md` refreshed and the "15 reports covering..." count claim dropped (the filesystem is the source of truth; counts in prose are drift surfaces). Same fix on root README's "16 domain reports" claim — was the wrong number anyway.

### added
- **skill-maintainer 0.6.4 -> 0.6.5**: pre-commit hook gains a CLAUDE.md size guard. When CLAUDE.md is staged AND its size exceeds 150 lines OR ~4000 tokens (chars/4 heuristic), the hook prints a stderr warning recommending the author move detail into a `docs/internals/<topic>.md` spoke. Warning only — does not block. Same exit semantics as the existing "unbumped content changes" warning. Implemented as a function `claude_md_size_check()` invoked in both exit paths of the hook so it fires regardless of whether plugin content was also staged. Bash 3.2 portable; uses `wc -l` and `wc -c` only.

## 0.24.4

### changed
- **skill-maintainer 0.6.3 -> 0.6.4**: deduplicated `agents/session-log-drafter.md` "house style" against `dev-conventions/doc-conventions` and CLAUDE.md global rules. Four of the nine numbered items in the drafter's house-style block (last-updated date, document-the-why, no-emojis-no-filler, session-log file location) were verbatim restatements of rules already codified elsewhere -- effectively turning the drafter into a third source of truth for the same rules and creating a drift surface every time doc-conventions evolves. Replaced with a one-line pointer to `/dev-conventions:doc-conventions` plus the six remaining session-log-specific rules (heading format, lowercase section headers, narrative-not-transcript, mandatory follow-ups section, explicit file paths, date-stamping relative time references). Behavior of generated logs is unchanged -- the deleted rules still apply via doc-conventions and CLAUDE.md, the drafter just no longer carries its own copy. last_verified bumped on all six sub-skills.

## 0.24.3

### fixed
- **skill-maintainer 0.6.2 -> 0.6.3**: `skill-maintain log` crashed with `AttributeError: 'dict' object has no attribute 'split'` whenever the tail window included an `upstream_check` event written by v0.4.0+. Background: in v0.4.0, `upstream._log_event` was upgraded to record each changed page as a dict (`{"url", "status", "lines_added", "lines_removed", "chars_delta"}`) so subsequent `upstream` runs could compute deltas; `log.py` was not updated and still treated `changed_pages` entries as bare URL strings, calling `.split('/')` on the dict. The log file now mixes both shapes (older entries are strings, post-0.4.0 entries are dicts), so the formatter has to handle both. Fixed in `log.py:62-64` by extracting `url` if the entry is a dict, otherwise using the value directly, then taking the basename via `rstrip('/').split('/')[-1]`. Verified by re-running `skill-maintain log --tail 5` on this repo's `changes.jsonl`, which contains both shapes.

## 0.24.2

### changed
- **skill-maintainer 0.6.1 -> 0.6.2**: code-clarity polish in `hooks/maybe-draft-session-log.sh` (no behavior change). Combined the test-then-capture pair `if ! git rev-parse ...; then exit 0; fi; repo_root=$(git rev-parse ...)` into one capture-with-fallback `repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0` -- saves one fork in the hot path and removes the small worktree-changed-between-calls TOCTOU window. Wrapped the Linux `stat -c "%y" | cut` branch in `{ ... ; }` so the `||` / `|` operator precedence is unambiguous to a future reader; the macOS branch never paired with `cut` at runtime, but the unwrapped form looked like `cut` was a shared post-process for both branches. Same five-scenario regression suite from 0.6.1 still passes. last_verified bumped on all six sub-skills.

## 0.24.1

### fixed
- **skill-maintainer 0.6.0 -> 0.6.1**: two bugs in the `Stop` hook `maybe-draft-session-log.sh`. (1) The Linux-fallback branch parsed `stat -c "%y"` output with `cut -dc -f1`, which uses `c` as the delimiter -- a no-op on `2026-04-25 14:45:10.123 -0500`-style output, returning the entire timestamp string and never matching `today`. So on Linux the "log already updated today, exit early" short-circuit never fired and the hook always proceeded to the count step. Fixed to `cut -d' ' -f1`. (2) The substantive-files counter pipeline ended `... | grep -Ev "^(internal/log/|...)"` -- when the input pipeline produced no lines (e.g., a session with no diffs and no untracked files, or a session that touched only excluded paths), `grep -Ev` exits 1 because nothing matched the negation. Combined with the script's `set -euo pipefail`, that exit-1 killed the script before the trailing `exit 0`, surfacing as a non-zero hook exit on Stop. Fixed by wrapping the grep in `{ ... || true; }` so an empty pipeline doesn't propagate. Both reproduced on macOS by feeding `{}` on stdin into a fresh repo with no changes; both pass after the fix. Also bumped `last_verified` on all six sub-skills to today since the plugin content changed.

## 0.24.0

### added
- **path-privacy 0.1.0** (new plugin): enforces a single rule -- every path written into a repo must be relative to the repo root. Anything that resolves outside the repo (other repos on disk, `~/.claude/<plan>`, `/Users/<name>/...`, `/home/<name>/...`, `$HOME`-based paths) is treated as a leak. Three layers of enforcement: (1) a `SessionStart` hook that injects the rule into Claude's context whenever a session opens in a git repo, so paths outside the repo are never written in the first place; (2) a `pre-commit` git hook that hard-blocks any commit whose staged file content contains a leak; (3) a `commit-msg` git hook that hard-blocks any commit whose message body or current branch name contains one. Single shared scanner script (`find-external-paths.sh`, ripgrep-based) backs all three. Pattern shapes mirror `scan-for-secrets/regex-scan.sh` for `/Users/`, `/home/`, `~/`, and `$HOME`-anchored paths; placeholder usernames (`USERNAME`, `<user>`, `$USER`, `me`, `you`, etc.) are skipped so documentation snippets like `/Users/USERNAME/foo` don't false-flag. Per-line opt-out via the literal token `path-privacy: ignore`. Hooks installer (`install-git-hooks.sh`) writes wrappers into `.git/hooks/` and preserves any pre-existing hook as `.local`. Skill triggers on "scan for path leaks", "check for leaked paths", "are we leaking my home path", "scrub external paths", "install path-privacy hooks", and similar. Sibling to `scan-for-secrets`: that plugin scans for arbitrary secret shapes; this one enforces the narrower repo-scoped-paths rule at commit time with a hard block.

## 0.23.0

### added
- **scan-for-secrets 0.1.0** (new plugin): pre-share scanner that wraps [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (Apache 2.0) for literal matching with JSON/URL/HTML/backslash/unicode-escape variants, and composes a bundled ripgrep wrapper (`regex-scan.sh`) for shape-based patterns the literal pass can't express. Two shipped scripts: `privacy-tokens.sh` emits identity literals from the environment (HOME, USER, git email/name, macOS ComputerName/LocalHostName, Linux GECOS, Apple ID, SSH pubkeys, gh/npm/aws/gcloud logins) as a ready-made `scan-for-secrets -c` config; `regex-scan.sh` sweeps for other users' home paths, emails, IPv4, MAC addresses, SSH fingerprints, and (via `--api-keys`) common API-token shapes (OpenAI/Anthropic/GitHub/AWS/Google/JWT/Slack/PEM). Invoked via `uvx scan-for-secrets` (no install pollution). Skill triggers on "scan for secrets", "pre-share scan", "redact home paths", "PII scan", and similar. Simon's tool stays unmodified; all extension work is composition.

## 0.22.15

### added
- **skill-maintainer 0.5.2 -> 0.6.0**: new `Stop` hook `maybe-draft-session-log.sh`. When the model tries to stop, checks whether the session touched >= 3 "substantive" files (excluding log files, lock files, and `.skill-maintainer/state/`) AND today's `internal/log/log_YYYY-MM-DD.md` doesn't exist or wasn't modified today. If both true, prints a one-line stderr nudge pointing Claude at `/skill-maintainer:finish-session`. Never blocks (exit 0 always). Honors `stop_hook_active=true` so repeated stops don't loop-nudge.
- **agent-state-mcp 0.1.3 -> 0.2.0**: new `/agent-state-mcp:enable` skill. One-shot `.mcp.json` promotion that moves the `agent-state` entry from `_available_servers` (opt-in convention) into `mcpServers` (active), using an idempotent `jq` transform that no-ops on double-runs. Verifies with `uv run agent-state-mcp --list-tools`, tells the user to restart Claude Code, never commits. Closes the "easy to miss the opt-in" friction called out in 0.22.8.

## 0.22.14

### added
- **dimensional-modeling 0.3.1 -> 0.3.2**: kimball-principles directive gains the "facts don't join to facts" rule. Route through a conformed dimension instead of joining two fact tables on a shared FK. Auto-injected via SessionStart hook when DuckDB markers are detected, so any session touching star-schema work sees the rule without having to re-state it.
- **CLAUDE.md**: new "Schema evolution: greenfield default" subsection under Key patterns. Captures the user's stated preference to prefer `CREATE OR REPLACE VIEW` + schema re-init over migration bridges for local/dev DBs (agent_state, readwise-reader, etc.). Production-facing schemas (marketplace, published plugins) remain the exception.

## 0.22.13

### fixed
- **agent-state 0.2.0 -> 0.2.1**: /simplify pass findings.
  - `get_run_messages` gained an optional `limit` parameter that pushes `LIMIT ?` into the SQL. Previously the MCP layer fetched all rows for a run and sliced in Python (`rows[:limit]`), transferring unbounded data from DuckDB only to discard most of it. `get_run_messages_tool` in the MCP layer now requests `limit + 1` rows and uses overflow as the truncation signal -- no extra COUNT round-trip needed.
  - `get_failed_runs` now binds statuses via `RunStatus.FAILURE.value` / `RunStatus.PARTIAL.value` instead of literal strings, so the `models.RunStatus` enum remains the single source of truth. If enum values ever change, the query fails loudly at load time rather than silently returning zero rows.
  - `get_failed_runs` `dim_skill_version` subquery is now a CTE (`WITH sv AS ...`), binding `skill_name` once (not three times) and giving the planner one scan to reference from both IN clauses.
  - `get_failed_runs` bug: CTE parameter must come first in the params list (SQL-text order, not insertion order). Fixed by splitting into `cte_params` + `body_params` and assembling at the call site. Previous code was positionally shifted when `skill_name` was supplied, causing DuckDB to interpret status strings as CTE lookups and cutoff timestamps as status values -- a silent correctness bug this /simplify pass caught before it reached production.
  - `get_failed_runs` now computes the `since_days` cutoff as a Python datetime and binds it directly instead of `CURRENT_TIMESTAMP - (? * INTERVAL 1 DAY)`. Multi-typed parameter binding in that expression tripped DuckDB's BIGINT/DOUBLE overload resolver.
  - `get_run_stats` dropped the redundant per-field `or 0` guards -- the tuple fallback already covers the only case where COUNT(*) could yield NULL (table dropped mid-query).
- **agent-state-mcp 0.1.2 -> 0.1.3**: `get_run_messages_tool` passes `limit` through to the underlying query helper; no in-Python slicing. Behavior unchanged when under the limit; with the previous code, memory-bound. `_envelope` `extra_meta` still surfaces `truncated: true` when the overflow row is seen.
- **agent_state.sql**: `v_latest_watermark` outer projection switched from an explicit 9-column list to `SELECT * EXCLUDE (rn)`. Removes a maintenance hazard where adding a column inside the inner `ranked` subquery would silently drop from the view output.

## 0.22.12

### changed
- **agent-state 0.1.0 -> 0.2.0**: cleanup of the three findings deferred in 0.22.11.
  - `agent_state.query` gained four functions previously carried as inline SQL in the MCP layer: `get_failed_runs(db, since_days, skill_name, limit)`, `get_tracked_domains(db)`, `get_run_sources(db)`, `get_watermark_sources(db)`. Now reachable from the CLI package too, and testable directly against the schema rather than only through the MCP transport.
  - `get_run_stats` consolidated four scalar counts (total_runs, active_watermarks, tracked_skills, total_messages) into one query via scalar subqueries. The two GROUP BYs (by_status, by_type) remain separate because PIVOT / UNION-with-discriminator hurts readability more than it saves round-trips. 6 queries -> 3.
  - `v_latest_watermark` view rewritten from a correlated `MAX(watermark_id)` subquery to `ROW_NUMBER() OVER (PARTITION BY watermark_source_key ORDER BY watermark_id DESC)`. DuckDB now resolves the latest row per source in a single pass.
  - **Bug fix along the way**: `dim_run_source` query in `list_run_sources` was GROUPing on columns that don't exist (`identifier`, `display_name` -- those live on `dim_watermark_source`). Fixed to use the actual columns (`source_name`, `source_version`, `config_hash`, `first_seen_at`, `last_seen_at`). The bug was latent because the function was never exercised before this refactor.
- **agent-state-mcp 0.1.1 -> 0.1.2**: `tools.py` no longer carries inline SQL for `find_failed_runs`, `list_tracked_domains`, `list_run_sources`, `list_watermark_sources`. Each delegates to the corresponding `agent_state.query` function.

### notes
- The view rewrite uses `CREATE OR REPLACE VIEW` so existing databases pick up the change automatically on next schema init. No migration required.
- Dimensional-modeling discipline verified: all new queries route fact -> dim or dim -> fact; no fact-to-fact joins introduced.

## 0.22.11

### fixed
- **agent-state-mcp 0.1.0 -> 0.1.1**: three post-review fixes.
  - Connection cache: `_open_db` now yields a singleton `AgentStateDB` per `db_path` for the life of the server instead of opening+closing on every tool call. Schema DDL (15 CREATE TABLE, 10 CREATE INDEX, 4 CREATE VIEW) no longer re-executes per invocation. `atexit` hook closes cached connections on server shutdown.
  - Envelope consistency for single-row tools: `get_run`, `get_active_skill_version`, `resolve_skill_version_by_hash` now return `{data: null, _meta: {...}}` on not-found/missing-DB paths, matching their docstring contract. Previously returned `rows: []` which would `KeyError` callers expecting `data`.
  - `find_failed_runs` SQL: replaced the f-string WHERE-clause interpolation (structurally unsafe, though not currently exploitable because the interpolated fragment was literal) with list-concatenation construction where every user value binds via `?`.
  - `get_run_messages_tool` gained an explicit `limit: int = 500` param (max 5000) with a `_meta.truncated=true` flag when the cap is hit. Previously returned unbounded rows.
  - `get_run_tree` server-side docstring now mentions `_meta` in its Returns line, matching the SERVER_INSTRUCTIONS envelope contract.
- **skill-maintainer 0.5.1 -> 0.5.2**: `hooks/sync-bundled-ref.sh` bug fixes.
  - `jq` extractor now picks up `tool_input.edits[].file_path` (MultiEdit shape) in addition to the Edit/Write `tool_input.file_path`. Previously MultiEdit touches to `best_practices.md` silently skipped the sync.
  - `repo_root` derivation now handles relative paths correctly by resolving absolute first. Previously `.skill-maintainer/best_practices.md` as a relative path derived `repo_root` as `$PWD` (the `dirname/..` of `.skill-maintainer` is the current directory, not the repo root), which happened to work when CWD was already the repo root but would break otherwise.

## 0.22.10

### changed
- **skill-maintainer 0.5.0 -> 0.5.1**: README now documents the v0.5.0 skills (sync-bundled-ref, finish-session), the session-log-drafter agent, and the PostToolUse bundled-ref sync hook. Version bump is doc-only; no behavioral changes. `tools/skill-maintainer/README.md` also picked up the per-page snapshot note on the `upstream` subcommand row (behavior landed in 0.4.0, never reflected).

## 0.22.9

### added
- **skill-maintainer v0.5.0**: three new pieces for end-of-session workflow.
  - `sync-bundled-ref` skill: manual mirror of `.skill-maintainer/best_practices.md` -> `skills/skill-maintainer/references/best_practices.md` (the seed copied by `skill-maintain init` in new repos). Fixes the silent drift gap documented this session.
  - `sync-bundled-ref.sh` PostToolUse hook at `skills/skill-maintainer/hooks/`: fires on Edit/Write/MultiEdit of the working copy and auto-mirrors. `cmp -s` gated so no-op edits are silent; exits 0 always.
  - `finish-session` composed skill: orchestrates `session-log-drafter` subagent -> bundled-ref sync check -> version-bump detection -> quality scan. Single entrypoint before commits.
  - `session-log-drafter` agent (at `skills/skill-maintainer/agents/`): forked subagent that reads conversation + `git diff` and drafts a house-style entry for `internal/log/log_YYYY-MM-DD.md`. Returns content only; main session writes to disk.
- **skill-maintainer**: `sync-versions` skill gained step 3c-alt for multi-skill plugins -- discovers all sub-skill SKILL.md files under the plugin and bumps each `metadata.version` + `metadata.last_verified`. Closes the gap that required manual sub-skill bumps for skill-maintainer itself.

### changed
- **skill-maintainer**: bumped plugin + Python package to v0.5.0. All six SKILL.md files (init-maintenance, maintain, quality, sync-versions, sync-bundled-ref, finish-session) carry `metadata.version: 0.5.0`.
- Root `.claude/settings.json`: added `env.ENABLE_SECURITY_REMINDER=0` to disable the `security-guidance` plugin's PreToolUse hook for this repo. Hook substring-matches on tokens that appear in prose (code-eval builtin names, serialization libs, DOM sinks) with no path awareness; false-positive rate on docs is high. Trade-off documented in CLAUDE.md "Security hook gotcha" section.
- Root `CLAUDE.md`: added "Canonical best_practices.md" subsection, "Security hook gotcha" subsection, and a `state/pages/<slug>.md` bullet to the State section. Updated plugin versioning paragraph to flag sub-skill bump requirement.

## 0.22.8

### added
- **agent-state-mcp** (new plugin, v0.1.0): stdio MCP server at `apps/agent-state-mcp/` that exposes `<HOME>/.claude/agent_state.duckdb` to Claude Code as 18 read-only tools (`list_recent_runs`, `get_run_tree`, `find_failed_runs`, `get_watermark_status`, `list_skills_by_domain`, `get_flywheel_metrics`, etc.). Thin wrapper over the existing `agent-state` Python package; designed so Claude reaches for MCP tools instead of shelling out to the `agent-state` CLI. Structured return envelopes (`{rows, _meta}` with row_count, duration_ms, schema_version), parameterized queries, graceful fallback when the DB is missing. Includes a single `agent-state-mcp` skill teaching Claude the question-to-tool mapping.
- Root `.mcp.json` now documents an opt-in `agent-state` server entry under `_available_servers` (commented out by default; copy into `mcpServers` to enable).

### changed
- Root `pyproject.toml` workspace now includes `apps/agent-state-mcp`.
- Root `.claude-plugin/marketplace.json` registers the new plugin.
- Root `CLAUDE.md` repo structure and workspace dependencies table updated.

## 0.22.7

### added
- **skill-maintainer**: `upstream` command now retains per-page content snapshots under `.skill-maintainer/state/pages/<slug>.md`, so subsequent runs report concrete `+added / -removed lines, ±chars` deltas instead of just "changed". Delta metadata is also persisted in `changes.jsonl`.
- **skill-maintainer**: `.skill-maintainer/best_practices.md` gains HTML-comment source anchors (`<!-- source: <url> | last_verified: <date> -->`) under each section, routing upstream doc changes to the specific rules they affect. Grep by URL to find rules to re-verify.

### changed
- **skill-maintainer**: bumped plugin + Python package to v0.4.0. Bundled reference (`skills/skill-maintainer/references/best_practices.md`) re-synced from this repo's working copy so new inits pull the latest rules (AGENTS.md compat, 1% description budget, `when_to_use` frontmatter field, corrected hook exit codes, 25KB MEMORY.md cap, 1536-char skill-listing truncation, compaction budget details).
- **mlx-skills** (sibling repo): bootstrapped with `skill-maintain init`, seeded best_practices.md, tracked_repos configured for mlx/mlx-lm/mlx-vlm/mlx-embeddings/mlx-examples, baseline page snapshots captured.

## 0.22.6

### fixed
- **mece-decomposer**: bump to v0.4.1 so marketplace update refreshes stale hooks.json cache (array->object fix from v0.22.4 was never picked up)
- **dimensional-modeling**: bump to v0.3.1 (same stale cache issue)
- **env-forge**: bump to v0.3.1 (same stale cache issue)
- **tui-design**: bump to v0.3.1 (same stale cache issue)

## 0.22.5

### added
- **dev-conventions**: version pinning conventions in python.md and javascript.md directives -- applications pin exact, libraries use floors/caret ranges
- **dev-conventions**: dependency change tracking in doc-conventions -- session logs now include a structured table of package changes

### changed
- **dev-conventions**: bumped plugin to v0.5.0
- Global rule (`.claude/rules/general.md`) now includes version pinning guidance for both uv and bun

## 0.22.4

### added
- **tui-design**: SessionStart hook auto-injects Five Principles when Rich/Textual/Questionary/Click imports detected. Directive: `hooks/directives/tui-principles.md`. Bumped to v0.3.0.
- **dimensional-modeling**: SessionStart hook auto-injects Kimball principles when DuckDB imports, .duckdb files, or fact_/dim_ SQL patterns detected. Directive: `hooks/directives/kimball-principles.md`. Bumped to v0.3.0.
- **mece-decomposer**: SessionStart hook auto-injects MECE principles when Agent SDK imports or decomposition files detected. Directive: `hooks/directives/mece-principles.md`. Bumped to v0.4.0.
- **env-forge**: SessionStart hook auto-injects task-first design principles when `.env-forge/` directory or fastapi-mcp usage detected. Directive: `hooks/directives/env-forge-principles.md`. Bumped to v0.3.0.

### changed
- **dev-conventions**: refactored SessionStart hook to composable directive files (`hooks/directives/*.md`). Each directive declares its trigger signal (`python`, `javascript`, `docs`, `any`) on line 1. Adding a new convention = dropping a file, no shell editing.
- **dev-conventions**: promoted doc-conventions (last-updated dates, lowercase filenames, document-the-why) to auto-loaded directive alongside TDD and session logging
- **dev-conventions**: bumped plugin to v0.4.0

## 0.22.3

### added
- **json-query**: added to marketplace -- installable plugin for jg/jq tool selection and syntax guidance (from schema-bench research)

### changed
- **dev-conventions**: SessionStart hook now detects project markers up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, etc.

### fixed
- **dev-conventions**: replaced bare `python3` calls in SessionStart hook with `jq` -- eliminates stdlib json usage and bare python3 convention violations

## 0.22.2

### changed
- **dev-conventions**: SessionStart hook now injects TDD as a directive (not a hint) and adds session logging directive when `internal/` directory exists
- **dev-conventions**: bumped plugin to v0.3.0

## 0.22.1

### changed
- **VISION.md**: added `## the architecture` section (trees not workflows, harness coupling, context isolation, use-before-prepare, structured outputs as state, compound feedback loops)
- **VISION.md**: broadened intro paragraph to frame both architecture and retrieval
- **VISION.md**: extended `## what this means for this repo` with 4 new bullets (agent topology, harness-native design, state management, compound feedback)
- **CLAUDE.md**: updated blockquote to reference architectural worldview alongside retrieval
- **CLAUDE.md**: updated "Context as retrieval" subsection to match new VISION.md language
- **README.md**: updated VISION.md blockquote to match new language, dropped overly specific detail
- **docs/analysis/memory_and_rules_system.md**: updated auto memory description to reflect VISION.md architecture section

## 0.22.0

### added
- **skill-dashboard**: Phase B -- drill-down, measure, verify
  - `skill-measure` tool: per-file token breakdown for a single skill (path, chars, tokens, pctOfTotal)
  - `skill-verify` tool: app-only tool that updates `metadata.last_verified` in SKILL.md frontmatter on disk
  - sidebar UI: click any skill row to open file breakdown table with percentage bars and budget status
  - "Mark Verified" button: updates SKILL.md and refreshes quality data
  - two-panel layout (main + sidebar) with grid-based responsive design
  - new components: SkillSidebar, FileBreakdownTable
  - refactored `measureTokens` into `measureTokensDetailed` (returns per-file entries) + thin wrapper
  - `findSkillPath` helper for resolving skill name to SKILL.md path
  - bumped to v1.1.0

## 0.21.0

### changed
- **skill-dashboard**: rebuilt as ext-apps MCP App (TypeScript, React, same pattern as mece-decomposer)
  - replaced Python rawHtml server with interactive ext-apps UI
  - `skill-quality-check` tool: discovers skills/plugins, runs 5 per-skill + 3 per-plugin + 5 repo checks
  - optional `filter` parameter for skill name substring matching
  - all check logic ported to native TypeScript (gray-matter for frontmatter, no Python dependency)
  - components: SummaryBar, SkillTable with token budget bars, PluginTable, RepoChecks with status dots
  - dual transport: stdio + HTTP (port 3002)
  - version sync check: validates plugin.json, marketplace.json, SKILL.md, pyproject.toml alignment
  - removed Python files: server.py, templates/dashboard.html, pyproject.toml
  - removed from uv workspace members (no longer a Python package)
  - bumped to v1.0.0

### added
- **skill-maintainer**: `/skill-maintainer:sync-versions <plugin> <version>` -- bump a plugin's version across all sources (plugin.json, marketplace.json, SKILL.md, pyproject.toml) atomically

### fixed
- **version alignment**: synced plugin.json across 4 plugins that had drifted from marketplace.json
  - dimensional-modeling: 0.1.0 -> 0.2.0
  - tui-design: 0.1.0 -> 0.2.0
  - skill-maintainer: 0.1.0 -> 0.3.0
  - readwise-reader: marketplace 0.1.0 -> 1.0.0 (aligned with plugin.json/SKILL.md)

## 0.20.1

### added
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:quality` (filter by skill name, substring match)
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:init-maintenance` (target directory path)
- **skill-maintainer**: cross-reference validation in quality skill (checks `load the \`X\` skill` patterns resolve)
- **skill-maintainer**: reference file date check in quality skill (checks `last updated:` line in references/*.md)

## 0.20.0

### added
- **skill-maintainer**: new installable plugin at `skills/skill-maintainer/`
  - `/skill-maintainer:maintain`: full maintenance pass (upstream, sources, quality, best practices review) -- replaces legacy `.claude/commands/maintain.md`
  - `/skill-maintainer:quality`: quick quality check (spec, tokens, freshness, description quality) -- no CLI install required
  - `/skill-maintainer:init-maintenance`: set up `.skill-maintainer/` config and state in any repo
  - `references/best_practices.md`: machine-parseable checklist bundled with the plugin
  - skills embed maintenance knowledge directly (thresholds, rules, checks) -- falls back to CLI if available but doesn't require it
  - registered in marketplace.json

### changed
- **skill-maintainer** (CLI): README updated to note plugin is the primary interactive interface, CLI is for CI/headless
- CLAUDE.md: updated repo structure, installation list, maintenance table for plugin

### removed
- `.claude/commands/maintain.md`: replaced by `/skill-maintainer:maintain` plugin skill
- `.claude/commands/` directory: empty after command removal

## 0.19.0

### added
- **dev-conventions**: SessionStart hook for automatic project-type detection
  - detects Python/JS markers in cwd, injects uv/orjson/bun/TDD conventions as additionalContext
  - skills reframed as on-demand references (no longer claim background auto-trigger)
  - bumped plugin version to 0.2.0

## 0.18.3

### fixed
- **skill-maintainer**: `measure_tokens()` now counts only `.md` files (was counting `.py`, `.json`, `.sh`, etc. that are executed, not loaded into context)
  - mece-decomposer dropped from 23,283 to 16,647 tokens (scripts/validate_mece.py was 6,636 phantom tokens)

## 0.18.2

### changed
- **mece-decomposer**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `decompose`, `interview`, `validate`, `export` now use Agent Skills frontmatter (proper `skills/<name>/SKILL.md` layout)
  - removed `commands/` directory (legacy format caused "Legacy format" separator in Cowork)
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **mece-decomposer**: bumped plugin version to 0.3.0
- **mece-decomposer**: updated main skill and README references from "commands" to "skills"
- **env-forge**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `browse`, `forge`, `launch`, `verify` now use Agent Skills frontmatter
  - removed `commands/` directory
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **env-forge**: bumped plugin version to 0.2.0
- **env-forge**: updated main skill and README references from "commands" to "skills"
- CLAUDE.md: updated stale `apps/env-forge/commands/forge.md` path reference

## 0.18.1

### added
- **agent-state**: `domain`, `task_type`, `status` columns on `dim_skill_version` for routing and lifecycle management
- **agent-state**: new workspace package for DuckDB audit and state tracking
  - Kimball star schema: `fact_run`, `fact_run_message`, `fact_watermark`, `dim_run_source`, `dim_skill_version`, `dim_watermark_source`
  - `RunContext` context manager: atomic watermark commits on success, automatic rollback on failure
  - skill version lineage: `dim_skill_version` connects pipeline outputs to agent inputs
  - watermark tracking: replaces `upstream_hashes.json` with queryable history (`v_latest_watermark`)
  - views: `v_run_tree` (recursive hierarchy), `v_flywheel` (producer->skill->consumer), `v_restartable_failures`
  - migration from `changes.jsonl` and `upstream_hashes.json`
  - CLI: `agent-state init|status|runs|tree|watermarks|flywheel|migrate`
  - storage: single global DuckDB at `<HOME>/.claude/agent_state.duckdb`

## 0.18.0

### changed
- **repo structure**: reorganized from flat layout to type-based grouping
  - `skills/`: pure markdown skill bundles (tui-design, dimensional-modeling, cogapp-markdown, dev-conventions, mcp-apps, plugin-toolkit)
  - `apps/`: MCP server applications (mece-decomposer, env-forge, skill-dashboard, heylook-monitor, readwise-reader)
  - `tools/`: CLI packages (skill-maintainer)
- **readwise-reader**: migrated from another project into `apps/readwise-reader/`
  - flattened `plugin/readwise-reader/` contents to top level
  - converted build system from setuptools to hatchling
  - skill-maintainer dep changed from git URL to workspace reference
  - removed non-portable artifacts (certs, models, zip, .venv, scripts/package_plugin.sh)
- workspace member paths updated: `skill-maintainer` -> `tools/skill-maintainer`, `env-forge` -> `apps/env-forge`, etc.
- readwise-reader excluded from default workspace (requires Python 3.13+)
- skill-dashboard `PROJECT_ROOT` fixed for new `apps/` depth
- marketplace.json source paths updated for all plugins
- root `.mcp.json` server path updated
- skill-maintainer git-install subdirectory updated to `tools/skill-maintainer`

### fixed
- **readwise-reader**: added `metadata.last_verified`, `metadata.author`, `metadata.version` to all 3 SKILL.md files
- **readwise-reader**: fixed description quality (added WHAT verb + WHEN trigger) on all 3 skills
- **readwise-reader**: added `repository` field to plugin.json
- stale path references in READMEs and rules from pre-reorg layout (skill-maintainer git-install path, skill-dashboard server.py path, mece-decomposer dev setup path)
- general.md state path corrected to `.skill-maintainer/state/`
- marketplace_distribution_patterns.md section 4.1 updated for current repo layout
- create-mcp-app and migrate-oai-app descriptions fixed (added WHAT verb)
- docs/claude-docs: flattened 2 files from nested .md-named directories, added to index
- docs/README.md: removed empty internals section, added memory and best_practices to claude-docs index
- removed stale web-tdd references from 4 analysis docs (deleted in v0.14.0)
- mcp_ecosystem_audit: updated for current plugin set (added readwise-reader, env-forge, dev-conventions)
- claude_ecosystem_synthesis.md: fixed 9 stale path/config references for v0.17.0/v0.18.0 changes
- claude_ecosystem_synthesis.md: rewrote section 8 for property-driven maintenance (was stale CDC pipeline from v0.12.x), fixed report count 15->16
- skills_guide_analysis.md: config.yaml -> .skill-maintainer/config.json

## 0.17.0

### changed
- **skill-maintainer**: converted from `package = false` scripts to a proper installable Python package
  - new `src/skill_maintainer/` package with CLI entry point `skill-maintain`
  - git-installable: `uv add git+<repo>#subdirectory=skill-maintainer`
  - all commands accept `--dir <path>` to target any skill repo (default: `.`)
  - subcommands: init, validate, quality, freshness, measure, test, upstream, sources, log
  - per-repo config in `.skill-maintainer/config.json` (upstream URLs, tracked repos)
  - per-repo state in `.skill-maintainer/state/` (hashes, changes log)
  - best_practices.md moved to `.skill-maintainer/best_practices.md`
  - version bumped to 0.2.0
- **skill-dashboard**: replaced `sys.path.insert` hack with proper `skill-maintainer` workspace dependency
  - imports now: `from skill_maintainer.tests import ...` and `from skill_maintainer.shared import ...`
  - removed unused `sys` import

## 0.16.0

### changed
- **skill-dashboard**: rewritten to show full run_tests.py dataset (was: 5 columns from file scan; now: skills + plugins + repo hygiene pass/fail)
  - server.py imports test_skills/test_plugins/test_repo_hygiene from run_tests.py (no more duplicated discovery/measurement code)
  - HTML template: skills table with spec, description quality, freshness, budget, body size; plugins table with manifest/marketplace/README checks; repo hygiene section
  - dropped pyyaml dependency (no longer parses frontmatter directly)
  - bumped to v0.3.0
- **skill-dashboard**: moved `.mcp.json` from `skill-dashboard/` to project root so Claude Code auto-discovers the MCP server
- **skill-maintainer**: consolidated `measure_tokens()` and `check_description_quality()` into `shared.py` (was duplicated in run_tests.py and quality_report.py)

## 0.15.1

### added
- **skill-maintainer**: `run_tests.py` -- red/green test suite encoding best_practices.md as pass/fail checks
  - three categories: skills (spec, budget, body size, staleness, description), plugins (manifest, marketplace, README), repo hygiene (gitignore, hooks, state, duplicates, freshness)
  - `--verbose` shows all results; `--category skills|plugins|repo` runs one category
  - no network calls, no file writes, pure read-only
- **skill-maintainer**: `/maintain` slash command for full maintenance passes
  - orchestrates pull_sources.py -> check_upstream.py -> quality_report.py -> best_practices.md review
  - Claude proposes edits to best_practices.md based on detected changes; user approves before any writes
- **skill-maintainer**: `pull_sources.py` script for pulling 10 tracked coderef repos and detecting changes
  - records HEAD SHAs in `upstream_hashes.json["local_repos"]`, captures commit logs for changed repos
  - appends `source_pull` events to `changes.jsonl` audit log
  - CLI flags: `--no-pull`, `--no-save`, `--no-log`
- `VISION.md`: design principles document -- skills as retrieval, precision/recall framework, progressive disclosure, always-loaded context justification
- **skill-maintainer**: `shared.py` -- added `discover_plugins()` function (mirrors `discover_skills()` for plugin directories)

### changed
- `query_log.py`: added `source_pull` event type display
- `.claude/rules/plugins.md`: removed stale references to config.yaml and monitored_sources.md (removed in v0.13.0)
- **skill-maintainer**: `best_practices.md` rewritten as machine-parseable checklist with sections mapped to VISION.md principles
- **skill-maintainer**: `README.md` rewritten with full workflow section (before/after changes, periodic maintenance, individual checks table)

### removed
- PostToolUse hook on Skill tool (was firing on every skill invocation across all sessions; staleness now checked on-demand via `/maintain` or `check_freshness.py`)
- `.claude/hooks/check-skill-freshness.sh`: dead hook script (PostToolUse hook removed)
- `.gitignore`: removed blanket `.claude/` ignore; project-shared files (rules, commands, hooks, settings.json) are now tracked

## 0.15.0

### changed
- **pyproject.toml**: restructured as uv workspace with four members (skill-maintainer, env-forge, skill-dashboard, mece-decomposer)
  - each subfolder declares its own dependencies instead of a monolithic root
  - removed `coderef/` editable paths that broke on clone (local-only symlinks)
  - `skills-ref` now installed from PyPI; `mcp-ui-server` from git (github.com/idosal/mcp-ui)
  - root is a workspace coordinator with dev-only deps (pytest, ruff)
  - setup: `uv sync --all-packages`; existing `uv run` commands unchanged

### added
- **dev-conventions**: new installable plugin extracting global CLAUDE.md into selective skills
  - `python-tooling` (background): enforces uv over pip, orjson over json
  - `bun-tooling` (background): enforces bun over npm/yarn/pnpm
  - `tdd-workflow` (user-invocable): red/green TDD workflow
  - `doc-conventions` (user-invocable): last-updated dates, lowercase filenames, session logs, document the "why"

## 0.14.0

### removed
- **web-tdd**: removed plugin (generic TDD workflow that duplicates Claude's built-in knowledge; stack preferences belong in CLAUDE.md)

### changed
- migrated all JS/TS tooling references from npm/npx to bun/bunx across package.json scripts, SKILL.md files, READMEs, and settings
- replaced package-lock.json with bun.lockb in heylook-monitor and mece-decomposer/mcp-app

## 0.13.0

### changed
- **skill-maintainer**: replaced pipeline-driven model with property-driven maintenance
  - removed: SKILL.md (no longer a skill), DuckDB store (store.py, migrate_state.py), CDC pipeline (docs_monitor.py, source_monitor.py, update_report.py, apply_updates.py), journal system (journal.py), config.yaml, state.json
  - added: pre-commit git hook (validates staged SKILL.md files with skills-ref)
  - added: PostToolUse Claude Code hook (checks last_verified age when any skill is invoked)
  - added: quality_report.py (unified CLI: validation, token budget, last_verified, description quality)
  - added: check_upstream.py (on-demand upstream doc change detection via llms-full.txt hashing)
  - added: query_log.py (query append-only changes.jsonl audit log)
  - simplified: validate_skill.py, measure_content.py, check_freshness.py (removed DuckDB deps, auto-discover skills)
  - added `.claude/settings.json` with PostToolUse hook config
  - added `.claude/hooks/check-skill-freshness.sh`
- all 10 SKILL.md files: added `metadata.last_verified: 2026-02-25` to frontmatter
- `pyproject.toml`: removed `duckdb` dependency
- `CLAUDE.md`: removed DuckDB/CDC/pipeline docs, updated maintenance section with hook/CLI model

## 0.12.1

### changed
- **env-forge**: extracted `scripts/shared.py` module from duplicated code in catalog.py and materialize.py (constants, download_file, load_jsonl, ensure_dir)
- **env-forge**: materialize.py now compile-checks generated server.py and verifiers.py before writing (WARNING on error, never blocks)
- **env-forge**: verifier assembly deduplicates imports across verifier records instead of raw code concatenation
- **env-forge**: forge.md adds new step 2 "Reference from Catalog" (search AWM-1K for structural exemplar before generating from scratch)
- **env-forge**: README.md expanded with Quick Start, Status (Phase 1 vs 2), and Patterns sections
- `docs/README.md`: expanded to authoritative documentation index (16 analysis reports, synthesis, internals, 18 captured claude-docs)
- `CLAUDE.md`: replaced 36-line documentation index with pointer to docs/README.md; added catalog-as-exemplar pattern and huggingface-hub dependency; fixed domain report count (15 -> 16); net ~20 lines removed

## 0.12.0

### added
- **env-forge**: new installable plugin for generating database-backed MCP tool environments
  - SKILL.md: task-first environment design methodology extracted from AWM synthesis pipeline
  - 2 commands (browse, forge) + 2 Phase 2 stubs (launch, verify)
  - references: schema_patterns.md, api_design_rules.md, verification_patterns.md, fastapi_mcp_template.md, catalog_index.md
  - scripts: catalog.py (search/browse AWM-1K on HF), materialize.py (fetch and write environment), validate_env.py (structural validation)
  - two modes: browse 1000 pre-generated environments from AWM-1K catalog, or forge new ones from scenario descriptions
  - covers: SQLite schema synthesis, RESTful API design, FastAPI+MCP server generation, DB state verification, self-correction patterns
  - fetches data from Snowflake/AgentWorldModel-1K on HF at runtime (no large files in repo)

## 0.11.3

### added
- `skill-dashboard`: new project-scoped Python MCP App plugin
  - pure Python server (FastMCP + mcp-ui rawHtml) -- no Node.js or build step
  - reads skill registry from `skill-maintainer/config.yaml`, SKILL.md frontmatter for versions
  - queries DuckDB store for freshness and token budget data; falls back to file mtime scan
  - self-contained HTML dashboard (Tailwind CDN + Alpine.js CDN) with color-coded status, budget bars, and filter buttons
  - reference implementation for the Python-native MCP App pattern
  - `mcp-ui-server` editable dependency added to `pyproject.toml`
- `.claude/rules/general.md`: always-loaded general conventions (package manager, JSON, logs, READMEs)
- `.claude/rules/skills.md`: path-scoped to `**/SKILL.md` -- trigger phrases, 1024-char limit, script paths, 500-line limit
- `.claude/rules/plugins.md`: path-scoped to `**/.claude-plugin/**`, `**/plugin.json` -- new plugin checklist, auto-discovery, required fields

### changed
- `skill-maintainer/config.yaml`: added `https://code.claude.com/docs/en/memory` to `anthropic-skills-docs` watched pages
- `CLAUDE.md`: removed Conventions section (~28 lines); replaced with one-liner pointing to `.claude/rules/`; fixed domain report count (14 -> 15)

## 0.11.2

### added
- `docs/analysis/memory_and_rules_system.md`: domain report covering the six-level memory hierarchy, auto memory storage and behavior, CLAUDE.md import syntax, `.claude/rules/` modular path-scoped rules, glob patterns, organization-level management, and how this repo uses memory
- `docs/reports/claude_ecosystem_synthesis.md`: new section 2.5 (Memory and Rules System) with hierarchy table, auto memory details, import syntax, rules comparison table
- `docs/reports/claude_ecosystem_synthesis.md`: memory & rules row added to Component Maturity Assessment (section 4)
- `docs/reports/claude_ecosystem_synthesis.md`: memory mentions added to Solo (CLAUDE.local.md, auto memory) and Team (.claude/rules/) building strategies (section 5), and Enterprise (managed policy CLAUDE.md) tier (section 5)
- `docs/reports/claude_ecosystem_synthesis.md`: auto memory and project memory rows added to This Repo as Reference (section 10)
- `docs/reports/claude_ecosystem_synthesis.md`: memory report added to Report Index (section 11)

### changed
- `skill-maintainer/SKILL.md`: added disambiguation note in journal section distinguishing DuckDB session journal from Claude's built-in auto memory system

## 0.11.1

### fixed
- **mece-decomposer MCP App**: VALIDATE_SCRIPT path resolution broken when running from compiled `dist/index.cjs` -- `import.meta.dirname` polyfills to `__dirname` (= `mcp-app/dist/`), so `..` resolved to `mcp-app/` instead of `mece-decomposer/`. Added `PLUGIN_ROOT` constant with source vs dist detection.
- **mece-decomposer MCP App**: HTTP server bound to `0.0.0.0` (all interfaces) creating DNS rebinding risk. Changed to `127.0.0.1` (localhost only).
- **mece-decomposer MCP App**: stale build artifacts (`index.js`, `server.js`) accumulating in `dist/` from older builds. Added `prebuild` script to clean dist before each build.

## 0.11.0

### added
- **7 domain reports** in `docs/analysis/`: comprehensive coverage of the Claude extension ecosystem
  - `plugin_system_architecture.md`: plugin anatomy, schema, component types, auto-discovery, implementation audit of all 7 repo plugins
  - `marketplace_distribution_patterns.md`: marketplace schema, source types, monorepo patterns, enterprise distribution
  - `mcp_protocol_and_servers.md`: MCP protocol fundamentals, primitives, transports, TypeScript/Python SDKs, inspector, registry
  - `mcp_apps_and_ui_development.md`: MCP Apps SDK, MCP UI SDK, tool-UI linkage, React hooks, framework templates, bundling
  - `hooks_system_patterns.md`: all 14 event types, 3 hook types, matchers, security/automation patterns, plugin hooks
  - `subagents_and_agent_teams.md`: custom agents, built-in agents, tool control, agent teams, delegation patterns
  - `cross_surface_compatibility.md`: 7 surfaces, feature compatibility matrix, transport requirements, permission model differences
- **synthesis report** in `docs/reports/claude_ecosystem_synthesis.md`: executive summary, architecture decision tree, component maturity assessment, building strategies, cross-surface strategy, maintenance problem, report index

### changed
- `CLAUDE.md`: refactored to cover full ecosystem (plugins, MCP, hooks, agents), added documentation index section, added plugin/MCP development sections, streamlined from 251 to 256 lines
- `README.md`: added documentation section with links to all 14 domain reports and synthesis, organized by domain/existing/synthesis/internals categories

## 0.10.0

### added
- **mece-decomposer MCP App**: interactive tree visualization companion for MECE decompositions
  - 4 MCP tools: mece-decompose (tree render), mece-validate (structural validation), mece-refine-node (app-only editing), mece-export-sdk (Agent SDK code generation)
  - React UI with recursive tree view, expand/collapse, node selection, dependency badges
  - streaming support via useStreamingTree hook (progressive tree building as Claude generates)
  - sidebar panels: metadata, node detail (editable), validation report with score gauges, export preview with copy
  - SDK code generation: walks tree recursively, emits Agent() for agent atoms, orchestration functions for branches
  - follows ext-apps SDK patterns (basic-server-react structure, threejs-server wrapper pattern)
  - validation tool spawns validate_mece.py via subprocess with graceful fallback if uv unavailable
  - co-located at mece-decomposer/mcp-app/

## 0.9.0

### added
- **mece-decomposer**: new installable plugin for MECE decomposition of goals, tasks, and workflows
  - SKILL.md: 4 commands (decompose, interview, validate, export)
  - references: decomposition_methodology.md, sme_interview_protocol.md, validation_heuristics.md, agent_sdk_mapping.md, output_schema.md
  - scripts: validate_mece.py for deterministic structural validation of decomposition JSON
  - dual output: human-readable tree for SME validation + structured JSON mapping to Agent SDK primitives
  - covers: MECE scoring rubrics, depth-adaptive rigor, atomicity criteria, cross-branch dependency scanning

### fixed
- restored root pyproject.toml (was accidentally overwritten by mece-decomposer-specific one)
- restructured mece-decomposer to standard plugin layout (skills/mece-decomposer/)

## 0.8.0

### added
- **tui-design**: new installable plugin for terminal UI design
  - SKILL.md: 5 principles (semantic color, responsive layout, right component, visual hierarchy, progressive density)
  - references: rich_patterns.md, questionary_patterns.md, anti_patterns.md, layout_recipes.md
  - covers: Rich component selection, Questionary interactive prompts, 9 anti-patterns with before/after, 4 complete layout recipes
  - 16-color safe palette with semantic meanings, pipe-safe output patterns

## 0.7.0

### added
- **dimensional-modeling**: new installable plugin for Kimball-style star schema design
  - SKILL.md: router skill teaching dimensional modeling patterns for DuckDB agent state
  - references: schema_patterns.md, query_patterns.md, key_generation.md, anti_patterns.md, dag_execution.md
  - covers: SCD Type 2 dimensions, hash surrogate keys, fact table design, analytical views, agent execution DAG
- star-schema-llm-context: repo cleanup
  - deleted ~3950 lines of dead knowledge graph code (graph_algorithms.py, mcp_server.py, schema.sql, db_manager.py, setup.py, requirements.txt, Makefile, ARCHITECTURE.md, config.yaml)
  - rewrote README.md with clear vision statement (pattern library, not code library)
  - rewrote CLAUDE.md to reflect current state
  - added pyproject.toml
  - replaced speculative expansion roadmap (embeddings, graph DB) with DAG execution model and automation patterns

## 0.6.0

### changed
- **store.py**: complete rewrite from OLTP to Kimball dimensional model
  - MD5 hash surrogate keys on all dimensions (replaced integer PKs and MAX(id)+1 pattern)
  - SCD Type 2 on all dimension tables (effective_from/to, is_current, hash_diff for change detection)
  - no PRIMARY KEY constraints on dimensions (SCD Type 2 requires multiple rows per entity)
  - no primary keys on fact tables (dropped all 6 sequences; grain = composite dimension keys + timestamp)
  - no FK constraints (join by convention, validate at application layer)
  - metadata columns on all tables: record_source, session_id, inserted_at
  - meta_schema_version table for schema evolution tracking
  - meta_load_log table for operational visibility (script execution tracking)
  - merged fact_session into fact_session_event (session boundaries are events with event_type='session_start'/'session_end')
  - all views updated to filter is_current = TRUE and join on hash_key
  - automatic v1 -> v2 schema migration (detects old schema, drops and recreates)
- **migrate_state.py**: added --force flag for clean schema recreation, integrated with meta_load_log
- **source_monitor.py**: explicit record_source='source_monitor' on change records
- **journal.py**: rewritten for merged session/event model (no more fact_session table)
- duckdb_schema.md: complete rewrite reflecting v2 Kimball schema

### added
- `v_skill_budget_trend` view and `--budget-trend` CLI flag: token budget trend over time per skill (meta-cognition: "am I getting fatter?")
- `docs/analysis/abstraction_analogies.md`: unified framework document -- selection under constraint, five invariant operations (decompose/route/prune/synthesize/verify), database analogy for skills, DAG hierarchy model
- CLAUDE.md: selection-under-constraint design principle, dimensional model section, three-repo architecture
- README.md: design philosophy section
- star-schema-llm-context design docs: library_design.md and abstraction_analogies.md (canonical home)

### fixed
- SCD Type 2 bug: removed PRIMARY KEY from dimension tables that would cause constraint violations when closing old rows and opening new ones (hash_key must appear in multiple rows for SCD Type 2)

## 0.5.0

### added
- DuckDB-backed relational store (`store.py`) replacing flat `state.json` overwrite pattern
  - star schema: dimension tables (dim_source, dim_skill, dim_page, skill_source_dep) + append-only fact tables (fact_watermark_check, fact_change, fact_validation, fact_update_attempt, fact_content_measurement, fact_session, fact_session_event)
  - pre-built views: v_latest_watermark, v_latest_page_hash, v_skill_freshness, v_skill_budget, v_latest_source_check
  - WAL mode for concurrent access from hooks
  - backward-compatible state.json export via `Store.export_state_json()`
- `migrate_state.py`: one-time migration from state.json into DuckDB with round-trip verification
- `measure_content.py`: token budget tracker for all tracked skills
  - walks skill directories, classifies files, measures line/word/char/token counts
  - budget thresholds: 4000 tokens (warn), 8000 tokens (critical)
  - records measurements in fact_content_measurement for historical tracking
- `journal.py`: session activity logger with three modes
  - append: fast JSONL buffer for hooks (no DuckDB access, <50ms)
  - ingest: batch import JSONL into DuckDB
  - query: show recent session activity with filters
- `/skill-maintainer budget` command for token budget measurement
- `/skill-maintainer history` command for temporal change queries
- `/skill-maintainer journal` command for session activity queries
- `docs/internals/duckdb_schema.md`: full schema documentation
- `docs/analysis/data_centric_agent_state_research.md`: strategic research on star schema patterns for LLM agent systems (10 use cases analyzed)
- `duckdb>=1.0` dependency

### changed
- `docs_monitor.py`: migrated from load_state/save_state to Store class
- `source_monitor.py`: migrated from load_state/save_state to Store class
- `check_freshness.py`: migrated from JSON traversal to DuckDB v_skill_freshness view
- `apply_updates.py`: records update attempts and validations in DuckDB
- `validate_skill.py`: records validation results in fact_validation table
- `update_report.py`: reads changes from DuckDB instead of state dict
- skill-maintainer SKILL.md version bumped to 0.2.0 with new commands documented

## 0.4.0

### changed
- migrated all plugins to canonical `.claude-plugin/plugin.json` manifest location (was `plugin.json` at root)
- removed non-standard `skills` and `agents` array fields from plugin manifests (auto-discovery handles these)
- added `repository` field to all plugin manifests
- created root `.claude-plugin/marketplace.json` making this repo a proper plugin marketplace
- rewrote README.md installation section with correct CLI commands (`install`/`uninstall`, not `add`/`remove`)
- README.md now documents the marketplace-based install flow (`/plugin marketplace add fblissjr/fb-claude-skills`)
- README.md usage section updated with correct namespaced skill invocations
- updated CLAUDE.md repo structure and installation sections to match new layout
- replaced docs/claude-docs/ HTML scrapes with clean markdown from live site (3 replaced, 2 new)
- added docs/claude-docs/claude_docs_discover_plugins.md and claude_docs_plugin_marketplaces.md
- updated docs/README.md with claude-docs contents table
- added discover-plugins and plugin-marketplaces to skill-maintainer config.yaml watched pages
- updated docs/analysis/skills_guide_analysis.md with v0.4.0 compliance section
- added skill-maintainer/README.md (was the only module without one)

## 0.3.1

### added
- heylook-monitor: MCP App dashboard for heylookitsanllm local LLM server
  - live monitoring: models, system metrics (RAM/CPU), per-model performance (TPS, latency)
  - quick inference panel for testing prompts against local models
  - 4 tools: show_llm_dashboard, poll_status, quick_inference, list_local_models
  - server-side API proxying (no CSP issues), auto-polling with graceful degradation
  - follows system-monitor-server reference implementation pattern

### changed
- web-tdd: restructured as installable plugin (SKILL.md moved to `skills/web-tdd/SKILL.md`, added plugin.json, metadata fields)
- cogapp-markdown: restructured as installable plugin (SKILL.md moved to `skills/cogapp-markdown/SKILL.md`, added plugin.json, metadata fields)
- all plugin READMEs: standardized with installation commands, skills table, invocation examples
- root README.md: added comprehensive installation guide (clone + install, GitHub install, project-scoped, uninstall, usage)
- CLAUDE.md: added Installation section, updated repo structure to reflect plugin layout, added READMEs convention

## 0.3.0

### added
- mcp-apps: new skill module for building and migrating MCP Apps (interactive UIs for MCP)
  - create-mcp-app skill: guides building MCP Apps from scratch (framework selection, tool+resource registration, theming, streaming, testing)
  - migrate-oai-app skill: step-by-step migration from OpenAI Apps SDK to MCP Apps SDK with API mapping tables and CSP checklist
  - plugin.json: plugin manifest with both skills
  - references/: local copies of upstream docs (overview, patterns, testing, specification, migration guide) for offline use
  - README.md: user-facing documentation
- skill-maintainer: ext-apps source added to config.yaml for upstream change detection
  - monitors 7 upstream files (2 skills, 1 spec, 4 docs)
  - create-mcp-app and migrate-oai-app tracked as managed skills
- docs/internals/: technical documentation for skill-maintainer system
  - api_reference.md: function signatures, parameters, return types for all Python scripts
  - schema.md: formal schemas for state.json and config.yaml
  - troubleshooting.md: common issues, error messages, recovery procedures
- docs/README.md: documentation index linking all doc sections
- CLAUDE.md: added "adding a new skill module" checklist and direct skills-ref validate shortcut

## 0.2.1

### changed
- docs_monitor.py: rewritten as CDC pipeline (detect -> identify -> classify)
  - detect: HEAD request comparing Last-Modified header (zero bandwidth if unchanged)
  - identify: fetch llms-full.txt, split by page, hash each watched page
  - classify: keyword heuristic on diff text
  - removed markdownify dependency (no longer needed)
- config.yaml: sources use llms_full_url + pages instead of individual urls
- state.json: new format with _watermark (per-source) and _pages (per-page) with last_changed tracking
- check_freshness.py, apply_updates.py, update_report.py: updated for new state format

### removed
- .github/workflows/skill-maintenance.yml and validate-skills.yml: local freshness hooks are sufficient; CI adds overhead without value for solo use

## 0.2.0

### added
- skill-maintainer: new skill for automated skill maintenance and monitoring
  - docs_monitor.py: hash-based change detection for Anthropic docs URLs
  - source_monitor.py: git-based upstream code change detection (generalized from mlx-skills)
  - update_report.py: unified change report generation
  - apply_updates.py: update pipeline with report-only, apply-local, and create-pr modes
  - validate_skill.py: extended validation wrapping skills-ref with best practice checks
  - check_freshness.py: lightweight staleness check for hooks integration
  - config.yaml: source registry and skill tracking configuration
  - references/: best practices, monitored sources, update patterns documentation
  - state/: versioned state for content hashes, timestamps, versions
- docs/analysis/: structured reference documentation
  - skills_guide_structured.md: full extraction from Anthropic skills guide PDF
  - skills_guide_analysis.md: gap analysis and actionable findings
  - self_updating_system_design.md: cross-reference of all sources with architecture decisions
- GitHub Actions workflows
  - skill-maintenance.yml: daily cron + manual dispatch for automated monitoring
  - validate-skills.yml: PR validation for skill file changes
- pyproject.toml: uv-based dependency management with skills-ref integration

### fixed
- docs_monitor.py: content extraction now extracts main content div instead of capturing raw JS/CSS from Next.js pages

### changed
- plugin-toolkit/skills/plugin-toolkit/SKILL.md: added metadata.version field
- CLAUDE.md: comprehensive get-up-to-speed guide for the repo (Phase 8)

## 0.1.0

### added
- plugin-toolkit: plugin analysis, polish, and feature management skill
- web-tdd: test-driven development workflow for web applications
- cogapp-markdown: auto-generate markdown sections using cogapp
