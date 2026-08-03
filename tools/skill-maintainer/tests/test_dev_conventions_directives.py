"""Bracket for the dev-conventions SessionStart hook's directive selection.

The hook is check-shaped -- it classifies a repo and speaks or stays silent --
so it gets its own control (see plugin-patterns.md, "Bracket-the-hook"). The
rot these arms exist to notice: ground patterns widening until blocks go
silent in repos that need them (the arm that matters most is the
architecture-only CLAUDE.md staying LOUD), coverage detection breaking so
blocks broadcast over local rules again, mute stopping working, and the
metadata lines leaking into injected content.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "skills/dev-conventions/hooks/dev-conventions-session-start.sh"


def run_hook(cwd: Path) -> str | None:
    """Run the hook against cwd; return additionalContext, or None if silent."""
    out = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"cwd": str(cwd)}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def headings(ctx: str | None) -> set[str]:
    if ctx is None:
        return set()
    return {l.split("(")[0].strip("# ").strip() for l in ctx.splitlines() if l.startswith("## ")}


ALL = {
    "Python conventions",
    "JavaScript/TypeScript conventions",
    "TDD workflow",
    "Documentation conventions",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "package.json").touch()
    (tmp_path / "internal/log").mkdir(parents=True)
    return tmp_path


def test_bare_repo_gets_every_block(repo: Path):
    assert headings(run_hook(repo)) == ALL


def test_architecture_only_claude_md_stays_loud(repo: Path):
    # The granularity arm: a CLAUDE.md about module layout covers no block's
    # ground, so file existence must NOT silence anything. If this goes red,
    # coverage detection has degraded to file-existence detection.
    (repo / "CLAUDE.md").write_text(
        "This service parses events into a DuckDB store.\n"
        "Modules: parser/, store/, cli/. See ARCHITECTURE for the dataflow.\n"
    )
    assert headings(run_hook(repo)) == ALL


def test_local_rule_silences_exactly_its_block(repo: Path):
    (repo / "CLAUDE.md").write_text("Python: always uv, never pip.\n")
    assert headings(run_hook(repo)) == ALL - {"Python conventions"}


def test_claude_rules_dir_is_a_coverage_surface(repo: Path):
    rules = repo / ".claude/rules"
    rules.mkdir(parents=True)
    (rules / "general.md").write_text("JS: always bun. Write the failing test first.\n")
    assert headings(run_hook(repo)) == ALL - {
        "JavaScript/TypeScript conventions",
        "TDD workflow",
    }


def test_config_rules_are_a_coverage_surface_and_still_emit(repo: Path):
    (repo / ".dev-conventions.json").write_text(
        json.dumps({"rules": ["Session log in internal/log/ before finishing."]})
    )
    ctx = run_hook(repo)
    assert ctx is not None
    assert "Documentation conventions" not in headings(ctx)
    assert "Session log in internal/log/ before finishing." in ctx


def test_mute_still_works_alongside_coverage(repo: Path):
    (repo / ".dev-conventions.json").write_text(
        json.dumps({"directives": {"javascript": False}})
    )
    assert headings(run_hook(repo)) == ALL - {"JavaScript/TypeScript conventions"}


def test_all_ground_covered_is_fully_silent(repo: Path):
    (repo / "CLAUDE.md").write_text(
        "Use uv, never pip. Always bun for JS. TDD: failing test first. "
        "Session log in internal/log/.\n"
    )
    assert run_hook(repo) is None


@pytest.mark.parametrize(
    ("bait", "must_survive"),
    [
        # Each bait is a verified over-match specimen from the 2026-08-03
        # review: a token mention that is NOT a stated rule. The block whose
        # ground the old patterns wrongly matched must still load.
        ("last updated: 2026-08-01", "Documentation conventions"),
        ("changelog entries are ordered latest first", "TDD workflow"),
        ("UV mapping for the mesh is stored per vertex", "Python conventions"),
        ("the internal/logging module wraps stderr", "Documentation conventions"),
        ("this library is distributed via npm", "JavaScript/TypeScript conventions"),
    ],
)
def test_token_mentions_do_not_silence(repo: Path, bait: str, must_survive: str):
    (repo / "CLAUDE.md").write_text(bait + "\n")
    assert must_survive in headings(run_hook(repo))


def test_fenced_command_examples_do_not_cover(repo: Path):
    # The consumer-measured specimen (2026-08-03): a documented invocation in
    # a fenced block is documentation-of-a-command, not a stated rule. Before
    # fence-stripping, `bun run ...` here silenced the javascript block in a
    # repo with no npm prohibition and no pinning policy — a wrong verdict,
    # the unrecoverable direction. Prose-only grepping is positional, not
    # lexical: no alternation tuning finds this boundary.
    (repo / "CLAUDE.md").write_text(
        "Build steps:\n\n```\nbun run scripts/build.js\nuv run tools/gen.py\n```\n"
    )
    h = headings(run_hook(repo))
    assert "JavaScript/TypeScript conventions" in h
    assert "Python conventions" in h


def test_inline_code_rules_still_cover(repo: Path):
    # The other half of the specimen pair: a rule with code IN it is still a
    # rule. Only fenced blocks are stripped; inline spans stay.
    (repo / "CLAUDE.md").write_text("Use `bun add`, never `npm install`.\n")
    assert "JavaScript/TypeScript conventions" not in headings(run_hook(repo))


def test_explicit_true_forces_load_over_coverage(repo: Path):
    # Mute can only force silence; explicit true is the force-on escape for a
    # ground pattern that over-matches. Without it a wrongly-silenced
    # convention is simply lost.
    (repo / "CLAUDE.md").write_text("Python: always uv, never pip.\n")
    assert "Python conventions" not in headings(run_hook(repo))
    (repo / ".dev-conventions.json").write_text(
        json.dumps({"directives": {"python": True}})
    )
    assert "Python conventions" in headings(run_hook(repo))


def test_force_overrides_a_trigger_miss(tmp_path: Path):
    # The consumer-verified design gap (2026-08-03): a block is wrongly
    # silenced two ways — coverage over-match OR a trigger whose markers are
    # gitignored/deep — and force originally recovered only coverage. A repo
    # with NO JS marker plus javascript:true must still get the block.
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "internal").mkdir()
    (tmp_path / ".dev-conventions.json").write_text(
        json.dumps({"directives": {"javascript": True}})
    )
    assert "JavaScript/TypeScript conventions" in headings(run_hook(tmp_path))


def test_explain_names_the_gate_per_directive(repo: Path):
    # Three causes of silence are byte-identical in hook mode; --explain must
    # distinguish them and cite the matched line, sharing the same gate code.
    (repo / "CLAUDE.md").write_text("Use uv, never pip.\n")
    out = subprocess.run(
        ["bash", str(HOOK), "--explain", str(repo)],
        capture_output=True, text=True, check=True,
    ).stdout
    python_line = next(l for l in out.splitlines() if l.startswith("python"))
    assert "ground covered by" in python_line and "CLAUDE.md:1" in python_line
    tdd_line = next(l for l in out.splitlines() if l.startswith("tdd"))
    assert "LOADS" in tdd_line


def test_explain_counts_matches_beyond_the_first(repo: Path):
    # Consumer specimen, one level up from the founding one: the diagnostic
    # can point at a real match that isn't the reason. Their tdd coverage
    # displayed a meta-sentence ABOUT the silence while the load-bearing rule
    # sat further down, and only a hand-run counterfactual proved the gate
    # wasn't silencing off its own epitaph. With two covering lines, the
    # explain line must carry the count; with one, it must not.
    (repo / "CLAUDE.md").write_text(
        "Use uv, never pip.\nPython packages: always uv add, pinned exact.\n"
    )
    out = subprocess.run(
        ["bash", str(HOOK), "--explain", str(repo)],
        capture_output=True, text=True, check=True,
    ).stdout
    python_line = next(l for l in out.splitlines() if l.startswith("python"))
    assert "+1 more matching line" in python_line
    (repo / "CLAUDE.md").write_text("Use uv, never pip.\n")
    out = subprocess.run(
        ["bash", str(HOOK), "--explain", str(repo)],
        capture_output=True, text=True, check=True,
    ).stdout
    python_line = next(l for l in out.splitlines() if l.startswith("python"))
    assert "more matching line" not in python_line


def test_this_repo_stays_fully_covered():
    # The re-enable premise pin cited by docs/internals/gotchas.md: run the
    # hook against THIS repo live and require complete silence. If a rewording
    # of CLAUDE.md or .claude/rules/ ever slips past the ground patterns, this
    # goes red before a re-enabled plugin starts broadcasting here.
    assert run_hook(REPO) is None


def test_metadata_is_a_head_only_class(tmp_path: Path):
    # Ground is honored anywhere in the LEADING metadata run (not just line
    # 2), and a body line that merely looks like metadata survives into the
    # output. Runs a copy of the hook against a custom directives dir, since
    # shipped directives deliberately keep ground on line 2.
    hookdir = tmp_path / "plug"
    (hookdir / "directives").mkdir(parents=True)
    hook_copy = hookdir / "session-start.sh"
    hook_copy.write_text(HOOK.read_text())
    hook_copy.chmod(0o755)
    (hookdir / "directives" / "custom.md").write_text(
        "# trigger: any\n"
        "# scope: demo\n"
        "# ground: zebra convention\n"
        "## Custom block\n"
        "- The syntax is `# ground: <ERE>` on a metadata line.\n"
    )
    workdir = tmp_path / "work"
    (workdir / "internal").mkdir(parents=True)
    (workdir / "pyproject.toml").touch()

    def run_copy() -> str | None:
        out = subprocess.run(
            ["bash", str(hook_copy)],
            input=json.dumps({"cwd": str(workdir)}),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else None

    ctx = run_copy()
    assert ctx is not None
    assert "Custom block" in ctx
    # The body's literal metadata-looking line survives; the head run is gone.
    assert "`# ground: <ERE>`" in ctx
    assert "# scope: demo" not in ctx
    # Ground on line 3 is honored: covering it silences the custom block.
    (workdir / "CLAUDE.md").write_text("the zebra convention applies here\n")
    ctx = run_copy()
    assert ctx is None or "Custom block" not in ctx


def test_metadata_lines_never_leak(repo: Path):
    ctx = run_hook(repo)
    assert ctx is not None
    assert "# trigger:" not in ctx and "# ground:" not in ctx


def test_every_shipped_directive_declares_ground():
    # A shipped directive without a ground line can never be silenced by
    # coverage -- fail-open is for CUSTOM directives, not the defaults.
    for f in sorted((REPO / "skills/dev-conventions/hooks/directives").glob("*.md")):
        line2 = f.read_text().splitlines()[1]
        assert line2.startswith("# ground: "), f"{f.name} has no ground pattern"
