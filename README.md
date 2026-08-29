last updated: 2026-08-17

# fb-claude-skills

> **[Design Principles (VISION.md)](VISION.md)** -- Skills are retrieval. High precision is the constraint, high recall is the goal, and every instruction spends from two budgets: context and friction.

A collection of Claude Code plugins, skills, and MCP Apps. Installable as a plugin marketplace in Claude Code, Cowork, and Claude Desktop.

## what this is, and how to use it

**These exist because I wanted them, and they are personalized to how I work.**
That is stated up front rather than hedged into every skill body: the pinning
policy, where unshared notes live, what counts as evidence for a finding, the
tone -- all of it is one person's house style, arrived at by using it and
measuring what failed.

Some of it is directly useful to anyone. The privacy and pre-share scanners, the
postmortem and audit family, and the plugin-maintenance tooling make no
assumptions about how you work. Take those as they are.

For the rest, the more interesting move is not to install it. **Point your own
harness at this repo and adapt what fits.** Fork it, strip what does not match
how you work, keep the shapes that do, and let your version diverge -- that is
the whole point. A conventions plugin that broadcasts someone else's preferences
into your repo is worth less than the hour you spend writing your own, which is
a lesson this repo learned the expensive way and recorded in
[docs/postmortems/](docs/postmortems/).

## plugins

Grouped by purpose: development conventions & authoring, decomposition & model routing, plugin & skill maintenance, MCP servers & apps, privacy & pre-share safety.

### development conventions & authoring

| Plugin | Type | Description |
|--------|------|-------------|
| [dev-conventions](skills/dev-conventions/) | Skills | On-demand references carrying only what a repo cannot state by being read: the house Python pinning policy and the two mistakes behind most Pydantic/Pyright diagnostic walls; documentation conventions (dates, where unshared notes live, dependency-change records, no decorative counts in prose); and a `uv`/`bun` dependency CVE audit. Hooks and ambient injection were retired in 0.17.0 — conventions belong in each repo's own always-loaded files. |
| [dimensional-modeling](skills/dimensional-modeling/) | Skill | Kimball-style dimensional modeling for DuckDB star schemas. A skill you invoke when designing a schema -- the SessionStart hook was removed, since the principles are needed at a decision point rather than before every session. |
| [writing](skills/writing/) | Skill | Writing skills for clear, accessible prose. `plain-language-us` — an American plain-language house style (plain English, active voice, front-loaded content, sentence case, no bold for emphasis). `voice-match` — write in the user's own voice, learned from the conversation and a saved profile; overrides the house style where they conflict. `show-me` — answer with a compact visual (pseudocode, call tree, component tree, file tree, types-and-signatures, a diff of any of those, mermaid, or one focused HTML page) instead of a paragraph about structure. `wait-what` — user-invoked only: rewrite the last message when it did not land, with more context and the project's own vocabulary. |
| [claim-audit](skills/claim-audit/) | Skill | Audit the added prose of a diff as untrusted claims — every count, status, and attribution re-derived by executing a command whose output is that claim, never by reading. Unsourceable claims get labeled (`(memory)`, `(local)`, `(reported)`) or recommended for deletion; the report states its own scope (lines read, claims extracted, claims derived) so a green result is distinguishable from a run that read nothing. Report, don't rewrite — the caller weighs the findings. |
| [postmortem](skills/postmortem/) | Skills | Evidence-grounded retrospectives. `postmortem` — verdicted look-back at a session, feature, or span (git history, session logs, changelogs); every finding cites an artifact, empty sections are valid, annotate-don't-rewrite. Filed as standalone dated files in a per-repo resolved location, optionally rendered to a self-contained HTML file. `postmortem-index` — a generated browsable page over them, answering "has anything been written about this file". `test-audit` — does each green test still mean anything: claim recovery, spot-mutation oracle checks, reachability-envelope mapping, keep/rewrite/delete verdicts. `adversarial-verify` — the single-claim primitive the audits dispatch to: construct the refutation via the bundled `control-builder` agent, then separately verify the attempt reached the subject. `control-audit` — census of everything check-shaped outside the test suite (hooks, validators, reminders; four slots per control, derived vs transcribed) with mandatory live-fire of controls nothing watches. |
| [json-query](skills/json-query/) | Skill | JSON query tool selection and syntax -- jg (jsongrep) for extraction, jq for transformation |
| [pyright-autoconfig](skills/pyright-autoconfig/) | Hook | Points pyright at the project's uv venv automatically, self-heals once `.venv` appears, and retracts its config when the project declares its own `[tool.pyright]` |
| [ruff-diagnostics](skills/ruff-diagnostics/) | Hook | Runs Ruff on each edited Python file and reports findings. A hook rather than an LSP because Claude Code starts only one language server per file extension, so `ruff server` cannot run alongside pyright. Silent on clean files. |

### decomposition & model routing

| Plugin | Type | Description |
|--------|------|-------------|
| [mece-decomposer](apps/mece-decomposer/) | Hook + Skills + MCP App | MECE decomposition of goals and workflows into Agent SDK-ready components, with interactive tree visualizer. Hook detects Agent SDK imports. |
| [model-routing](skills/model-routing/) | Skill | Opt a project into down-tier model delegation: installs a standalone `.claude/rules/model-delegation.md` telling Claude to route well-specified data/coding tasks to a cheaper model in a subagent, keeping judgment-heavy work in the main loop. Optional pre-shaped `fast-executor` / `task-coder` agents. **Installation is paused (2026-08-01)** — the rule asserts a cost/quality tradeoff nothing has measured, so it was removed everywhere and the skill is now user-invoked only. Removal still works. See [model_routing_flywheel.md](docs/internals/model_routing_flywheel.md). |
| [advisor](skills/advisor/) | Skill + hooks | Consult a higher-tier advisor model about the current session, emulating the Claude API's advisor tool inside Claude Code. Reconstructs the session transcript into a bounded digest so a stronger model can see what was actually done. Strictly user-invoked: only a typed `/advisor` mints the spend authorization, and hooks deny any spawn without it. Mirror image of `model-routing`. |
| [grilling](skills/grilling/) | Skill | A design interview that works the problem as a tree instead of asking questions in the order they occur. Each round asks every question whose prerequisites are already settled, with a recommended answer attached; facts the codebase can settle are looked up, never asked; the session ends when nothing is left unasked. |

### plugin & skill maintenance

| Plugin | Type | Description |
|--------|------|-------------|
| [plugin-toolkit](skills/plugin-toolkit/) | Skills + Agents | Analyze, polish, and manage Claude Code plugins |
| [skill-maintainer](skills/skill-maintainer/) | Skills + Hooks + Agent | Maintenance tools for skill repos: quality, freshness, upstream detection (per-page snapshots + line/char deltas), best practices review, wiki-sanity `lint` (orphans, count drift, link-rot), tracked pre-commit hook scaffolding, `finish-session` workflow, `session-log-drafter` agent, PostToolUse bundled-ref sync, Stop-event session-log nudge |
| [skill-dashboard](apps/skill-dashboard/) | MCP App | Interactive quality dashboard: checks, token budgets, freshness, version alignment |

### MCP servers & apps

| Plugin | Type | Description |
|--------|------|-------------|
| [readwise-reader](apps/readwise-reader/) | MCP Server | Search, save, and surface your Readwise Reader library via MCP with OAuth, DuckDB, and full-text search |

### cross-model bridges

| Plugin | Type | Description |
|--------|------|-------------|
| [gemini-bridge](apps/gemini-bridge/) | CLI + Skill + Command | Hand a perceptual task to a Gemini model when Claude cannot do it directly — comparing two renders and reporting what a person would notice, rather than falling back to pixel statistics. Recipes are data (frontmatter plus a system instruction), every call writes an auditable run directory, and the API surface was established by live probing rather than documentation. Secret-manager agnostic. |

### provider integrations

| Plugin | Type | Description |
|--------|------|-------------|
| [heylook-provider](skills/heylook-provider/) | Skill + Script | Wire an application to [heylook](https://github.com/fblissjr/heylookitsanllm), a local multimodal server on Apple Silicon serving MLX and gguf. It exposes an Anthropic Messages-conformant `/v1/messages` beside an OpenAI-compatible `/v1/chat/completions`, so an SDK habit mostly transfers — what does not is everything following from the server being local and single-user: model ids are install-local so discovery is a constraint rather than a nicety, capabilities vary per model, the client resizes images because that wire has no resize params, an absent sampler field means the server cascade decides, and a busy server answers 503 with `Retry-After` as a queue rather than a quota. A stdlib `probe.py` resolves the roster and exits non-zero when a required capability is unserved. Knowledge only; it calls nothing on your behalf. |

### privacy & pre-share safety

| Plugin | Type | Description |
|--------|------|-------------|
| [scan-for-secrets](skills/scan-for-secrets/) | Skill + Scripts | Pre-share scanner built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets): literal pass + ripgrep regex pass for leaked secrets and privacy-sensitive paths (your `$HOME`/`$USER`, SSH keys, other users' home paths, emails, IPv4, common API-token shapes). <!-- path-privacy: ignore --> |
| [path-privacy](skills/path-privacy/) | Hook + Skill + Scripts | Enforces a single rule across every artifact: every path written into the repo must be relative to the repo root. SessionStart directive plus pre-commit and commit-msg git hooks that hard-block commits whose staged files, message, or branch name reference anything outside the repo. |
| [dangling-refs](skills/dangling-refs/) | Skill | Remove a unit without leaving references behind. Sweeps tracked content *before* the delete and sorts every hit into what must change, what must stay as history, and what reaches users. Exists because deletion-induced breakage is non-local — the files that break are ones nobody edited, so no language server, hook, or diff check ever fires. |

### project-scoped

| Module | Description |
|--------|-------------|

### installable as a package (not a Claude plugin)

| Module | Description |
|--------|-------------|
| [skill-maintainer](tools/skill-maintainer/) | `skill-maintain` CLI for validating, monitoring, and maintaining skill repos. Git-installable into any repo. |

## installation

### from GitHub (recommended)

```bash
# Add the marketplace (once)
/plugin marketplace add fblissjr/fb-claude-skills

# Install individual plugins
/plugin install mece-decomposer@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
/plugin install dev-conventions@fb-claude-skills
/plugin install skill-maintainer@fb-claude-skills
/plugin install readwise-reader@fb-claude-skills
/plugin install json-query@fb-claude-skills
/plugin install pyright-autoconfig@fb-claude-skills
/plugin install ruff-diagnostics@fb-claude-skills
/plugin install skill-dashboard@fb-claude-skills
/plugin install scan-for-secrets@fb-claude-skills
/plugin install path-privacy@fb-claude-skills
/plugin install writing@fb-claude-skills
/plugin install model-routing@fb-claude-skills
/plugin install advisor@fb-claude-skills
/plugin install claim-audit@fb-claude-skills
/plugin install postmortem@fb-claude-skills
/plugin install gemini-bridge@fb-claude-skills
/plugin install dangling-refs@fb-claude-skills
/plugin install grilling@fb-claude-skills
/plugin install heylook-provider@fb-claude-skills
```

Or from the terminal:

```bash
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mece-decomposer@fb-claude-skills
```

### from local clone

```bash
git clone https://github.com/fblissjr/fb-claude-skills.git
cd fb-claude-skills
/plugin marketplace add .
/plugin install mece-decomposer@fb-claude-skills
```

### temporary loading (development)

```bash
claude --plugin-dir ./apps/mece-decomposer
```

### uninstall

```bash
claude plugin uninstall mece-decomposer@fb-claude-skills
claude plugin list  # verify
```

### updating

Installed plugins auto-update at Claude Code startup when a newer version is published to the marketplace. To pull updates immediately, without waiting for a restart:

```bash
# refresh the marketplace catalog from GitHub
claude plugin marketplace update fb-claude-skills

# update a plugin to its latest version (repeat per plugin)
claude plugin update dev-conventions@fb-claude-skills
```

`claude plugin list` shows installed plugins and versions. To sweep every plugin from this marketplace at once, loop `claude plugin update` over its `@fb-claude-skills` entries. On a multi-machine setup, wrap the marketplace-update + per-plugin-update in a small script and run it after each push to keep every machine current.

## where things work

Plugins from this repo work across multiple Claude surfaces, but capabilities differ by surface:

| Surface | Skills (slash commands) | MCP App UI | Transport |
|---------|------------------------|------------|-----------|
| **Claude Code** (terminal) | yes (namespaced) | text fallback | stdio |
| **Claude Desktop** | yes | text fallback | stdio |
| **Cowork** (in Claude Desktop) | yes | yes (interactive) | stdio |
| **Claude.ai** (web) | -- | yes (if hosted) | Streamable HTTP |

**Key points:**
- **Skills** (including user-invocable slash commands) work in Claude Code, Claude Desktop, and Cowork via stdio transport. This is what `.mcp.json` configures with `--stdio`.
- **MCP App interactive UIs** (like the MECE tree visualizer) render in Cowork and Claude.ai. On CLI/Desktop surfaces, the tools return text summaries instead.
- **Claude.ai requires HTTP transport.** The web interface can't spawn local processes, so it needs a hosted server using Streamable HTTP (not stdio). See [Claude.ai deployment](#deploying-mcp-apps-to-claudeai) below.

## usage

### slash commands

Once installed, invoke as namespaced slash commands:

```
/mece-decomposer:decompose    # Break down a goal into MECE components
/mece-decomposer:interview    # Extract process knowledge from an SME
/mece-decomposer:validate     # Check MECE compliance and scores
/mece-decomposer:export       # Generate Agent SDK Python scaffolding


/plugin-toolkit                # Analyze and manage plugins
/dimensional-modeling          # Star schema design patterns

/dev-conventions:python-tooling  # Pinning policy, Pydantic/Pyright diagnostic traps
/dev-conventions:doc-conventions # Dates, where notes live, no decorative counts in prose
/dev-conventions:dep-audit       # Dependency CVE audit across uv and bun

/json-query                      # JSON query tool selection + jg syntax
/scan-for-secrets:scan-for-secrets  # Pre-share scan: literal secrets + regex privacy patterns
/writing:plain-language-us       # Write or rewrite prose in an American plain-language style
/writing:voice-match             # Write in your own voice, learned from the thread and a saved profile
/writing:show-me                 # Answer with a compact visual instead of a paragraph about structure
/writing:wait-what               # Rewrite the last message when it did not land (user-invoked only)
/grilling:grilling               # Design interview in rounds over a tree; facts looked up, not asked
/model-routing:model-routing     # Per-project down-tier delegation rule (install paused; removal works)
/advisor                         # Consult a higher-tier model about this session (user-invoked only)
/claim-audit:claim-audit         # Audit added prose as claims, each re-derived by execution

/postmortem:postmortem           # Evidence-grounded retrospective of a session, feature, or span
/postmortem:postmortem-index     # Browsable HTML index over a repo's postmortems
/postmortem:test-audit           # Audit the test suite: claims, oracles, envelope, verdicts
/postmortem:adversarial-verify   # Refute one claim by construction; verify the needle threaded
/postmortem:control-audit        # Census + live-fire audit of hooks, validators, reminders
/gemini                          # Hand a perceptual task to Gemini; answer lands in a run directory
/heylook-provider:heylook-provider  # Wire an app to heylook: the wire contract and capability discovery
/dangling-refs:retire            # Remove a unit without leaving references behind


/skill-maintainer:quality              # Quick quality check for all skills
/skill-maintainer:quality path-privacy   # Check a specific skill
/skill-maintainer:maintain             # Full maintenance pass
/skill-maintainer:init-maintenance     # Set up maintenance in a new repo
/skill-maintainer:sync-versions path-privacy 0.7.4  # Bump version across all sources
/skill-maintainer:finish-session       # Orchestrate end-of-session: log -> sync -> bumps -> quality
```

### keyword activation

Skills also trigger automatically on relevant keywords. Say "decompose this process" or "interview me about this workflow" and the mece-decomposer skill loads.

Two exceptions: `advisor` and `model-routing` set `disable-model-invocation: true`, so their descriptions never enter Claude's context and only an explicit slash command reaches them. For `advisor` that is the point — a typed `/advisor` is what authorizes the spend.

### MCP App tools

Plugins with MCP Apps expose tools that the model calls automatically during conversations:

| MCP Tool | Plugin | What it does |
|----------|--------|-------------|
| `mece-decompose` | mece-decomposer | Render decomposition as interactive tree |
| `mece-validate` | mece-decomposer | Validate and display score gauges + issues |
| `mece-refine-node` | mece-decomposer | Edit nodes from the UI (app-only) |
| `mece-export-sdk` | mece-decomposer | Preview generated Agent SDK code |
| `skill-quality-check` | skill-dashboard | Quality checks, token budgets, freshness, version alignment |
| `skill-measure` | skill-dashboard | Per-file token breakdown for a single skill |
| `skill-verify` | skill-dashboard | Mark a skill as verified (app-only, updates SKILL.md on disk) |

On Cowork, these render as interactive React UIs. On CLI, they return text.

## MCP Apps

### what are MCP Apps?

MCP Apps are interactive UIs served by MCP servers. They pair a tool (server logic) with a resource (bundled HTML/React) so that when the model calls the tool, a rich UI renders in the host.

The mece-decomposer plugin includes an MCP App that visualizes decomposition trees with collapsible nodes, score gauges, validation panels, and code export preview.

### how they work

1. Model calls an MCP tool (e.g., `mece-decompose`)
2. Server processes the request, returns text (fallback) + structured data (for UI)
3. Host fetches the UI resource (`ui://mece/mcp-app.html`)
4. Host renders the HTML in a sandboxed iframe
5. Host sends tool data to the iframe via MCP messaging
6. UI renders interactively -- user can click nodes, run validation, export code

### deploying MCP Apps to Claude.ai

The plugins in this repo use stdio transport (local process). To use MCP Apps on Claude.ai (web):

1. Run the server as an HTTP service (not stdio):
   ```bash
   cd apps/mece-decomposer/mcp-app
   bun install
   node dist/index.cjs  # starts Streamable HTTP on port 3001
   ```
2. Host the server somewhere network-accessible
3. Register as an MCP connector in Claude.ai settings

The server's `main.ts` supports both transports: `--stdio` for local, HTTP for remote.

## skill-maintainer

Two interfaces: a **plugin** for interactive use in Claude Code, and a **CLI package** for CI/headless automation.

**Plugin** (recommended): install via the marketplace (see above), then use `/skill-maintainer:quality`, `/skill-maintainer:maintain`, `/skill-maintainer:init-maintenance`, `/skill-maintainer:sync-versions`. Skills accept `$ARGUMENTS` for targeting specific skills or directories.

**CLI**: available after `uv sync --all-packages` in this repo, or git-installable into other repos:

```bash
uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer
uv run skill-maintain init     # writes .skill-maintainer/config.json + installs the bundled pre-commit hook
```

`skill-maintain init` is idempotent — re-running on a repo that already has the hook prints `already up to date`. Pass `--force-hook` to replace an existing hook (the prior is preserved as `.git/hooks/pre-commit.local`).

Common CLI commands:

```bash
uv run skill-maintain test              # red/green test suite
uv run skill-maintain quality           # validation + budget + freshness report
uv run skill-maintain upstream          # check Claude Code docs for changes
uv run skill-maintain sources           # pull tracked repos, detect changes
uv run skill-maintain lint              # wiki sanity: orphans, count drift, broken links
uv run skill-maintain log --tail 5      # query audit log
```

The `/skill-maintainer:maintain` skill orchestrates the full pipeline: `sources -> upstream -> quality -> review`. See [skill-maintainer CLI README](tools/skill-maintainer/README.md) for the full CLI reference and data flow diagram.

## documentation

See [docs/README.md](docs/README.md) for the full documentation index.

Highlights:
- [docs/internals/](docs/internals/) -- repo-specific operating reference (version cascade, plugin patterns, maintenance commands, gotchas)
- Upstream Claude Code docs are **not** vendored here — `skill-maintain upstream` fetches them to `.skill-maintainer/state/pages/` (gitignored)
- Each plugin has its own README with detailed usage

## credits

- Original idea for MECE decomposer by [Ron Zika](https://www.linkedin.com/in/ronzika/)
- scan-for-secrets built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (Apache 2.0) — all literal-matching and escape-variant logic is his work
- More skills: [mlx-skills](https://github.com/fblissjr/mlx-skills) (Apple MLX)
- env-forge (removed 2026-07-26; in git history) built on the synthesis methodology and dataset from [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) by Snowflake Labs
