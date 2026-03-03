"""
skill-dashboard MCP server

Python-native MCP App using mcp-ui rawHtml. Runs the full run_tests.py suite
(skills, plugins, repo hygiene) and renders results as a self-contained HTML dashboard.

Transport: stdio (started by Claude Code via root .mcp.json)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import orjson
from mcp.server.fastmcp import FastMCP
from mcp_ui_server import UIMetadataKey, create_ui_resource

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"

# Make skill-maintainer/scripts importable
sys.path.insert(0, str(PROJECT_ROOT / "skill-maintainer" / "scripts"))

from run_tests import Result, test_plugins, test_repo_hygiene, test_skills  # noqa: E402
from shared import TOKEN_BUDGET_CRITICAL, TOKEN_BUDGET_WARN  # noqa: E402

mcp = FastMCP("skill-dashboard")


def _group_results(results: list[Result]) -> list[dict[str, Any]]:
    """Group Results by entity name into {name, checks: {check_name: {passed, detail}}}."""
    grouped: dict[str, dict[str, Any]] = {}
    for r in results:
        if r.name not in grouped:
            grouped[r.name] = {"name": r.name, "checks": {}}
        grouped[r.name]["checks"][r.check] = {
            "passed": r.passed,
            "detail": r.detail,
        }
    return sorted(grouped.values(), key=lambda e: e["name"])


def collect_data(root: Path) -> dict[str, Any]:
    """Run all test suites and transform Results into dashboard JSON."""
    skill_results = test_skills(root)
    plugin_results = test_plugins(root)
    repo_results = test_repo_hygiene(root)

    all_results = skill_results + plugin_results + repo_results
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)

    return {
        "skills": _group_results(skill_results),
        "plugins": _group_results(plugin_results),
        "repo": [
            {"check": r.check, "passed": r.passed, "detail": r.detail}
            for r in repo_results
        ],
        "summary": {"passed": passed, "failed": failed, "total": passed + failed},
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "budget_warn": TOKEN_BUDGET_WARN,
            "budget_critical": TOKEN_BUDGET_CRITICAL,
        },
    }


def render_dashboard(data: dict[str, Any]) -> str:
    """Inline data into the dashboard HTML template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data_json = orjson.dumps(data).decode("utf-8")
    html = template.replace("__DASHBOARD_DATA__", data_json)
    return html


@mcp.tool()
def show_skill_dashboard() -> list:
    """
    Show a dashboard of all tracked skills, plugins, and repo hygiene checks.

    Returns a self-contained HTML dashboard with color-coded pass/fail indicators,
    token budget bars, freshness status, spec compliance, description quality,
    plugin manifest checks, and repo-level hygiene checks.
    """
    data = collect_data(PROJECT_ROOT)
    html = render_dashboard(data)

    ui = create_ui_resource(
        {
            "uri": "ui://skill-dashboard/main",
            "content": {"type": "rawHtml", "htmlString": html},
            "encoding": "text",
            "uiMetadata": {
                UIMetadataKey.PREFERRED_FRAME_SIZE: ["1024px", "800px"],
            },
        }
    )
    return [ui]


if __name__ == "__main__":
    mcp.run(transport="stdio")
