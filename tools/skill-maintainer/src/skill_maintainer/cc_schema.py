"""Claude Code skill-frontmatter schema validation.

This repo's skills run in Claude Code, so the hard gate validates against
Claude Code's actual skill frontmatter schema -- a superset of the cross-vendor
Agent Skills spec (agentskills.io). The base spec's six-field allowlist rejects
Claude Code's own fields (`disable-model-invocation`, `argument-hint`, `model`,
`context`, ...), which is why we no longer use it as the gate.

`ALLOWED_FIELDS` (base union CC extensions) is what the default gate accepts, via
`validate_cc`. The optional `--strict` portability check is `portability_warnings`,
which flags any field in `CLAUDE_CODE_FIELDS` as non-portable to a strict
cross-vendor host. (`validate_frontmatter`'s `allowed` parameter is a generic
building block that defaults to `ALLOWED_FIELDS`; passing `BASE_SPEC_FIELDS` gives
an equivalent field-allowlist check, but the CLI's `--strict` path uses
`portability_warnings` for its clearer per-field message.)

Field set current as of 2026-07 per code.claude.com/docs/en/skills.md. There is
no official JSON schema, so this list is the source of truth. This repo already
tracks that page for upstream drift via `skill-maintain upstream`; when it flags
a change to the skills doc, re-derive `CLAUDE_CODE_FIELDS` from it.

Parsing is delegated to skills_ref; only the field allowlist and value rules
live here.
"""

import unicodedata
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

# The cross-vendor Agent Skills spec (agentskills.io/specification).
BASE_SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

# Claude Code extensions beyond the base spec (code.claude.com/docs/en/skills.md).
CLAUDE_CODE_FIELDS = {
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}

ALLOWED_FIELDS = BASE_SPEC_FIELDS | CLAUDE_CODE_FIELDS


def _validate_name(name, skill_dir: Path | None) -> list[str]:
    """Name must be lowercase kebab-case, <=64 chars, and match the directory."""
    errors = []

    if not name or not isinstance(name, str) or not name.strip():
        return ["Field 'name' must be a non-empty string"]

    name = unicodedata.normalize("NFKC", name.strip())

    if len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"Skill name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} character limit "
            f"({len(name)} chars)"
        )
    if name != name.lower():
        errors.append(f"Skill name '{name}' must be lowercase")
    if name.startswith("-") or name.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")
    if "--" in name:
        errors.append("Skill name cannot contain consecutive hyphens")
    if not all(c.isalnum() or c == "-" for c in name):
        errors.append(
            f"Skill name '{name}' contains invalid characters. "
            "Only letters, digits, and hyphens are allowed."
        )
    if skill_dir:
        dir_name = unicodedata.normalize("NFKC", skill_dir.name)
        if dir_name != name:
            errors.append(
                f"Directory name '{skill_dir.name}' must match skill name '{name}'"
            )
    return errors


def _validate_description(description) -> list[str]:
    if not description or not isinstance(description, str) or not description.strip():
        return ["Field 'description' must be a non-empty string"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return [
            f"Description exceeds {MAX_DESCRIPTION_LENGTH} character limit "
            f"({len(description)} chars)"
        ]
    return []


def _validate_compatibility(compatibility) -> list[str]:
    if not isinstance(compatibility, str):
        return ["Field 'compatibility' must be a string"]
    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        return [
            f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} character limit "
            f"({len(compatibility)} chars)"
        ]
    return []


def validate_frontmatter(
    metadata: dict, skill_dir: Path | None = None, allowed: set[str] = ALLOWED_FIELDS
) -> list[str]:
    """Validate parsed frontmatter against `allowed` fields plus value rules.

    Pass `allowed=BASE_SPEC_FIELDS` for a strict cross-vendor check.
    """
    errors = []

    extra = set(metadata.keys()) - allowed
    if extra:
        errors.append(
            f"Unexpected fields in frontmatter: {', '.join(sorted(extra))}. "
            f"Allowed: {', '.join(sorted(allowed))}."
        )

    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    else:
        errors.extend(_validate_name(metadata["name"], skill_dir))

    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    else:
        errors.extend(_validate_description(metadata["description"]))

    if "compatibility" in metadata:
        errors.extend(_validate_compatibility(metadata["compatibility"]))

    return errors


def validate_cc(skill_dir: Path) -> list[str]:
    """Validate a skill against the Claude Code schema. [] means valid."""
    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return ["SKILL.md not found"]
    try:
        metadata, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except Exception as e:
        # Surface the parser's own reason ("must start with ---", "Invalid YAML
        # ...") rather than collapsing every failure into one generic message.
        return [f"SKILL.md frontmatter could not be parsed: {e}"]
    if not isinstance(metadata, dict):
        return ["SKILL.md frontmatter must be a mapping"]
    return validate_frontmatter(metadata, skill_dir, allowed=ALLOWED_FIELDS)


def portability_warnings(metadata: dict) -> list[str]:
    """Report frontmatter that would fail a strict cross-vendor host.

    Claude Code extension fields are valid here but not portable to a validator
    that enforces only the base Agent Skills spec.
    """
    extensions = sorted(set(metadata.keys()) & CLAUDE_CODE_FIELDS)
    if not extensions:
        return []
    return [
        f"Field '{f}' is a Claude Code extension, not in the cross-vendor "
        "Agent Skills spec (not portable to strict hosts)."
        for f in extensions
    ]
