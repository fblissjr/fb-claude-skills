"""Red/green test suite for skill ecosystem properties.

Encodes the measurable checks from best practices as pass/fail assertions.
No pytest dependency. No network calls. No file writes. Pure read-only.
"""

import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import orjson

from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

from skill_maintainer.config import best_practices_file
from skill_maintainer.shared import (
    STALE_DAYS,
    TOKEN_BUDGET_CRITICAL,
    TOKEN_BUDGET_WARN,
    check_description_quality,
    discover_plugins,
    discover_skills,
    get_last_verified,
    measure_tokens,
)

PLUGIN_REQUIRED_FIELDS = ("name", "version", "description", "author", "repository")

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

        # 2. Token budget (skill_tokens only; refs are on-demand)
        token_info = measure_tokens(skill_dir)
        skill_tokens = token_info["skill_tokens"]
        budget_pass = skill_tokens < TOKEN_BUDGET_WARN
        detail = f"{skill_tokens:,} (refs: {token_info['ref_tokens']:,})"
        if not budget_pass:
            if skill_tokens >= TOKEN_BUDGET_CRITICAL:
                detail = f"{skill_tokens:,} > {TOKEN_BUDGET_CRITICAL:,} (refs: {token_info['ref_tokens']:,})"
            else:
                detail = f"{skill_tokens:,} > {TOKEN_BUDGET_WARN:,} (refs: {token_info['ref_tokens']:,})"
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

        lv_str, days_ago = get_last_verified(metadata)
        if lv_str and days_ago is not None:
            results.append(Result(
                "skill", name, "staleness",
                days_ago <= STALE_DAYS,
                f"{days_ago}d" if days_ago <= STALE_DAYS else f"{days_ago}d > {STALE_DAYS}d",
            ))
        elif lv_str:
            results.append(Result("skill", name, "staleness", False, f"invalid date: {lv_str}"))
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
    mp_path = root / ".claude-plugin" / "marketplace.json"
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

        # 2. Marketplace listing (only if marketplace.json exists)
        if marketplace_names:
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
    """Run repo-level checks."""
    results = []

    # 1. No blanket .claude/ gitignore
    gitignore_path = root / ".gitignore"
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
    settings_path = root / ".claude" / "settings.json"
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
    state_patterns = [".skill-maintainer/state/"]
    all_ignored = True
    not_ignored = []
    for pattern in state_patterns:
        try:
            cp = subprocess.run(
                ["git", "check-ignore", "-q", pattern],
                cwd=str(root),
                capture_output=True,
            )
            if cp.returncode != 0:
                all_ignored = False
                not_ignored.append(pattern)
        except FileNotFoundError:
            all_ignored = False
            not_ignored.append(f"{pattern} (git not found)")
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

    # 5. best_practices.md freshness (if it exists)
    bp_path = best_practices_file(root)
    if bp_path.exists():
        content = bp_path.read_text()
        first_line = content.splitlines()[0] if content else ""
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


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Red/green test suite for skill ecosystem properties.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show PASS results (default: only FAIL + summary)")
    parser.add_argument("--category", choices=["skills", "plugins", "repo"], help="Run only one category")
    parsed = parser.parse_args(args)

    root = parsed.dir
    all_results: list[Result] = []

    runners = {
        "skills": test_skills,
        "plugins": test_plugins,
        "repo": test_repo_hygiene,
    }

    labels = {"skills": "Running skill tests...", "plugins": "Running plugin tests...", "repo": "Running repo hygiene tests..."}

    if parsed.category:
        print(labels[parsed.category], file=sys.stderr, flush=True)
        all_results.extend(runners[parsed.category](root))
    else:
        for key, runner in runners.items():
            print(labels[key], file=sys.stderr, flush=True)
            all_results.extend(runner(root))

    # Output
    passed = [r for r in all_results if r.passed]
    failed = [r for r in all_results if not r.passed]

    for r in all_results:
        if r.passed and not parsed.verbose:
            continue
        print(format_result(r))

    print()
    print(f"{len(passed)} passed, {len(failed)} failed")

    sys.exit(0 if len(failed) == 0 else 1)
