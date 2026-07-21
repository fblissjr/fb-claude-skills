"""Tests for changelog/version agreement.

Proposed during cross-review after a changelog edit dropped its version heading
and left the repo version unbumped -- two failures nothing in the repo would
have caught. Both violate one exact comparison: the top `## X.Y.Z` heading must
equal the root pyproject version. Exact, so it can legitimately gate; no
threshold and no judgement.
"""

from skill_maintainer.tests import check_changelog_version


def _write(tmp_path, changelog: str | None, version: str | None):
    if changelog is not None:
        (tmp_path / "CHANGELOG.md").write_text(changelog)
    if version is not None:
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\nname = "x"\nversion = "{version}"\n'
        )
    return tmp_path


def test_matching_version_passes(tmp_path):
    _write(tmp_path, "# changelog\n\n## 1.2.3\n\n- thing\n", "1.2.3")
    assert all(r.passed for r in check_changelog_version(tmp_path))


def test_version_bumped_without_changelog_entry_fails(tmp_path):
    """The repo version moved and the changelog did not."""
    _write(tmp_path, "# changelog\n\n## 1.2.3\n\n- thing\n", "1.3.0")
    failed = [r for r in check_changelog_version(tmp_path) if not r.passed]
    assert len(failed) == 1
    assert "1.3.0" in failed[0].detail and "1.2.3" in failed[0].detail


def test_dropped_version_heading_fails(tmp_path):
    """The exact failure that prompted this: an insert matched `# changelog`
    instead of the version heading, so the entry landed with no version."""
    _write(tmp_path, "# changelog\n\n### fixed\n- thing\n\n## 1.2.3\n", "1.3.0")
    failed = [r for r in check_changelog_version(tmp_path) if not r.passed]
    assert failed, "an entry above the top version heading should not pass"


def test_missing_files_are_not_failures(tmp_path):
    """A repo without a changelog is legitimate; do not invent failures."""
    assert check_changelog_version(tmp_path) == []
    _write(tmp_path, "# changelog\n\n## 1.0.0\n", None)
    assert check_changelog_version(tmp_path) == []


def test_changelog_with_no_version_heading_fails(tmp_path):
    _write(tmp_path, "# changelog\n\nnothing here\n", "1.0.0")
    failed = [r for r in check_changelog_version(tmp_path) if not r.passed]
    assert failed
