"""metadata.freshness: "cascade" replaces the calendar window for skills whose
source is in-repo code (dates-are-look-triggers migration, step 1, 2026-08-04).
The calendar interval is a proxy for source movement; where movement is
observable in-repo, the version cascade is the freshness mechanism and elapsed
time stops being evidence. File-level claim: delete this file and cascade
skills silently return to being flagged stale by a clock their source never
consults.
"""

from pathlib import Path

from skill_maintainer.freshness import check_skill
from skill_maintainer.quality import _is_stale
from skill_maintainer.shared import freshness_mode


def _make_skill(tmp_path: Path, meta_lines: list[str]) -> Path:
    skill_dir = tmp_path / "some-skill"
    skill_dir.mkdir()
    body = "---\n" + "\n".join(
        ["name: some-skill", "description: a test fixture skill", "metadata:"]
        + [f"  {line}" for line in meta_lines]
    ) + "\n---\n\n# some-skill\n"
    (skill_dir / "SKILL.md").write_text(body)
    return skill_dir


def test_cascade_skill_ignores_calendar_age(tmp_path):
    # Claim: a skill declaring freshness: cascade is never stale by elapsed
    # time alone -- the whole point of the migration. Deleting this case
    # un-pins the exemption.
    skill_dir = _make_skill(tmp_path, ['last_verified: "2020-01-01"', 'freshness: "cascade"'])
    result = check_skill(skill_dir)
    assert result["is_stale"] is False
    assert result["mechanism"] == "cascade"


def test_cascade_conflict_with_interval_is_reported(tmp_path):
    # Claim: declaring both mechanisms is a config error, not a quiet
    # precedence choice -- one skill, one freshness mechanism. Deleting this
    # case lets both fields coexist silently and the pair drift.
    skill_dir = _make_skill(
        tmp_path,
        ['last_verified: "2026-08-04"', 'freshness: "cascade"', 'review_interval_days: "365"'],
    )
    result = check_skill(skill_dir)
    assert result["is_stale"] is True
    assert "both" in (result["message"] or "")


def test_unknown_mechanism_keeps_the_calendar(tmp_path):
    # Claim (pin): a typo'd mechanism must not grant an unbounded window --
    # same principle get_review_interval already applies to bad intervals.
    # Born green; fallibility proven at birth by mutating
    # get_freshness_mechanism to accept any string (went red), then reverted.
    skill_dir = _make_skill(tmp_path, ['last_verified: "2020-01-01"', 'freshness: "vibes"'])
    result = check_skill(skill_dir)
    assert result["is_stale"] is True


def test_quality_stale_respects_cascade():
    # Claim: the quality report's staleness column honours the declared
    # mechanism through the same helper, so the two commands cannot disagree
    # about the same skill. Deleting this case lets quality.py keep counting
    # cascade skills stale.
    r = {"days_ago": 400, "review_interval": 30, "freshness_mode": "cascade"}
    assert _is_stale(r) is False


def test_skill_maintain_test_staleness_respects_cascade(tmp_path):
    # Claim: the third staleness consumer -- `skill-maintain test`'s per-skill
    # rows -- honours the mechanism too. This is the path that regressed
    # first: removing review_interval_days dropped converted skills to the
    # 30-day default and turned the board red. Deleting this case lets that
    # regression return.
    from skill_maintainer.tests import test_skills

    _make_skill(tmp_path, ['last_verified: "2020-01-01"', 'freshness: "cascade"'])
    rows = [r for r in test_skills(tmp_path) if r.check == "staleness"]
    assert rows and all(r.passed for r in rows)


def test_freshness_mode_three_way():
    # Claim: the mode derivation itself -- cascade only when declared alone,
    # conflict when paired with an interval, calendar otherwise.
    assert freshness_mode({"metadata": {"freshness": "cascade"}}) == "cascade"
    assert freshness_mode(
        {"metadata": {"freshness": "cascade", "review_interval_days": "365"}}
    ) == "conflict"
    assert freshness_mode({"metadata": {"review_interval_days": "90"}}) == "calendar"
    assert freshness_mode({}) == "calendar"
