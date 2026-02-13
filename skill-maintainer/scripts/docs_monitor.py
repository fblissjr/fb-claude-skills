#!/usr/bin/env python3
"""
Hash-based change detection for documentation URLs.

Fetches page content via httpx, converts HTML to markdown via markdownify,
computes content hash, and compares to stored hashes in state.json.

Usage:
    uv run python skill-maintainer/scripts/docs_monitor.py
    uv run python skill-maintainer/scripts/docs_monitor.py --source anthropic-skills-docs
    uv run python skill-maintainer/scripts/docs_monitor.py --config skill-maintainer/config.yaml
"""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import markdownify
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


def load_config(config_path: Path) -> dict:
    """Load and return the config.yaml."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_state(state_path: Path) -> dict:
    """Load state.json, returning empty dict if missing or empty."""
    if not state_path.exists():
        return {}
    data = state_path.read_bytes()
    if not data or data.strip() == b"{}":
        return {}
    return orjson.loads(data)


def save_state(state_path: Path, state: dict) -> None:
    """Write state to state.json using orjson."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))


def fetch_and_hash(url: str, timeout: float = 30.0) -> tuple[str, str, str]:
    """Fetch URL, convert to markdown, return (markdown_content, content_hash, raw_text).

    Returns:
        Tuple of (markdown_content, sha256_hash, raw_text_for_diff)
    """
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "html" in content_type:
        md_content = markdownify.markdownify(
            resp.text,
            heading_style="ATX",
            strip=["img", "script", "style", "nav", "footer"],
        )
    else:
        md_content = resp.text

    # Normalize whitespace for stable hashing
    normalized = "\n".join(
        line.strip() for line in md_content.splitlines()
        if line.strip()
    )
    content_hash = hashlib.sha256(normalized.encode()).hexdigest()

    return md_content, content_hash, normalized


def hash_file(file_path: Path) -> str:
    """Hash a local file (e.g., PDF) for change detection."""
    if not file_path.exists():
        return ""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def classify_changes(old_content: str, new_content: str) -> str:
    """Classify a change as breaking, additive, or cosmetic.

    Simple heuristic: check the diff text for keywords.
    """
    if not old_content:
        return "ADDITIVE"

    # Compute a simple line-level diff
    old_lines = set(old_content.splitlines())
    new_lines = set(new_content.splitlines())
    added_lines = new_lines - old_lines
    removed_lines = old_lines - new_lines

    diff_text = " ".join(added_lines | removed_lines).lower()

    for keyword in CHANGE_KEYWORDS_BREAKING:
        if keyword in diff_text:
            return "BREAKING"

    for keyword in CHANGE_KEYWORDS_ADDITIVE:
        if keyword in diff_text:
            return "ADDITIVE"

    return "COSMETIC"


def check_docs_source(
    source_name: str,
    source_config: dict,
    state: dict,
) -> list[dict]:
    """Check a docs-type source for changes.

    Returns list of change dicts with keys:
        source, url, classification, old_hash, new_hash, summary
    """
    changes = []
    source_state = state.get("docs", {}).get(source_name, {})

    urls = source_config.get("urls", [])
    hash_file_path = source_config.get("hash_file")

    for url in urls:
        url_state = source_state.get(url, {})
        old_hash = url_state.get("hash", "")
        old_content = url_state.get("normalized_content", "")

        try:
            md_content, new_hash, normalized = fetch_and_hash(url)
        except Exception as e:
            changes.append({
                "source": source_name,
                "url": url,
                "classification": "ERROR",
                "old_hash": old_hash,
                "new_hash": "",
                "summary": f"Failed to fetch: {e}",
            })
            continue

        if new_hash != old_hash:
            classification = classify_changes(old_content, normalized)
            lines_added = 0
            lines_removed = 0
            if old_content:
                old_set = set(old_content.splitlines())
                new_set = set(normalized.splitlines())
                lines_added = len(new_set - old_set)
                lines_removed = len(old_set - new_set)

            changes.append({
                "source": source_name,
                "url": url,
                "classification": classification,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "summary": f"{lines_added} lines added, {lines_removed} lines removed"
                if old_hash else "Initial capture",
                "normalized_content": normalized,
            })

            # Update state
            if "docs" not in state:
                state["docs"] = {}
            if source_name not in state["docs"]:
                state["docs"][source_name] = {}
            state["docs"][source_name][url] = {
                "hash": new_hash,
                "normalized_content": normalized[:5000],  # Keep truncated for diff
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # Update last_checked even when unchanged
            if "docs" not in state:
                state["docs"] = {}
            if source_name not in state["docs"]:
                state["docs"][source_name] = {}
            state["docs"][source_name][url] = {
                **url_state,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }

    # Handle local file hash (e.g., PDF)
    if hash_file_path:
        fpath = Path(hash_file_path)
        old_fhash = source_state.get("_file_hash", "")
        new_fhash = hash_file(fpath)
        if new_fhash and new_fhash != old_fhash:
            changes.append({
                "source": source_name,
                "url": f"file://{fpath}",
                "classification": "ADDITIVE",
                "old_hash": old_fhash,
                "new_hash": new_fhash,
                "summary": "Local file changed" if old_fhash else "Initial capture",
            })
            if "docs" not in state:
                state["docs"] = {}
            if source_name not in state["docs"]:
                state["docs"][source_name] = {}
            state["docs"][source_name]["_file_hash"] = new_fhash
            state["docs"][source_name]["_file_last_checked"] = (
                datetime.now(timezone.utc).isoformat()
            )

    return changes


def generate_report(all_changes: list[dict]) -> str:
    """Generate a markdown report from detected changes."""
    lines = [
        "# Documentation Change Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not all_changes:
        lines.append("No changes detected.")
        return "\n".join(lines)

    # Group by classification
    breaking = [c for c in all_changes if c["classification"] == "BREAKING"]
    additive = [c for c in all_changes if c["classification"] == "ADDITIVE"]
    cosmetic = [c for c in all_changes if c["classification"] == "COSMETIC"]
    errors = [c for c in all_changes if c["classification"] == "ERROR"]

    if breaking:
        lines.append("## BREAKING Changes")
        lines.append("")
        for c in breaking:
            lines.append(f"- **{c['source']}**: {c['url']}")
            lines.append(f"  - {c['summary']}")
            lines.append(f"  - Hash: `{c['old_hash'][:12]}` -> `{c['new_hash'][:12]}`")
        lines.append("")

    if additive:
        lines.append("## Additive Changes")
        lines.append("")
        for c in additive:
            lines.append(f"- **{c['source']}**: {c['url']}")
            lines.append(f"  - {c['summary']}")
        lines.append("")

    if cosmetic:
        lines.append("## Cosmetic Changes")
        lines.append("")
        for c in cosmetic:
            lines.append(f"- **{c['source']}**: {c['url']}")
            lines.append(f"  - {c['summary']}")
        lines.append("")

    if errors:
        lines.append("## Errors")
        lines.append("")
        for c in errors:
            lines.append(f"- **{c['source']}**: {c['url']}")
            lines.append(f"  - {c['summary']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor documentation URLs for changes."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
        help="Path to state.json",
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
        changes = check_docs_source(name, src_config, state)
        all_changes.extend(changes)

        if changes:
            print(
                f"  {len(changes)} change(s) detected",
                file=sys.stderr,
            )
        else:
            print("  No changes", file=sys.stderr)

    # Save updated state
    save_state(args.state, state)

    # Generate and output report
    report = generate_report(all_changes)

    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
