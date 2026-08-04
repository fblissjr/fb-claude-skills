"""Shared constants and utilities for skill-maintainer."""

from pathlib import Path

SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal"}
"""Directories never scanned for skills or plugins.

`_deprecated` used to be here, for units withdrawn from circulation but kept on
disk. That tree is gone: removal is now a deletion, and git history is the
archive. A parallel archive was a second place to maintain whose contents were
never read, and it needed this skip entry precisely because everything in it
would otherwise sit permanently red -- an unpublished plugin legitimately fails
"listed in marketplace.json". The entry is left out rather than kept "just in
case", so a directory reappearing under that name is scanned like any other.
"""
TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000
STALE_DAYS = 30


def _skipped(path: Path, root: Path) -> bool:
    """True if `path` sits under a SKIP_DIRS component *inside* the repo.

    Matching against the absolute path is wrong: a repo checked out beneath a
    directory that happens to be named `internal`, `coderef`, `.venv` or the
    like made every file invisible, so discovery returned nothing and the suite
    reported green having scanned nothing -- the worst failure available to a
    checker. Only components below the root can disqualify a file.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    # `.backup` also matches as a SUFFIX -- a directory named
    # `plugin-toolkit.backup` is a snapshot, not a unit to check. The original
    # code expressed this as a separate substring test; folding it in here keeps
    # both rules in one place instead of one of them getting dropped in a
    # refactor, which is exactly what happened.
    return any(part in SKIP_DIRS or part.endswith(".backup") for part in rel.parts)


def discover_skills(root: Path) -> list[Path]:
    """Find all SKILL.md files, return their parent directories."""
    results = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        if _skipped(skill_md, root):
            continue
        results.append(skill_md.parent)
    return results


def discover_plugins(root: Path) -> list[Path]:
    """Find all plugin directories (have .claude-plugin/plugin.json), skip coderef/."""
    results = []
    for pj in sorted(root.rglob(".claude-plugin/plugin.json")):
        if _skipped(pj, root):
            continue
        # plugin dir is parent of .claude-plugin/
        plugin_dir = pj.parent.parent
        # skip the root marketplace (root .claude-plugin/ is not a plugin)
        if plugin_dir == root:
            continue
        results.append(plugin_dir)
    return results


def measure_tokens(skill_dir: Path) -> dict[str, int]:
    """Estimate context tokens for markdown files in a skill directory.

    Returns a dict with:
      - skill_tokens: tokens from SKILL.md (always-loaded when skill triggers)
      - ref_tokens: tokens from references/ and other .md files (on-demand)
      - total: sum of both (for backward compat / informational)

    Only counts .md files since those are loaded into context via progressive
    disclosure. Scripts (.py, .sh) are executed, not loaded. Config files
    (.json, .yaml) are not part of the skill context window budget.
    """
    skill_chars = 0
    ref_chars = 0
    skip = SKIP_DIRS | {"state"}
    for f in skill_dir.rglob("*"):
        if f.is_dir() or f.name.startswith("."):
            continue
        if any(s in f.parts for s in skip):
            continue
        if f.suffix == ".md":
            try:
                chars = len(f.read_text())
            except (OSError, UnicodeDecodeError):
                continue
            if f.name == "SKILL.md":
                skill_chars += chars
            else:
                ref_chars += chars
    return {
        "skill_tokens": skill_chars // 4,
        "ref_tokens": ref_chars // 4,
        "total": (skill_chars + ref_chars) // 4,
    }


def get_last_verified(metadata: dict) -> tuple[str | None, int | None]:
    """Extract last_verified date and days-ago from parsed frontmatter metadata.

    Returns (date_str, days_ago). Either or both may be None.
    """
    from datetime import date

    meta = metadata.get("metadata", {})
    if not isinstance(meta, dict):
        return None, None
    lv = meta.get("last_verified")
    if not lv:
        return None, None
    lv_str = str(lv)
    try:
        lv_date = date.fromisoformat(lv_str)
        days_ago = (date.today() - lv_date).days
        return lv_str, days_ago
    except ValueError:
        return lv_str, None


def get_review_interval(metadata: dict) -> int:
    """Days a skill may go unverified before it counts as stale.

    Reads `metadata.review_interval_days`, falling back to the global
    STALE_DAYS. A single global window is wrong for a repo tracking sources of
    very different volatility -- the Claude Code docs move weekly, Kimball
    dimensional modeling has not moved in decades. Forcing both to 30 days
    keeps the board permanently red, which is how a signal stops being read.

    Invalid values fall back rather than raise: frontmatter is user input, and
    a typo must not silently grant an unbounded window.
    """
    meta = metadata.get("metadata")
    if not isinstance(meta, dict):
        return STALE_DAYS
    raw = meta.get("review_interval_days")
    if raw is None or isinstance(raw, bool):
        return STALE_DAYS
    try:
        days = int(raw)
    except (TypeError, ValueError, OverflowError):
        return STALE_DAYS
    return days if days > 0 else STALE_DAYS


def freshness_mode(metadata: dict) -> str:
    """How this skill's freshness is established: 'cascade', 'conflict', or 'calendar'.

    `metadata.freshness: "cascade"` records that the skill's source is code in
    this repo, whose changes the version cascade already surfaces -- elapsed
    time is not evidence of drift there, so the calendar window is dropped
    (dates-are-look-triggers migration, 2026-08-04). The calendar interval
    remains the fallback for sources whose drift cannot be observed.

    Declaring cascade AND review_interval_days together is 'conflict': one
    skill, one mechanism -- a quiet precedence choice would let the pair drift.
    Unknown mechanism values are ignored (calendar): frontmatter is user input,
    and a typo must not silently grant an unbounded window.
    """
    meta = metadata.get("metadata")
    if not isinstance(meta, dict):
        return "calendar"
    if meta.get("freshness") == "cascade":
        if meta.get("review_interval_days") is not None:
            return "conflict"
        return "cascade"
    return "calendar"


# Verbs a description may lead with. Deliberately broad and non-exhaustive:
# every entry below leads a real description in this repo, and the original
# 10-item list contained only four of them. A narrow list does not enforce
# quality, it just fires on unfamiliar phrasing -- extend this rather than
# rewording a description to satisfy it.
_WHAT_VERBS = frozenset({
    "add", "analyze", "audit", "break", "build", "bump", "consult", "create",
    "creates", "decompose", "decomposes", "design", "enable", "enforce",
    "enforces", "extract", "generate", "generates", "guide", "handle",
    "handles", "inspect", "install", "manage", "manages", "monitor",
    "monitors", "orchestrate", "pair", "query", "record", "remove", "render",
    "report", "reproduce", "rewrite", "run", "scan", "set", "show",
    "synthesize", "synthesizes", "validate", "validates", "verify", "write",
})

_WHAT_PHRASES = ("use when", "use for", "used to", "helps with")

_WHEN_PHRASES = (
    "use when", "when user", "when the", "if user",
    "trigger", "mention", "says",
)


def check_description_quality(
    description: str, *, model_invocable: bool = True
) -> list[str]:
    """Check a description for a WHAT verb and, when relevant, a WHEN trigger.

    Set `model_invocable=False` for skills declaring
    `disable-model-invocation: true`. Their description never enters Claude's
    context, so it is never matched against a user's phrasing -- requiring a
    trigger phrase there demands text that provably cannot do anything, and
    the only way to satisfy it is to write a trigger that will never fire.

    The WHAT check still applies in that case: the description is what a
    person reads in the slash-command menu when deciding whether to run it.

    Default is `True` so a skill that omits the frontmatter flag is held to
    the stricter standard -- an exemption should have to be declared.
    """
    if not description:
        return ["no description"]

    issues = []
    desc_lower = description.lower()
    first_word = desc_lower.split()[0].strip(",.:;!?") if desc_lower.split() else ""

    has_what = first_word in _WHAT_VERBS or any(
        p in desc_lower for p in _WHAT_PHRASES
    )
    if not has_what:
        issues.append("missing WHAT verb")

    if model_invocable and not any(p in desc_lower for p in _WHEN_PHRASES):
        issues.append("missing WHEN trigger")

    return issues
