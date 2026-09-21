"""The token budget gate fires on the re-attachment cap, and only where the estimate is sure.

Demoted 2026-08-13. The gate used to fail at TOKEN_BUDGET_WARN (4,000), which is
an opinion about attention rather than a measurement, and it sat red on two
skills that were ~1% over while nothing measured the skill listing -- the cost
that is actually paid every session. The gate now fires at
TOKEN_BUDGET_REATTACH (5,000), where behaviour genuinely changes: above it a
skill is silently truncated when re-attached after a compaction.

Banded 2026-09-21. The estimate used to be a flat chars/4, and measured against
`claude plugin details` it passed skills the first-party count put over the cut
(path-privacy: 4,076 by chars/4, ~5.7k by the CLI). Characters per token run
from ~2.65 on dense technical text to ~4.3 on prose, so the estimate now decides
only where it is certain: red when over even at the sparsest ratio, green when
under even at the densest, and "unverified" in between -- passing, and naming
the real measurement, rather than warning.

These arms exist because a threshold change is exactly the kind of edit that can
silently stop gating anything. Each one pins a side of a boundary, and the red
arm is the load-bearing one -- a gate that cannot go red is decoration.
"""

import tempfile
from pathlib import Path

from skill_maintainer.shared import (
    REATTACH_CHARS_PER_TOKEN_DENSE,
    REATTACH_CHARS_PER_TOKEN_SPARSE,
    TOKEN_BUDGET_REATTACH,
    TOKEN_BUDGET_WARN,
)

# Aliased: the source function is named `test_skills`, and pytest would collect
# it as a test case and error on its `root` argument. Same reason
# test_repo_hygiene_provenance.py aliases its import.
from skill_maintainer.tests import budget_scope_line
from skill_maintainer.tests import test_skills as run_skill_checks

# The band edges in characters. Derived from the constants rather than written
# as literals, so a change to either ratio moves the fixtures with it and the
# edge arms keep pinning the edge rather than a stale number.
RED_EDGE = int(TOKEN_BUDGET_REATTACH * REATTACH_CHARS_PER_TOKEN_SPARSE)  # 22,500
GREEN_EDGE = int(TOKEN_BUDGET_REATTACH * REATTACH_CHARS_PER_TOKEN_DENSE)  # 13,250


def _skill_of_chars(root: Path, name: str, chars: int) -> None:
    """Write a skill whose SKILL.md is exactly `chars` characters long."""
    skill_dir = root / "skills" / name / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        f"description: A fixture skill used to pin the token budget gate boundary for {name}.\n"
        "---\n\n"
    )
    body = "x" * max(0, chars - len(frontmatter))
    (skill_dir / "SKILL.md").write_text(frontmatter + body)
    assert len((skill_dir / "SKILL.md").read_text()) == max(chars, len(frontmatter))


def _budget_result(root: Path, name: str):
    for r in run_skill_checks(root):
        if r.name == name and r.check == "token budget":
            return r
    raise AssertionError(f"no token budget result for {name}")


def test_gate_goes_red_when_certainly_over():
    """The control: one character past the red edge must fail, or the gate is decoration.

    Claim: a SKILL.md long enough to exceed 5,000 tokens even at the sparsest
    observed ratio fails the board and names the consequence.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "oversized", RED_EDGE + 1)
        result = _budget_result(root, "oversized")
        assert not result.passed, (
            "a skill certainly above the re-attachment cap must fail the gate; "
            f"got passed=True with detail {result.detail!r}"
        )
        assert "re-attach" in result.detail, (
            f"failure should name the consequence, got {result.detail!r}"
        )


def test_red_edge_is_exclusive():
    """Exactly at the red edge is not certainly over, so it does not fail.

    Claim: the red verdict is strict (`>`). Without this arm, a `>=` mutation
    would pass every other test.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "at-red-edge", RED_EDGE)
        result = _budget_result(root, "at-red-edge")
        assert result.passed, f"exactly at the red edge must not fail; detail {result.detail!r}"
        assert "unverified" in result.detail


def test_band_passes_as_unverified_and_names_the_measurement():
    """Between the edges the estimate has no authority: pass, and hand it to a real count.

    Claim: a skill the flat chars/4 estimate called 4,076 tokens -- path-privacy's
    size on 2026-09-21, which the CLI measured at ~5.7k -- is reported as
    unverified with the command that settles it, not silently green.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "dense", 16_304)
        result = _budget_result(root, "dense")
        assert result.passed, f"an unverified skill must not fail the board; detail {result.detail!r}"
        assert "unverified" in result.detail, result.detail
        assert "claude plugin details" in result.detail, (
            f"an unverified verdict must name the measurement that settles it; got {result.detail!r}"
        )


def test_green_edge_is_exclusive():
    """Exactly at the green edge is not certainly under, so it is unverified.

    Claim: the green verdict is strict (`<`); one character less is green.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "at-green-edge", GREEN_EDGE)
        _skill_of_chars(root, "under-green-edge", GREEN_EDGE - 1)
        at_edge = _budget_result(root, "at-green-edge")
        under = _budget_result(root, "under-green-edge")
        assert at_edge.passed and "unverified" in at_edge.detail, at_edge.detail
        assert under.passed and "unverified" not in under.detail, under.detail


def test_gate_stays_green_between_the_soft_number_and_the_cap():
    """The demotion itself: over the house soft number reports but never fails.

    Claim: a skill whose chars/4 estimate sits between 4,000 and 5,000 passes,
    and the soft-threshold observation is still reported as not gated.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        midpoint_tokens = (TOKEN_BUDGET_WARN + TOKEN_BUDGET_REATTACH) // 2
        _skill_of_chars(root, "midband", midpoint_tokens * 4)
        result = _budget_result(root, "midband")
        assert result.passed, (
            f"a skill at ~{midpoint_tokens} tokens is over the house soft number but not "
            f"certainly over the cap, and must not fail; detail {result.detail!r}"
        )
        assert "not gated" in result.detail, (
            f"the soft-threshold observation should still be reported, got {result.detail!r}"
        )


def test_small_skill_passes_without_a_warning():
    """Green for the right reason: well under every number, no observation text.

    Claim: a small skill carries none of the red, soft, or unverified wording.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "small", 800)
        result = _budget_result(root, "small")
        assert result.passed
        assert "not gated" not in result.detail
        assert "re-attach" not in result.detail
        assert "unverified" not in result.detail


def test_scope_line_counts_every_verdict():
    """A green states its scope: the summary counts under, unverified and over, and names the unverified.

    Claim: the printed scope line is derived from the budget results, so an
    unverified skill is visible in default (non-verbose) output even though it
    passes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _skill_of_chars(root, "small-one", 800)
        _skill_of_chars(root, "small-two", 900)
        _skill_of_chars(root, "dense", 16_304)
        _skill_of_chars(root, "oversized", RED_EDGE + 1)
        line = budget_scope_line(run_skill_checks(root))
        assert line is not None
        assert "2 certainly under" in line, line
        assert "1 unverified" in line, line
        assert "1 over" in line, line
        assert "dense" in line, f"the unverified skill should be named; got {line!r}"
        assert "claude plugin details" in line, line


def test_scope_line_is_absent_without_budget_results():
    """No skills scanned means no scope claim, rather than a line reading '0 certainly under'."""
    assert budget_scope_line([]) is None
