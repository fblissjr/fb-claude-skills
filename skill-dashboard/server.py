"""
skill-dashboard MCP server

Python-native MCP App using mcp-ui rawHtml. Auto-discovers skills by walking
SKILL.md files, reads last_verified from frontmatter, estimates token budgets,
and renders a self-contained HTML dashboard.

Transport: stdio (started by Claude Code via .mcp.json)
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import orjson
import yaml
from mcp.server.fastmcp import FastMCP
from mcp_ui_server import UIMetadataKey, create_ui_resource

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"

SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal"}
STALE_DAYS = 30

mcp = FastMCP("skill-dashboard")


def _discover_skills() -> list[Path]:
    """Find all SKILL.md files, return their parent directories."""
    results = []
    for skill_md in sorted(PROJECT_ROOT.rglob("SKILL.md")):
        if any(skip in skill_md.parts for skip in SKIP_DIRS):
            continue
        if ".backup" in str(skill_md):
            continue
        results.append(skill_md.parent)
    return results


def _parse_frontmatter(skill_dir: Path) -> dict[str, Any]:
    """Extract frontmatter fields from SKILL.md."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}


def _estimate_tokens(skill_dir: Path) -> int:
    """Estimate total tokens for text files in a skill directory."""
    total_chars = 0
    for f in skill_dir.rglob("*"):
        if f.is_dir() or f.name.startswith("."):
            continue
        if any(s in f.parts for s in SKIP_DIRS):
            continue
        if f.suffix in (".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml"):
            try:
                total_chars += len(f.read_text())
            except (OSError, UnicodeDecodeError):
                pass
    return total_chars // 4


def _status_from_last_verified(last_verified: str | None) -> str:
    if last_verified is None:
        return "unknown"
    try:
        lv_date = date.fromisoformat(last_verified)
        days = (date.today() - lv_date).days
        if days > STALE_DAYS:
            return "critical"
        if days > 14:
            return "stale"
        return "fresh"
    except ValueError:
        return "unknown"


def collect_skills() -> list[dict[str, Any]]:
    """Auto-discover skills and collect metadata."""
    skill_dirs = _discover_skills()
    skills = []

    for skill_dir in skill_dirs:
        fm = _parse_frontmatter(skill_dir)
        meta = fm.get("metadata", {}) or {}
        name = fm.get("name", skill_dir.name)
        version = str(meta.get("version", "")) or None
        last_verified = str(meta.get("last_verified", "")) or None

        token_count = _estimate_tokens(skill_dir)
        status = _status_from_last_verified(last_verified)

        # Compute relative path from project root
        try:
            rel_path = str(skill_dir.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_path = str(skill_dir)

        skills.append({
            "name": name,
            "path": rel_path,
            "version": version,
            "status": status,
            "last_checked": last_verified,
            "token_count": token_count,
            "sources": [],
        })

    order = {"critical": 0, "stale": 1, "fresh": 2, "unknown": 3}
    skills.sort(key=lambda s: (order.get(s["status"], 9), s["name"]))
    return skills


def render_dashboard(skills: list[dict[str, Any]]) -> str:
    """Inline skill data into the dashboard HTML template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    data = {
        "skills": skills,
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "skill_count": len(skills),
        },
    }

    data_json = orjson.dumps(data).decode("utf-8")
    html = template.replace("__SKILL_DATA__", data_json)
    return html


@mcp.tool()
def show_skill_dashboard() -> list:
    """
    Show a dashboard of all tracked skills in the current project.

    Returns a self-contained HTML dashboard with color-coded freshness status,
    token budget indicators, last-checked timestamps, and source dependencies
    for every skill tracked in the project.
    """
    skills = collect_skills()
    html = render_dashboard(skills)

    ui = create_ui_resource(
        {
            "uri": "ui://skill-dashboard/main",
            "content": {"type": "rawHtml", "htmlString": html},
            "encoding": "text",
            "uiMetadata": {
                UIMetadataKey.PREFERRED_FRAME_SIZE: ["1024px", "700px"],
            },
        }
    )
    return [ui]


if __name__ == "__main__":
    mcp.run(transport="stdio")
