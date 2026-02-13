#!/usr/bin/env python3
"""
CDC-style change detection for documentation sources.

Pipeline:
  1. DETECT  -- HEAD request, compare Last-Modified header (zero bytes if unchanged)
  2. IDENTIFY -- fetch llms-full.txt (or HTML fallback), split into pages, hash each
  3. CLASSIFY -- keyword heuristic on diff text (breaking/additive/cosmetic)

Each source carries its own watermark (last_modified, etag, page hashes) in state.json.

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
import orjson
import yaml


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
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


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    data = state_path.read_bytes()
    if not data or data.strip() == b"{}":
        return {}
    return orjson.loads(data)


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))


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
) -> tuple[list[dict], dict]:
    """Fetch the bundle, split into pages, compare hashes to stored state.

    Args:
        bundle_url: URL to llms-full.txt
        watched_pages: list of page URLs we care about (empty = all)
        stored_pages: {url: {hash, content_preview, last_changed}} from state

    Returns:
        (changes, new_pages_state)
        changes: list of dicts with source_url, old_hash, new_hash, content
        new_pages_state: updated page state to store
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
    new_state = {}
    now = _now_iso()

    for url, content in pages.items():
        page_hash = _hash(content)
        old = stored_pages.get(url, {})
        old_hash = old.get("hash", "")

        new_state[url] = {
            "hash": page_hash,
            "content_preview": content[:3000],
            "last_checked": now,
            "last_changed": old.get("last_changed", now) if page_hash == old_hash
                else now,
        }

        if page_hash != old_hash:
            changes.append({
                "url": url,
                "old_hash": old_hash,
                "new_hash": page_hash,
                "old_content": old.get("content_preview", ""),
                "new_content": content,
            })

    return changes, new_state


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
# Source-level orchestration
# ---------------------------------------------------------------------------

def check_source(
    source_name: str,
    source_config: dict,
    state: dict,
) -> list[dict]:
    """Run the full CDC pipeline for one docs source.

    Returns list of classified change dicts.
    """
    source_state = state.setdefault("docs", {}).setdefault(source_name, {})
    changes = []

    bundle_url = source_config.get("llms_full_url")
    watched_pages = source_config.get("pages", [])
    hash_file_path = source_config.get("hash_file")

    if bundle_url:
        # Layer 1: DETECT
        watermark = source_state.get("_watermark", {})
        changed, new_watermark = detect_change(bundle_url, watermark)
        source_state["_watermark"] = new_watermark

        if not changed:
            print("  no change (Last-Modified match)", file=sys.stderr)
            source_state["_watermark"]["last_checked"] = _now_iso()
            return []

        # Layer 2: IDENTIFY
        stored_pages = source_state.get("_pages", {})
        try:
            page_changes, new_pages = identify_changes(
                bundle_url, watched_pages, stored_pages,
            )
        except Exception as e:
            return [{
                "source": source_name,
                "url": bundle_url,
                "classification": "ERROR",
                "old_hash": "", "new_hash": "",
                "summary": f"fetch failed: {e}",
            }]

        source_state["_pages"] = new_pages

        # Layer 3: CLASSIFY
        for pc in page_changes:
            classification = classify_change(pc["old_content"], pc["new_content"])
            changes.append({
                "source": source_name,
                "url": pc["url"],
                "classification": classification,
                "old_hash": pc["old_hash"],
                "new_hash": pc["new_hash"],
                "summary": diff_summary(pc["old_content"], pc["new_content"]),
            })

    # Local file hash (PDF, etc.)
    if hash_file_path:
        fpath = Path(hash_file_path)
        old_fhash = source_state.get("_file_hash", "")
        fc = check_local_file(fpath, old_fhash)
        if fc:
            fc["source"] = source_name
            changes.append(fc)
            source_state["_file_hash"] = fc["new_hash"]
            source_state["_file_last_checked"] = _now_iso()

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

def main():
    parser = argparse.ArgumentParser(
        description="CDC-style change detection for documentation sources."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
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
    state = load_state(args.state)

    all_changes = []
    sources = config.get("sources", {})

    for name, src_config in sources.items():
        if src_config.get("type") != "docs":
            continue
        if args.source and name != args.source:
            continue

        print(f"Checking {name}...", file=sys.stderr, flush=True)
        changes = check_source(name, src_config, state)
        all_changes.extend(changes)

        if changes:
            print(
                f"  {len(changes)} change(s) detected", file=sys.stderr,
            )
        else:
            print("  no changes", file=sys.stderr)

    save_state(args.state, state)

    report = generate_report(all_changes)
    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
