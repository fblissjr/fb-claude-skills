"""Red/green test suite for skill ecosystem properties.

Encodes the measurable checks from best practices as pass/fail assertions.
No pytest dependency. No network calls. No file writes. Pure read-only.
"""

import re
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
    get_review_interval,
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
        interval = get_review_interval(metadata)
        if lv_str and days_ago is not None:
            results.append(Result(
                "skill", name, "staleness",
                days_ago <= interval,
                f"{days_ago}d" if days_ago <= interval else f"{days_ago}d > {interval}d",
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


def check_version_alignment(root: Path) -> list[Result]:
    """Compare every plugin.json version against its marketplace.json entry.

    The pre-commit hook only inspects plugins a given commit happens to touch,
    so a marketplace entry can drift for releases at a time without anything
    noticing -- path-privacy sat five versions behind that way, and installs
    resolved the stale version the whole time. This walks the repo instead.

    Returns [] when there is no marketplace.json: a plugin repo without one is
    legitimate, and inventing failures there would train people to ignore this.
    """
    mp_path = root / ".claude-plugin" / "marketplace.json"
    if not mp_path.exists():
        return []

    try:
        entries = orjson.loads(mp_path.read_bytes()).get("plugins", [])
    except Exception as e:
        return [Result("repo", "", "version alignment", False, f"unreadable marketplace.json: {e}")]

    results = []
    listed: dict[str, str] = {}

    for entry in entries:
        name = entry.get("name", "")
        listed[name] = entry.get("version", "")
        # removeprefix, not lstrip: lstrip strips a character SET, so a source of
        # "./.claude/thing" became "claude/thing" and the check then reported a
        # missing plugin.json at a path that was never right.
        source = (entry.get("source") or f"./{name}").removeprefix("./")
        pj = root / source / ".claude-plugin" / "plugin.json"
        if not pj.exists():
            results.append(Result(
                "repo", name, "version alignment", False,
                f"marketplace lists '{name}' but {source}/.claude-plugin/plugin.json does not exist",
            ))
            continue
        try:
            real = orjson.loads(pj.read_bytes()).get("version", "")
        except Exception as e:
            results.append(Result("repo", name, "version alignment", False, f"unreadable plugin.json: {e}"))
            continue
        aligned = real == entry.get("version")
        results.append(Result(
            "repo", name, "version alignment", aligned,
            "" if aligned else f"marketplace.json={entry.get('version')} vs plugin.json={real}",
        ))

    # A plugin on disk that nobody can install is the same class of bug, seen
    # from the other side.
    for plugin_dir in discover_plugins(root):
        try:
            name = orjson.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_bytes()).get("name", "")
        except Exception as e:
            # Do NOT skip. A corrupt manifest would otherwise remove the plugin
            # from the very check meant to catch plugins nobody can install, and
            # the check would report green -- the same silent-drift failure this
            # function exists to prevent.
            results.append(Result(
                "repo", plugin_dir.name, "version alignment", False,
                f"unreadable plugin.json at {plugin_dir.name}: {e}",
            ))
            continue
        if name and name not in listed:
            results.append(Result(
                "repo", name, "version alignment", False,
                f"plugin '{name}' exists on disk but is not in marketplace.json",
            ))

    return results


def check_changelog_version(root: Path) -> list[Result]:
    """The top `## X.Y.Z` in CHANGELOG.md must equal the root pyproject version.

    Proposed during cross-review after a changelog insert matched `# changelog`
    instead of the version heading below it: the entry landed with no version
    and the repo version was never bumped. Nothing in the repo would have caught
    either -- `check_version_alignment` compares plugin manifests, and the
    pre-commit only warns when content changes with no version file staged, and
    version files *were* staged.

    Both failures violate this one comparison, which is exact rather than
    heuristic and can therefore legitimately gate. Returns [] when either file
    is absent: a repo without a changelog is a legitimate shape, and inventing
    failures for it is how a check gets ignored.
    """
    changelog = root / "CHANGELOG.md"
    pyproject = root / "pyproject.toml"
    if not changelog.exists() or not pyproject.exists():
        return []

    ver = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.M)
    if not ver:
        return []

    text = changelog.read_text()
    heading = re.search(r"^## (\d+\.\d+\.\d+)\s*$", text, re.M)
    if not heading:
        return [Result("repo", "", "changelog version", False,
                       "CHANGELOG.md has no `## X.Y.Z` heading")]

    # Anything other than the title before the first version heading means an
    # entry was written without one -- the exact failure this exists to catch.
    preamble = text[: heading.start()]
    stray = [ln for ln in preamble.splitlines()
             if ln.strip() and not ln.startswith("# ")]
    if stray:
        return [Result("repo", "", "changelog version", False,
                       f"content above the first version heading: {stray[0][:60]!r}")]

    ok = heading.group(1) == ver.group(1)
    return [Result("repo", "", "changelog version", ok,
                   "" if ok else
                   f"pyproject={ver.group(1)} but top CHANGELOG heading={heading.group(1)}")]


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
    # Repo-wide plugin/marketplace version alignment.
    results.extend(check_version_alignment(root))

    # Changelog heading vs repo version.
    results.extend(check_changelog_version(root))

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

    # 6. best_practices.md copies in sync
    #    Canonical: skills/skill-maintainer/references/best_practices.md
    #    Per-repo:  .skill-maintainer/best_practices.md
    #    Only checked when both exist (i.e., within the skill-maintainer repo itself).
    canonical_bp = _find_canonical_best_practices(root)
    if canonical_bp and bp_path.exists() and canonical_bp != bp_path:
        in_sync = canonical_bp.read_text() == bp_path.read_text()
        results.append(Result(
            "repo", "", "best_practices.md copies in sync",
            in_sync,
            "" if in_sync else f"{canonical_bp.relative_to(root)} != {bp_path.relative_to(root)}",
        ))

    return results


def _find_canonical_best_practices(root: Path) -> Path | None:
    """Find the plugin-bundled best_practices.md (canonical copy).

    Searches for skills/skill-maintainer/references/best_practices.md
    relative to root. Returns None if not found (i.e., not in the
    skill-maintainer source repo).
    """
    candidate = root / "skills" / "skill-maintainer" / "references" / "best_practices.md"
    return candidate if candidate.exists() else None


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
