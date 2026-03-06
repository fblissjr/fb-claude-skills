"""On-demand upstream change detection.

Fetches llms-full.txt from Claude Code docs, splits by page,
compares hashes to stored state, prints what changed.
"""

import hashlib
import sys
from datetime import date
from pathlib import Path

import httpx

from skill_maintainer.config import (
    append_event,
    get_llms_full_url,
    get_upstream_urls,
    hashes_file,
    load_hashes,
    save_hashes,
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


def _log_event(root: Path, changed: list[dict]) -> None:
    append_event(root, {
        "type": "upstream_check",
        "date": date.today().isoformat(),
        "changed_pages": [c["url"] for c in changed],
        "total_changed": len(changed),
    })


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Check for upstream doc changes.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory (for config/state)")
    parser.add_argument(
        "--url-file", type=Path, default=None,
        help="File with one URL per line to watch (overrides config)",
    )
    parser.add_argument("--no-save", action="store_true", help="Don't update hash state")
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
            changed.append({"url": url, "status": "NEW", "hash": new_hash})
        elif old_hash != new_hash:
            changed.append({"url": url, "status": "CHANGED", "old_hash": old_hash, "hash": new_hash})

        new_hashes[url] = new_hash

    # Report
    watched = len(watch_pages)
    found = sum(1 for u in watch_pages if u in sections)
    print(f"\nWatched: {watched} pages, Found: {found}, Changed: {len(changed)}")
    print()

    if changed:
        for c in changed:
            short_url = c["url"].replace("https://code.claude.com/docs/en/", "")
            print(f"  [{c['status']}] {short_url}")
    else:
        print("  No changes detected.")

    # Save state
    if not parsed.no_save:
        save_hashes(root, new_hashes)
        print(f"\nHashes saved to {hashes_file(root)}", file=sys.stderr)

    if changed and not parsed.no_log:
        _log_event(root, changed)

    sys.exit(0)
