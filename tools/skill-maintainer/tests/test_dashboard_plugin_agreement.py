"""skill-dashboard's plugin description-length check, run as TypeScript against the Python gate.

Same reason as test_dashboard_budget_agreement.py: `checks.ts` is a port with a
real consumer, and a rule duplicated across two engines is only safe while a
test runs both over one corpus and asserts they agree. The rule here is
Cowork's 500-character limit on a plugin.json description, which dropped
dev-conventions 0.20.0 from the marketplace sync.

Skipped when bun or the dashboard's node_modules are unavailable.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import orjson
import pytest

from skill_maintainer.tests import PLUGIN_DESCRIPTION_MAX, test_plugins as run_plugin_checks

REPO = Path(__file__).resolve().parents[3]
DASH = REPO / "apps/skill-dashboard/mcp-app"
CHECKS_TS = DASH / "src/utils/checks.ts"

pytestmark = pytest.mark.skipif(
    not CHECKS_TS.exists()
    or shutil.which("bun") is None
    or not (DASH / "node_modules").exists(),
    reason="skill-dashboard sources, bun, or its node_modules unavailable",
)


def _plugin(root: Path, name: str, desc_len: int) -> None:
    d = root / "skills" / name
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_bytes(orjson.dumps({
        "name": name, "version": "1.0.0", "description": "d" * desc_len,
        "author": {"name": "x"}, "repository": "https://example.invalid",
    }))
    (d / "README.md").write_text("x")


def test_description_length_verdicts_agree_at_the_edge():
    """Claim: the dashboard's descriptionLength pass/fail equals the Python gate's
    on both sides of the limit. Fails if either engine's constant or its `<=`
    drifts, or if the dashboard stops reporting the check at all.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _plugin(root, "at-limit", PLUGIN_DESCRIPTION_MAX)
        _plugin(root, "over-limit", PLUGIN_DESCRIPTION_MAX + 1)

        py = {r.name: r.passed for r in run_plugin_checks(root) if r.check == "description length"}
        r = subprocess.run(
            ["bun", "-e",
             "import { checkPlugins } from './src/utils/checks.ts';"
             f"const r = checkPlugins({orjson.dumps(str(root)).decode()});"
             "console.log(JSON.stringify(Object.fromEntries("
             "r.map(p => [p.name, p.checks.descriptionLength?.passed ?? null]))));"],
            cwd=DASH, capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, f"bun failed: {r.stderr}"
        ts = orjson.loads(r.stdout.strip().splitlines()[-1])
        assert ts == py, f"dashboard and gate disagree: ts={ts} py={py}"
        assert py == {"at-limit": True, "over-limit": False}, py
