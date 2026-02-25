#!/usr/bin/env python3
"""
On-demand upstream change detection.

Fetches llms-full.txt from Claude Code docs, splits by page,
compares hashes to state/upstream_hashes.json, prints what changed.

Usage:
    uv run python skill-maintainer/scripts/check_upstream.py
    uv run python skill-maintainer/scripts/check_upstream.py --url-file upstream_urls.txt
"""

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

import httpx
import orjson

LLMS_FULL_URL = "https://code.claude.com/docs/llms-full.txt"
HASHES_FILE = Path("skill-maintainer/state/upstream_hashes.json")
CHANGES_LOG = Path("skill-maintainer/state/changes.jsonl")

# Default pages to watch (from the old config.yaml)
DEFAULT_PAGES = [
    "https://code.claude.com/docs/en/skills",
    "https://code.claude.com/docs/en/plugins",
    "https://code.claude.com/docs/en/plugins-reference",
    "https://code.claude.com/docs/en/discover-plugins",
    "https://code.claude.com/docs/en/plugin-marketplaces",
    "https://code.claude.com/docs/en/hooks-guide",
    "https://code.claude.com/docs/en/hooks",
    "https://code.claude.com/docs/en/sub-agents",
    "https://code.claude.com/docs/en/memory",
]


def load_hashes() -> dict:
    if HASHES_FILE.exists():
        return orjson.loads(HASHES_FILE.read_bytes())
    return {}


def save_hashes(hashes: dict) -> None:
    HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASHES_FILE.write_bytes(orjson.dumps(hashes, option=orjson.OPT_INDENT_2))


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


def append_to_log(changed: list[dict]) -> None:
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "type": "upstream_check",
        "date": date.today().isoformat(),
        "changed_pages": [c["url"] for c in changed],
        "total_changed": len(changed),
    }
    with open(CHANGES_LOG, "ab") as f:
        f.write(orjson.dumps(event) + b"\n")


def main():
    parser = argparse.ArgumentParser(description="Check for upstream doc changes.")
    parser.add_argument(
        "--url-file", type=Path, default=None,
        help="File with one URL per line to watch (default: built-in list)",
    )
    parser.add_argument("--no-save", action="store_true", help="Don't update hash state")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    args = parser.parse_args()

    # Determine which pages to watch
    if args.url_file and args.url_file.exists():
        watch_pages = [
            line.strip() for line in args.url_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        watch_pages = DEFAULT_PAGES

    # Fetch llms-full.txt
    print("Fetching llms-full.txt...", file=sys.stderr)
    try:
        resp = httpx.get(LLMS_FULL_URL, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error fetching llms-full.txt: {e}", file=sys.stderr)
        sys.exit(1)

    sections = split_by_source(resp.text)
    old_hashes = load_hashes()
    new_hashes = dict(old_hashes)
    changed = []

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
    if not args.no_save:
        save_hashes(new_hashes)
        print(f"\nHashes saved to {HASHES_FILE}", file=sys.stderr)

    if changed and not args.no_log:
        append_to_log(changed)

    sys.exit(0)


if __name__ == "__main__":
    main()
