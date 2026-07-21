"""Tests for per-skill review intervals.

A single global 30-day staleness window is wrong for a repo whose skills track
sources of very different volatility: the Claude Code docs move weekly, Kimball
dimensional modeling has not moved since the 1990s. Applying 30 days to both
guarantees a permanently-red board, which is how a signal gets ignored.
`metadata.review_interval_days` lets each skill declare its own window.
"""

from skill_maintainer.shared import STALE_DAYS, get_review_interval


def test_defaults_to_global_stale_days_when_absent():
    """A skill that says nothing keeps today's behaviour."""
    assert get_review_interval({}) == STALE_DAYS
    assert get_review_interval({"metadata": {}}) == STALE_DAYS
    assert get_review_interval({"metadata": {"version": "1.0.0"}}) == STALE_DAYS


def test_reads_explicit_interval():
    """A skill tracking a stable source can declare a longer window."""
    assert get_review_interval({"metadata": {"review_interval_days": 365}}) == 365
    assert get_review_interval({"metadata": {"review_interval_days": 7}}) == 7


def test_accepts_string_values_from_yaml():
    """YAML may hand back a string; treat it as a number."""
    assert get_review_interval({"metadata": {"review_interval_days": "180"}}) == 180


def test_rejects_nonsense_values_by_falling_back():
    """Garbage must not silently become an infinite window."""
    for bad in ["soon", "", None, 0, -30, 3.5e400]:
        assert get_review_interval({"metadata": {"review_interval_days": bad}}) == STALE_DAYS


def test_non_dict_metadata_does_not_crash():
    """Frontmatter is user input; a scalar `metadata:` must not raise."""
    assert get_review_interval({"metadata": "nope"}) == STALE_DAYS
    assert get_review_interval({"metadata": None}) == STALE_DAYS
