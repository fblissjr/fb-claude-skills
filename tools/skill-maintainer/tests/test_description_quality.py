"""check_description_quality: the WHEN trigger is only meaningful when the
description can actually be matched against a user's phrasing.

Both cases here were found by running the check over this repo's 32 skills. The
only two failures were `advisor` and `model-routing`, which are also the only
two skills with `disable-model-invocation: true` -- so every failure the check
produced was a false positive of the same kind.
"""

from skill_maintainer.shared import check_description_quality


class TestWhenTriggerExemption:
    """A description that never enters context cannot carry a trigger phrase."""

    def test_model_invocable_skill_still_needs_a_trigger(self):
        desc = "Install the per-project delegation rule."
        assert "missing WHEN trigger" in check_description_quality(desc)

    def test_user_invoked_only_skill_is_exempt(self):
        desc = "Install the per-project delegation rule."
        issues = check_description_quality(desc, model_invocable=False)
        assert "missing WHEN trigger" not in issues

    def test_exemption_does_not_suppress_the_what_check(self):
        """Users still read the description in the slash-command menu, so it
        must say what the skill does even when the model never sees it."""
        issues = check_description_quality("", model_invocable=False)
        assert issues == ["no description"]

    def test_default_is_model_invocable(self):
        """Omitting the flag must not silently grant the exemption."""
        assert "missing WHEN trigger" in check_description_quality("Bump versions.")


class TestWhatVerbBreadth:
    """The verb list was a 10-item whitelist that missed most real verbs.

    It passed almost everything anyway because "use when" was in *both* the
    WHAT and WHEN lists, so the WHAT check had no independent signal -- its
    failures were identical to the WHEN check's across all 32 skills.
    """

    def test_recognizes_verbs_the_repo_actually_uses(self):
        # Every one of these leads a real description in this repo and was
        # reported as "missing WHAT verb" before the list was widened.
        for verb in [
            "Consult a higher-tier advisor model about the current session.",
            "Install, update, or remove the delegation rule.",
            "Enforces one rule: every path must be repo-relative.",
            "Audit an existing test suite for meaning and drift.",
            "Rewrite bloated prose into plain language.",
            "Reproduce this user's writing voice from evidence.",
            "Bump a plugin's version across all sources.",
            "Orchestrate end-of-session cleanup.",
        ]:
            issues = check_description_quality(verb, model_invocable=False)
            assert "missing WHAT verb" not in issues, verb

    def test_still_flags_a_description_with_no_verb_at_all(self):
        issues = check_description_quality(
            "A collection of assorted notes.", model_invocable=False
        )
        assert "missing WHAT verb" in issues
