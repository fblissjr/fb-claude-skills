#!/usr/bin/env python3
"""
Red/green test suite for skill ecosystem properties.

Encodes the measurable checks from best_practices.md as pass/fail assertions.
No pytest dependency. No network calls. No file writes. Pure read-only.

Usage:
    uv run python skill-maintainer/scripts/run_tests.py
    uv run python skill-maintainer/scripts/run_tests.py --verbose
    uv run python skill-maintainer/scripts/run_tests.py --category skills
    uv run python skill-maintainer/scripts/run_tests.py --category plugins
    uv run python skill-maintainer/scripts/run_tests.py --category repo
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import orjson

from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

from shared import (
    STALE_DAYS,
    TOKEN_BUDGET_CRITICAL,
    TOKEN_BUDGET_WARN,
    discover_plugins,
    discover_skills,
)

PLUGIN_REQUIRED_FIELDS = ("name", "version", "description", "author", "repository")
MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")
SETTINGS_PATH = Path(".claude/settings.json")
GITIGNORE_PATH = Path(".gitignore")
BEST_PRACTICES_PATH = Path("skill-maintainer/references/best_practices.md")
STATE_FILES = [
    Path("skill-maintainer/state/upstream_hashes.json"),
    Path("skill-maintainer/state/changes.jsonl"),
]

# High-frequency hook events that should not have broad (unmatched) triggers
HIGH_FREQ_EVENTS = {"PreToolUse", "PostToolUse"}


@dataclass
class Result:
    category: str
    name: str
    check: str
    passed: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Skill tests
# ---------------------------------------------------------------------------


def measure_tokens(skill_dir: Path) -> int:
    """Estimate total tokens for all text files in a skill directory."""
    total_chars = 0
    skip = {"__pycache__", ".backup", "node_modules", "state"}
    for f in skill_dir.rglob("*"):
        if f.is_dir() or f.name.startswith("."):
            continue
        if any(s in f.parts for s in skip):
            continue
        if f.suffix in (".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml"):
            try:
                total_chars += len(f.read_text())
            except (OSError, UnicodeDecodeError):
                pass
    return total_chars // 4


def check_description_quality(description: str) -> list[str]:
    """Check description for WHAT verb + WHEN trigger."""
    issues = []
    if not description:
        return ["no description"]
    desc_lower = description.lower()
    has_what = any(w in desc_lower for w in [
        "use when", "use for", "handles", "manages", "creates",
        "generates", "monitors", "validates", "analyzes", "design",
    ])
    has_when = any(w in desc_lower for w in [
        "use when", "when user", "when the", "if user",
        "trigger", "mention", "says",
    ])
    if not has_what:
        issues.append("missing WHAT verb")
    if not has_when:
        issues.append("missing WHEN trigger")
    return issues


def test_skills(root: Path) -> list[Result]:
    """Run per-skill checks: spec, budget, body size, staleness, description."""
    results = []
    skills = discover_skills(root)

    for skill_dir in skills:
        skill_md = find_skill_md(skill_dir)
        if skill_md is None:
            results.append(Result("skill", skill_dir.name, "spec compliance", False, "SKILL.md not found"))
            continue

        name = skill_dir.name

        # 1. Spec compliance
        errors = validate(skill_dir)
        results.append(Result(
            "skill", name, "spec compliance",
            len(errors) == 0,
            "; ".join(errors) if errors else "",
        ))

        # 2. Token budget
        tokens = measure_tokens(skill_dir)
        budget_pass = tokens < TOKEN_BUDGET_WARN
        detail = f"{tokens:,}"
        if not budget_pass:
            if tokens >= TOKEN_BUDGET_CRITICAL:
                detail = f"{tokens:,} > {TOKEN_BUDGET_CRITICAL:,}"
            else:
                detail = f"{tokens:,} > {TOKEN_BUDGET_WARN:,}"
        results.append(Result("skill", name, "token budget", budget_pass, detail))

        # 3. Body size
        content = skill_md.read_text()
        line_count = len(content.splitlines())
        results.append(Result(
            "skill", name, "body size",
            line_count <= 500,
            f"{line_count} lines" if line_count <= 500 else f"{line_count} lines > 500",
        ))

        # 4. Staleness
        try:
            metadata, _ = parse_frontmatter(content)
        except Exception:
            results.append(Result("skill", name, "staleness", False, "failed to parse frontmatter"))
            results.append(Result("skill", name, "description quality", False, "failed to parse frontmatter"))
            continue

        meta = metadata.get("metadata", {})
        lv = meta.get("last_verified") if isinstance(meta, dict) else None
        if lv:
            try:
                days = (date.today() - date.fromisoformat(str(lv))).days
                results.append(Result(
                    "skill", name, "staleness",
                    days <= STALE_DAYS,
                    f"{days}d" if days <= STALE_DAYS else f"{days}d > {STALE_DAYS}d",
                ))
            except ValueError:
                results.append(Result("skill", name, "staleness", False, f"invalid date: {lv}"))
        else:
            results.append(Result("skill", name, "staleness", False, "missing metadata.last_verified"))

        # 5. Description quality
        description = metadata.get("description", "")
        issues = check_description_quality(description)
        results.append(Result(
            "skill", name, "description quality",
            len(issues) == 0,
            "; ".join(issues) if issues else "",
        ))

    return results


# ---------------------------------------------------------------------------
# Plugin tests
# ---------------------------------------------------------------------------


def load_marketplace(root: Path) -> list[str]:
    """Return plugin names listed in marketplace.json."""
    mp_path = root / MARKETPLACE_PATH
    if not mp_path.exists():
        return []
    data = orjson.loads(mp_path.read_bytes())
    return [p["name"] for p in data.get("plugins", [])]


def test_plugins(root: Path) -> list[Result]:
    """Run per-plugin checks: manifest fields, marketplace listing, README."""
    results = []
    plugins = discover_plugins(root)
    marketplace_names = load_marketplace(root)

    for plugin_dir in plugins:
        name = plugin_dir.name
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"

        # 1. Manifest fields
        try:
            manifest = orjson.loads(manifest_path.read_bytes())
        except Exception as e:
            results.append(Result("plugin", name, "manifest fields", False, f"cannot read: {e}"))
            results.append(Result("plugin", name, "marketplace listing", False, "skipped (no manifest)"))
            results.append(Result("plugin", name, "README exists", False, "skipped (no manifest)"))
            continue

        missing = []
        for field in PLUGIN_REQUIRED_FIELDS:
            if field not in manifest or not manifest[field]:
                missing.append(field)
        results.append(Result(
            "plugin", name, "manifest fields",
            len(missing) == 0,
            f"missing: {', '.join(missing)}" if missing else "",
        ))

        # 2. Marketplace listing
        results.append(Result(
            "plugin", name, "marketplace listing",
            name in marketplace_names,
            "" if name in marketplace_names else "not in marketplace.json",
        ))

        # 3. README exists
        readme = plugin_dir / "README.md"
        results.append(Result(
            "plugin", name, "README exists",
            readme.exists(),
            "" if readme.exists() else "missing README.md",
        ))

    return results


# ---------------------------------------------------------------------------
# Repo hygiene tests
# ---------------------------------------------------------------------------


def test_repo_hygiene(root: Path) -> list[Result]:
    """Run one-time repo-level checks."""
    results = []

    # 1. No blanket .claude/ gitignore
    gitignore_path = root / GITIGNORE_PATH
    blanket_found = False
    if gitignore_path.exists():
        for line in gitignore_path.read_text().splitlines():
            stripped = line.strip()
            if stripped in (".claude/", ".claude"):
                blanket_found = True
                break
    results.append(Result(
        "repo", "", "no blanket .claude/ gitignore",
        not blanket_found,
        "found blanket .claude/ ignore rule" if blanket_found else "",
    ))

    # 2. No broad ambient hooks
    settings_path = root / SETTINGS_PATH
    broad_hooks = []
    if settings_path.exists():
        try:
            settings = orjson.loads(settings_path.read_bytes())
            hooks = settings.get("hooks", {})
            for event_name, hook_list in hooks.items():
                if event_name not in HIGH_FREQ_EVENTS:
                    continue
                if not isinstance(hook_list, list):
                    continue
                for hook in hook_list:
                    matcher = hook.get("matcher")
                    if matcher is None:
                        broad_hooks.append(f"{event_name} (no matcher)")
        except Exception:
            pass
    results.append(Result(
        "repo", "", "no broad ambient hooks",
        len(broad_hooks) == 0,
        "; ".join(broad_hooks) if broad_hooks else "",
    ))

    # 3. State files gitignored
    all_ignored = True
    not_ignored = []
    for sf in STATE_FILES:
        try:
            cp = subprocess.run(
                ["git", "check-ignore", "-q", str(sf)],
                cwd=str(root),
                capture_output=True,
            )
            if cp.returncode != 0:
                all_ignored = False
                not_ignored.append(sf.name)
        except FileNotFoundError:
            # git not available
            all_ignored = False
            not_ignored.append(f"{sf.name} (git not found)")
    results.append(Result(
        "repo", "", "state files gitignored",
        all_ignored,
        f"not ignored: {', '.join(not_ignored)}" if not_ignored else "",
    ))

    # 4. No duplicate skill names
    skills = discover_skills(root)
    names = [s.name for s in skills]
    seen = set()
    dupes = set()
    for n in names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    results.append(Result(
        "repo", "", "no duplicate skill names",
        len(dupes) == 0,
        f"duplicates: {', '.join(sorted(dupes))}" if dupes else "",
    ))

    # 5. best_practices.md freshness
    bp_path = root / BEST_PRACTICES_PATH
    if bp_path.exists():
        first_line = bp_path.read_text().splitlines()[0] if bp_path.read_text() else ""
        bp_date = None
        if first_line.startswith("last updated:"):
            try:
                bp_date = date.fromisoformat(first_line.split(":", 1)[1].strip())
            except ValueError:
                pass
        if bp_date:
            days = (date.today() - bp_date).days
            results.append(Result(
                "repo", "", "best_practices.md fresh",
                days <= STALE_DAYS,
                f"{days}d" if days <= STALE_DAYS else f"{days}d > {STALE_DAYS}d",
            ))
        else:
            results.append(Result(
                "repo", "", "best_practices.md fresh",
                False,
                "missing or unparseable 'last updated' date",
            ))
    else:
        results.append(Result(
            "repo", "", "best_practices.md fresh",
            False,
            "file not found",
        ))

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_result(r: Result) -> str:
    """Format a single result as a line of output."""
    tag = "PASS" if r.passed else "FAIL"
    prefix = f"{r.category}/{r.name}" if r.name else r.category
    detail = f" ({r.detail})" if r.detail else ""
    return f"{tag}  {prefix:<35} {r.check}{detail}"


def main():
    parser = argparse.ArgumentParser(description="Red/green test suite for skill ecosystem properties.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show PASS results (default: only FAIL + summary)")
    parser.add_argument("--category", choices=["skills", "plugins", "repo"], help="Run only one category")
    args = parser.parse_args()

    root = Path(".")
    all_results: list[Result] = []

    runners = {
        "skills": test_skills,
        "plugins": test_plugins,
        "repo": test_repo_hygiene,
    }

    if args.category:
        all_results.extend(runners[args.category](root))
    else:
        for runner in runners.values():
            all_results.extend(runner(root))

    # Output
    passed = [r for r in all_results if r.passed]
    failed = [r for r in all_results if not r.passed]

    for r in all_results:
        if r.passed and not args.verbose:
            continue
        print(format_result(r))

    print()
    print(f"{len(passed)} passed, {len(failed)} failed")

    sys.exit(0 if len(failed) == 0 else 1)


if __name__ == "__main__":
    main()
