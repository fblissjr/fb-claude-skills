"""The token budget gate fires on the re-attachment cap, not the house soft numbers.

Demoted 2026-08-13. The gate used to fail at TOKEN_BUDGET_WARN (4,000), which is
an opinion about attention rather than a measurement, and it sat red on two
skills that were ~1% over while nothing measured the skill listing -- the cost
that is actually paid every session. The gate now fires at
TOKEN_BUDGET_REATTACH (5,000), where behaviour genuinely changes: above it a
skill is silently truncated when re-attached after a compaction.

These arms exist because a threshold change is exactly the kind of edit that can
silently stop gating anything. Each one pins a side of the new boundary, and the
red arm is the load-bearing one -- a gate that cannot go red is decoration.
"""

import tempfile
from pathlib import Path

from skill_maintainer.shared import (
    TOKEN_BUDGET_REATTACH,
    TOKEN_BUDGET_WARN,
)

# Aliased: the source function is named `test_skills`, and pytest would collect
# it as a test case and error on its `root` argument. Same reason
# test_repo_hygiene_provenance.py aliases its import.
from skill_maintainer.tests import test_skills as run_skill_checks


def _skill_of_tokens(root: Path, name: str, tokens: int) -> None:
    """Write a skill whose SKILL.md measures approximately `tokens` (4 chars = 1)."""
    skill_dir = root / "skills" / name / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        f"description: A fixture skill used to pin the token budget gate boundary for {name}.\n"
        "---\n\n"
    )
    body = "x" * max(0, (tokens * 4) - len(frontmatter))
    (skill_dir / "SKILL.md").write_text(frontmatter + body)


def _budget_result(root: Path, name: str):
    for r in run_skill_checks(root):
        if r.name == name and r.check == "token budget":
            return r
    raise AssertionError(f"no token budget result for {name}")


def test_gate_goes_red_above_the_reattachment_cap():
    """The control: a skill over 5,000 tokens must fail, or the gate is decoration."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_tokens(root, "oversized", TOKEN_BUDGET_REATTACH + 500)
        result = _budget_result(root, "oversized")
        assert not result.passed, (
            "a skill above the re-attachment cap must fail the gate; "
            f"got passed=True with detail {result.detail!r}"
        )
        assert "re-attach" in result.detail, (
            f"failure should name the consequence, got {result.detail!r}"
        )


def test_gate_stays_green_between_the_soft_number_and_the_cap():
    """The demotion itself: 4,000-5,000 reports but no longer fails."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        midpoint = (TOKEN_BUDGET_WARN + TOKEN_BUDGET_REATTACH) // 2
        _skill_of_tokens(root, "midband", midpoint)
        result = _budget_result(root, "midband")
        assert result.passed, (
            f"a skill at {midpoint} tokens is over the house soft number but under "
            f"the cap, and must not fail; detail {result.detail!r}"
        )
        assert "not gated" in result.detail, (
            f"the soft-threshold observation should still be reported, got {result.detail!r}"
        )


def test_small_skill_passes_without_a_warning():
    """Green for the right reason: well under both numbers, no observation text."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_tokens(root, "small", 200)
        result = _budget_result(root, "small")
        assert result.passed
        assert "not gated" not in result.detail
        assert "re-attach" not in result.detail
