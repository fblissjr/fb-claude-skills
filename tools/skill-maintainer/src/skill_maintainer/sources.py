"""Pull tracked local repos and detect what changed since last run."""

import subprocess
import sys
from datetime import date
from pathlib import Path

from skill_maintainer.config import (
    append_event,
    get_tracked_repos,
    hashes_file,
    load_hashes,
    save_hashes,
)


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


def _log_event(root: Path, results: list[dict]) -> None:
    changed = [r for r in results if r["status"] in ("CHANGED", "NEW")]
    append_event(root, {
        "type": "source_pull",
        "date": date.today().isoformat(),
        "repos_checked": len(results),
        "repos_changed": len(changed),
        "changes": [
            {"repo": r["name"], "status": r["status"], "commits": len(r.get("commits", []))}
            for r in changed
        ],
    })


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Pull tracked repos and detect changes.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory (for config/state)")
    parser.add_argument("--no-pull", action="store_true", help="Check only, don't git pull")
    parser.add_argument("--no-save", action="store_true", help="Don't update hash state")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    parsed = parser.parse_args(args)

    root = parsed.dir
    tracked_repos = get_tracked_repos(root)

    if not tracked_repos:
        print("No tracked repos configured.", file=sys.stderr)
        print("Add repos to .skill-maintainer/config.json under 'tracked_repos'.", file=sys.stderr)
        print('Example: "tracked_repos": ["coderef/agentskills", "coderef/mcp/python-sdk"]', file=sys.stderr)
        sys.exit(1)

    all_hashes = load_hashes(root)
    local_repos = all_hashes.get("local_repos", {})
    results = []

    action = "Checking" if parsed.no_pull else "Pulling"
    print(f"{action} {len(tracked_repos)} tracked repos...", file=sys.stderr, flush=True)

    for rel_path in tracked_repos:
        path = root / rel_path
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
        if parsed.no_pull:
            sys.stderr.write(f"  Checking {name}...")
            sys.stderr.flush()
        before_sha = git_head(resolved)

        if before_sha is None:
            print(f"  ERROR reading HEAD: {name}", file=sys.stderr)
            results.append({"name": name, "status": "ERROR"})
            continue

        # Pull unless --no-pull
        if not parsed.no_pull:
            sys.stderr.write(f"  Pulling {name}...")
            sys.stderr.flush()
            ok, msg = git_pull(resolved)
            if not ok:
                sys.stderr.write(f" FAILED: {msg}\n")
            else:
                sys.stderr.write(" ok\n")
            sys.stderr.flush()

        after_sha = git_head(resolved)
        if after_sha is None:
            print(f"  ERROR reading HEAD after pull: {name}", file=sys.stderr)
            results.append({"name": name, "status": "ERROR"})
            continue

        if old_sha is None:
            status = "NEW"
            commits = []
        elif old_sha != after_sha:
            status = "CHANGED"
            commits = git_log_oneline(resolved, old_sha, after_sha)
        else:
            status = "UP_TO_DATE"
            commits = []

        if parsed.no_pull:
            sys.stderr.write(f" {status.lower().replace('_', ' ')}\n")
            sys.stderr.flush()

        results.append({
            "name": name,
            "status": status,
            "old_sha": old_sha,
            "new_sha": after_sha,
            "commits": commits,
        })

        local_repos[name] = after_sha

    # Report
    changed = [r for r in results if r["status"] in ("CHANGED", "NEW")]
    up_to_date = [r for r in results if r["status"] == "UP_TO_DATE"]
    errors = [r for r in results if r["status"] in ("MISSING", "NOT_GIT", "ERROR")]

    print(f"\nRepos: {len(tracked_repos)} tracked, {len(changed)} changed, "
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

        print(f"  [{marker:>8}] {r['name']}")

        if r.get("commits"):
            for commit in r["commits"][:5]:
                print(f"             {commit}")
            if len(r["commits"]) > 5:
                print(f"             ... and {len(r['commits']) - 5} more")

    # Save state
    if not parsed.no_save:
        all_hashes["local_repos"] = local_repos
        save_hashes(root, all_hashes)
        print(f"\nHashes saved to {hashes_file(root)}", file=sys.stderr)

    if changed and not parsed.no_log:
        _log_event(root, results)

    sys.exit(0)
