"""loop_state.py: the single writer for improvement-loops' loop state, and its Stop-hook guard.

The script ships in the improvement-loops plugin and runs as bare `python3`
from inside worktree-isolated sessions, so every test drives it the same way:
as a subprocess, under `-I -S` (isolated mode, no site-packages), which makes
any third-party import fail here before it fails in an installer's session.

Each test carries a one-line comment naming what breaks if it is deleted.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "skills/improvement-loops/scripts/loop_state.py"


def _constants():
    spec = importlib.util.spec_from_file_location("loop_state_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GIT_ENV = {
    **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}
GIT_ENV.pop("LOOP_STATE_DIR", None)


def run(args, *, state=None, cwd=None, stdin="", python=None, env=None):
    # Never default to the pytest cwd: that is this repo, and `start` would write
    # its pointer file into this repo's .git.
    if cwd is None:
        assert state is not None and Path(state).is_dir(), "pass cwd= or an existing --state dir"
        cwd = state
    cmd = [python or sys.executable, "-I", "-S", str(SCRIPT)]
    if python:  # a foreign interpreter may not accept -I; -S alone keeps site-packages out
        cmd = [python, "-S", str(SCRIPT)]
    if state is not None:
        cmd += ["--state", str(state)]
    cmd += [str(a) for a in args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        env=env or GIT_ENV,
        timeout=30,
    )


def git(*args, cwd):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env=GIT_ENV,
    )


def start(state, *, loop="improve", session="sess-1", done=("first item", "second item"), cwd=None):
    args = ["start", "--loop", loop, "--base", "abc123", "--session", session, "--budget-minutes", "60"]
    for d in done:
        args += ["--done", d]
    r = run(args, state=state, cwd=cwd)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def record_path(state, run_id):
    return Path(state) / "runs" / run_id / "record.json"


def load(state, run_id):
    return json.loads(record_path(state, run_id).read_text())


def edit(state, run_id, **fields):
    rec = load(state, run_id)
    rec.update(fields)
    record_path(state, run_id).write_text(json.dumps(rec))


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def guard(state, session="sess-1", **extra):
    payload = {"session_id": session, "stop_hook_active": False, "cwd": str(state), **extra}
    return run(["stop-guard"], state=state, stdin=json.dumps(payload))


FULL_ROW = {
    "commit": "abc123",
    "scenario": "export-large",
    "inputs": "fixtures/big.json",
    "deps": "bun 1.3",
    "machine": "m3-max",
    "load": "idle",
    "samples": [10, 11, 12],
    "median": 11,
    "spread": 0,
}


@pytest.fixture
def repo(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", cwd=main)
    git("commit", "-q", "--allow-empty", "-m", "init", cwd=main)
    return main


# --- state dir resolution -------------------------------------------------


def test_default_state_dir_is_main_checkout_from_linked_worktree(repo, tmp_path):
    # Deleting this lets loop state land in the worktree, where it dies with the worktree.
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", str(wt), "-b", "loop-branch", cwd=repo)
    run_id = start(None, cwd=wt)
    assert record_path(repo / ".loops", run_id).is_file()
    assert not (wt / ".loops").exists()
    r = run(["heartbeat", "--run", run_id], cwd=wt)
    assert r.returncode == 0, r.stderr
    exclude = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    assert exclude.count("/.loops/") == 1
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo, capture_output=True, text=True, env=GIT_ENV, check=True,
    ).stdout
    assert ".loops" not in status


def test_start_writes_pointer_file_that_later_commands_follow(repo, tmp_path):
    # Deleting this lets a run started with a custom --state become invisible to flagless commands.
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", str(wt), "-b", "loop-branch", cwd=repo)
    custom = tmp_path / "elsewhere"
    run_id = start(custom, cwd=wt)
    pointer = repo / ".git" / "improvement-loops-state"
    assert pointer.read_text().strip() == str(custom.resolve())
    r = run(["heartbeat", "--run", run_id], cwd=wt)
    assert r.returncode == 0, r.stderr
    assert not (repo / ".loops").exists()


def test_env_state_dir_used_when_no_flag(tmp_path):
    # Deleting this lets LOOP_STATE_DIR be ignored in favour of the git default.
    env = {**GIT_ENV, "LOOP_STATE_DIR": str(tmp_path / "envstate")}
    r = run(["start", "--loop", "improve", "--base", "a", "--session", "s", "--budget-minutes", "5",
             "--done", "x"], cwd=tmp_path, env=env)
    assert r.returncode == 0, r.stderr
    assert record_path(tmp_path / "envstate", r.stdout.strip()).is_file()


def test_relative_state_resolves_against_main_checkout(repo, tmp_path):
    # Deleting this lets a relative --state resolve against the worktree cwd.
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", str(wt), "-b", "loop-branch", cwd=repo)
    run_id = start("custom-state", cwd=wt)
    assert record_path(repo / "custom-state", run_id).is_file()
    assert not (wt / "custom-state").exists()


# --- start / record shape --------------------------------------------------


def test_start_writes_running_record_with_unmet_done_items(tmp_path):
    # Deleting this lets the record schema drift under the skills that read it.
    run_id = start(tmp_path)
    assert run_id.endswith("-improve")
    rec = load(tmp_path, run_id)
    assert rec["status"] == "running"
    assert rec["continuations"] == 0
    assert rec["done"] == [
        {"item": "first item", "met": False, "evidence": None},
        {"item": "second item", "met": False, "evidence": None},
    ]
    for key in ("run_id", "loop", "base", "session", "started", "budget_deadline", "heartbeat", "notes"):
        assert key in rec


def test_two_starts_in_one_second_get_distinct_run_ids(tmp_path):
    # Deleting this lets a second run silently overwrite the first run's record.
    a = start(tmp_path)
    b = start(tmp_path)
    assert a != b
    assert record_path(tmp_path, a).is_file() and record_path(tmp_path, b).is_file()


# --- score -------------------------------------------------------------------


def test_score_refuses_row_missing_conditions_and_names_every_missing_key(tmp_path):
    # Deleting this lets unconditioned numbers into the scoreboard, where they cannot be compared.
    run_id = start(tmp_path)
    row = {k: v for k, v in FULL_ROW.items() if k not in ("machine", "load")}
    row["deps"] = "  "
    r = run(["score", "--run", run_id, "--row", json.dumps(row)], state=tmp_path)
    assert r.returncode == 2
    for key in ("machine", "load", "deps"):
        assert key in r.stderr
    assert not (tmp_path / "scoreboard.jsonl").exists()


def test_score_appends_row_with_run_id_and_zero_spread_counts_as_present(tmp_path):
    # Deleting this lets a zero spread (a real measurement) be refused as missing.
    run_id = start(tmp_path)
    for _ in range(2):
        r = run(["score", "--run", run_id, "--row", json.dumps(FULL_ROW)], state=tmp_path)
        assert r.returncode == 0, r.stderr
    lines = (tmp_path / "scoreboard.jsonl").read_text().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["run_id"] == run_id and row["recorded_at"] and row["spread"] == 0


# --- finish --------------------------------------------------------------------


def test_finish_done_refused_while_any_done_item_unmet(tmp_path):
    # Deleting this lets a run claim done with its definition of done unmet.
    run_id = start(tmp_path)
    assert run(["check", "--run", run_id, "--item", 1, "--evidence", "ran it"], state=tmp_path).returncode == 0
    r = run(["finish", "--run", run_id, "--status", "done"], state=tmp_path)
    assert r.returncode == 1
    assert "second item" in r.stderr and "first item" not in r.stderr
    assert load(tmp_path, run_id)["status"] == "running"
    assert run(["check", "--run", run_id, "--item", 2, "--evidence", "ok"], state=tmp_path).returncode == 0
    assert run(["finish", "--run", run_id, "--status", "done"], state=tmp_path).returncode == 0
    assert load(tmp_path, run_id)["status"] == "done"


def test_finish_stopped_requires_reason(tmp_path):
    # Deleting this lets a run stop without saying why.
    run_id = start(tmp_path)
    assert run(["finish", "--run", run_id, "--status", "stopped"], state=tmp_path).returncode == 2
    r = run(["finish", "--run", run_id, "--status", "stopped", "--reason", "blocked on creds"], state=tmp_path)
    assert r.returncode == 0, r.stderr
    rec = load(tmp_path, run_id)
    assert rec["status"] == "stopped" and rec["reason"] == "blocked on creds"


def test_check_rejects_out_of_range_item(tmp_path):
    # Deleting this lets `check --item 3` on a two-item run fail with a traceback instead of exit 2.
    run_id = start(tmp_path)
    assert run(["check", "--run", run_id, "--item", 3, "--evidence", "x"], state=tmp_path).returncode == 2
    assert run(["check", "--run", run_id, "--item", 0, "--evidence", "x"], state=tmp_path).returncode == 2


# --- can-tidy / tidy -----------------------------------------------------------


def test_can_tidy_blocks_on_fresh_other_run_and_lists_stale_ones_as_abandoned(tmp_path):
    # Deleting this lets one run rewrite the ledger under another run that is still using it.
    stale = _constants().STALE_MINUTES
    mine = start(tmp_path, session="a")
    other = start(tmp_path, loop="optimize", session="b")
    r = run(["can-tidy", "--run", mine], state=tmp_path)
    assert r.returncode == 1 and other in r.stderr
    old = datetime.now(timezone.utc) - timedelta(minutes=stale + 1)
    edit(tmp_path, other, heartbeat=iso(old))
    r = run(["can-tidy", "--run", mine], state=tmp_path)
    assert r.returncode == 1
    assert other in r.stderr and "looks abandoned" in r.stderr
    assert run(["finish", "--run", other, "--status", "stopped", "--reason", "x"], state=tmp_path).returncode == 0
    assert run(["can-tidy", "--run", mine], state=tmp_path).returncode == 0


def test_tidy_archives_old_ledger_before_replacing_it(tmp_path):
    # Deleting this lets tidy destroy ledger history with no archived copy.
    run_id = start(tmp_path)
    r = run(["ledger", "--run", run_id, "--lens", "speed", "--idea", "cache the parse",
             "--ev", "0.4", "--status", "open", "--evidence", "profile shows parse hot"], state=tmp_path)
    assert r.returncode == 0, r.stderr
    old = (tmp_path / "ledger.md").read_text()
    new = tmp_path / "new-ledger.md"
    new.write_text("# Ledger\n\ncondensed\n")
    r = run(["tidy", "--run", run_id, "--from", new], state=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "archive" / f"ledger-{run_id}.md").read_text() == old
    assert (tmp_path / "ledger.md").read_text() == new.read_text()


def test_tidy_refused_while_another_run_is_live(tmp_path):
    # Deleting this lets tidy skip its own can-tidy gate.
    mine = start(tmp_path, session="a")
    start(tmp_path, loop="optimize", session="b")
    (tmp_path / "ledger.md").write_text("# Ledger\n\nkeep me\n")
    new = tmp_path / "new.md"
    new.write_text("replaced\n")
    assert run(["tidy", "--run", mine, "--from", new], state=tmp_path).returncode == 1
    assert (tmp_path / "ledger.md").read_text() == "# Ledger\n\nkeep me\n"
    assert not (tmp_path / "archive").exists()


# --- ledger / bookmark ---------------------------------------------------------


def test_ledger_appends_under_one_header_and_rejects_non_numeric_ev(tmp_path):
    # Deleting this lets the ledger lose entries or grow a header per append.
    run_id = start(tmp_path)
    base = ["ledger", "--run", run_id, "--lens", "size", "--status", "kept", "--evidence", "diff"]
    assert run(base + ["--idea", "idea one", "--ev", "1"], state=tmp_path).returncode == 0
    assert run(base + ["--idea", "idea two", "--ev", "-0.5"], state=tmp_path).returncode == 0
    assert run(base + ["--idea", "idea three", "--ev", "lots"], state=tmp_path).returncode == 2
    text = (tmp_path / "ledger.md").read_text()
    assert text.count("# Ledger") == 1
    assert "idea one" in text and "idea two" in text and "idea three" not in text
    assert text.index("idea one") < text.index("idea two")


def test_bookmark_records_lens_and_dep_and_rejects_mixed_forms(tmp_path):
    # Deleting this lets bookmarks.json lose its {lenses, deps} shape.
    assert run(["bookmark", "--lens", "speed", "--commit", "abc"], state=tmp_path).returncode == 0
    assert run(["bookmark", "--dep", "bun", "--release", "1.3.0"], state=tmp_path).returncode == 0
    assert run(["bookmark", "--lens", "speed", "--release", "1"], state=tmp_path).returncode == 2
    data = json.loads((tmp_path / "bookmarks.json").read_text())
    assert data == {"lenses": {"speed": "abc"}, "deps": {"bun": "1.3.0"}}


# --- log -------------------------------------------------------------------------


def test_log_refuses_absolute_and_escaping_paths(repo, tmp_path):
    # Deleting this lets a loop write outside the main checkout through the log command.
    state = tmp_path / "state"
    run_id = start(state, cwd=repo)
    body = tmp_path / "body.md"
    body.write_text("did things\n")
    for bad in ("../outside.md", str(tmp_path / "abs.md"), "internal/../../outside.md"):
        r = run(["log", "--run", run_id, "--path", bad, "--from", body], state=state, cwd=repo)
        assert r.returncode == 2, bad
    assert not (tmp_path / "outside.md").exists() and not (tmp_path / "abs.md").exists()


def test_log_appends_under_run_heading_creating_parents(repo, tmp_path):
    # Deleting this lets the session log lose its per-run heading or a second append.
    state = tmp_path / "state"
    run_id = start(state, cwd=repo)
    body = tmp_path / "body.md"
    body.write_text("did things\n")
    for _ in range(2):
        r = run(["log", "--run", run_id, "--path", "internal/log/log.md", "--from", body], state=state, cwd=repo)
        assert r.returncode == 0, r.stderr
    text = (repo / "internal/log/log.md").read_text()
    assert text.count(f"## {run_id}") == 2 and text.count("did things") == 2


# --- status ------------------------------------------------------------------------


def test_status_lists_runs_with_age_and_unmet_items(tmp_path):
    # Deleting this lets the status summary drop the fields the owner reads to decide.
    run_id = start(tmp_path)
    r = run(["status"], state=tmp_path)
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    assert [row["run_id"] for row in rows] == [run_id]
    row = rows[0]
    assert row["loop"] == "improve" and row["status"] == "running"
    assert isinstance(row["heartbeat_age_minutes"], (int, float))
    assert [u["item"] for u in row["unmet"]] == ["first item", "second item"]
    one = json.loads(run(["status", "--run", run_id], state=tmp_path).stdout)
    assert one["run_id"] == run_id


# --- stop-guard --------------------------------------------------------------------


def test_stop_guard_silent_when_no_record_matches_session(tmp_path):
    # Deleting this lets the guard block sessions that are not running a loop.
    start(tmp_path, session="sess-1")
    r = guard(tmp_path, session="someone-else")
    assert r.returncode == 0 and r.stdout == ""


def test_stop_guard_blocks_with_unmet_items(tmp_path):
    # Deleting this lets a loop end its turn with done items unmet and nothing pushing back.
    run_id = start(tmp_path)
    run(["check", "--run", run_id, "--item", 1, "--evidence", "ok"], state=tmp_path)
    r = guard(tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert "second item" in out["reason"] and "first item" not in out["reason"]
    assert "finish" in out["reason"] and "stopped" in out["reason"]
    assert load(tmp_path, run_id)["continuations"] == 1


def test_stop_guard_stands_down_after_max_continuations(tmp_path):
    # Deleting this lets the guard trap a session in an endless continue loop.
    cap = _constants().MAX_CONTINUATIONS
    run_id = start(tmp_path)
    for _ in range(cap):
        assert json.loads(guard(tmp_path).stdout)["decision"] == "block"
    for _ in range(2):
        r = guard(tmp_path)
        assert r.returncode == 0 and r.stdout == ""
    notes = load(tmp_path, run_id)["notes"]
    assert len(notes) == 1 and "stood down" in notes[0]["text"]


def test_stop_guard_resets_after_heartbeat(tmp_path):
    # Deleting this lets a stand-down become permanent even after the loop shows progress.
    cap = _constants().MAX_CONTINUATIONS
    run_id = start(tmp_path)
    for _ in range(cap + 1):
        guard(tmp_path)
    assert guard(tmp_path).stdout == ""
    assert run(["heartbeat", "--run", run_id], state=tmp_path).returncode == 0
    assert json.loads(guard(tmp_path).stdout)["decision"] == "block"


def test_stop_guard_silent_past_budget_deadline(tmp_path):
    # Deleting this lets the guard keep a session running after its time budget is spent.
    run_id = start(tmp_path)
    edit(tmp_path, run_id, budget_deadline=iso(datetime.now(timezone.utc) - timedelta(minutes=1)))
    r = guard(tmp_path)
    assert r.returncode == 0 and r.stdout == ""
    assert load(tmp_path, run_id)["continuations"] == 0


def test_stop_guard_silent_when_all_items_met(tmp_path):
    # Deleting this lets the guard block a run whose done list is already satisfied.
    run_id = start(tmp_path, done=("only",))
    run(["check", "--run", run_id, "--item", 1, "--evidence", "ok"], state=tmp_path)
    r = guard(tmp_path)
    assert r.returncode == 0 and r.stdout == ""


@pytest.mark.parametrize("stdin", ["not json at all", "", "[1, 2]", '{"session_id": 7}'])
def test_stop_guard_fails_open_on_garbage_stdin(tmp_path, stdin):
    # Deleting this lets malformed hook input crash the guard into a non-zero exit.
    start(tmp_path)
    r = run(["stop-guard"], state=tmp_path, stdin=stdin)
    assert r.returncode == 0 and r.stdout == ""


def _tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_stop_guard_outside_git_repo_is_silent_and_creates_nothing(tmp_path):
    # Deleting this lets the plugin-wide Stop hook write into, or fail in, directories that are not repos.
    plain = tmp_path / "plain"
    plain.mkdir()
    r = run(["stop-guard"], cwd=plain, stdin=json.dumps({"session_id": "s", "cwd": str(plain)}))
    assert r.returncode == 0 and r.stdout == ""
    assert _tree(tmp_path) == ["plain"]


def test_stop_guard_in_repo_without_state_creates_nothing(repo):
    # Deleting this lets every Stop in every repo create .loops/ or edit info/exclude.
    before = _tree(repo)
    exclude = (repo / ".git" / "info" / "exclude").read_bytes()
    r = run(["stop-guard"], cwd=repo, stdin=json.dumps({"session_id": "s", "cwd": str(repo)}))
    assert r.returncode == 0 and r.stdout == ""
    assert _tree(repo) == before
    assert (repo / ".git" / "info" / "exclude").read_bytes() == exclude


def test_stop_guard_finds_custom_state_run_via_pointer_from_worktree(repo, tmp_path):
    # Deleting this lets a flagless Stop hook miss every run started with a custom --state.
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", str(wt), "-b", "loop-branch", cwd=repo)
    custom = tmp_path / "custom"
    start(custom, cwd=wt, session="wt-sess")
    elsewhere = tmp_path / "not-a-repo"
    elsewhere.mkdir()
    r = run(["stop-guard"], cwd=elsewhere, stdin=json.dumps({"session_id": "wt-sess", "cwd": str(wt)}))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["decision"] == "block"


def test_stop_guard_fails_open_on_corrupt_record(tmp_path):
    # Deleting this lets a corrupt state file trap every session that stops.
    run_id = start(tmp_path)
    record_path(tmp_path, run_id).write_text("{truncated")
    r = guard(tmp_path)
    assert r.returncode == 0 and r.stdout == ""
    assert r.stderr


# --- refused writes ------------------------------------------------------------------
#
# The state lands in the main checkout from inside a worktree-isolated session
# only because isolation does not cover a script's file writes today. If that
# changes, the refusal must be loud and name the escape, not a traceback.

needs_non_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores directory permissions"
)


class read_only_tree:
    """Make every directory under root read-only; restore on exit so tmp cleanup works."""

    def __init__(self, root):
        self.dirs = [Path(root), *(p for p in Path(root).rglob("*") if p.is_dir())]

    def __enter__(self):
        for d in self.dirs:
            d.chmod(0o555)
        return self

    def __exit__(self, *exc):
        for d in self.dirs:
            d.chmod(0o755)
        return False


def _names_escape(stderr, path):
    return str(path) in stderr and "--state" in stderr and "LOOP_STATE_DIR" in stderr


@needs_non_root
def test_start_into_read_only_state_exits_3_naming_path_and_escape(tmp_path):
    # Deleting this lets a refused state write surface as a traceback (exit 1) with no way out named.
    state = tmp_path / "state"
    state.mkdir()
    with read_only_tree(state):
        r = run(["start", "--loop", "improve", "--base", "a", "--session", "s", "--budget-minutes", "5",
                 "--done", "x"], state=state)
    assert r.returncode == 3, r.stderr
    assert _names_escape(r.stderr, state), r.stderr
    assert "Traceback" not in r.stderr


@needs_non_root
def test_score_into_read_only_state_exits_3_naming_path_and_escape(tmp_path):
    # Deleting this lets a write refused mid-run (after the lock is taken) escape the exit-3 path.
    run_id = start(tmp_path)
    with read_only_tree(tmp_path):
        r = run(["score", "--run", run_id, "--row", json.dumps(FULL_ROW)], state=tmp_path)
    assert r.returncode == 3, r.stderr
    assert _names_escape(r.stderr, tmp_path / "scoreboard.jsonl"), r.stderr
    assert not (tmp_path / "scoreboard.jsonl").exists()


@needs_non_root
def test_stop_guard_on_read_only_state_exits_0_silently_but_names_escape(tmp_path):
    # Deleting this lets a refused write in the Stop hook trap the session, or fail with no hint why.
    run_id = start(tmp_path)
    with read_only_tree(tmp_path):
        r = guard(tmp_path)
    assert r.returncode == 0 and r.stdout == ""
    assert _names_escape(r.stderr, record_path(tmp_path, run_id)), r.stderr


# --- interpreter floor ---------------------------------------------------------------


def _python39():
    for cand in ("python3.9", "/usr/bin/python3"):
        path = shutil.which(cand)
        if not path:
            continue
        out = subprocess.run([path, "-c", "import sys;print(sys.version_info[:2])"],
                             capture_output=True, text=True)
        if out.stdout.strip() == "(3, 9)":
            return path
    return None


@pytest.mark.skipif(_python39() is None, reason="no python 3.9 interpreter on this machine")
def test_runs_on_python_3_9(tmp_path):
    # Deleting this lets newer-than-3.9 syntax or stdlib calls ship to machines whose python3 is 3.9.
    py = _python39()
    r = run(["start", "--loop", "optimize", "--base", "a", "--session", "s", "--budget-minutes", "5",
             "--done", "x"], state=tmp_path, python=py)
    assert r.returncode == 0, r.stderr
    g = run(["stop-guard"], state=tmp_path, python=py,
            stdin=json.dumps({"session_id": "s", "stop_hook_active": False}))
    assert json.loads(g.stdout)["decision"] == "block", g.stderr
