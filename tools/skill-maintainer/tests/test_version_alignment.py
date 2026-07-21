"""Tests for repo-wide plugin/marketplace version alignment.

`path-privacy` sat at 0.1.1 in marketplace.json while its plugin.json had
reached 0.1.6 -- five releases during which installs resolved a stale version.
The pre-commit hook only compares plugins whose files a commit happens to touch,
so nothing ever looked at the repo as a whole. This check does.
"""

import orjson

from skill_maintainer.tests import check_version_alignment


def _write_plugin(root, name, version, source=None):
    d = root / name
    (d / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (d / ".claude-plugin" / "plugin.json").write_bytes(
        orjson.dumps({"name": name, "version": version})
    )
    return {"name": name, "source": source or f"./{name}", "version": version}


def _write_marketplace(root, entries):
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_bytes(
        orjson.dumps({"plugins": entries})
    )


def test_aligned_versions_pass(tmp_path):
    e = _write_plugin(tmp_path, "alpha", "1.2.3")
    _write_marketplace(tmp_path, [e])
    results = check_version_alignment(tmp_path)
    assert all(r.passed for r in results), [r.detail for r in results if not r.passed]


def test_detects_marketplace_behind_plugin_json(tmp_path):
    """The exact path-privacy failure: marketplace stale, plugin.json ahead."""
    e = _write_plugin(tmp_path, "alpha", "0.1.6")
    e["version"] = "0.1.1"
    _write_marketplace(tmp_path, [e])
    results = check_version_alignment(tmp_path)
    failed = [r for r in results if not r.passed]
    assert len(failed) == 1
    assert "0.1.1" in failed[0].detail and "0.1.6" in failed[0].detail


def test_detects_plugin_missing_from_marketplace(tmp_path):
    _write_plugin(tmp_path, "alpha", "1.0.0")
    _write_marketplace(tmp_path, [])
    results = check_version_alignment(tmp_path)
    assert any(not r.passed and "not in marketplace" in r.detail for r in results)


def test_detects_marketplace_entry_with_no_plugin(tmp_path):
    """A marketplace entry whose source does not exist -- a rename or deletion."""
    _write_marketplace(tmp_path, [{"name": "ghost", "source": "./ghost", "version": "1.0.0"}])
    results = check_version_alignment(tmp_path)
    assert any(not r.passed and "does not exist" in r.detail for r in results)


def test_no_marketplace_is_not_a_failure(tmp_path):
    """A plugin repo without a marketplace is legitimate; do not invent failures."""
    _write_plugin(tmp_path, "alpha", "1.0.0")
    assert check_version_alignment(tmp_path) == []


def test_reports_every_drifted_plugin_not_just_the_first(tmp_path):
    a = _write_plugin(tmp_path, "alpha", "1.0.0")
    b = _write_plugin(tmp_path, "beta", "2.0.0")
    a["version"] = "0.9.0"
    b["version"] = "1.9.0"
    _write_marketplace(tmp_path, [a, b])
    failed = [r for r in check_version_alignment(tmp_path) if not r.passed]
    assert len(failed) == 2


def test_source_with_dot_directory_resolves(tmp_path):
    """`lstrip('./')` strips a character SET, not a prefix.

    A source of `./.claude/thing` became `claude/thing`, so the check reported
    "plugin.json does not exist" while pointing at a path that was never right
    -- sending someone to look for a missing file rather than a mangled path.
    """
    d = tmp_path / ".claude" / "thing"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_bytes(
        orjson.dumps({"name": "thing", "version": "1.0.0"})
    )
    _write_marketplace(tmp_path, [
        {"name": "thing", "source": "./.claude/thing", "version": "1.0.0"}
    ])
    failed = [r for r in check_version_alignment(tmp_path) if not r.passed]
    assert not failed, [r.detail for r in failed]


def test_unreadable_manifest_in_reverse_sweep_is_reported(tmp_path):
    """A malformed plugin.json must not make a plugin invisible.

    The forward loop reports an unreadable manifest; the reverse loop used to
    `continue` past it, so a corrupt manifest silently removed the plugin from
    the very check meant to catch plugins nobody can install -- and the check
    then reported green.
    """
    d = tmp_path / "broken"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_text("{ not valid json")
    _write_marketplace(tmp_path, [])
    failed = [r for r in check_version_alignment(tmp_path) if not r.passed]
    assert any("unreadable" in r.detail or "broken" in r.detail for r in failed), \
        f"corrupt manifest was silently skipped: {[r.detail for r in failed]}"
