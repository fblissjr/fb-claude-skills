"""skill-dashboard's token-budget check, run as TypeScript against the Python gate.

WHY THIS FILE EXISTS. `apps/skill-dashboard/mcp-app/src/utils/checks.ts` is a
deliberate port of this package's checks: the dashboard is an MCP App and cannot
import Python, so the copy has a real consumer. On 2026-09-21 the two had
diverged twice with every test green -- the dashboard still failed skills at
4,000 tokens (the threshold demoted here on 2026-08-13), and it summed every
`.md` in the skill directory where the gate counts SKILL.md alone. Per-engine
tests cannot see that: each engine is right by its own lights and the bug lives
between them. So this file runs both engines over one corpus and asserts they
AGREE, which is the only kind of test that earns a duplicated rule its place.

Skipped when bun or the dashboard's node_modules are unavailable, because the
TypeScript side cannot run; the skip reason says so rather than passing silently.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import orjson
import pytest

from skill_maintainer.shared import reattach_verdict
from skill_maintainer.tests import test_skills as run_skill_checks

REPO = Path(__file__).resolve().parents[3]
DASH = REPO / "apps/skill-dashboard/mcp-app"
CHECKS_TS = DASH / "src/utils/checks.ts"

pytestmark = pytest.mark.skipif(
    not CHECKS_TS.exists()
    or shutil.which("bun") is None
    or not (DASH / "node_modules").exists(),
    reason="skill-dashboard sources, bun, or its node_modules unavailable",
)

# Both band edges and a point either side of each, plus path-privacy's size on
# 2026-09-21 (inside the band) and heylook-provider's (over).
CORPUS = [0, 800, 13_249, 13_250, 16_304, 22_500, 22_501, 22_673, 40_000]


def _bun(script: str) -> object:
    r = subprocess.run(
        ["bun", "-e", script], cwd=DASH, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, f"bun failed: {r.stderr}"
    return orjson.loads(r.stdout.strip().splitlines()[-1])


def test_verdicts_agree_across_the_band():
    """Claim: for every corpus length, reattachVerdict (TS) == reattach_verdict (Python).

    Fails if either side's constants or comparison operators drift -- including
    the strict `>`/`<` at each edge, which the corpus straddles.
    """
    ts = _bun(
        "import { reattachVerdict } from './src/utils/checks.ts';"
        f"console.log(JSON.stringify({orjson.dumps(CORPUS).decode()}.map(reattachVerdict)));"
    )
    py = [reattach_verdict(c) for c in CORPUS]
    assert ts == py, f"engines disagree on {CORPUS}: ts={ts} py={py}"


def _skill(root: Path, name: str, skill_chars: int, ref_chars: int = 0) -> None:
    d = root / "skills" / name / "skills" / name
    (d / "references").mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\ndescription: Fixture skill pinning budget agreement for {name}.\n---\n\n"
    (d / "SKILL.md").write_text(fm + "x" * max(0, skill_chars - len(fm)))
    if ref_chars:
        (d / "references" / "big.md").write_text("y" * ref_chars)


def test_whole_skill_verdicts_agree_and_ignore_references():
    """Claim: on the same fixture repo, the dashboard's tokenBudget pass/fail equals
    the Python gate's for every skill -- including one whose references are huge
    but whose SKILL.md is small, which the dashboard used to fail by summing them.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill(root, "small", 800)
        _skill(root, "small-with-big-refs", 800, ref_chars=60_000)
        _skill(root, "banded", 16_304)
        _skill(root, "oversized", 22_501)

        py = {r.name: r.passed for r in run_skill_checks(root) if r.check == "token budget"}
        ts = _bun(
            "import { checkSkills } from './src/utils/checks.ts';"
            f"const r = checkSkills({orjson.dumps(str(root)).decode()});"
            "console.log(JSON.stringify(Object.fromEntries("
            "r.map(s => [s.name, s.checks.tokenBudget.passed]))));"
        )
        assert ts == py, f"dashboard and gate disagree: ts={ts} py={py}"
        assert py == {
            "small": True, "small-with-big-refs": True, "banded": True, "oversized": False,
        }, py
