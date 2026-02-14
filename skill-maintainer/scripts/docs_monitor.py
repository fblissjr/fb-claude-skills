#!/usr/bin/env python3
"""
CDC-style change detection for documentation sources.

Pipeline:
  1. DETECT  -- HEAD request, compare Last-Modified header (zero bytes if unchanged)
  2. IDENTIFY -- fetch llms-full.txt (or HTML fallback), split into pages, hash each
  3. CLASSIFY -- keyword heuristic on diff text (breaking/additive/cosmetic)

State is stored in DuckDB via the Store class. Backward-compatible state.json
is exported after each run.

Usage:
    uv run python skill-maintainer/scripts/docs_monitor.py
    uv run python skill-maintainer/scripts/docs_monitor.py --source anthropic-skills-docs
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")

CHANGE_KEYWORDS_BREAKING = [
    "removed", "breaking", "deprecated", "no longer", "must now",
    "required", "mandatory",
]
CHANGE_KEYWORDS_ADDITIVE = [
    "new", "added", "now supports", "introducing", "optional",
    "can now", "also",
]

# Regex to split llms-full.txt into per-page sections.
# Each page starts with a markdown heading followed by "Source: <url>".
_PAGE_SPLIT = re.compile(r"^(?=# .+\nSource: https?://)", re.MULTILINE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Layer 1: DETECT -- did the source change at all?
# ---------------------------------------------------------------------------

def detect_change(
    bundle_url: str,
    stored_watermark: dict,
    timeout: float = 10.0,
) -> tuple[bool, dict]:
    """HEAD request to check Last-Modified / ETag.

    Returns (changed: bool, new_watermark: dict).
    If the server doesn't support conditional headers, returns changed=True
    so we always fall through to identify.
    """
    try:
        resp = httpx.head(bundle_url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        # Can't reach server -- assume changed so identify step fetches
        return True, stored_watermark

    last_modified = resp.headers.get("last-modified", "")
    etag = resp.headers.get("etag", "")

    new_watermark = {
        "last_modified": last_modified,
        "etag": etag,
        "last_checked": _now_iso(),
    }

    if not last_modified and not etag:
        # No caching headers -- can't detect, always fetch
        return True, new_watermark

    old_lm = stored_watermark.get("last_modified", "")
    old_etag = stored_watermark.get("etag", "")

    changed = (last_modified != old_lm) or (etag != old_etag)
    return changed, new_watermark


# ---------------------------------------------------------------------------
# Layer 2: IDENTIFY -- what pages changed?
# ---------------------------------------------------------------------------

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _parse_llms_full(text: str) -> dict[str, str]:
    """Split llms-full.txt into {source_url: page_content}."""
    pages = {}
    sections = _PAGE_SPLIT.split(text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n", 2)
        if len(lines) < 2:
            continue
        source_line = lines[1]
        if not source_line.startswith("Source: "):
            continue
        url = source_line[len("Source: "):].strip()
        content = lines[2].strip() if len(lines) > 2 else ""
        pages[url] = content
    return pages


def identify_changes(
    bundle_url: str,
    watched_pages: list[str],
    stored_pages: dict,
    timeout: float = 30.0,
) -> list[dict]:
    """Fetch the bundle, split into pages, compare hashes to stored state.

    Args:
        bundle_url: URL to llms-full.txt
        watched_pages: list of page URLs we care about (empty = all)
        stored_pages: {url: {hash, content_preview, last_changed}} from Store

    Returns:
        list of change dicts with url, old_hash, new_hash, old_content, new_content, content_preview
    """
    resp = httpx.get(bundle_url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()

    all_pages = _parse_llms_full(resp.text)

    # Filter to watched pages if specified
    if watched_pages:
        pages = {url: content for url, content in all_pages.items()
                 if url in watched_pages}
    else:
        pages = all_pages

    changes = []
    for url, content in pages.items():
        page_hash = _hash(content)
        old = stored_pages.get(url, {})
        old_hash = old.get("hash", "")

        if page_hash != old_hash:
            changes.append({
                "url": url,
                "old_hash": old_hash,
                "new_hash": page_hash,
                "old_content": old.get("content_preview", ""),
                "new_content": content,
                "content_preview": content[:3000],
            })

    return changes


# ---------------------------------------------------------------------------
# Layer 3: CLASSIFY -- breaking / additive / cosmetic
# ---------------------------------------------------------------------------

def classify_change(old_content: str, new_content: str) -> str:
    if not old_content:
        return "ADDITIVE"

    old_lines = set(old_content.splitlines())
    new_lines = set(new_content.splitlines())
    diff_text = " ".join(new_lines - old_lines | old_lines - new_lines).lower()

    for kw in CHANGE_KEYWORDS_BREAKING:
        if kw in diff_text:
            return "BREAKING"
    for kw in CHANGE_KEYWORDS_ADDITIVE:
        if kw in diff_text:
            return "ADDITIVE"
    return "COSMETIC"


def diff_summary(old_content: str, new_content: str) -> str:
    if not old_content:
        return "initial capture"
    old_lines = set(old_content.splitlines())
    new_lines = set(new_content.splitlines())
    added = len(new_lines - old_lines)
    removed = len(old_lines - new_lines)
    return f"+{added} -{removed} lines"


# ---------------------------------------------------------------------------
# Local file hash (PDF, etc.)
# ---------------------------------------------------------------------------

def check_local_file(file_path: Path, stored_hash: str) -> dict | None:
    """Check a local file for changes. Returns change dict or None."""
    if not file_path.exists():
        return None
    new_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if new_hash == stored_hash:
        return None
    return {
        "url": f"file://{file_path}",
        "old_hash": stored_hash,
        "new_hash": new_hash,
        "classification": "ADDITIVE",
        "summary": "local file changed" if stored_hash else "initial capture",
    }


# ---------------------------------------------------------------------------
# Source-level orchestration (using Store)
# ---------------------------------------------------------------------------

def check_source(
    source_name: str,
    source_config: dict,
    store: Store,
) -> list[dict]:
    """Run the full CDC pipeline for one docs source.

    Returns list of classified change dicts.
    """
    changes = []
    bundle_url = source_config.get("llms_full_url")
    watched_pages = source_config.get("pages", [])
    hash_file_path = source_config.get("hash_file")

    if bundle_url:
        # Layer 1: DETECT
        stored_wm = store.get_latest_watermark(source_name) or {}
        changed, new_watermark = detect_change(bundle_url, stored_wm)

        # Record watermark check
        store.record_watermark_check(
            source_name,
            last_modified=new_watermark.get("last_modified", ""),
            etag=new_watermark.get("etag", ""),
            changed=changed,
        )

        if not changed:
            print("  no change (Last-Modified match)", file=sys.stderr)
            return []

        # Layer 2: IDENTIFY
        stored_pages = store.get_all_page_hashes(source_name)
        try:
            page_changes = identify_changes(
                bundle_url, watched_pages, stored_pages,
            )
        except Exception as e:
            store.record_change(
                source_name,
                classification="ERROR",
                summary=f"fetch failed: {e}",
            )
            return [{
                "source": source_name,
                "url": bundle_url,
                "classification": "ERROR",
                "old_hash": "", "new_hash": "",
                "summary": f"fetch failed: {e}",
            }]

        # Layer 3: CLASSIFY + record
        for pc in page_changes:
            classification = classify_change(pc["old_content"], pc["new_content"])
            summary = diff_summary(pc["old_content"], pc["new_content"])

            store.record_change(
                source_name,
                classification=classification,
                old_hash=pc["old_hash"],
                new_hash=pc["new_hash"],
                summary=summary,
                content_preview=pc["content_preview"],
                page_url=pc["url"],
            )

            changes.append({
                "source": source_name,
                "url": pc["url"],
                "classification": classification,
                "old_hash": pc["old_hash"],
                "new_hash": pc["new_hash"],
                "summary": summary,
            })

    # Local file hash (PDF, etc.)
    if hash_file_path:
        fpath = Path(hash_file_path)
        fh = store.get_file_hash(source_name)
        old_fhash = fh["hash"] if fh else ""
        fc = check_local_file(fpath, old_fhash)
        if fc:
            fc["source"] = source_name
            changes.append(fc)
            store.record_change(
                source_name,
                classification=fc["classification"],
                old_hash=fc["old_hash"],
                new_hash=fc["new_hash"],
                summary=fc["summary"],
            )

    return changes


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def generate_report(all_changes: list[dict]) -> str:
    lines = [
        "# Documentation Change Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not all_changes:
        lines.append("No changes detected.")
        return "\n".join(lines)

    by_class = {}
    for c in all_changes:
        by_class.setdefault(c["classification"], []).append(c)

    for label in ["BREAKING", "ADDITIVE", "COSMETIC", "ERROR"]:
        items = by_class.get(label, [])
        if not items:
            continue
        lines.append(f"## {label} Changes")
        lines.append("")
        for c in items:
            lines.append(f"- **{c['source']}**: {c['url']}")
            lines.append(f"  - {c['summary']}")
            if label == "BREAKING":
                lines.append(
                    f"  - hash: `{c['old_hash'][:12]}` -> `{c['new_hash'][:12]}`"
                )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="CDC-style change detection for documentation sources."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
        help="Path to export backward-compatible state.json",
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Check only this source (by name from config)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    with Store(db_path=args.db, config_path=args.config) as store:
        all_changes = []
        sources = config.get("sources", {})

        for name, src_config in sources.items():
            if src_config.get("type") != "docs":
                continue
            if args.source and name != args.source:
                continue

            print(f"Checking {name}...", file=sys.stderr, flush=True)
            changes = check_source(name, src_config, store)
            all_changes.extend(changes)

            if changes:
                print(
                    f"  {len(changes)} change(s) detected", file=sys.stderr,
                )
            else:
                print("  no changes", file=sys.stderr)

        # Export backward-compatible state.json
        store.export_state_json_file(args.state)

    report = generate_report(all_changes)
    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
