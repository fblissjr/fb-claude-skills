"""Tests for changelog claim-window scoping.

Header claim: check_changelog_claims audits exactly the newest RELEASE
section -- located by the same fence-aware version-heading logic
check_changelog_version uses, skipping an [Unreleased] section -- and reads
no claim from inside a fenced code block. Delete these and the window can
silently drift: a `## ` line inside a fence ends the section early (so real
claims escape and fenced example claims false-fire), and an Unreleased
section steals the window from the release it sits above.
"""

from skill_maintainer.tests import check_changelog_claims


def _repo(tmp_path, changelog: str):
    (tmp_path / "CHANGELOG.md").write_text(changelog)
    pkg = tmp_path / "foo"
    pkg.mkdir()
    (pkg / "pyproject.toml").write_text(
        '[project]\nname = "foo"\nversion = "2.0.0"\n'
    )
    return tmp_path


def test_fenced_heading_does_not_end_the_window(tmp_path):
    """A `## ` line inside a fence is content, not a section boundary.

    Before the shared extractor, the bare `^## ` slice ended the top section
    at the fenced line: the real claim below the fence escaped unaudited, and
    the bogus example claim inside the fence was audited -- a false fail in
    the direction that gets a check disabled."""
    root = _repo(tmp_path, (
        "# changelog\n\n"
        "## 3.0.0\n\n"
        "An entry quoting a changelog in a code block:\n\n"
        "```\n"
        "## 1.0.0\n"
        "`foo` 0.9.0 -> 1.9.9\n"
        "```\n\n"
        "and the real claim: `foo` 1.0.0 -> 2.0.0 shipped.\n\n"
        "## 2.9.0\n\n"
        "- old entry\n"
    ))
    results = check_changelog_claims(root)
    assert all(r.passed for r in results), [r.detail for r in results]
    assert any(r.name == "foo" for r in results), \
        "the real claim after the fence must still be audited"


def test_unreleased_section_does_not_steal_the_window(tmp_path):
    """The check guards what the changelog says was RELEASED; an Unreleased
    section above it used to become the whole window, so the newest release's
    claims were never read."""
    root = _repo(tmp_path, (
        "# changelog\n\n"
        "## [Unreleased]\n\n"
        "- pending\n\n"
        "## 3.0.0\n\n"
        "shipped: `foo` 1.0.0 -> 2.0.0\n"
    ))
    results = check_changelog_claims(root)
    assert any(r.name == "foo" for r in results), \
        "the newest release section must be the window"
    assert all(r.passed for r in results)


def test_older_sections_stay_unaudited(tmp_path):
    """An old entry describing an old state MUST disagree with today's
    manifests; auditing it would make every historical claim a permanent red."""
    root = _repo(tmp_path, (
        "# changelog\n\n"
        "## 3.0.0\n\n"
        "shipped: `foo` 1.0.0 -> 2.0.0\n\n"
        "## 2.0.0\n\n"
        "shipped: `foo` 0.1.0 -> 0.5.0\n"
    ))
    assert all(r.passed for r in check_changelog_claims(root))


def test_top_section_mismatch_still_fails(tmp_path):
    """The founding specimen: the top section claims a version no manifest
    carries."""
    root = _repo(tmp_path, (
        "# changelog\n\n"
        "## 3.0.0\n\n"
        "shipped: `foo` 1.0.0 -> 9.9.9\n"
    ))
    failed = [r for r in check_changelog_claims(root) if not r.passed]
    assert len(failed) == 1
    assert "9.9.9" in failed[0].detail
