---
name: claim-audit
argument-hint: "[what to audit: a diff ref, doc paths, or quoted text] [--fix]"
description: "Audits prose as untrusted claims and re-derives each one by running a command, never by reading and nodding: the added lines of a diff, a standing doc such as a README, AGENTS.md or SKILL.md checked against today's code, or a summary, changelog entry or PR text about to be sent. Checks counts, statuses, capabilities, pointers, attributions and numbers in prose; labels what cannot be derived; with --fix, applies the corrections the evidence settles. Use when the user says 'audit the claims', 'is this README still true', 'check the docs against the code', 'verify this summary', 'check what the changelog says actually happened', or before committing prose that describes work. Do NOT use for auditing a test suite (use test-audit) or for reviewing code changes themselves (use a code review)."
---

# Claim audit

Prose about work drifts from the work, and the drift concentrates in the newest
writing and in docs nobody re-read after the code moved. This skill treats every
claim in the audited prose as untrusted and re-derives it by running a command
whose output is the claim.

<scope>
Audit exactly one of these, chosen from the argument:
- **A diff** (the default, or a ref): the added lines of prose in the pending
  change, plus the commit message or changelog entry being written for it.
- **Standing docs** (paths): a README, AGENTS.md, a SKILL.md, a docs folder,
  checked against the code as it is today. The claims are every sentence that
  says what the project does, contains, or requires.
- **Quoted text**: a summary, PR description or report the user pastes or is
  about to send.

A directory or "the docs" is too vague to audit well. Narrow it to files and
sections first, and say which you chose.
</scope>

<where_it_runs>
Decided by who wrote the prose:
- **This session wrote it**: dispatch the extraction and derivation to one
  fresh-context subagent for the whole set. Brief it with the scoped prose and
  the repo, never with why the prose says what it says. The context that wrote
  a claim reads its evidence generously.
- **Someone else wrote it** (another session, another author, a commit under
  review): run it here.
- **Claims spanning several independent units** (plugins, packages, doc trees)
  and too many for one context: one subagent per unit, in parallel.

Whoever runs it, open two or three returned rows and confirm the pasted output
is what the command prints before accepting the rest.
</where_it_runs>

<claims>
| Class | Shape | Example | Derived by |
|---|---|---|---|
| Count | a number bound to a noun | "18 test arms", "suite at 225" | the command that counts them |
| Status | a state of the repo, a file, a phase | "all green", "not started", "defaults to false" | running it, or reading the value where it is set |
| Capability | what the code does or accepts | "every subcommand takes --json" | invoking it |
| Pointer | a path, command, link or section that must resolve | "see `docs/x.md`", "run `make lint`" | opening or running it |
| Attribution | who or what caused, found or fixed something | "caught by the hook" | the log, commit or record that shows it |
| Measurement | a speed, size, time or rate in prose | "3x faster", "~2,300 tokens" | see `<numbers>` |

Extract by reading, not by regex: a scanner cannot recognise a claim in
arbitrary prose.
</claims>

<procedure>
1. **Extract.** List every claim in scope, one line each, verbatim or nearly.
2. **Name the deriving command before running anything.** A command chosen
   after seeing output drifts toward confirming. If no command can be named,
   that is the finding (step 4).
3. **Run and record both sides.** One row per claim: the sentence, the
   command, its actual output pasted rather than paraphrased, and the verdict
   (holds, wrong, or partly wrong, with what is true instead). Capture exit
   status before filtering output for display: piping a validator through
   `tail` or `grep` masks its verdict.
4. **Label what cannot be derived.** A judgment or design rationale ("we chose
   X because Y") is out of scope by construction; count it and leave it. For
   anything else with no deriving command, recommend one of:
   - past tense with an observation time ("as of the 10:30 run, ...");
   - a source tag: `(memory)`, `(local)`, `(reported)`;
   - deletion.
5. **Run the extra arms when the prose qualifies** (`<arms>`).
</procedure>

<numbers>
Every number in the prose is checked against the three kinds, even when its
value derives correctly:
- **Derivable now** (a file size, a count, a current default): replace the
  value with the command or constant that produces it.
- **Measured once** (a speedup, a wall time): point it at the dated record
  that carries its conditions. A number with no findable origin is deleted if
  the reader's next action doesn't depend on it; otherwise it is marked
  unsupported with the date.
- **Normative** (a limit being set): allowed, cited by the one constant that
  holds it.

First test whether the number is decorative: substitute a plausible different
value. If the reader would act the same, recommend deletion, not a corrected
figure. Order: delete, then point, then derive.
</numbers>

<arms>
- **Adversarial input**, when the prose describes executable behaviour: build
  and run the input that would prove the claim false, instead of reading. Where
  the `postmortem` plugin is installed, `/postmortem:adversarial-verify` is
  this move with a separate check that the input actually reached the code.
- **Control against reimplementation**, when the prose describes something
  that mirrors logic living elsewhere (a validator restating its subject, a
  doc restating a schema): read the two side by side for divergence.
- **Invalidation sweep**, when a decision, merge or version just landed: grep
  the same day's prose for distinctive phrases of the old state, ignoring case
  and with word stems (`delet` finds `Deleting`).

A single-line `grep` over hard-wrapped prose misses phrases that span a line
break. Join lines first (`tr '\n' ' '`) before concluding that something is
stated nowhere, because that verdict is the one this failure silently inverts.
</arms>

<fix>
Without `--fix`, report and change nothing. The caller weighs the findings.

With `--fix`, apply only the corrections the evidence settles:
- replace a wrong count, status, capability or pointer with what the command
  showed;
- apply the `<numbers>` recommendation (delete, point, or mark unsupported);
- repair or remove a pointer that doesn't resolve.

Leave as findings anything that needs judgment: a claim that is partly right,
a rationale, a claim whose command gave an ambiguous result, and anything in a
file the user did not name. Show each applied change as a before and after.
Never commit.
</fix>

<report>
One table row per claim: sentence, class, command, output, verdict, and the
recommended or applied fix. Then the findings left for the caller.

End with the scope line, so a clean report can be told apart from a run that
read nothing:

`scope: 214 lines read, 17 claims, 14 derived, 2 labelled, 1 out of scope, 3 fixed`

If the repo keeps postmortems, session logs or a changelog, cite its own
prose-drift incidents when a finding matches one.
</report>
