"""Always-on context proxy per plugin, and the ratchet that holds it down.

THIS IS NOT A COST REPORT. `claude plugin details <name>` is the authoritative
per-plugin always-on count, and AGENTS.md invariant 1c says to measure with it
rather than build a duplicate. It cannot gate a commit, though: it reads the
INSTALLED copy rather than the working tree, cannot see a plugin that is not
installed, has no JSON output, and counts hooks as zero. This module answers a
narrower question it can answer deterministically from the working tree: did
any plugin's always-loaded surface GROW since the baseline was last written?

Five metrics per plugin in `.claude-plugin/marketplace.json`:

- `listing_chars`: the authored text the skill listing carries on every turn.
  len(description) + len(when_to_use) for each skill in `skills/*/SKILL.md`
  (or a plugin-root `SKILL.md` when there is no `skills/` dir) and each command
  in `commands/**/*.md`, skipping any with `disable-model-invocation: true`,
  plus len(description) of every agent under `agents/` (loaded recursively).
  Characters, not tokens, and measured before the listing's per-entry cap and
  budget truncation are applied -- a proxy that moves when the real cost moves.
- `emitting_hooks`: handlers on the events whose plain stdout or
  `additionalContext` enters context (EMITTING_EVENTS). A handler that is
  silent in practice still counts: the ratchet guards the CAPABILITY to emit,
  because whether it speaks is a runtime property a file read cannot see.
- `always_monitors`: monitors that start every session (`when` absent or
  "always"); each stdout line of one reaches Claude as a notification.
- `mcp_servers`: distinct server names the plugin declares, from `.mcp.json`
  and plugin.json `mcpServers` (path, list, or inline object). A plugin server
  starts with the plugin, and under tool search its tool names and its
  instructions load every session. The instructions themselves are NOT
  measured: the server returns them in its `initialize` response at runtime,
  so no file in the tree holds them and a character count would be invented.
  The server count is the static handle on that cost.
- `per_call_emitters`: handlers on PER_CALL_EVENTS, whose `additionalContext`
  enters context beside a tool result. Same capability stance as
  `emitting_hooks`, kept separate because its cost scales with tool calls, not
  sessions, and summing the two would hide which one grew.

The baseline (BASELINE_PATH, tracked) holds a ceiling per plugin per metric.
`skill-maintain test` fails when a metric exceeds its ceiling, and when a
plugin's entry has no ceiling for a metric (a baseline written before the
metric existed) -- the same stance as a plugin missing from the baseline.
`skill-maintain ratchet --write` resets every ceiling to the current value,
which is how a trim is locked in, how a deliberate raise is made, and how a
new metric is first recorded -- each shows up as a diff to the baseline.
"""

import sys
from pathlib import Path

import orjson
from skills_ref.parser import find_skill_md, parse_frontmatter

from skill_maintainer.shared import _skipped

BASELINE_PATH = Path(".skill-maintainer") / "always_on_baseline.json"
"""Tracked on purpose: `.skill-maintainer/state/` is the gitignored part."""

METRICS = ("listing_chars", "emitting_hooks", "always_monitors", "mcp_servers", "per_call_emitters")

EMITTING_EVENTS = frozenset({
    "SessionStart", "UserPromptSubmit", "UserPromptExpansion", "PostModelSwitch",
})
"""Upstream hooks reference, exit-code-0 section: for these four events Claude
Code adds plain-text stdout to context; for the rest stdout goes to the debug
log. `additionalContext` on the tool events fires per tool call, not per
session; those handlers are PER_CALL_EVENTS, counted apart."""

PER_CALL_EVENTS = frozenset({"PostToolUse", "PostToolUseFailure", "PostToolBatch"})
"""Upstream hooks reference, decision-control sections: each of these can return
`additionalContext`, which Claude Code places next to the tool result. It fires
on every matching tool call (PostToolBatch once per batch, with no matcher)."""

_MANIFEST_COMPONENT_PATHS = ("skills", "commands", "agents")
"""Manifest fields that move where components load from. Not resolved here."""


class MeasureError(Exception):
    """The working tree could not be measured; the ratchet must fail, not pass."""


def _read_json(path: Path, what: str):
    try:
        return orjson.loads(path.read_bytes())
    except (OSError, orjson.JSONDecodeError) as e:
        raise MeasureError(f"unreadable {what} {path}: {e}") from e


def marketplace_plugins(root: Path) -> dict[str, Path]:
    """Plugin name -> directory, for every local source in marketplace.json.

    An object source (github, git, url) has no working-tree copy to measure and
    is left out. A string source that escapes the repo root is an error.
    """
    mp = root / ".claude-plugin" / "marketplace.json"
    data = _read_json(mp, "marketplace")
    entries = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise MeasureError(f"{mp} has no `plugins` list")
    out: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise MeasureError(f"malformed marketplace entry: {entry!r}")
        name = entry["name"]
        source = entry.get("source") or f"./{name}"
        if not isinstance(source, str):
            continue
        d = root / source.removeprefix("./")
        try:
            d.resolve().relative_to(root.resolve())
        except (ValueError, OSError) as e:
            raise MeasureError(f"{name}: source escapes the repo root: {source!r}") from e
        out[name] = d
    return out


def _frontmatter(path: Path) -> tuple[dict, str]:
    """(metadata, body). A file with no frontmatter is all body, as for a bare command."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise MeasureError(f"unreadable {path}: {e}") from e
    if not text.startswith("---"):
        return {}, text
    try:
        return parse_frontmatter(text)
    except Exception as e:
        raise MeasureError(f"unparseable frontmatter in {path}: {e}") from e


def _entry_chars(path: Path, *, with_when_to_use: bool) -> int:
    """Listing characters one skill, command or agent contributes."""
    meta, body = _frontmatter(path)
    # strictyaml returns scalars as strings, so `true` arrives as "true" and a
    # truthiness test would also exclude an explicit "false".
    if with_when_to_use and str(meta.get("disable-model-invocation", "")).strip().lower() == "true":
        return 0
    desc = meta.get("description")
    if desc is None:
        # Upstream: a skill with no description lists its first non-empty line.
        desc = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    n = len(str(desc))
    if with_when_to_use:
        n += len(str(meta.get("when_to_use", "")))
    return n


def _md_files(d: Path, plugin_dir: Path) -> list[Path]:
    if not d.is_dir():
        return []
    return [p for p in sorted(d.rglob("*.md")) if p.is_file() and not _skipped(p, plugin_dir)]


def _listing_chars(plugin_dir: Path) -> int:
    total = 0
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        # One level, as Claude Code loads them: `skills/<name>/SKILL.md`. Not
        # `discover_skills`, whose whole-tree rglob would also count SKILL.md
        # fixtures under tests/ that no install ever lists.
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            md = find_skill_md(d)
            if md is not None:
                total += _entry_chars(md, with_when_to_use=True)
    else:
        md = find_skill_md(plugin_dir)
        if md is not None:
            total += _entry_chars(md, with_when_to_use=True)
    for md in _md_files(plugin_dir / "commands", plugin_dir):
        total += _entry_chars(md, with_when_to_use=True)
    for md in _md_files(plugin_dir / "agents", plugin_dir):
        total += _entry_chars(md, with_when_to_use=False)
    return total


def _config_sources(plugin_dir: Path, manifest: dict, field: str, default: Path) -> list[dict]:
    """Every config for a component with its own merge rule: the default file plus
    the manifest field, which may be a path, an inline object, or a list of either.

    Used for `hooks` and `mcpServers`, whose manifest field has the same
    string|array|object shape. A path named twice (the default among them) is
    read once.
    """
    paths: list[Path] = []
    configs: list[dict] = []
    if default.is_file():
        paths.append(default)
    declared = manifest.get(field)
    for item in (declared if isinstance(declared, list) else [declared] if declared else []):
        if isinstance(item, str):
            p = plugin_dir / item.removeprefix("./")
            if not p.is_file():
                raise MeasureError(f"{plugin_dir.name}: manifest {field} path missing: {item}")
            if p.resolve() not in {q.resolve() for q in paths}:
                paths.append(p)
        elif isinstance(item, dict):
            configs.append(item)
        else:
            raise MeasureError(f"{plugin_dir.name}: unsupported manifest {field} entry: {item!r}")
    for p in paths:
        data = _read_json(p, f"{field} config")
        if not isinstance(data, dict):
            raise MeasureError(f"{p} is not a JSON object")
        configs.append(data)
    return configs


def _hook_handlers(plugin_dir: Path, manifest: dict, counted: frozenset[str]) -> int:
    """Handlers registered on any event in `counted`, across every hooks config."""
    count = 0
    configs = _config_sources(plugin_dir, manifest, "hooks", plugin_dir / "hooks" / "hooks.json")
    for config in configs:
        events = config.get("hooks", config)
        if not isinstance(events, dict):
            raise MeasureError(f"{plugin_dir.name}: hooks config `hooks` is not an object")
        for event, groups in events.items():
            if event not in counted:
                continue
            if not isinstance(groups, list):
                raise MeasureError(f"{plugin_dir.name}: {event} is not a list of matcher groups")
            for group in groups:
                handlers = group.get("hooks") if isinstance(group, dict) else None
                if not isinstance(handlers, list):
                    raise MeasureError(f"{plugin_dir.name}: {event} group has no `hooks` list")
                count += len(handlers)
    return count


def _mcp_servers(plugin_dir: Path, manifest: dict) -> int:
    """Distinct server names across `.mcp.json` and manifest `mcpServers`.

    Each config is `{"mcpServers": {...}}` or a bare server map, as `.mcp.json`
    files are written both ways. The reference page says only that MCP servers
    have their own merge rule, not what it is, so this counts the union by
    name: a server declared in two places counts once, and if the manifest in
    fact replaced `.mcp.json` the count errs high, never low. A `$`-prefixed key
    (`$schema`) names no server; any other non-object entry is an error rather
    than a silent zero.
    """
    names: set[str] = set()
    for config in _config_sources(plugin_dir, manifest, "mcpServers", plugin_dir / ".mcp.json"):
        servers = config.get("mcpServers", config)
        if not isinstance(servers, dict):
            raise MeasureError(f"{plugin_dir.name}: MCP config `mcpServers` is not an object")
        for name, spec in servers.items():
            if name.startswith("$"):
                continue
            if not isinstance(spec, dict):
                raise MeasureError(f"{plugin_dir.name}: MCP server '{name}' is not an object")
            names.add(name)
    return len(names)


def _always_monitors(plugin_dir: Path, manifest: dict) -> int:
    experimental = manifest.get("experimental")
    declared = experimental.get("monitors") if isinstance(experimental, dict) else None
    if declared is None:
        declared = manifest.get("monitors")  # top-level form: deprecated, still loads
    if declared is None:
        default = plugin_dir / "monitors" / "monitors.json"
        entries = _read_json(default, "monitors config") if default.is_file() else []
    elif isinstance(declared, str):
        entries = _read_json(plugin_dir / declared.removeprefix("./"), "monitors config")
    else:
        entries = declared
    if not isinstance(entries, list):
        raise MeasureError(f"{plugin_dir.name}: monitors config is not a JSON array")
    return sum(
        1 for m in entries
        if isinstance(m, dict) and m.get("when", "always") == "always"
    )


def measure_plugin(plugin_dir: Path) -> dict[str, int]:
    manifest = _read_json(plugin_dir / ".claude-plugin" / "plugin.json", "plugin.json")
    if not isinstance(manifest, dict):
        raise MeasureError(f"{plugin_dir.name}: plugin.json is not an object")
    moved = [f for f in _MANIFEST_COMPONENT_PATHS if f in manifest]
    if moved:
        # Refuse rather than undercount: a path that replaces the default dir
        # would otherwise read as a trim to zero.
        raise MeasureError(
            f"{plugin_dir.name}: plugin.json declares {', '.join(moved)} paths, which "
            "always_on does not resolve -- extend it before trusting the ratchet here"
        )
    return {
        "listing_chars": _listing_chars(plugin_dir),
        "emitting_hooks": _hook_handlers(plugin_dir, manifest, EMITTING_EVENTS),
        "always_monitors": _always_monitors(plugin_dir, manifest),
        "mcp_servers": _mcp_servers(plugin_dir, manifest),
        "per_call_emitters": _hook_handlers(plugin_dir, manifest, PER_CALL_EVENTS),
    }


def measure(root: Path) -> dict[str, dict[str, int]]:
    """Per-plugin always-on proxy for every local plugin in marketplace.json.

    Raises MeasureError on anything it cannot read; a caller must fail on it.
    """
    root = Path(root)
    return {name: measure_plugin(d) for name, d in sorted(marketplace_plugins(root).items())}


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def load_baseline(root: Path) -> dict[str, dict[str, int]]:
    """The tracked ceilings. Missing, unparseable or mis-shaped is a MeasureError.

    An absent metric key is not mis-shaped: it is a baseline older than the
    metric, and `findings` reports it against the plugin. A key that is present
    but not an integer is corruption and fails the whole file.
    """
    path = Path(root) / BASELINE_PATH
    if not path.is_file():
        raise MeasureError(
            f"no baseline at {BASELINE_PATH} -- create it with `skill-maintain ratchet --write`"
        )
    data = _read_json(path, "baseline")
    if not isinstance(data, dict):
        raise MeasureError(f"{BASELINE_PATH} is not a JSON object")
    for plugin, row in data.items():
        if not isinstance(row, dict) or any(m in row and not _is_int(row[m]) for m in METRICS):
            raise MeasureError(
                f"{BASELINE_PATH}: entry for '{plugin}' needs integer {', '.join(METRICS)}"
            )
    return data


def write_baseline(root: Path, current: dict[str, dict[str, int]]) -> None:
    path = Path(root) / BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = {p: {m: current[p][m] for m in METRICS} for p in current}
    path.write_bytes(orjson.dumps(rows, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n")


def findings(current: dict, baseline: dict) -> list[tuple[str, str]]:
    """(plugin, message) for every way the tree breaks the ratchet. Empty is green."""
    out: list[tuple[str, str]] = []
    for plugin in sorted(current):
        if plugin not in baseline:
            out.append((plugin, (
                f"not in {BASELINE_PATH}: a new plugin's always-on cost is a decision "
                "-- record it with `skill-maintain ratchet --write`"
            )))
            continue
        missing = [m for m in METRICS if m not in baseline[plugin]]
        if missing:
            out.append((plugin, (
                f"no ceiling for {', '.join(missing)} in {BASELINE_PATH}: the entry predates "
                "the metric -- record it with `skill-maintain ratchet --write`"
            )))
        for m in METRICS:
            if m in missing:
                continue
            cur, ceil = current[plugin][m], baseline[plugin][m]
            if cur > ceil:
                out.append((plugin, (
                    f"{m} {cur:,} > ceiling {ceil:,} -- trim it, or raise the ceiling "
                    f"deliberately with `skill-maintain ratchet --write` and commit {BASELINE_PATH}"
                )))
    for plugin in sorted(set(baseline) - set(current)):
        out.append((plugin, (
            f"{BASELINE_PATH} names '{plugin}', which is not in marketplace.json "
            "-- drop it with `skill-maintain ratchet --write`"
        )))
    return out


def scope_line(current: dict, baseline: dict) -> str:
    """The one green line. Called only when `findings` is empty, so every ceiling exists."""
    def pair(m: str) -> str:
        total = sum(r[m] for r in current.values())
        ceiling = sum(baseline[p][m] for p in current if p in baseline)
        return f"{total:,}/{ceiling:,}"

    roomy = sum(
        1 for p in current
        if p in baseline and any(current[p][m] < baseline[p][m] for m in METRICS)
    )
    return (
        f"{len(current)} plugins measured; listing {pair('listing_chars')} chars; "
        f"mcp servers {pair('mcp_servers')}; per-call hooks {pair('per_call_emitters')}; "
        f"{roomy} with headroom -- tighten with `skill-maintain ratchet --write`"
    )


def _table(current: dict, baseline: dict) -> str:
    short = {
        "listing_chars": "listing", "emitting_hooks": "hooks", "always_monitors": "monitors",
        "mcp_servers": "mcp", "per_call_emitters": "percall",
    }
    header = ["plugin"]
    for m in METRICS:
        header += [short[m], "ceil", "room"]
    rows = [header]

    def cells(cur: dict, base: dict | None) -> list[str]:
        out = []
        for m in METRICS:
            c = cur[m]
            ceil = None if base is None else base.get(m)
            if ceil is None:
                out += [f"{c:,}", "-", "-"]
            else:
                out += [f"{c:,}", f"{ceil:,}", f"{ceil - c:+,}" if ceil != c else "0"]
        return out

    for plugin in sorted(current):
        rows.append([plugin] + cells(current[plugin], baseline.get(plugin)))
    total = {m: sum(r[m] for r in current.values()) for m in METRICS}
    # A metric no in-scope entry records has no total ceiling: `-`, not a false 0.
    total_base = {
        m: sum(baseline[p][m] for p in current if m in baseline.get(p, {}))
        if any(m in baseline.get(p, {}) for p in current) else None
        for m in METRICS
    }
    rows.append(["TOTAL"] + cells(total, total_base if baseline else None))
    widths = [max(len(r[i]) for r in rows) for i in range(len(header))]
    lines = []
    for r in rows:
        lines.append("  ".join(
            r[i].ljust(widths[i]) if i == 0 else r[i].rjust(widths[i]) for i in range(len(r))
        ))
    return "\n".join(lines)


def _changes(old: dict, new: dict) -> list[str]:
    out = []
    for plugin in sorted(set(old) | set(new)):
        if plugin not in old:
            out.append(f"{plugin}: added ({', '.join(f'{m} {new[plugin][m]:,}' for m in METRICS)})")
        elif plugin not in new:
            out.append(f"{plugin}: removed")
        else:
            for m in METRICS:
                a, b = old[plugin].get(m), new[plugin][m]
                if a is None:
                    out.append(f"{plugin}.{m}: recorded {b:,}")
                elif a != b:
                    verb = "tightened" if isinstance(a, int) and b < a else "raised"
                    out.append(f"{plugin}.{m}: {a} -> {b} ({verb})")
    return out


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="skill-maintain ratchet",
        description="Per-plugin always-on proxy against the tracked baseline. "
                    "Not a cost report: `claude plugin details <name>` is.",
    )
    parser.add_argument("--dir", type=Path, default=Path("."), help="Repo root (default: .)")
    parser.add_argument("--write", action="store_true",
                        help="Reset every ceiling to the current value and print what changed")
    parsed = parser.parse_args(args)
    root = parsed.dir

    try:
        current = measure(root)
    except MeasureError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if parsed.write:
        try:
            old = load_baseline(root)
        except MeasureError as e:
            print(f"replacing unreadable or missing baseline ({e})")
            old = {}
        write_baseline(root, current)
        changed = _changes(old, current)
        print(f"wrote {BASELINE_PATH}")
        print("\n".join(changed) if changed else "no change")
        sys.exit(0)

    try:
        baseline = load_baseline(root)
    except MeasureError as e:
        print(_table(current, {}))
        print(f"\nerror: {e}", file=sys.stderr)
        sys.exit(1)

    print(_table(current, baseline))
    print()
    problems = findings(current, baseline)
    for plugin, msg in problems:
        print(f"FAIL  {plugin}: {msg}")
    if not problems:
        print(scope_line(current, baseline))
    sys.exit(1 if problems else 0)
