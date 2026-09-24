"""`skill-maintain lint` scans the files a reader treats as the repo's hub.

Claim: when a repo moves its instructions from CLAUDE.md into AGENTS.md (with
CLAUDE.md reduced to an `@AGENTS.md` import), count-drift and broken-link
checks still read the file that holds the prose. Deleting this test lets the
scan list regress to CLAUDE.md alone, which then checks a one-line import and
reports clean over content it never opened -- the state this repo was in on
2026-09-24.
"""

from pathlib import Path

from skill_maintainer.lint import lint_scan_files


def _touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")


def test_agents_md_is_scanned(tmp_path):
    # The hub moved: AGENTS.md holds the prose, CLAUDE.md only imports it.
    _touch(tmp_path, "AGENTS.md")
    _touch(tmp_path, "CLAUDE.md")
    names = {p.name for p in lint_scan_files(tmp_path)}
    assert {"AGENTS.md", "CLAUDE.md"} <= names


def test_internals_docs_are_still_scanned(tmp_path):
    # Guards the refactor itself: extracting the list must not drop the spokes.
    _touch(tmp_path, "docs/internals/topic.md")
    paths = lint_scan_files(tmp_path)
    assert tmp_path / "docs/internals/topic.md" in paths
