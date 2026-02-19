"""
skill-dashboard MCP server

Python-native MCP App using mcp-ui rawHtml. Reads skill registry from config.yaml,
parses SKILL.md frontmatter for version info, queries DuckDB store for freshness and
token budget data, and renders a self-contained HTML dashboard.

Transport: stdio (started by Claude Code via .mcp.json)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import orjson
import yaml
from mcp.server.fastmcp import FastMCP
from mcp_ui_server import UIMetadataKey, create_ui_resource

# Resolve project root (two levels up from this file: skill-dashboard/server.py)
PROJECT_ROOT = Path(__file__).parent.parent

CONFIG_PATH = PROJECT_ROOT / "skill-maintainer" / "config.yaml"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"
DUCKDB_PATH = PROJECT_ROOT / "skill-maintainer" / "state" / "skill_maintainer.duckdb"

mcp = FastMCP("skill-dashboard")


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"skills": {}}
    with open(CONFIG_PATH, "rb") as f:
        return yaml.safe_load(f) or {}


def _parse_frontmatter_version(skill_path: Path) -> str | None:
    """Extract version from SKILL.md YAML frontmatter."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None
    text = skill_md.read_text(encoding="utf-8")
    # Match --- ... --- block at start
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        meta = fm.get("metadata", {}) or {}
        return str(meta.get("version", "")) or None
    except Exception:
        return None


def _skill_path_exists(relative_path: str) -> tuple[bool, Path]:
    """Resolve a skill path relative to project root."""
    p = PROJECT_ROOT / relative_path.lstrip("./")
    return p.exists(), p


def _file_mtime_days(path: Path) -> float | None:
    """Return age in days of the most recently modified file in a directory."""
    if not path.exists():
        return None
    mtimes = [f.stat().st_mtime for f in path.rglob("*") if f.is_file()]
    if not mtimes:
        return None
    newest = max(mtimes)
    age = (datetime.now(timezone.utc).timestamp() - newest) / 86400
    return round(age, 1)


def _status_from_age(age_days: float | None, skill_exists: bool) -> str:
    if not skill_exists:
        return "critical"
    if age_days is None:
        return "unknown"
    if age_days > 14:
        return "critical"
    if age_days > 7:
        return "stale"
    return "fresh"


def _query_duckdb(skill_names: list[str]) -> dict[str, dict[str, Any]]:
    """Query DuckDB store for freshness and budget data. Returns {} if unavailable."""
    if not DUCKDB_PATH.exists():
        return {}
    try:
        import duckdb
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        # Freshness: v_skill_freshness has skill_name, days_since_check, is_current
        freshness_rows = con.execute(
            """
            SELECT skill_name, days_since_check, last_checked
            FROM v_skill_freshness
            WHERE skill_name = ANY(?)
            """,
            [skill_names],
        ).fetchall()
        freshness: dict[str, dict[str, Any]] = {}
        for row in freshness_rows:
            freshness[row[0]] = {
                "days_since_check": row[1],
                "last_checked": str(row[2]) if row[2] else None,
            }

        # Budget: v_skill_budget has skill_name, total_tokens
        budget_rows = con.execute(
            """
            SELECT skill_name, total_tokens
            FROM v_skill_budget
            WHERE skill_name = ANY(?)
            """,
            [skill_names],
        ).fetchall()
        budget: dict[str, int] = {row[0]: row[1] for row in budget_rows}

        con.close()

        # Merge
        result: dict[str, dict[str, Any]] = {}
        for name in skill_names:
            f = freshness.get(name, {})
            result[name] = {
                "days_since_check": f.get("days_since_check"),
                "last_checked": f.get("last_checked"),
                "token_count": budget.get(name),
            }
        return result
    except Exception:
        return {}


def collect_skills() -> tuple[list[dict[str, Any]], bool]:
    """
    Read config.yaml + SKILL.md files + DuckDB store.
    Returns (skills_list, duckdb_available).
    """
    config = _load_config()
    skills_config: dict[str, Any] = config.get("skills", {}) or {}

    skill_names = list(skills_config.keys())
    db_data = _query_duckdb(skill_names)
    duckdb_available = bool(db_data)

    skills = []
    for name, cfg in skills_config.items():
        relative_path = cfg.get("path", "")
        path_exists, skill_dir = _skill_path_exists(relative_path)

        version = _parse_frontmatter_version(skill_dir) if path_exists else None
        sources: list[str] = cfg.get("sources", []) or []

        if duckdb_available and name in db_data:
            d = db_data[name]
            age_days = d.get("days_since_check")
            last_checked_raw = d.get("last_checked")
            last_checked = (
                last_checked_raw[:16].replace("T", " ")
                if last_checked_raw
                else None
            )
            token_count = d.get("token_count")
            status = _status_from_age(age_days, path_exists)
        else:
            age_days = _file_mtime_days(skill_dir) if path_exists else None
            last_checked = (
                f"{age_days}d ago" if age_days is not None else None
            )
            token_count = None
            status = _status_from_age(age_days, path_exists)

        skills.append(
            {
                "name": name,
                "path": relative_path,
                "version": version,
                "status": status,
                "last_checked": last_checked,
                "token_count": token_count,
                "sources": sources,
            }
        )

    # Sort: critical first, then stale, then fresh, then unknown
    order = {"critical": 0, "stale": 1, "fresh": 2, "unknown": 3}
    skills.sort(key=lambda s: (order.get(s["status"], 9), s["name"]))
    return skills, duckdb_available


def render_dashboard(skills: list[dict[str, Any]], duckdb_available: bool) -> str:
    """Inline skill data into the dashboard HTML template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    data = {
        "skills": skills,
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "duckdb_available": duckdb_available,
            "skill_count": len(skills),
        },
    }

    # Inject data into the template placeholder
    data_json = orjson.dumps(data).decode("utf-8")
    html = template.replace("__SKILL_DATA__", data_json)
    return html


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------

@mcp.tool()
def show_skill_dashboard() -> list:
    """
    Show a dashboard of all tracked skills in the current project.

    Returns a self-contained HTML dashboard with color-coded freshness status,
    token budget indicators, last-checked timestamps, and source dependencies
    for every skill tracked in skill-maintainer/config.yaml.
    """
    skills, duckdb_available = collect_skills()
    html = render_dashboard(skills, duckdb_available)

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
