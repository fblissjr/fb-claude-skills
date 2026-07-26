---
name: configure
description: >-
  Add, remove, or change this repo's dev conventions -- which package-manager and
  lockfile rules are enforced, and what extra house rules load each session. Use when
  the user says "change the dev conventions here", "add a rule", "disable the pip
  block", "this repo uses npm", "turn off the lockfile guard", "customise dev
  conventions for this project", or "/dev-conventions:configure".
argument-hint: "[show|allow|deny|add|remove] [rule or text]"
arguments:
  - action
  - target
metadata:
  last_verified: "2026-07-26"
---

# Configure dev conventions for this repo

Requested action: `$action` — target: `$target`
(full input: `$ARGUMENTS`)

The plugin ships one set of defaults. Repos differ, so those defaults are
overridable per repo by a single tracked file, `.dev-conventions.json` at the
repo root. It is read by both the PreToolUse enforcement hook and the
SessionStart directive, so a change takes effect on the next tool call and the
next session respectively.

## The file

```json
{
  "enforce": {
    "python-package-manager": true,
    "js-package-manager": true,
    "lockfile-edits": true
  },
  "rules": [
    "Migrations are forward-only; never edit a shipped migration.",
    "Public API changes need a CHANGELOG entry in the same commit."
  ]
}
```

- `enforce.*` — turn an individual block off for this repo. Omitted keys default
  to `true`. This is the honest way to say "this repo really does use npm",
  rather than reaching for `DEV_CONVENTIONS_ALLOW=1`, which disables everything
  everywhere for that one call.
- `rules[]` — extra house rules appended to the SessionStart directive for this
  repo only. Keep them to one line each; this is always-loaded text and every
  line is paid on every session, including after each compaction.

## What to do

**`show`** (or no arguments) — read `.dev-conventions.json` if it exists and
report the effective settings, naming which are defaults and which are
overridden. If the file is absent, say so and show what the defaults are.

**`allow <rule>` / `deny <rule>`** — set `enforce.<rule>` to `false` / `true`.
Valid rules: `python-package-manager`, `js-package-manager`, `lockfile-edits`.
Create the file if needed, preserving any existing keys.

**`add <text>`** — append a one-line rule to `rules[]`. Before writing it, apply
the tier test: if the rule is mechanically checkable, say so and offer a hook
instead, because a blocked action is more reliable than a remembered
instruction. If the model would already do it without being told, say that and
recommend not adding it — the exclude list is "anything inferable from code,
standard conventions, detailed API docs". Add it anyway if the user confirms.

**`remove <text or index>`** — drop a matching entry from `rules[]`.

## Rules for you

- Always show the resulting file after writing it.
- Never add a rule that duplicates something another plugin here already owns:
  lint config belongs to `ruff-diagnostics`, path rules to `path-privacy`,
  Pyright setup to `pyright-autoconfig`.
- The file is tracked on purpose, so the whole repo gets the same conventions.
  Do not add it to `.gitignore`.
