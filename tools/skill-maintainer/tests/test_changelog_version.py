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


# --- shapes fixed 2026-07-21, previously unpinned ----------------------------
# Each of these was a real defect found by review. None had a test, so all six
# could have silently regressed -- the failure mode this suite exists to prevent.

def _repo(tmp_path, pyproject, changelog):
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


def _failed(results):
    return [r for r in results if not r.passed]


def test_poetry_layout_is_compared_not_rejected(tmp_path):
    """A [tool.poetry] version must be compared, not hard-failed.

    The regex this replaced found it by accident; failing it turned a correct
    changelog into a permanent red row for every non-PEP-621 repo.
    """
    r = _repo(tmp_path, '[tool.poetry]\nname = "x"\nversion = "1.2.3"\n',
              "# changelog\n\n## 1.2.3\n")
    assert not _failed(check_changelog_version(r))


def test_poetry_mismatch_still_fails(tmp_path):
    r = _repo(tmp_path, '[tool.poetry]\nversion = "9.9.9"\n', "# changelog\n\n## 1.2.3\n")
    assert _failed(check_changelog_version(r))


def test_tool_table_above_project_does_not_win(tmp_path):
    """The old regex took the first `version =` anywhere in the file."""
    r = _repo(tmp_path, '[tool.poetry]\nversion = "9.9.9"\n\n[project]\nversion = "1.2.3"\n',
              "# changelog\n\n## 9.9.9\n")
    assert _failed(check_changelog_version(r)), "must compare [project], not the first match"


def test_populated_unreleased_section_passes(tmp_path):
    """The whole point of an Unreleased section is to hold entries.

    Exempting only the heading meant a conventional section still failed on its
    own bullets, so only an empty (unconventional) one passed.
    """
    r = _repo(tmp_path, '[project]\nversion = "1.2.3"\n',
              "# changelog\n\n## [Unreleased]\n\n### Added\n- a pending thing\n\n## [1.2.3] - 2024-01-01\n")
    assert not _failed(check_changelog_version(r))


def test_stray_prose_above_heading_still_fails(tmp_path):
    """The Unreleased exemption must not swallow the bug it sits next to."""
    r = _repo(tmp_path, '[project]\nversion = "1.2.3"\n',
              "# changelog\n\n### fixed\n- orphaned entry\n\n## 1.2.3\n")
    assert _failed(check_changelog_version(r))


def test_keep_a_changelog_heading_is_accepted(tmp_path):
    r = _repo(tmp_path, '[project]\nversion = "1.2.3"\n',
              "# changelog\n\n## [1.2.3] - 2024-01-01\n")
    assert not _failed(check_changelog_version(r))
