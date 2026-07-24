"""Tests for the Claude Code skill-schema validator (skill_maintainer.cc_schema).

The gate must accept Claude Code's frontmatter fields (the old cross-vendor
allowlist rejected them), still catch unknown fields and name violations, and
offer a strict cross-vendor portability check.
"""

from pathlib import Path

from skill_maintainer.cc_schema import (
    BASE_SPEC_FIELDS,
    portability_warnings,
    validate_cc,
    validate_frontmatter,
)

GOOD_DESC = "Does a thing. Use when the user wants that thing done."


def _skill_dir(tmp_path, frontmatter, name="demo"):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(frontmatter, encoding="utf-8")
    return d


def _meta(**extra):
    m = {"name": "demo", "description": GOOD_DESC}
    m.update(extra)
    return m


def test_accepts_claude_code_extension_fields():
    # These are exactly the fields the old cross-vendor allowlist rejected.
    meta = _meta(**{
        "disable-model-invocation": "true",
        "argument-hint": "[show | reset]",
        "model": "inherit",
        "arguments": "target",
    })
    errors = validate_frontmatter(meta, Path("demo"))
    assert errors == [], errors


def test_accepts_base_spec_fields():
    meta = _meta(license="MIT", metadata={"k": "v"}, compatibility="Claude Code")
    assert validate_frontmatter(meta, Path("demo")) == []


def test_rejects_unknown_field():
    # A typo of a real field must still be caught.
    meta = _meta(**{"disable-model-invokation": "true"})
    errors = validate_frontmatter(meta, Path("demo"))
    assert any("Unexpected fields" in e and "disable-model-invokation" in e for e in errors)


def test_strict_mode_rejects_cc_extensions():
    meta = _meta(**{"disable-model-invocation": "true"})
    # Default (CC) allowlist: fine.
    assert validate_frontmatter(meta, Path("demo")) == []
    # Cross-vendor allowlist: the CC field is now unexpected.
    strict = validate_frontmatter(meta, Path("demo"), allowed=BASE_SPEC_FIELDS)
    assert any("Unexpected fields" in e for e in strict)


def test_missing_required_fields():
    assert any("name" in e for e in validate_frontmatter({"description": GOOD_DESC}, Path("x")))
    assert any("description" in e for e in validate_frontmatter({"name": "x"}, Path("x")))


def test_name_rules():
    assert any("lowercase" in e for e in validate_frontmatter(
        {"name": "Demo", "description": GOOD_DESC}, Path("Demo")))
    assert any("consecutive" in e for e in validate_frontmatter(
        {"name": "a--b", "description": GOOD_DESC}, Path("a--b")))
    assert any("match" in e for e in validate_frontmatter(
        {"name": "demo", "description": GOOD_DESC}, Path("other")))


def test_portability_warnings_flags_extensions_only():
    meta = _meta(**{"disable-model-invocation": "true", "model": "inherit", "license": "MIT"})
    warns = portability_warnings(meta)
    assert any("disable-model-invocation" in w for w in warns)
    assert any("model" in w for w in warns)
    # base-spec fields are portable, so not flagged
    assert not any("license" in w for w in warns)
    assert not any("'name'" in w for w in warns)


def test_portability_clean_when_base_only():
    assert portability_warnings(_meta(license="MIT")) == []


# --- validate_cc: the production entry point (file I/O path) -----------------

def test_validate_cc_valid_skill(tmp_path):
    d = _skill_dir(
        tmp_path,
        f"---\nname: demo\ndescription: {GOOD_DESC}\ndisable-model-invocation: true\n---\nbody\n",
    )
    assert validate_cc(d) == []


def test_validate_cc_missing_skill_md(tmp_path):
    (tmp_path / "empty").mkdir()
    errors = validate_cc(tmp_path / "empty")
    assert errors and "not found" in errors[0].lower()


def test_validate_cc_malformed_frontmatter_surfaces_reason(tmp_path):
    d = tmp_path / "demo"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter at all\n", encoding="utf-8")
    errors = validate_cc(d)
    # The specific parser reason must survive, not collapse into a generic string.
    assert errors and "parsed" in errors[0].lower()


def test_validate_cc_strict_flags_cc_extension_end_to_end(tmp_path):
    from skill_maintainer.validate import validate_single

    d = _skill_dir(
        tmp_path, f"---\nname: demo\ndescription: {GOOD_DESC}\nmodel: inherit\n---\nbody\n"
    )
    # Default: the CC field is fine.
    ok, _, _ = validate_single(d, strict=False)
    assert ok
    # --strict: the CC field is flagged as non-portable and fails.
    ok_strict, errors, _ = validate_single(d, strict=True)
    assert not ok_strict
    assert any("Claude Code extension" in e for e in errors)
