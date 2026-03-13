"""Shared constants and utilities for skill-maintainer."""

from pathlib import Path

SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal"}
TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000
STALE_DAYS = 30


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


def discover_plugins(root: Path) -> list[Path]:
    """Find all plugin directories (have .claude-plugin/plugin.json), skip coderef/."""
    results = []
    for pj in sorted(root.rglob(".claude-plugin/plugin.json")):
        if any(skip in pj.parts for skip in SKIP_DIRS):
            continue
        # plugin dir is parent of .claude-plugin/
        plugin_dir = pj.parent.parent
        # skip the root marketplace (root .claude-plugin/ is not a plugin)
        if plugin_dir == root:
            continue
        results.append(plugin_dir)
    return results


def measure_tokens(skill_dir: Path) -> int:
    """Estimate total context tokens for markdown files in a skill directory.

    Only counts .md files since those are loaded into context via progressive
    disclosure. Scripts (.py, .sh) are executed, not loaded. Config files
    (.json, .yaml) are not part of the skill context window budget.
    """
    total_chars = 0
    skip = SKIP_DIRS | {"state"}
    for f in skill_dir.rglob("*"):
        if f.is_dir() or f.name.startswith("."):
            continue
        if any(s in f.parts for s in skip):
            continue
        if f.suffix == ".md":
            try:
                total_chars += len(f.read_text())
            except (OSError, UnicodeDecodeError):
                pass
    return total_chars // 4


def get_last_verified(metadata: dict) -> tuple[str | None, int | None]:
    """Extract last_verified date and days-ago from parsed frontmatter metadata.

    Returns (date_str, days_ago). Either or both may be None.
    """
    from datetime import date

    meta = metadata.get("metadata", {})
    if not isinstance(meta, dict):
        return None, None
    lv = meta.get("last_verified")
    if not lv:
        return None, None
    lv_str = str(lv)
    try:
        lv_date = date.fromisoformat(lv_str)
        days_ago = (date.today() - lv_date).days
        return lv_str, days_ago
    except ValueError:
        return lv_str, None


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
