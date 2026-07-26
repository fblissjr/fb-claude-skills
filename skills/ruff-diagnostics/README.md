# ruff-diagnostics

last updated: 2026-07-26

Runs Ruff on each `.py`/`.pyi` file Claude edits, and reports the findings back to Claude as context. Read-only: it never writes Ruff config, never syncs your environment, and says nothing when a file is clean.


## Why a hook and not an LSP

Ruff ships a language server (`ruff server`), and Astral's own guidance is to run it *alongside* a type-checking server rather than instead of one:

> the server is intended to be used alongside another Python Language Server in order to support features like navigation and autocompletion

That is how it works in VS Code and Neovim. It cannot work that way in Claude Code, which registers **one language server per file extension**:

> when more than one enabled LSP server declares the same file extension in `extensionToLanguage`, whether the servers come from one plugin or from different plugins, the first server registered handles files with that extension and the others never start

`pyright-lsp` claims `.py` and `.pyi`. A second plugin declaring those extensions loses the race and never starts — silently, decided by registration order. So Ruff cannot ride in as an LSP without displacing Pyright.

This hook reconstructs the intended split from outside the LSP layer: **Pyright owns types and navigation, Ruff owns lint.**

Astral reached the same conclusion independently. Their own Claude Code plugin (`astral-sh/claude-code-plugins`) ships a `ty` language server and deliberately does *not* register Ruff as one.

Note that Astral's plugin claims `.py`/`.pyi` for `ty`, so installing it **will** collide with `pyright-lsp`. One of the two will not start.


## What it does

On every `Edit`/`Write` of a Python file:

1. Walks up to the project root (`pyproject.toml`, `ruff.toml`, `.ruff.toml`, or `.git`).
2. Resolves a Ruff binary without mutating anything (see below).
3. Runs `ruff check` on that one file, honouring whatever config the project already has.
4. Reports findings, marking which are auto-fixable.

It is silent when the file is clean, so a passing edit costs no context.


## Binary resolution

Ordered to prefer the project's pinned Ruff, and to never change your environment:

| Order | Form | When |
|---|---|---|
| 1 | `.venv/bin/ruff` | The project's own Ruff, found by a `stat`. No subprocess at all. |
| 2 | `uv run --no-sync ruff` | Ruff is in the project env but not at that path. Matches what CI runs. |
| 3 | `ruff` | A global install is on `PATH`. |
| 4 | `uvx ruff@latest` | Nothing else available. Output says so — results may not match the project's CI. |
| 5 | *(skip)* | No `uv` and no `ruff`. Silent no-op. |

Rung 1 exists because this fires on every Python edit and rung 2 costs a full
`uv run` environment resolution just to answer a question the filesystem already
answers.

`uv run` **without** `--no-sync` syncs the project environment before running — observed installing 24 packages into a project that merely lacked Ruff. A diagnostic hook must not do that, so every probe uses `--no-sync`.


## The `select` notice

Ruff 0.16 (2026-07-23) raised the default rule set from 59 rules to 413. Critically:

- `select` **replaces** the default set.
- `extend-select` **extends** it.

So a curated `select = [...]` written before 0.16 now enables *fewer* checks than having no Ruff config at all, and does so silently. Measured on this repo's own `readwise-reader`: its seven-group `select` reports the package clean, while Ruff's defaults find seven real issues in it, including four blind-`except` handlers.

When the hook sees a project using `select` without `extend-select`, it says so **once per session per project** — including when the edited file is clean, since a narrow `select` is precisely what makes everything look clean. It never edits your config.


## Requirements

- `jq` on `PATH` (missing `jq` is a silent no-op)
- One of: `uv`, or a global `ruff`

Pairs with `pyright-autoconfig`, which points Pyright at the project's `.venv`. The two do not overlap: measured Pyright/Ruff diagnostic overlap on this repo was zero at line level, and 0.5% even with Pyright forced to strict mode.


## Installation

```bash
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install ruff-diagnostics@fb-claude-skills
```


## Verifying it works

Edit any Python file with a lint issue and watch for the Ruff summary. To exercise the hook directly:

```bash
echo '{"session_id":"test","tool_input":{"file_path":"'"$PWD"'/some_file.py"}}' \
  | bash skills/ruff-diagnostics/hooks/ruff-diagnostics-post-edit-ruff.sh
```

A clean file in a project without a `select` list prints nothing. That is correct.


## Deliberate non-goals

- **No auto-fixing.** It reports `ruff check --fix` as a suggestion; it never runs it. Fixes are edits, and edits are the user's call.
- **No formatting.** Following Astral's own skill guidance: reformatting a project that does not use Ruff's formatter obscures the actual change.
- **No config writes.** Ruff's config lives in tracked files, so there is no untracked place to put settings. Contrast `pyright-autoconfig`, which can drop a git-excluded `pyrightconfig.json`.
- **No rule-set opinion.** It runs bare `ruff check`. Config-less projects get Ruff's defaults; configured projects get their own config.
