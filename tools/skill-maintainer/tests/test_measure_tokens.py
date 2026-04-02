"""Tests for measure_tokens() split reporting (skill vs reference tokens)."""

import tempfile
from pathlib import Path

from skill_maintainer.shared import measure_tokens


def _make_skill(tmp: Path, skill_content: str, refs: dict[str, str] | None = None) -> Path:
    """Create a minimal skill directory with SKILL.md and optional references."""
    skill_dir = tmp / "test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_content)
    if refs:
        ref_dir = skill_dir / "references"
        ref_dir.mkdir(exist_ok=True)
        for name, content in refs.items():
            (ref_dir / name).write_text(content)
    return skill_dir


def test_returns_dict_with_split_counts():
    """measure_tokens() should return a dict with skill_tokens, ref_tokens, total."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = _make_skill(Path(tmp), "# SKILL\nSome content here.")
        result = measure_tokens(skill_dir)
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "skill_tokens" in result, "Missing 'skill_tokens' key"
        assert "ref_tokens" in result, "Missing 'ref_tokens' key"
        assert "total" in result, "Missing 'total' key"


def test_skill_only_no_refs():
    """With no references, ref_tokens should be 0 and total == skill_tokens."""
    with tempfile.TemporaryDirectory() as tmp:
        content = "x" * 400  # ~100 tokens
        skill_dir = _make_skill(Path(tmp), content)
        result = measure_tokens(skill_dir)
        assert result["skill_tokens"] == 100
        assert result["ref_tokens"] == 0
        assert result["total"] == 100


def test_skill_with_refs_split():
    """References should be counted separately from SKILL.md."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_content = "x" * 400  # 100 tokens
        ref_content = "y" * 800  # 200 tokens
        skill_dir = _make_skill(
            Path(tmp), skill_content,
            refs={"patterns.md": ref_content},
        )
        result = measure_tokens(skill_dir)
        assert result["skill_tokens"] == 100
        assert result["ref_tokens"] == 200
        assert result["total"] == 300


def test_backward_compat_int_comparison():
    """Total should support direct integer comparison for backward compat."""
    with tempfile.TemporaryDirectory() as tmp:
        content = "x" * 400  # 100 tokens
        skill_dir = _make_skill(Path(tmp), content)
        result = measure_tokens(skill_dir)
        # Callers that do `tokens > THRESHOLD` should still work
        assert result["total"] > 50
        assert result["total"] < 200
