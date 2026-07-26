"""Measure how plugins actually behave, across every repo you use them in.

This deliberately does NOT compute what Claude Code already reports. Before
adding a section here, check whether one of these covers it:

    claude plugin details <name>   per-plugin token cost, always-on vs on-invoke
    /context                       what occupies the context window, by category
    /doctor                        config problems, skill-listing cost, CLAUDE.md trim
    /hooks                         which hooks are registered
    claude --debug hooks           which hooks fired, with exit codes and output
    claude --safe-mode             isolate whether a plugin/hook/skill causes a problem

What none of those show is behaviour *over time and across projects*: how often
a hook actually speaks versus merely fires, how that differs per repo, whether
skills are ever invoked, and whether the files a plugin wrote into a repo have
drifted behind the plugin. That is what this reads out of session transcripts.

Four traps, each of which produced plausible-looking wrong numbers before being
caught. They are handled here and must stay handled:

  1. `{}` is not speech. A no-op JSON response is the common hook return; count
     it and every silent hook reads as a 100% emitter.
  2. Do not double-count channels. `hook_success.stdout` and
     `hook_additional_context` are separate records for what may be one
     emission; summing both yields rates above 100%.
  3. `session-start.sh` cannot be attributed by command string -- several
     plugins share the filename and the plugin-root variable is stored
     unexpanded. Resolve against the installed plugin registry instead.
  4. Date-filter. Transcripts span months and mix in since-disabled plugins and
     since-fixed behaviour.
"""

from __future__ import annotations

import argparse
import collections
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import orjson

NOOP_STDOUT = {"", "{}", "{ }", "null", "[]"}

# The only attachment kinds analyze_project branches on. Used as a bytes
# pre-filter so unrelated attachments never reach orjson.loads.
_WANTED_KINDS = (b'"hook_success"', b'"hook_additional_context"',
                 b'"diagnostics"', b'"invoked_skills"')

# The one place this module names a location outside the repo. Claude Code owns
# these directories; there is no repo-relative way to refer to them.
_CLAUDE_HOME = Path(os.path.expanduser("~/.claude"))  # path-privacy: ignore

PLUGIN_ROOTS = (_CLAUDE_HOME / "plugins" / "cache",
                _CLAUDE_HOME / "plugins" / "marketplaces")
PROJECTS_DIR = _CLAUDE_HOME / "projects"


def _plugin_registry() -> dict[str, str]:
    """Map a hook script's plugin-root-relative path to its owning plugin.

    Trap 3. Built from the installed plugin manifests rather than guessed from
    the command string, because several plugins ship `hooks/session-start.sh`
    and the transcript stores the plugin-root variable unexpanded. A path owned
    by more than one plugin stays ambiguous and is reported as such, rather than
    attributed to whichever happened to sort first.
    """
    owners: dict[str, set[str]] = {}
    for root in PLUGIN_ROOTS:
        if not root.is_dir():
            continue
        for hj in root.rglob("hooks.json"):
            pdir = hj.parent.parent if hj.parent.name == "hooks" else hj.parent
            name = pdir.name
            pj = pdir / ".claude-plugin" / "plugin.json"
            if pj.exists():
                try:
                    name = orjson.loads(pj.read_bytes()).get("name", name) or name
                except (ValueError, OSError):
                    pass  # unreadable manifest: fall back to the directory name
            try:
                data = orjson.loads(hj.read_bytes())
            except (ValueError, OSError):
                continue  # skip this manifest, keep scanning the rest
            for groups in (data.get("hooks") or {}).values():
                for group in groups:
                    for hook in group.get("hooks") or []:
                        parts = [str(hook.get("command", ""))]
                        parts += [str(a) for a in (hook.get("args") or [])]
                        for tok in " ".join(parts).split():
                            if "PLUGIN_ROOT" in tok:
                                key = tok.strip('"').split("PLUGIN_ROOT}")[-1]
                                owners.setdefault(key, set()).add(name)
    return {k: (next(iter(v)) if len(v) == 1 else f"ambiguous({'/'.join(sorted(v))})")
            for k, v in owners.items()}


def _attribute(command: str, registry: dict[str, str]) -> str:
    best = ""
    for path in registry:
        if path and path in command and len(path) > len(best):
            best = path
    return registry[best] if best else "unattributed"


def _iter_records(path: Path, cutoff: datetime | None):
    with path.open("rb") as fh:
        for raw in fh:
            if not any(k in raw for k in _WANTED_KINDS):
                continue
            try:
                rec = orjson.loads(raw)
            except ValueError:
                continue  # truncated final line of a live transcript
            if cutoff is not None:
                ts = rec.get("timestamp")
                if ts:
                    try:
                        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                        if when < cutoff:
                            continue
                    except ValueError:
                        pass
            yield rec


def _blank_stat() -> dict[str, int]:
    return {"fired": 0, "spoke": 0, "stdout_b": 0, "ctx": 0,
            "ctx_b": 0, "ms": 0, "blocked": 0}


@dataclass
class ProjectStats:
    """Typed because the mixed-value dict this replaced inferred as `int`."""

    transcripts: int = 0
    stats: dict[str, dict[str, int]] = field(
        default_factory=lambda: collections.defaultdict(_blank_stat))
    skills: collections.Counter = field(default_factory=collections.Counter)
    diag_pushes: int = 0
    diag_msgs: int = 0


def analyze_project(pdir: Path, registry: dict[str, str], cutoff) -> ProjectStats:
    res = ProjectStats()
    stats, skills = res.stats, res.skills

    for jf in sorted(pdir.glob("*.jsonl")):
        res.transcripts += 1
        for rec in _iter_records(jf, cutoff):
            att = rec.get("attachment") or {}
            kind = att.get("type")
            if kind == "hook_success":
                st = stats[_attribute(att.get("command") or "", registry)]
                st["fired"] += 1
                out = (att.get("stdout") or "").strip()
                # Trap 1: a no-op JSON body is silence, not speech.
                if out not in NOOP_STDOUT:
                    st["spoke"] += 1
                    st["stdout_b"] += len(out)
                try:
                    st["ms"] += int(att.get("durationMs") or 0)
                except (TypeError, ValueError):
                    pass
                if str(att.get("exitCode")) == "2":
                    st["blocked"] += 1
            elif kind == "hook_additional_context":
                # Trap 2: its own channel, never folded into `spoke`.
                # `hookName` here is the event, not a script path, so the
                # registry cannot attribute it. Bucket it honestly by event
                # rather than blaming a plugin we did not identify.
                st = stats[f"context via {att.get('hookName') or 'unknown'}"]
                st["ctx"] += 1
                st["ctx_b"] += len(str(att.get("content") or ""))
            elif kind == "diagnostics":
                res.diag_pushes += 1
                for entry in att.get("files") or []:
                    res.diag_msgs += len(entry.get("diagnostics") or [])
            elif kind == "invoked_skills":
                for sk in att.get("skills") or []:
                    if isinstance(sk, dict):
                        skills[sk.get("name", "?")] += 1

    return res


def _installed_template_version() -> str | None:
    """The `tN` stamp the installed path-privacy would write today."""
    for root in PLUGIN_ROOTS:
        if not root.is_dir():
            continue
        for inst in root.rglob("skills/path-privacy/scripts/install-git-hooks.sh"):
            try:
                for line in inst.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("WRAPPER_TEMPLATE_VERSION="):
                        return "t" + line.split("=", 1)[1].strip()
            except OSError:
                continue
    return None


def artifact_drift(repos: list[Path]) -> list[tuple[str, str, str, str]]:
    """Report files our plugins wrote into repos, and whether they have drifted.

    Plugin *code* cannot drift -- it installs once per user, and every repo
    picks up the new version. Files a plugin writes INTO a repo are the
    exception, and a git hook is frozen at install time by design, since it
    cannot source from a plugin that may not be installed. That freeze is
    correct, and it is also the only place staleness can hide -- which is
    exactly how it hides: you only find out by opening a session in that repo.
    """
    # Wrapper stamps are template versions ("t2"), not plugin versions. Reading
    # plugin.json here compared two different namespaces, so a perfectly current
    # wrapper reported "cannot compare -- reinstall" in every repo.
    current = _installed_template_version()
    rows: list[tuple[str, str, str, str]] = []
    for repo in repos:
        hook = repo / ".git" / "hooks" / "pre-commit"
        if hook.exists():
            stamp = None
            try:
                for line in hook.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("# path-privacy:wrapper-version "):
                        stamp = line.split(" ", 2)[-1].strip()
                        break
            except OSError:
                pass
            # Direction has to be established, not assumed. A bare `!=` fires
            # in both directions and calls both "stale" -- the exact defect
            # path-privacy 0.7.2/0.7.3 exists to fix. A wrapper installed from a
            # source checkout is legitimately AHEAD of the installed plugin, and
            # telling someone to re-run the installer there would regenerate the
            # wrapper from the older plugin: the advertised fix as a downgrade.
            def _tn(v: str) -> int | None:
                return int(v[1:]) if v.startswith("t") and v[1:].isdigit() else None
            have, want = _tn(stamp or ""), _tn(current or "")
            if current is None:
                # The installed plugin predates template stamps entirely. The
                # wrapper is not the thing that is behind, and telling someone to
                # reinstall from that plugin is the downgrade this whole
                # comparison exists to prevent.
                verdict = ("installed path-privacy predates wrapper-template "
                           "versioning -- update the plugin, not the wrapper")
            elif stamp is None:
                verdict = "no stamp (foreign hook, or pre-0.6.0 install) -- reinstall"
            elif have is None:
                verdict = f"legacy stamp, plugin ships {current} -- reinstall to migrate"
            elif have == want:
                verdict = "current"
            elif have > want:
                verdict = (f"wrapper AHEAD of installed plugin {current} -- "
                           "gate is fine; do NOT re-run the installer")
            else:
                verdict = f"STALE (plugin at {current}) -- reinstall"
            rows.append((repo.name, "path-privacy wrapper", stamp or "-", verdict))

        pc = repo / "pyrightconfig.json"
        if pc.exists():
            try:
                body = orjson.loads(pc.read_bytes())
            except (ValueError, OSError):
                body = {}  # unparseable: treat as not-ours, leave it alone
            ours = bool(body) and set(body) <= {
                "venvPath", "venv", "reportMissingImports", "reportMissingModuleSource"}
            has_tool_pyright = False
            pyproject = repo / "pyproject.toml"
            if pyproject.exists():
                try:
                    has_tool_pyright = "[tool.pyright" in pyproject.read_text(
                        encoding="utf-8", errors="replace")
                except OSError:
                    pass
            if ours and has_tool_pyright:
                verdict = "SHADOWING [tool.pyright] -- pyright ranks this file higher"
            elif ours:
                verdict = "autoconfig-owned"
            else:
                verdict = "hand-written (not ours, left alone)"
            rows.append((repo.name, "pyrightconfig.json", "-", verdict))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(prog="skill-maintain tune")
    ap.add_argument("--days", type=int, default=30,
                    help="only count transcript records newer than N days (default 30); "
                         "0 for all time")
    ap.add_argument("--project", action="append",
                    help="substring of a project dir to include; repeatable")
    ap.add_argument("--repo", action="append",
                    help="repo path to check for written-in artifacts; repeatable")
    ap.add_argument("--min-fired", type=int, default=1)
    # cli.py already rewrites argv to ["skill-maintain tune", ...rest], so the
    # command name is gone by now; slicing from 2 would eat the first flag.
    args = ap.parse_args(sys.argv[1:])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)) if args.days else None
    registry = _plugin_registry()

    if not PROJECTS_DIR.is_dir():
        print("no session transcripts found")
        return

    dirs = [d for d in sorted(PROJECTS_DIR.iterdir())
            if d.is_dir() and any(d.glob("*.jsonl"))]
    if args.project:
        dirs = [d for d in dirs if any(p in d.name for p in args.project)]

    window = f"last {args.days}d" if args.days else "all time"
    print(f"# tune -- {window}, {len(dirs)} project(s), "
          f"{len(registry)} hook paths in registry\n")

    grand: dict[str, dict] = collections.defaultdict(_blank_stat)
    for d in dirs:
        res = analyze_project(d, registry, cutoff)
        rows = [(k, v) for k, v in res.stats.items()
                if v["fired"] >= args.min_fired or v["ctx"]]
        if not rows and not res.skills:
            continue
        print(f"## {d.name}  ({res.transcripts} transcripts)")
        print(f"{'plugin':<30}{'fired':>7}{'spoke':>7}{'rate':>7}"
              f"{'stdout_b':>10}{'ctx_b':>9}{'blk':>5}{'ms/fire':>8}")
        for name, s in sorted(rows, key=lambda kv: -(kv[1]["stdout_b"] + kv[1]["ctx_b"])):
            rate = (100 * s["spoke"] / s["fired"]) if s["fired"] else 0
            mpf = (s["ms"] / s["fired"]) if s["fired"] else 0
            print(f"{name:<30}{s['fired']:>7}{s['spoke']:>7}{rate:>6.0f}%"
                  f"{s['stdout_b']:>10}{s['ctx_b']:>9}{s['blocked']:>5}{mpf:>8.0f}")
            g = grand[name]
            for k in g:
                g[k] += s[k]
        if res.diag_pushes:
            per = res.diag_msgs / res.diag_pushes
            note = "   <- noisy channel; a never-zero channel gets ignored" if per > 3 else ""
            print(f"LSP diagnostics: {res.diag_pushes} pushes / {res.diag_msgs} "
                  f"messages ({per:.1f} per push){note}")
        inv = sum(res.skills.values())
        if res.transcripts:
            print(f"skills invoked: {inv} across {len(res.skills)} distinct "
                  f"({inv / res.transcripts:.2f}/transcript)")
        print()

    if grand:
        print("## across all projects")
        print(f"{'plugin':<30}{'fired':>8}{'spoke':>8}{'rate':>7}{'bytes':>11}")
        for name, s in sorted(grand.items(),
                              key=lambda kv: -(kv[1]["stdout_b"] + kv[1]["ctx_b"])):
            rate = (100 * s["spoke"] / s["fired"]) if s["fired"] else 0
            print(f"{name:<30}{s['fired']:>8}{s['spoke']:>8}{rate:>6.0f}%"
                  f"{s['stdout_b'] + s['ctx_b']:>11}")
        print()
        print("Read the rate, not the count. A hook that fires constantly and stays")
        print("silent is nearly free; one that fires rarely and always speaks is not.")
        print()

    repos = [Path(os.path.expanduser(r)) for r in (args.repo or [])]
    if repos:
        print("## artifacts written into repos")
        rows = artifact_drift(repos)
        if not rows:
            print("  none found")
        for repo, what, ver, verdict in rows:
            print(f"  {repo:<26}{what:<24}{ver:<10}{verdict}")


if __name__ == "__main__":
    main()
