"""Tests for the provenance-join glue inside `test_repo_hygiene` itself.

`test_provenance_join.py` exercises `join_provenance`/`parse_annotations`
directly with hand-built dicts. Nothing exercised the glue around them --
state loading via `load_hashes`, the `local_repos` wiring, the mtime-based
"upstream hash state fresh" arm, and the Result message formatting -- through
`test_repo_hygiene`'s actual code path. A regression in that glue could pass
unnoticed with the pure functions still green.
"""

import os
import time

import orjson

from skill_maintainer.tests import test_repo_hygiene as run_repo_hygiene_checks


def _write_best_practices(root, content):
    d = root / ".skill-maintainer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "best_practices.md").write_text(content, encoding="utf-8")


def _write_hashes(root, hashes):
    d = root / ".skill-maintainer" / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / "upstream_hashes.json").write_bytes(orjson.dumps(hashes))


def _by_check(results):
    return {r.check: r for r in results}


def test_current_citation_via_full_state_loading_path(tmp_path):
    _write_hashes(tmp_path, {"https://code.claude.com/docs/en/skills": "abc123"})
    _write_best_practices(tmp_path, (
        "## Some Section\n"
        "<!-- class: harness | source: https://code.claude.com/docs/en/skills "
        "| verified_hash: abc123 | last_verified: 2026-08-07 -->\n"
    ))
    results = _by_check(run_repo_hygiene_checks(tmp_path))

    prov = results["best_practices provenance"]
    assert prov.passed, prov.detail
    assert "1 current" in prov.detail

    fresh = results["upstream hash state fresh"]
    assert fresh.passed, fresh.detail
    assert "0d ago" in fresh.detail


def test_moved_citation_is_reported_and_fails(tmp_path):
    _write_hashes(tmp_path, {"https://code.claude.com/docs/en/skills": "newhash"})
    _write_best_practices(tmp_path, (
        "## Some Section\n"
        "<!-- class: harness | source: https://code.claude.com/docs/en/skills "
        "| verified_hash: oldhash | last_verified: 2026-04-19 -->\n"
    ))
    results = _by_check(run_repo_hygiene_checks(tmp_path))

    prov = results["best_practices provenance"]
    assert not prov.passed
    assert "1 moved" in prov.detail
    assert "Some Section" in prov.detail


def test_repo_sourced_citation_reads_local_repos_key(tmp_path):
    """`sources.py` writes tracked-repo HEAD SHAs under `local_repos`; the glue
    must pass that namespace through to `join_provenance` as `repos=`."""
    _write_hashes(tmp_path, {"local_repos": {"coderef/agentskills": "abcdef1234567890"}})
    _write_best_practices(tmp_path, (
        "## Repo Section\n"
        "<!-- class: harness | source: coderef/agentskills "
        "| verified_hash: abcdef12 | last_verified: 2026-08-07 -->\n"
    ))
    results = _by_check(run_repo_hygiene_checks(tmp_path))

    prov = results["best_practices provenance"]
    assert prov.passed, prov.detail
    assert "1 current" in prov.detail


def test_missing_hash_state_reports_untracked_and_not_fresh(tmp_path):
    _write_best_practices(tmp_path, (
        "## Some Section\n"
        "<!-- class: harness | source: https://code.claude.com/docs/en/skills "
        "| verified_hash: abc123 | last_verified: 2026-08-07 -->\n"
    ))
    results = _by_check(run_repo_hygiene_checks(tmp_path))

    fresh = results["upstream hash state fresh"]
    assert not fresh.passed
    assert "no upstream_hashes.json" in fresh.detail

    prov = results["best_practices provenance"]
    assert "1 untracked source" in prov.detail


def test_stale_hash_state_is_reported_via_mtime(tmp_path):
    _write_hashes(tmp_path, {"https://code.claude.com/docs/en/skills": "abc123"})
    _write_best_practices(tmp_path, "")
    hashes_file = tmp_path / ".skill-maintainer" / "state" / "upstream_hashes.json"
    forty_days_ago = time.time() - 40 * 86400
    os.utime(hashes_file, (forty_days_ago, forty_days_ago))

    results = _by_check(run_repo_hygiene_checks(tmp_path))
    fresh = results["upstream hash state fresh"]
    assert not fresh.passed
    assert "40d ago" in fresh.detail
    assert "skill-maintain upstream" in fresh.detail
