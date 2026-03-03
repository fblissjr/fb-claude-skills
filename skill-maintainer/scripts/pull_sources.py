#!/usr/bin/env python3
"""
Pull tracked local repos and detect what changed since last run.

Resolves coderef/ symlinks, runs git pull --ff-only on each repo,
compares HEAD before/after against stored state, captures commit logs.

Usage:
    uv run python skill-maintainer/scripts/pull_sources.py
    uv run python skill-maintainer/scripts/pull_sources.py --no-pull
    uv run python skill-maintainer/scripts/pull_sources.py --no-save --no-log
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

import orjson

HASHES_FILE = Path("skill-maintainer/state/upstream_hashes.json")
CHANGES_LOG = Path("skill-maintainer/state/changes.jsonl")

# Tracked repos under coderef/ (relative to repo root).
# Entries may be symlinks -- resolved at runtime.
TRACKED_REPOS = [
    "coderef/agentskills",
    "coderef/skills",
    "coderef/claude-plugins-official",
    "coderef/knowledge-work-plugins",
    "coderef/claude-agent-sdk-python",
    "coderef/claude-cookbooks",
    "coderef/mcp/modelcontextprotocol",
    "coderef/mcp/python-sdk",
    "coderef/mcp/ext-apps",
    "coderef/mcp/experimental-ext-skills",
]


def load_hashes() -> dict:
    if HASHES_FILE.exists():
        return orjson.loads(HASHES_FILE.read_bytes())
    return {}


def save_hashes(hashes: dict) -> None:
    HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASHES_FILE.write_bytes(orjson.dumps(hashes, option=orjson.OPT_INDENT_2))


def git_head(repo_path: Path) -> str | None:
    """Get current HEAD SHA for a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def git_pull(repo_path: Path) -> tuple[bool, str]:
    """Run git pull --ff-only. Returns (success, message)."""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except OSError as e:
        return False, str(e)


def git_log_oneline(repo_path: Path, old_sha: str, new_sha: str) -> list[str]:
    """Get oneline log between two SHAs."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{old_sha}..{new_sha}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [line for line in result.stdout.strip().splitlines() if line]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return []


def append_to_log(results: list[dict]) -> None:
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    changed = [r for r in results if r["status"] in ("CHANGED", "NEW")]
    event = {
        "type": "source_pull",
        "date": date.today().isoformat(),
        "repos_checked": len(results),
        "repos_changed": len(changed),
        "changes": [
            {"repo": r["name"], "status": r["status"], "commits": len(r.get("commits", []))}
            for r in changed
        ],
    }
    with open(CHANGES_LOG, "ab") as f:
        f.write(orjson.dumps(event) + b"\n")


def main():
    parser = argparse.ArgumentParser(description="Pull tracked repos and detect changes.")
    parser.add_argument("--no-pull", action="store_true", help="Check only, don't git pull")
    parser.add_argument("--no-save", action="store_true", help="Don't update hash state")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    args = parser.parse_args()

    all_hashes = load_hashes()
    local_repos = all_hashes.get("local_repos", {})
    results = []

    for rel_path in TRACKED_REPOS:
        path = Path(rel_path)
        name = rel_path

        # Resolve symlinks to find the actual git repo
        resolved = path.resolve()
        if not resolved.exists():
            print(f"  MISSING: {name} ({resolved})", file=sys.stderr)
            results.append({"name": name, "status": "MISSING"})
            continue

        if not (resolved / ".git").exists():
            print(f"  NOT A GIT REPO: {name} ({resolved})", file=sys.stderr)
            results.append({"name": name, "status": "NOT_GIT"})
            continue

        old_sha = local_repos.get(name)
        before_sha = git_head(resolved)

        if before_sha is None:
            print(f"  ERROR reading HEAD: {name}", file=sys.stderr)
            results.append({"name": name, "status": "ERROR"})
            continue

        # Pull unless --no-pull
        if not args.no_pull:
            ok, msg = git_pull(resolved)
            if not ok:
                print(f"  PULL FAILED: {name}: {msg}", file=sys.stderr)
                # Still record current HEAD even if pull fails

        after_sha = git_head(resolved)
        if after_sha is None:
            print(f"  ERROR reading HEAD after pull: {name}", file=sys.stderr)
            results.append({"name": name, "status": "ERROR"})
            continue

        if old_sha is None:
            # First time seeing this repo
            status = "NEW"
            commits = []
        elif old_sha != after_sha:
            status = "CHANGED"
            commits = git_log_oneline(resolved, old_sha, after_sha)
        else:
            status = "UP_TO_DATE"
            commits = []

        results.append({
            "name": name,
            "status": status,
            "old_sha": old_sha,
            "new_sha": after_sha,
            "commits": commits,
        })

        # Update stored SHA
        local_repos[name] = after_sha

    # Report
    changed = [r for r in results if r["status"] in ("CHANGED", "NEW")]
    up_to_date = [r for r in results if r["status"] == "UP_TO_DATE"]
    errors = [r for r in results if r["status"] in ("MISSING", "NOT_GIT", "ERROR")]

    print(f"\nRepos: {len(TRACKED_REPOS)} tracked, {len(changed)} changed, "
          f"{len(up_to_date)} up to date, {len(errors)} errors")
    print()

    for r in results:
        marker = {
            "NEW": "NEW",
            "CHANGED": "CHANGED",
            "UP_TO_DATE": "OK",
            "MISSING": "MISSING",
            "NOT_GIT": "NOT_GIT",
            "ERROR": "ERROR",
        }.get(r["status"], "?")

        short_name = r["name"].replace("coderef/", "")
        print(f"  [{marker:>8}] {short_name}")

        if r.get("commits"):
            for commit in r["commits"][:5]:
                print(f"             {commit}")
            if len(r["commits"]) > 5:
                print(f"             ... and {len(r['commits']) - 5} more")

    # Save state
    if not args.no_save:
        all_hashes["local_repos"] = local_repos
        save_hashes(all_hashes)
        print(f"\nHashes saved to {HASHES_FILE}", file=sys.stderr)

    if changed and not args.no_log:
        append_to_log(results)

    sys.exit(0)


if __name__ == "__main__":
    main()
