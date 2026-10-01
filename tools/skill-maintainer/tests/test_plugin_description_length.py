"""Tests for the plugin.json description length gate.

Cowork's marketplace sync rejects a plugin whose manifest description runs
past 500 characters ("Plugin description must be at most 500 characters")
and syncs the rest of the marketplace without it. dev-conventions 0.20.0 sat
at 589 and never reached Cowork, while `claude plugin validate --strict`
passed it. Each case below pins one edge of that limit.
"""

import orjson

from skill_maintainer.tests import PLUGIN_DESCRIPTION_MAX, test_plugins as run_plugin_checks


def _write_plugin(root, description):
    d = root / "alpha"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_bytes(orjson.dumps({
        "name": "alpha", "version": "1.0.0", "description": description,
        "author": {"name": "x"}, "repository": "https://example.invalid",
    }))
    (d / "README.md").write_text("x")


def _length_result(root):
    return next(r for r in run_plugin_checks(root) if r.check == "description length")


def test_limit_matches_cowork():
    # The constant is the upstream limit; raising it reopens the silent drop.
    assert PLUGIN_DESCRIPTION_MAX == 500


def test_description_at_limit_passes(tmp_path):
    # Exactly 500 is accepted upstream; an off-by-one here would block a valid plugin.
    _write_plugin(tmp_path, "a" * PLUGIN_DESCRIPTION_MAX)
    assert _length_result(tmp_path).passed


def test_description_over_limit_fails(tmp_path):
    # The dev-conventions failure: one character over is dropped by Cowork.
    _write_plugin(tmp_path, "a" * (PLUGIN_DESCRIPTION_MAX + 1))
    r = _length_result(tmp_path)
    assert not r.passed
    assert "501" in r.detail and "500" in r.detail
