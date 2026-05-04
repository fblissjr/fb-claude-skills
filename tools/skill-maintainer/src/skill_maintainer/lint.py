"""Lint the doc tree: orphan detection, count drift, and link-rot.

This is the wiki-sanity pass: catches files that exist on disk but aren't linked from any
index, prose claims like "16 reports" that disagree with the filesystem, and markdown
links pointing at files that don't exist. All three are soft findings -- exit 0 always.
The lint pass runs on demand (`skill-maintain lint`), not on every commit.
Cross-reference suggestions and stale-claim heuristics are deferred to a future minor.
"""

import re
import sys
from pathlib import Path


ANALYSIS_DIR = Path("docs/analysis")
INDEX_FILES = [Path("docs/README.md"), Path("docs/analysis/index.md")]


def find_orphans(root: Path) -> list[str]:
    """Files in docs/analysis/ not linked from any index file."""
    analysis_dir = root / ANALYSIS_DIR
    if not analysis_dir.exists():
        return []

    candidates = sorted(p.name for p in analysis_dir.glob("*.md"))
    candidates = [f for f in candidates if f not in {"index.md", "log.md"}]

    linked: set[str] = set()
    for index_path in INDEX_FILES:
        full = root / index_path
        if not full.exists():
            continue
        text = full.read_text(encoding="utf-8")
        for match in re.finditer(r"analysis/([\w_-]+\.md)", text):
            linked.add(match.group(1))

    return [f for f in candidates if f not in linked]


def _count_analysis_reports(root: Path) -> int:
    return sum(
        1 for p in (root / "docs/analysis").glob("*.md")
        if p.name not in {"index.md", "log.md"}
    )


def _count_captured_docs(root: Path) -> int:
    return sum(1 for _ in (root / "docs/claude-docs").glob("*.md"))


COUNT_PATTERNS = [
    (re.compile(r"\b(\d+)\s+domain reports\b", re.IGNORECASE), "domain reports", _count_analysis_reports),
    (re.compile(r"\b(\d+)\s+captured (?:upstream )?docs\b", re.IGNORECASE), "captured docs", _count_captured_docs),
    (re.compile(r"\b(\d+)\s+reports covering\b", re.IGNORECASE), "reports covering", _count_analysis_reports),
]


MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _safe_read(path: Path) -> str | None:
    """Read file text or return None on any I/O failure. Honors the lint contract that
    unreadable files don't crash the pass (exit 0 always)."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def find_broken_links(root: Path, scan_files: list[Path]) -> list[tuple[Path, int, str]]:
    """Markdown links pointing at files that don't exist on disk.

    Skips URLs (`http://`, `https://`, `mailto:`) and pure anchor links (`#section`).
    Resolves relative links against the file containing them. Anchor fragments are
    stripped before existence checks.
    """
    findings = []
    for path in scan_files:
        text = _safe_read(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in MARKDOWN_LINK.finditer(line):
                target = m.group(1).strip()
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target_path = target.split("#", 1)[0]
                if not target_path:
                    continue
                resolved = (path.parent / target_path).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    # Link escapes the repo root; skip rather than flag.
                    continue
                if not resolved.exists():
                    findings.append((path, line_no, target))
    return findings


def find_count_drift(root: Path, scan_files: list[Path]) -> list[tuple[Path, int, str, int, int]]:
    """Return (file, line_no, label, claimed, actual) tuples where counts disagree.

    Counter results are memoized per-call: a single glob per distinct counter, regardless
    of how many lines or files match the pattern bound to it.
    """
    findings = []
    actual_cache: dict[int, int] = {}
    for path in scan_files:
        text = _safe_read(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern, label, counter in COUNT_PATTERNS:
                m = pattern.search(line)
                if not m:
                    continue
                claimed = int(m.group(1))
                actual = actual_cache.setdefault(id(counter), counter(root))
                if claimed != actual:
                    findings.append((path, line_no, label, claimed, actual))
    return findings


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Lint the doc tree: orphan detection + count drift. Soft findings only -- exit 0 always."
    )
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory (default: .)")
    parsed = parser.parse_args(args)

    root = parsed.dir.resolve()

    print(f"# skill-maintain lint -- {root}\n")

    orphans = find_orphans(root)
    print("## Orphans in docs/analysis/\n")
    if orphans:
        for f in orphans:
            print(f"  - {f} (not linked from docs/README.md or docs/analysis/index.md)")
    else:
        print("  (none)")
    print()

    scan_files = [
        root / "README.md",
        root / "CLAUDE.md",
        root / "docs/README.md",
    ]
    internals = root / "docs/internals"
    if internals.exists():
        scan_files += sorted(internals.glob("*.md"))

    findings = find_count_drift(root, scan_files)
    print("## Count drift\n")
    if findings:
        for path, line_no, label, claimed, actual in findings:
            rel = path.relative_to(root)
            print(f"  - {rel}:{line_no} -- claims {claimed} {label}, filesystem has {actual}")
    else:
        print("  (none)")
    print()

    link_scan_files = list(scan_files)
    analysis = root / "docs/analysis"
    if analysis.exists():
        link_scan_files += sorted(analysis.glob("*.md"))
    link_scan_files += [root / "VISION.md"]

    broken = find_broken_links(root, link_scan_files)
    print("## Broken markdown links\n")
    if broken:
        for path, line_no, target in broken:
            rel = path.relative_to(root)
            print(f"  - {rel}:{line_no} -- {target}")
    else:
        print("  (none)")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
