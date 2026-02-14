#!/usr/bin/env python3
"""
Git-based upstream code change detection.

Generalized from mlx-skills check_updates.py. Monitors configured git repos
for changes to watched files, extracts API changes, and detects breaking changes.

State is stored in DuckDB via the Store class. Backward-compatible state.json
is exported after each run.

Usage:
    uv run python skill-maintainer/scripts/source_monitor.py
    uv run python skill-maintainer/scripts/source_monitor.py --source agentskills-spec
    uv run python skill-maintainer/scripts/source_monitor.py --since 30days
"""

import argparse
import ast
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")

DEPRECATION_KEYWORDS = [
    "deprecat", "removed", "breaking", "rename", "replace",
    "migrate", "backward compat", "backwards compat",
]


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_git(repo_path: Path, *args: str, timeout: int = 30) -> Optional[str]:
    """Run a git command in the given repo path."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def clone_repo(url: str, dest: Path, since: str) -> bool:
    """Shallow bare clone scoped to the time window."""
    result = subprocess.run(
        [
            "git", "clone", "--bare", "--single-branch",
            "--shallow-since", since, url, str(dest),
        ],
        capture_output=True, text=True, timeout=120,
    )
    return result.returncode == 0


def get_recent_commits(repo_path: Path, since: str) -> list[dict]:
    """Get recent commits with metadata."""
    output = run_git(
        repo_path, "log", f"--since={since}",
        "--format=%H|%s|%an|%ai", "--no-merges",
    )
    if not output:
        return []

    commits = []
    for line in output.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:12],
                "subject": parts[1],
                "author": parts[2],
                "date": parts[3][:10],
            })
    return commits


def get_changed_files(repo_path: Path, since: str) -> list[str]:
    """Get list of files changed since the given date."""
    output = run_git(
        repo_path, "log", f"--since={since}",
        "--name-only", "--format=", "--no-merges",
    )
    if not output:
        return []

    files = set()
    for line in output.splitlines():
        line = line.strip()
        if line:
            files.add(line)
    return sorted(files)


def extract_public_api(file_path: Path) -> list[str]:
    """Extract public function and class names from a Python file using AST."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return []

    names = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [arg.arg for arg in node.args.args]
            names.append(f"def {node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = [
                item.name for item in node.body
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
            ]
            methods_str = f" [{', '.join(methods)}]" if methods else ""
            names.append(f"class {node.name}{methods_str}")
        elif isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
            names.append(f"async def {node.name}(...)")
    return names


def check_deprecations(commits: list[dict]) -> list[str]:
    """Check commit messages for deprecation-related keywords."""
    flagged = []
    for commit in commits:
        subject_lower = commit["subject"].lower()
        for keyword in DEPRECATION_KEYWORDS:
            if keyword in subject_lower:
                flagged.append(
                    f"  - [{commit['hash']}] {commit['subject']}"
                )
                break
    return flagged


def analyze_watched_files(
    repo_path: Path,
    watched_files: list[str],
    changed_files: list[str],
) -> list[dict]:
    """Check which watched files were modified and extract API info."""
    hits = []
    for wf in watched_files:
        if wf in changed_files:
            file_path = repo_path / wf
            api = []
            if file_path.exists() and file_path.suffix == ".py":
                api = extract_public_api(file_path)
            hits.append({
                "file": wf,
                "api": api[:10],
                "api_count": len(api),
            })
    return hits


def check_source(
    source_name: str,
    source_config: dict,
    store: Store,
    since: str,
) -> dict:
    """Check a source-type repo for changes.

    Returns a dict with keys:
        source, repo, commits_count, changed_files_count,
        watched_hits, deprecations, commits, classification
    """
    repo_url = source_config.get("repo", "")
    watched_files = source_config.get("watched_files", [])

    if not repo_url:
        return {
            "source": source_name,
            "error": "No repo URL configured",
        }

    # Clone to temp directory
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"skill-maint-{source_name}-"))
    try:
        print(f"  Cloning {repo_url}...", file=sys.stderr, end=" ", flush=True)
        if not clone_repo(repo_url, tmp_dir, since):
            print("skipped (no recent commits or clone failed)", file=sys.stderr)
            return {
                "source": source_name,
                "repo": repo_url,
                "commits_count": 0,
                "changed_files_count": 0,
                "watched_hits": [],
                "deprecations": [],
                "commits": [],
                "classification": "NONE",
            }
        print("done", file=sys.stderr)

        commits = get_recent_commits(tmp_dir, since)
        changed_files = get_changed_files(tmp_dir, since)
        watched_hits = analyze_watched_files(tmp_dir, watched_files, changed_files)
        deprecations = check_deprecations(commits)

        # Classify overall change
        if deprecations:
            classification = "BREAKING"
        elif watched_hits:
            classification = "ADDITIVE"
        elif commits:
            classification = "COSMETIC"
        else:
            classification = "NONE"

        # Record in Store
        if commits:
            store.record_change(
                source_name,
                classification=classification,
                summary=f"{len(commits)} commits, {len(changed_files)} files changed",
                commit_hash=commits[0]["hash"] if commits else "",
                commit_count=len(commits),
                record_source="source_monitor",
            )

        return {
            "source": source_name,
            "repo": repo_url,
            "commits_count": len(commits),
            "changed_files_count": len(changed_files),
            "watched_hits": watched_hits,
            "deprecations": deprecations,
            "commits": commits[:15],
            "classification": classification,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def generate_report(results: list[dict]) -> str:
    """Generate markdown report from source check results."""
    lines = [
        "# Source Change Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    has_changes = False

    for result in results:
        if result.get("error"):
            lines.append(f"## {result['source']} (ERROR)")
            lines.append(f"  {result['error']}")
            lines.append("")
            continue

        if result["commits_count"] == 0:
            continue

        has_changes = True
        classification = result["classification"]
        lines.append(f"## {result['source']} [{classification}]")
        lines.append("")
        lines.append(
            f"**{result['commits_count']} commits**, "
            f"**{result['changed_files_count']} files changed**"
        )
        lines.append("")

        if result["watched_hits"]:
            lines.append("### Watched File Changes")
            lines.append("")
            for hit in result["watched_hits"]:
                api_str = ""
                if hit["api"]:
                    api_str = f" -- API: {', '.join(hit['api'][:5])}"
                    if hit["api_count"] > 5:
                        api_str += f" (+{hit['api_count'] - 5} more)"
                lines.append(f"  - `{hit['file']}`{api_str}")
            lines.append("")

        if result["deprecations"]:
            lines.append("### Potential Breaking Changes")
            lines.append("")
            for d in result["deprecations"]:
                lines.append(d)
            lines.append("")

        if result["commits"]:
            lines.append("### Recent Commits")
            lines.append("")
            for commit in result["commits"]:
                lines.append(
                    f"  - `{commit['hash']}` {commit['subject']} "
                    f"({commit['author']}, {commit['date']})"
                )
            lines.append("")

    if not has_changes:
        lines.append("No changes detected in monitored source repositories.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor upstream git repos for changes affecting skills."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Path to config.yaml",
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
        "--since", default="30days",
        help="Time range for git log (e.g., '30days', '2024-01-15'). Default: 30days",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    with Store(db_path=args.db, config_path=args.config) as store:
        results = []
        sources = config.get("sources", {})

        for name, src_config in sources.items():
            if src_config.get("type") != "source":
                continue
            if args.source and name != args.source:
                continue

            print(f"Checking {name}...", file=sys.stderr, flush=True)
            result = check_source(name, src_config, store, args.since)
            results.append(result)

        # Export backward-compatible state.json
        store.export_state_json_file(args.state)

    report = generate_report(results)

    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
