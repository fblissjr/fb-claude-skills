#!/usr/bin/env python3
"""Single writer for the improvement-loops state, and the Stop-hook guard.

Every write the /improve and /optimize loops make to their state goes through
this script: run records, the scoreboard, the ledger, bookmarks, and appends
to the session log. The same script, as `stop-guard`, is the plugin's Stop
hook, pushing a run back to work while its definition of done is unmet.

Usage:
    python3 loop_state.py [--state DIR] <command> ...

Exit codes: 0 success, 1 a valid request that was refused, 2 bad input,
3 a state write the OS or sandbox refused (EPERM, EACCES, EROFS); its message
names the path and the escape, `--state DIR` or `LOOP_STATE_DIR`.
Human-readable messages go to stderr, machine output to stdout. `stop-guard`
always exits 0: a Stop hook must never trap a session, so every failure in it
fails open, a refused write included (its message still goes to stderr).

Writing into the main checkout from a worktree-isolated session works only
because Claude Code's worktree isolation does not cover a script's file
writes. That is observed, not documented (docs/internals/gotchas.md), so a
refusal is expected one day and must be loud: exit 3, never a traceback.

Standard library only, run with bare `python3` (3.9 or newer). This is a
deliberate exception to the repo's orjson-and-uv rule. The script runs from
inside worktree-isolated sessions, where `uv run` fails in a sandbox unless
UV_CACHE_DIR is overridden, and Claude Code's isolation refuses any command
that carries a runtime-computed variable, so that override cannot be passed.

State dir resolution, for every command:
    --state DIR  >  env LOOP_STATE_DIR  >  the pointer file  >  <main checkout>/.loops
The main checkout is the parent of `git rev-parse --git-common-dir`, so a
command run inside a linked worktree writes to the main checkout's state, which
outlives the worktree. A relative --state or LOOP_STATE_DIR resolves against
the main checkout, not the cwd. `start` records the state dir it used in the
pointer file `<git-common-dir>/improvement-loops-state`, so the Stop hook,
which runs with no flags and no model-supplied env, finds a run started with a
custom --state. When the state dir is `<main checkout>/.loops`, `/.loops/` is
listed once in `<git-common-dir>/info/exclude`.

Layout of the state dir:
    runs/<run_id>/record.json   one run's record
    scoreboard.jsonl            one measurement per line
    ledger.md                   ideas and their fate, append-only between tidies
    archive/ledger-<run_id>.md  the ledger as it stood before a tidy
    bookmarks.json              {"lenses": {name: commit}, "deps": {name: release}}
"""

from __future__ import annotations

import argparse
import errno
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # not POSIX; writes stay atomic but are not serialized
    fcntl = None

# Reasoned, not measured: a live loop heartbeats on every check and every
# guard-driven continuation, so half an hour of silence means it has most
# likely died. A stale run still blocks tidy; the owner decides.
STALE_MINUTES = 30

# Reasoned, not measured: Anthropic's Opus 5.5 guide says to stop after two or
# three automatic continuations. Past this the guard stands down.
MAX_CONTINUATIONS = 3

# Reasoned, not measured: every critical section is one small file write, so a
# lock held longer than this means a stuck writer, not a busy one. Kept well
# under the Stop hook's timeout so the guard gives up before the harness does.
LOCK_WAIT_SECONDS = 3

# Reasoned, not measured: `git rev-parse` answers from local files. Together
# with LOCK_WAIT_SECONDS this bounds stop-guard's worst case below the Stop
# hook timeout the plugin registers, so the guard returns before being killed.
GIT_TIMEOUT_SECONDS = 5

LOOPS = ("improve", "optimize")
SCORE_KEYS = ("commit", "scenario", "inputs", "deps", "machine", "load", "samples", "median", "spread")
LEDGER_STATUSES = ("open", "kept", "rejected", "died")
POINTER_NAME = "improvement-loops-state"
DEFAULT_DIRNAME = ".loops"
EXCLUDE_LINE = "/.loops/"
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-(?:%s)(?:-\d+)?$" % "|".join(LOOPS))


class Refused(Exception):
    """A valid request this script declines (exit 1)."""


class BadInput(Exception):
    """A malformed request (exit 2)."""


REFUSED_ERRNOS = (errno.EPERM, errno.EACCES, errno.EROFS)


class Unwritable(Exception):
    """A state write the OS or a sandbox refused (exit 3)."""

    def __init__(self, path, exc: OSError):
        super().__init__(
            "loop_state: cannot write %s (%s). The session may not write there; pass "
            "--state <dir the session can write> or set LOOP_STATE_DIR." % (path, exc.strerror or exc)
        )


class writing:
    """Turn a refused write under this block into Unwritable naming `path`."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        if isinstance(exc, OSError) and exc.errno in REFUSED_ERRNOS:
            raise Unwritable(self.path, exc) from exc
        return False


# --- time -------------------------------------------------------------------


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(dt: datetime) -> str:
    return dt.strftime(TS_FORMAT)


def parse_ts(text: str) -> datetime:
    return datetime.strptime(text, TS_FORMAT).replace(tzinfo=timezone.utc)


def age_minutes(text: str, at: datetime) -> float:
    return round((at - parse_ts(text)).total_seconds() / 60, 1)


# --- files ------------------------------------------------------------------


def _default_mode() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def write_atomic(path: Path, text: str) -> None:
    """Write via a temp file in the same dir, then os.replace."""
    with writing(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = path.stat().st_mode & 0o777 if path.exists() else _default_mode()
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def append_atomic(path: Path, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    write_atomic(path, existing + text)


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


class StateLock:
    """Serializes writers on one state dir, with a bounded wait."""

    def __init__(self, state: Path):
        self.path = state / ".lock"
        self.fh = None

    def __enter__(self):
        if fcntl is None:
            return self
        with writing(self.path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.fh = open(self.path, "a")
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    self.fh.close()
                    raise Refused("state dir %s is locked by another writer" % self.path.parent)
                time.sleep(0.05)

    def __exit__(self, *exc):
        if self.fh is not None:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
            self.fh.close()
        return False


# --- where the state lives -------------------------------------------------------


def git_common_dir(cwd) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=str(cwd), capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = out.stdout.strip()
    if out.returncode != 0 or not text:
        return None
    return Path(text)


class Where:
    def __init__(self, state: Path, common: Path | None):
        self.state = state
        self.common = common
        self.main = common.parent if common is not None else None


def resolve(flag: str | None, cwd) -> Where:
    """Apply --state > LOOP_STATE_DIR > pointer file > <main>/.loops. Creates nothing."""
    common = git_common_dir(cwd)
    main = common.parent if common is not None else None
    chosen = flag if flag else os.environ.get("LOOP_STATE_DIR") or None
    if chosen:
        path = Path(chosen).expanduser()
        if not path.is_absolute():
            if main is None:
                raise BadInput("relative state dir %r needs a git checkout to resolve against" % chosen)
            path = main / path
        return Where(Path(os.path.abspath(path)), common)
    if common is None:
        raise BadInput("not inside a git checkout; pass --state DIR or set LOOP_STATE_DIR")
    pointer = common / POINTER_NAME
    if pointer.is_file():
        target = pointer.read_text(encoding="utf-8").strip()
        if target and os.path.isabs(target):
            return Where(Path(target), common)
    return Where(main / DEFAULT_DIRNAME, common)


def ensure_exclude(where: Where) -> None:
    """List /.loops/ in info/exclude once, when the state dir is the default one."""
    if where.common is None or where.state != where.main / DEFAULT_DIRNAME:
        return
    exclude = where.common / "info" / "exclude"
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if EXCLUDE_LINE in (line.strip() for line in existing.splitlines()):
        return
    sep = "" if not existing or existing.endswith("\n") else "\n"
    write_atomic(exclude, existing + sep + EXCLUDE_LINE + "\n")


# --- records ------------------------------------------------------------------


def record_file(state: Path, run_id: str) -> Path:
    if not RUN_ID_RE.match(run_id or ""):
        raise BadInput("not a run id: %r" % run_id)
    return state / "runs" / run_id / "record.json"


def load_record(state: Path, run_id: str) -> dict:
    path = record_file(state, run_id)
    if not path.is_file():
        raise BadInput("unknown run %s in %s" % (run_id, state))
    return json.loads(path.read_text(encoding="utf-8"))


def save_record(state: Path, rec: dict) -> None:
    write_atomic(record_file(state, rec["run_id"]), dump(rec))


def all_records(state: Path):
    """Yield (run_id, record or None if unreadable, error)."""
    runs = state / "runs"
    if not runs.is_dir():
        return
    for path in sorted(runs.glob("*/record.json")):
        run_id = path.parent.name
        try:
            yield run_id, json.loads(path.read_text(encoding="utf-8")), None
        except (OSError, ValueError) as exc:
            yield run_id, None, exc


def unmet(rec: dict) -> list:
    return [{"n": i, "item": d["item"]} for i, d in enumerate(rec["done"], 1) if not d.get("met")]


def require_running(rec: dict) -> None:
    if rec.get("status") != "running":
        raise Refused("run %s is %s, not running" % (rec["run_id"], rec.get("status")))


def touch(rec: dict) -> None:
    rec["heartbeat"] = fmt(now())
    rec["continuations"] = 0


def nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple)):
        return bool(value)
    return True


def need_text(value: str, name: str) -> str:
    if not nonempty(value):
        raise BadInput("%s must not be empty" % name)
    return value


def read_from(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise BadInput("cannot read --from %s: %s" % (path, exc))


# --- commands -------------------------------------------------------------------


def cmd_start(args, where: Where) -> int:
    need_text(args.base, "--base")
    need_text(args.session, "--session")
    if args.budget_minutes <= 0:
        raise BadInput("--budget-minutes must be a positive integer")
    items = [need_text(d, "--done") for d in args.done]
    ensure_exclude(where)
    state = where.state
    started = now()
    with StateLock(state):
        runs = state / "runs"
        with writing(runs):
            runs.mkdir(parents=True, exist_ok=True)
        base_id = "%s-%s" % (started.strftime("%Y%m%d-%H%M%S"), args.loop)
        run_id, n = base_id, 1
        while True:
            try:
                with writing(runs / run_id):
                    (runs / run_id).mkdir()
                break
            except FileExistsError:
                n += 1
                run_id = "%s-%d" % (base_id, n)
        rec = {
            "run_id": run_id,
            "loop": args.loop,
            "base": args.base,
            "session": args.session,
            "started": fmt(started),
            "budget_deadline": fmt(started + timedelta(minutes=args.budget_minutes)),
            "heartbeat": fmt(started),
            "status": "running",
            "done": [{"item": d, "met": False, "evidence": None} for d in items],
            "continuations": 0,
            "notes": [],
        }
        save_record(state, rec)
    if where.common is not None:
        write_atomic(where.common / POINTER_NAME, str(state) + "\n")
    print(run_id)
    return 0


def cmd_heartbeat(args, where: Where) -> int:
    with StateLock(where.state):
        rec = load_record(where.state, args.run)
        require_running(rec)
        touch(rec)
        save_record(where.state, rec)
    return 0


def cmd_check(args, where: Where) -> int:
    need_text(args.evidence, "--evidence")
    with StateLock(where.state):
        rec = load_record(where.state, args.run)
        require_running(rec)
        if not 1 <= args.item <= len(rec["done"]):
            raise BadInput("--item must be 1..%d" % len(rec["done"]))
        rec["done"][args.item - 1].update(met=True, evidence=args.evidence)
        touch(rec)
        save_record(where.state, rec)
    return 0


def cmd_finish(args, where: Where) -> int:
    if args.status == "stopped" and not nonempty(args.reason):
        raise BadInput("--status stopped requires --reason")
    with StateLock(where.state):
        rec = load_record(where.state, args.run)
        require_running(rec)
        if args.status == "done":
            missing = unmet(rec)
            if missing:
                lines = "\n".join("  %d. %s" % (u["n"], u["item"]) for u in missing)
                raise Refused("run %s cannot finish done; unmet done items:\n%s" % (rec["run_id"], lines))
        rec["status"] = args.status
        rec["finished"] = fmt(now())
        if args.reason:
            rec["reason"] = args.reason
        save_record(where.state, rec)
    return 0


def cmd_score(args, where: Where) -> int:
    try:
        row = json.loads(args.row)
    except ValueError as exc:
        raise BadInput("--row is not JSON: %s" % exc)
    if not isinstance(row, dict):
        raise BadInput("--row must be a JSON object")
    missing = [k for k in SCORE_KEYS if not nonempty(row.get(k))]
    if missing:
        raise BadInput("score row is missing or empty: %s" % ", ".join(missing))
    with StateLock(where.state):
        load_record(where.state, args.run)
        row["run_id"] = args.run
        row["recorded_at"] = fmt(now())
        line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        append_atomic(where.state / "scoreboard.jsonl", line)
    return 0


def _one_line(text: str) -> str:
    return " ".join(text.split())


def cmd_ledger(args, where: Where) -> int:
    for name in ("lens", "idea", "evidence"):
        need_text(getattr(args, name), "--" + name)
    try:
        ev = float(args.ev)
    except ValueError:
        raise BadInput("--ev must be a number, got %r" % args.ev)
    if not math.isfinite(ev):
        raise BadInput("--ev must be finite")
    evidence = "\n  ".join(args.evidence.strip().splitlines())
    entry = (
        "\n## %s\n\n- run: %s\n- lens: %s\n- ev: %s\n- status: %s\n- evidence: %s\n- recorded: %s\n"
        % (_one_line(args.idea), args.run, _one_line(args.lens), args.ev.strip(), args.status, evidence, fmt(now()))
    )
    with StateLock(where.state):
        load_record(where.state, args.run)
        path = where.state / "ledger.md"
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if not existing.strip():
            existing = "# Ledger\n"
        write_atomic(path, existing + entry)
    return 0


def _tidy_blockers(state: Path, run_id: str):
    at = now()
    live, stale = [], []
    for other, rec, err in all_records(state):
        if other == run_id:
            continue
        if rec is None:
            live.append("%s (unreadable record: %s)" % (other, err))
            continue
        if rec.get("status") != "running":
            continue
        try:
            age = age_minutes(rec["heartbeat"], at)
        except (KeyError, ValueError):
            live.append("%s (no readable heartbeat)" % other)
            continue
        desc = "%s (%s, heartbeat %s min ago)" % (other, rec.get("loop"), age)
        (stale if age > STALE_MINUTES else live).append(desc)
    return live, stale


def _report_blockers(live, stale) -> None:
    for desc in live:
        print("running: %s" % desc, file=sys.stderr)
    for desc in stale:
        print("looks abandoned: %s; still blocks, the owner decides" % desc, file=sys.stderr)


def cmd_can_tidy(args, where: Where) -> int:
    load_record(where.state, args.run)
    live, stale = _tidy_blockers(where.state, args.run)
    if live or stale:
        _report_blockers(live, stale)
        return 1
    return 0


def cmd_tidy(args, where: Where) -> int:
    new_text = read_from(args.from_file)
    with StateLock(where.state):
        load_record(where.state, args.run)
        live, stale = _tidy_blockers(where.state, args.run)
        if live or stale:
            _report_blockers(live, stale)
            raise Refused("tidy refused: other runs may be using the ledger")
        ledger = where.state / "ledger.md"
        archive = None
        if ledger.exists():
            archive = where.state / "archive" / ("ledger-%s.md" % args.run)
            n = 1
            while archive.exists():
                n += 1
                archive = where.state / "archive" / ("ledger-%s-%d.md" % (args.run, n))
            write_atomic(archive, ledger.read_text(encoding="utf-8"))
        write_atomic(ledger, new_text)
    if archive is not None:
        print(archive)
    return 0


def cmd_bookmark(args, where: Where) -> int:
    lens_form = args.lens is not None or args.commit is not None
    dep_form = args.dep is not None or args.release is not None
    if lens_form == dep_form:
        raise BadInput("use either --lens NAME --commit SHA or --dep NAME --release VERSION")
    if lens_form:
        section, key, value = "lenses", args.lens, args.commit
    else:
        section, key, value = "deps", args.dep, args.release
    if not nonempty(key) or not nonempty(value):
        raise BadInput("both the name and the value are required")
    with StateLock(where.state):
        path = where.state / "bookmarks.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data.setdefault("lenses", {})
        data.setdefault("deps", {})
        data[section][key] = value
        write_atomic(path, dump(data))
    return 0


def cmd_log(args, where: Where) -> int:
    if where.main is None:
        raise BadInput("log needs a git checkout to resolve --path against")
    rel = args.path
    if not nonempty(rel) or os.path.isabs(rel):
        raise BadInput("--path must be relative to the main checkout: %r" % rel)
    root = os.path.realpath(str(where.main))
    target = os.path.realpath(os.path.join(root, rel))
    if target == root or os.path.commonpath([root, target]) != root:
        raise BadInput("--path escapes the main checkout: %r" % rel)
    body = read_from(args.from_file)
    if not body.endswith("\n"):
        body += "\n"
    with StateLock(where.state):
        load_record(where.state, args.run)
        path = Path(target)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        sep = "" if not existing or existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        write_atomic(path, existing + sep + "## %s\n\n%s" % (args.run, body))
    return 0


def cmd_status(args, where: Where) -> int:
    if args.run:
        print(dump(load_record(where.state, args.run)), end="")
        return 0
    at = now()
    rows = []
    for run_id, rec, err in all_records(where.state):
        if rec is None:
            rows.append({"run_id": run_id, "error": "unreadable record: %s" % err})
            continue
        rows.append({
            "run_id": run_id,
            "loop": rec.get("loop"),
            "status": rec.get("status"),
            "heartbeat_age_minutes": age_minutes(rec["heartbeat"], at),
            "unmet": unmet(rec),
        })
    print(dump(rows), end="")
    return 0


# --- stop-guard -------------------------------------------------------------------


def _guard_reason(rec: dict, missing: list, state: Path) -> str:
    items = "; ".join("%d. %s" % (u["n"], u["item"]) for u in missing)
    script = Path(__file__).resolve()
    return (
        "Improvement loop run %s still has unmet done items: %s. Continue with them. "
        "If one is blocked, say what blocks it and end the run with: "
        "python3 %s --state %s finish --run %s --status stopped --reason \"<what blocks it>\""
        % (rec["run_id"], items, script, state, rec["run_id"])
    )


def stop_guard(flag: str | None) -> int:
    """Stop-hook mode. Always exits 0; prints one block decision or nothing."""
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw)
        except ValueError:
            print("loop_state stop-guard: hook input is not JSON; standing aside", file=sys.stderr)
            return 0
        if not isinstance(data, dict):
            return 0
        session = data.get("session_id")
        if not isinstance(session, str) or not session:
            return 0
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or not os.path.isdir(cwd):
            cwd = os.getcwd()
        try:
            where = resolve(flag, cwd)
        except BadInput:
            return 0
        state = where.state
        if not (state / "runs").is_dir():
            return 0

        at = now()
        reasons = []
        candidates = []
        for run_id, rec, err in all_records(state):
            if rec is None:
                print("loop_state stop-guard: skipping unreadable record %s: %s" % (run_id, err), file=sys.stderr)
                continue
            if rec.get("status") == "running" and rec.get("session") == session:
                candidates.append(run_id)
        if not candidates:
            return 0

        with StateLock(state):
            for run_id in candidates:
                rec = load_record(state, run_id)
                if rec.get("status") != "running" or rec.get("session") != session:
                    continue
                if at > parse_ts(rec["budget_deadline"]):
                    continue
                missing = unmet(rec)
                if not missing:
                    continue
                count = int(rec.get("continuations", 0))
                if count < MAX_CONTINUATIONS:
                    rec["continuations"] = count + 1
                    reasons.append(_guard_reason(rec, missing, state))
                    save_record(state, rec)
                elif count == MAX_CONTINUATIONS:
                    rec["continuations"] = count + 1
                    rec.setdefault("notes", []).append({
                        "at": fmt(at),
                        "text": "stop-guard stood down after %d automatic continuations with %d done "
                                "item(s) unmet; a heartbeat re-arms it" % (MAX_CONTINUATIONS, len(missing)),
                    })
                    save_record(state, rec)
        if reasons:
            sys.stdout.write(json.dumps({"decision": "block", "reason": "\n\n".join(reasons)}, ensure_ascii=False) + "\n")
        return 0
    except Unwritable as exc:  # fail open, but say why and how out
        print("loop_state stop-guard: standing aside. %s" % exc, file=sys.stderr)
        return 0
    except Exception as exc:  # a Stop hook must never trap a session
        print("loop_state stop-guard: internal error, standing aside: %r" % (exc,), file=sys.stderr)
        return 0


# --- cli ------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="loop_state.py", description="Improvement-loops state writer and Stop guard.")
    p.add_argument("--state", help="state dir (default: LOOP_STATE_DIR, the pointer file, or <main checkout>/.loops)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("start")
    s.add_argument("--loop", required=True, choices=LOOPS)
    s.add_argument("--base", required=True)
    s.add_argument("--session", required=True)
    s.add_argument("--budget-minutes", required=True, type=int)
    s.add_argument("--done", required=True, action="append")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("heartbeat")
    s.add_argument("--run", required=True)
    s.set_defaults(func=cmd_heartbeat)

    s = sub.add_parser("check")
    s.add_argument("--run", required=True)
    s.add_argument("--item", required=True, type=int)
    s.add_argument("--evidence", required=True)
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("finish")
    s.add_argument("--run", required=True)
    s.add_argument("--status", required=True, choices=("done", "stopped"))
    s.add_argument("--reason")
    s.set_defaults(func=cmd_finish)

    s = sub.add_parser("score")
    s.add_argument("--run", required=True)
    s.add_argument("--row", required=True)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("ledger")
    s.add_argument("--run", required=True)
    s.add_argument("--lens", required=True)
    s.add_argument("--idea", required=True)
    s.add_argument("--ev", required=True)
    s.add_argument("--status", required=True, choices=LEDGER_STATUSES)
    s.add_argument("--evidence", required=True)
    s.set_defaults(func=cmd_ledger)

    s = sub.add_parser("can-tidy")
    s.add_argument("--run", required=True)
    s.set_defaults(func=cmd_can_tidy)

    s = sub.add_parser("tidy")
    s.add_argument("--run", required=True)
    s.add_argument("--from", required=True, dest="from_file")
    s.set_defaults(func=cmd_tidy)

    s = sub.add_parser("bookmark")
    s.add_argument("--lens")
    s.add_argument("--commit")
    s.add_argument("--dep")
    s.add_argument("--release")
    s.set_defaults(func=cmd_bookmark)

    s = sub.add_parser("log")
    s.add_argument("--run", required=True)
    s.add_argument("--path", required=True)
    s.add_argument("--from", required=True, dest="from_file")
    s.set_defaults(func=cmd_log)

    s = sub.add_parser("status")
    s.add_argument("--run")
    s.set_defaults(func=cmd_status)

    sub.add_parser("stop-guard")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stop-guard":
        return stop_guard(args.state)
    try:
        where = resolve(args.state, os.getcwd())
        return args.func(args, where)
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except BadInput as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except Unwritable as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
