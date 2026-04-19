"""On-demand upstream change detection.

Fetches llms-full.txt from Claude Code docs, splits by page,
compares hashes to stored state, prints what changed, and
(new in v0.4.0) retains per-page content snapshots under
.skill-maintainer/state/pages/ so downstream runs can show
line/char deltas instead of just "something changed".
"""

import hashlib
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import httpx

from skill_maintainer.config import (
    append_event,
    get_llms_full_url,
    get_upstream_urls,
    hashes_file,
    load_hashes,
    pages_dir,
    save_hashes,
    url_to_slug,
)


def split_by_source(text: str) -> dict[str, str]:
    """Split llms-full.txt into sections by Source: delimiter."""
    sections = {}
    current_source = None
    current_lines = []

    for line in text.splitlines():
        if line.startswith("Source: "):
            if current_source:
                sections[current_source] = "\n".join(current_lines)
            current_source = line[len("Source: "):].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_source:
        sections[current_source] = "\n".join(current_lines)

    return sections


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def snapshot_path(root: Path, url: str) -> Path:
    return pages_dir(root) / f"{url_to_slug(url)}.md"


def load_snapshot(root: Path, url: str) -> str | None:
    p = snapshot_path(root, url)
    if p.exists():
        return p.read_text()
    return None


def save_snapshot(root: Path, url: str, content: str) -> None:
    p = snapshot_path(root, url)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def compute_delta(old: str | None, new: str) -> dict:
    """Line/char delta summary between old and new content.

    Returns {"lines_added", "lines_removed", "chars_delta", "new"} where
    "new" is True when there is no prior snapshot. Uses multiset (Counter)
    semantics so duplicate lines -- blank lines, repeated headings -- are
    counted correctly rather than collapsed.
    """
    if old is None:
        return {
            "lines_added": len(new.splitlines()),
            "lines_removed": 0,
            "chars_delta": len(new),
            "new": True,
        }
    old_counts = Counter(old.splitlines())
    new_counts = Counter(new.splitlines())
    return {
        "lines_added": sum((new_counts - old_counts).values()),
        "lines_removed": sum((old_counts - new_counts).values()),
        "chars_delta": len(new) - len(old),
        "new": False,
    }


def _log_event(root: Path, changed: list[dict]) -> None:
    append_event(root, {
        "type": "upstream_check",
        "date": date.today().isoformat(),
        "changed_pages": [
            {
                "url": c["url"],
                "status": c["status"],
                "lines_added": c["delta"]["lines_added"],
                "lines_removed": c["delta"]["lines_removed"],
                "chars_delta": c["delta"]["chars_delta"],
            }
            for c in changed
        ],
        "total_changed": len(changed),
    })


def format_delta(d: dict) -> str:
    if d["new"]:
        return f"NEW, +{d['lines_added']} lines, +{d['chars_delta']} chars"
    sign = "+" if d["chars_delta"] >= 0 else ""
    return (
        f"+{d['lines_added']} / -{d['lines_removed']} lines, "
        f"{sign}{d['chars_delta']} chars"
    )


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Check for upstream doc changes.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory (for config/state)")
    parser.add_argument(
        "--url-file", type=Path, default=None,
        help="File with one URL per line to watch (overrides config)",
    )
    parser.add_argument("--no-save", action="store_true", help="Don't update hash state or page snapshots")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    parsed = parser.parse_args(args)

    root = parsed.dir

    # Determine which pages to watch
    if parsed.url_file and parsed.url_file.exists():
        watch_pages = [
            line.strip() for line in parsed.url_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        watch_pages = get_upstream_urls(root)

    llms_url = get_llms_full_url(root)

    # Fetch llms-full.txt
    print("Fetching llms-full.txt...", file=sys.stderr)
    try:
        resp = httpx.get(llms_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error fetching llms-full.txt: {e}", file=sys.stderr)
        sys.exit(1)

    sections = split_by_source(resp.text)
    old_hashes = load_hashes(root)
    new_hashes = dict(old_hashes)
    changed = []

    print(f"Comparing {len(watch_pages)} watched pages...", file=sys.stderr, flush=True)

    # Check each watched page
    for url in watch_pages:
        content = sections.get(url)
        if content is None:
            print(f"  NOT FOUND in llms-full.txt: {url}", file=sys.stderr)
            continue

        new_hash = hash_content(content)
        old_hash = old_hashes.get(url)

        if old_hash is None:
            delta = compute_delta(load_snapshot(root, url), content)
            changed.append({"url": url, "status": "NEW", "hash": new_hash, "delta": delta, "content": content})
        elif old_hash != new_hash:
            old_content = load_snapshot(root, url)
            delta = compute_delta(old_content, content)
            changed.append({
                "url": url, "status": "CHANGED",
                "old_hash": old_hash, "hash": new_hash,
                "delta": delta, "content": content,
            })

        new_hashes[url] = new_hash

    # Report
    watched = len(watch_pages)
    found = sum(1 for u in watch_pages if u in sections)
    print(f"\nWatched: {watched} pages, Found: {found}, Changed: {len(changed)}")
    print()

    if changed:
        for c in changed:
            short_url = c["url"].replace("https://code.claude.com/docs/en/", "")
            print(f"  [{c['status']}] {short_url}  ({format_delta(c['delta'])})")
    else:
        print("  No changes detected.")

    # Save state
    if not parsed.no_save:
        save_hashes(root, new_hashes)
        print(f"\nHashes saved to {hashes_file(root)}", file=sys.stderr)
        # Write snapshots only for changed pages or pages missing a baseline.
        # Skipping unchanged pages avoids bumping mtime on bytes-identical files.
        changed_urls = {c["url"] for c in changed}
        for url in watch_pages:
            content = sections.get(url)
            if content is None:
                continue
            if url in changed_urls or not snapshot_path(root, url).exists():
                save_snapshot(root, url, content)
        print(f"Page snapshots written to {pages_dir(root)}", file=sys.stderr)

    if changed and not parsed.no_log:
        _log_event(root, changed)

    sys.exit(0)
