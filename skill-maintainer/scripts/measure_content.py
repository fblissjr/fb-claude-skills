#!/usr/bin/env python3
"""
Token budget measurement for tracked skills.

Walks all tracked skills, measures each file (SKILL.md, references/, agents/),
records into fact_content_measurement, and outputs a budget report.

The 2% rule: a skill should use ~2% of the context window when loaded.
For a 200k token window, that's ~4000 tokens. For reference, 1 token ~ 4 chars.

Usage:
    uv run python skill-maintainer/scripts/measure_content.py
    uv run python skill-maintainer/scripts/measure_content.py --skill plugin-toolkit
"""

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")

# Budget thresholds (in estimated tokens)
TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000

# File type classification
FILE_TYPE_MAP = {
    "SKILL.md": "skill_md",
    "COMMAND.md": "command_md",
}


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def classify_file(file_path: Path, skill_root: Path) -> str:
    """Determine the file type for a file within a skill directory."""
    name = file_path.name
    if name in FILE_TYPE_MAP:
        return FILE_TYPE_MAP[name]

    # Check parent directory
    rel = file_path.relative_to(skill_root)
    parts = rel.parts
    if len(parts) > 1:
        if parts[0] == "references":
            return "reference"
        if parts[0] == "agents":
            return "agent"
        if parts[0] == "hooks":
            return "hook"
        if parts[0] == "scripts":
            return "script"
        if parts[0] == "commands":
            return "command_md"
        if parts[0] == "skills":
            # Nested skill directory
            if name == "SKILL.md":
                return "skill_md"
            return "reference"

    # Default based on extension
    if file_path.suffix == ".md":
        return "reference"
    if file_path.suffix == ".py":
        return "script"
    return "other"


def measure_file(file_path: Path) -> dict:
    """Measure a single file's content metrics."""
    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        # Binary file or unreadable
        try:
            raw = file_path.read_bytes()
            return {
                "line_count": 0,
                "word_count": 0,
                "char_count": len(raw),
                "content_hash": hashlib.sha256(raw).hexdigest(),
            }
        except OSError:
            return {
                "line_count": 0,
                "word_count": 0,
                "char_count": 0,
                "content_hash": "",
            }

    return {
        "line_count": len(content.splitlines()),
        "word_count": len(content.split()),
        "char_count": len(content),
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
    }


def walk_skill_files(skill_path: Path) -> list[tuple[Path, str]]:
    """Walk a skill directory and return (path, file_type) pairs.

    Skips hidden files, __pycache__, .backup dirs, etc.
    """
    results = []
    skip_dirs = {"__pycache__", ".backup", "node_modules", ".git", "state"}

    if not skill_path.exists():
        return results

    for item in sorted(skill_path.rglob("*")):
        if item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        if any(skip in item.parts for skip in skip_dirs):
            continue
        # Only measure text-like files
        if item.suffix in (".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml"):
            file_type = classify_file(item, skill_path)
            results.append((item, file_type))

    return results


def measure_skill(
    skill_name: str,
    skill_path: Path,
    store: Store,
) -> dict:
    """Measure all files in a skill and record in DuckDB.

    Returns summary dict.
    """
    files = walk_skill_files(skill_path)
    total_tokens = 0
    file_measurements = []

    for file_path, file_type in files:
        metrics = measure_file(file_path)
        estimated_tokens = metrics["char_count"] // 4
        total_tokens += estimated_tokens

        store.record_content_measurement(
            skill_name,
            file_path=str(file_path),
            file_type=file_type,
            line_count=metrics["line_count"],
            word_count=metrics["word_count"],
            char_count=metrics["char_count"],
            content_hash=metrics["content_hash"],
        )

        file_measurements.append({
            "path": str(file_path),
            "type": file_type,
            "lines": metrics["line_count"],
            "words": metrics["word_count"],
            "chars": metrics["char_count"],
            "tokens": estimated_tokens,
        })

    return {
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "file_count": len(files),
        "total_tokens": total_tokens,
        "over_budget": total_tokens > TOKEN_BUDGET_WARN,
        "critical": total_tokens > TOKEN_BUDGET_CRITICAL,
        "files": file_measurements,
    }


def generate_report(results: list[dict]) -> str:
    """Generate a token budget report."""
    lines = [
        "# Token Budget Report",
        "",
        f"Budget threshold: {TOKEN_BUDGET_WARN} tokens (warn), {TOKEN_BUDGET_CRITICAL} tokens (critical)",
        f"Estimate: 1 token ~ 4 characters",
        "",
    ]

    # Summary table
    lines.append("| Skill | Files | Tokens | Status |")
    lines.append("|-------|-------|--------|--------|")

    for r in results:
        if r["critical"]:
            status = "CRITICAL"
        elif r["over_budget"]:
            status = "OVER"
        else:
            status = "OK"
        lines.append(
            f"| {r['skill_name']} | {r['file_count']} | {r['total_tokens']:,} | {status} |"
        )

    lines.append("")

    # Detail per skill
    for r in results:
        if not r["files"]:
            continue
        lines.append(f"## {r['skill_name']} ({r['total_tokens']:,} tokens)")
        lines.append("")

        # Group by type
        by_type: dict[str, list] = {}
        for f in r["files"]:
            by_type.setdefault(f["type"], []).append(f)

        for file_type in ["skill_md", "reference", "agent", "hook", "command_md", "script", "other"]:
            type_files = by_type.get(file_type, [])
            if not type_files:
                continue
            type_tokens = sum(f["tokens"] for f in type_files)
            lines.append(f"### {file_type} ({type_tokens:,} tokens)")
            for f in type_files:
                short_path = f["path"].split("/", 1)[-1] if "/" in f["path"] else f["path"]
                lines.append(f"  - `{short_path}`: {f['lines']} lines, {f['tokens']:,} tokens")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Measure token budgets for tracked skills."
    )
    parser.add_argument(
        "--skill", type=str, default=None,
        help="Measure only this skill (by name from config)",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    skills = config.get("skills", {})

    if args.skill:
        if args.skill not in skills:
            print(f"Error: skill '{args.skill}' not found in config", file=sys.stderr)
            sys.exit(1)
        skills = {args.skill: skills[args.skill]}

    with Store(db_path=args.db, config_path=args.config) as store:
        results = []
        for name, skill_config in skills.items():
            skill_path = Path(skill_config["path"])
            print(f"Measuring {name} ({skill_path})...", file=sys.stderr, flush=True)
            result = measure_skill(name, skill_path, store)
            results.append(result)
            print(
                f"  {result['file_count']} files, {result['total_tokens']:,} tokens",
                file=sys.stderr,
            )

    report = generate_report(results)
    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
