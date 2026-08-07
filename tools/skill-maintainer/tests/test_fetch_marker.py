"""The freshness arm must date a FETCH, not a file several writers touch.

Claim: `upstream hash state fresh` existed to date the state the provenance
join trusts. It read the mtime of `upstream_hashes.json` — but `sources.py`
rewrites that same file on every run (`all_hashes["local_repos"] = ...;
save_hashes(...)`) while fetching zero documentation pages. So a `skill-maintain
sources` run, which is nothing but git pulls, reset the clock for another 30
days.

Specimen, 2026-08-07: the arm was shipped and its green reported as evidence it
worked. It read `fetched 0d ago` because `skill-maintain sources` had been run
minutes earlier. The number was an artifact of a git pull, not of any fetch.

`fetch_marker` is written by exactly one caller, `upstream.py`, and only after a
successful fetch. One writer is the whole point: a timestamp several writers
touch cannot answer "when did we last fetch".

Deleting `test_marker_is_not_written_by_other_state_writes` removes the only
thing pinning that separation, and the arm silently returns to dating the wrong
event.
"""

from datetime import date, timedelta

from skill_maintainer.config import (
    fetch_marker,
    load_fetch_date,
    record_fetch,
    save_hashes,
)


def test_record_and_load_roundtrip(tmp_path):
    record_fetch(tmp_path)
    assert load_fetch_date(tmp_path) == date.today()


def test_absent_marker_reads_none(tmp_path):
    """No marker must be distinguishable from a fresh fetch, never assumed fresh."""
    assert load_fetch_date(tmp_path) is None


def test_marker_is_not_written_by_other_state_writes(tmp_path):
    """`sources.py` writes hash state; that must not look like a fetch.

    This is the arm that matters. If `save_hashes` ever starts touching the
    marker — or the arm goes back to reading the hash file's mtime — a
    git-pull-only run resets the freshness clock again.
    """
    save_hashes(tmp_path, {"local_repos": {"coderef/x": "abc"}})
    assert not fetch_marker(tmp_path).exists()
    assert load_fetch_date(tmp_path) is None


def test_corrupt_marker_reads_none_rather_than_raising(tmp_path):
    """A hand-mangled marker must degrade to "unknown", not crash the suite.

    `test_repo_hygiene` has no exception boundary around this call, so raising
    here would take out every other repo arm — the failure mode the review
    found in the `stat()` narrowing on the previous implementation.
    """
    fetch_marker(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    fetch_marker(tmp_path).write_text("not-a-date", encoding="utf-8")
    assert load_fetch_date(tmp_path) is None


def test_stale_marker_reports_its_age(tmp_path):
    fetch_marker(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    old = (date.today() - timedelta(days=45)).isoformat()
    fetch_marker(tmp_path).write_text(old, encoding="utf-8")
    loaded = load_fetch_date(tmp_path)
    assert loaded is not None
    assert (date.today() - loaded).days == 45
