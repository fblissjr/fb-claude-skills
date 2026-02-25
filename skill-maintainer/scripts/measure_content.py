#!/usr/bin/env python3
"""
Token budget measurement for all skills in the repo.

Walks all SKILL.md files, measures each file in the skill directory,
and outputs a budget report. No DuckDB, no config file needed.

The 2% rule: a skill should use ~2% of the context window when loaded.
For a 200k token window, that's ~4000 tokens. Estimate: 1 token ~ 4 chars.

Usage:
    uv run python skill-maintainer/scripts/measure_content.py
    uv run python skill-maintainer/scripts/measure_content.py --skill plugin-toolkit
"""

import argparse
import hashlib
import sys
from pathlib import Path

TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000

FILE_TYPE_MAP = {
    "SKILL.md": "skill_md",
    "COMMAND.md": "command_md",
}

SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal", "state"}


def discover_skills(root: Path) -> list[Path]:
    """Find all SKILL.md files, return their parent directories."""
    results = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        if any(skip in skill_md.parts for skip in SKIP_DIRS):
            continue
        if ".backup" in str(skill_md):
            continue
        results.append(skill_md.parent)
    return results


def classify_file(file_path: Path, skill_root: Path) -> str:
    name = file_path.name
    if name in FILE_TYPE_MAP:
        return FILE_TYPE_MAP[name]

    rel = file_path.relative_to(skill_root)
    parts = rel.parts
    if len(parts) > 1:
        parent = parts[0]
        if parent == "references":
            return "reference"
        if parent == "agents":
            return "agent"
        if parent == "hooks":
            return "hook"
        if parent == "scripts":
            return "script"
        if parent == "commands":
            return "command_md"
        if parent == "skills":
            return "skill_md" if name == "SKILL.md" else "reference"

    if file_path.suffix == ".md":
        return "reference"
    if file_path.suffix == ".py":
        return "script"
    return "other"


def measure_file(file_path: Path) -> dict:
    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        try:
            raw = file_path.read_bytes()
            return {"line_count": 0, "word_count": 0, "char_count": len(raw),
                    "content_hash": hashlib.sha256(raw).hexdigest()}
        except OSError:
            return {"line_count": 0, "word_count": 0, "char_count": 0, "content_hash": ""}

    return {
        "line_count": len(content.splitlines()),
        "word_count": len(content.split()),
        "char_count": len(content),
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
    }


def walk_skill_files(skill_path: Path) -> list[tuple[Path, str]]:
    results = []
    if not skill_path.exists():
        return results

    for item in sorted(skill_path.rglob("*")):
        if item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        if any(skip in item.parts for skip in SKIP_DIRS):
            continue
        if item.suffix in (".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml"):
            file_type = classify_file(item, skill_path)
            results.append((item, file_type))

    return results


def measure_skill(skill_name: str, skill_path: Path) -> dict:
    files = walk_skill_files(skill_path)
    total_tokens = 0
    file_measurements = []

    for file_path, file_type in files:
        metrics = measure_file(file_path)
        estimated_tokens = metrics["char_count"] // 4
        total_tokens += estimated_tokens

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
    lines = [
        "# Token Budget Report",
        "",
        f"Budget threshold: {TOKEN_BUDGET_WARN} tokens (warn), {TOKEN_BUDGET_CRITICAL} tokens (critical)",
        "Estimate: 1 token ~ 4 characters",
        "",
        "| Skill | Files | Tokens | Status |",
        "|-------|-------|--------|--------|",
    ]

    for r in results:
        if r["critical"]:
            status = "CRITICAL"
        elif r["over_budget"]:
            status = "OVER"
        else:
            status = "OK"
        lines.append(f"| {r['skill_name']} | {r['file_count']} | {r['total_tokens']:,} | {status} |")

    lines.append("")

    for r in results:
        if not r["files"]:
            continue
        lines.append(f"## {r['skill_name']} ({r['total_tokens']:,} tokens)")
        lines.append("")

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
    parser = argparse.ArgumentParser(description="Measure token budgets for skills.")
    parser.add_argument("--skill", type=str, default=None, help="Measure only this skill (by directory name)")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search")
    parser.add_argument("--output", type=Path, default=None, help="Write report to file")
    args = parser.parse_args()

    skills = discover_skills(args.dir)

    if args.skill:
        skills = [s for s in skills if s.name == args.skill]
        if not skills:
            print(f"Error: skill '{args.skill}' not found", file=sys.stderr)
            sys.exit(1)

    results = []
    for skill_dir in skills:
        name = skill_dir.name
        print(f"Measuring {name} ({skill_dir})...", file=sys.stderr, flush=True)
        result = measure_skill(name, skill_dir)
        results.append(result)
        print(f"  {result['file_count']} files, {result['total_tokens']:,} tokens", file=sys.stderr)

    report = generate_report(results)
    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
