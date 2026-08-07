"""Discovery must not scan a second checkout of the same repo.

Claim: a git worktree under `.claude/worktrees/` — the location Claude Code
creates for `isolation: worktree` and `EnterWorktree`, and a path this repo's
own `.gitignore` excludes — contains a full copy of every SKILL.md and
plugin.json in the repo. Scanning it doubles every per-skill arm and makes the
duplicate-name check fail listing essentially every skill, so a live worktree
turns the suite red for reasons that have nothing to do with the tree under
test.

Specimen, 2026-08-07: a locked worktree left by a parallel session took the
suite from 265 passed / 3 failed to 499 passed / 6 failed, with 36 names
reported as duplicates.

Deleting either test below loses the guarantee that a concurrent worktree
cannot corrupt a verification run. `test_repo_root_still_discovered` is the
counterweight: the skip must not be so broad that it hides the real tree, which
is the failure the `_skipped` docstring already warns about — discovery
returning nothing and the suite reporting green having scanned nothing.
"""

from pathlib import Path

from skill_maintainer.shared import discover_plugins, discover_skills


def _write_skill(base: Path, plugin: str, skill: str) -> None:
    d = base / "skills" / plugin / "skills" / skill
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {skill}\ndescription: fixture skill for discovery tests\n---\n\n# {skill}\n",
        encoding="utf-8",
    )
    pj = base / "skills" / plugin / ".claude-plugin"
    pj.mkdir(parents=True, exist_ok=True)
    (pj / "plugin.json").write_text(
        f'{{"name": "{plugin}", "version": "0.1.0"}}\n', encoding="utf-8"
    )


def test_worktree_copy_is_not_discovered(tmp_path):
    """A worktree under .claude/worktrees/ is a second checkout, not more units."""
    _write_skill(tmp_path, "demo", "demo-skill")
    _write_skill(tmp_path / ".claude" / "worktrees" / "feature-x", "demo", "demo-skill")

    skills = discover_skills(tmp_path)
    plugins = discover_plugins(tmp_path)

    assert len(skills) == 1, f"expected only the real tree, got {skills}"
    assert len(plugins) == 1, f"expected only the real tree, got {plugins}"
    assert ".claude" not in skills[0].parts


def test_repo_root_still_discovered(tmp_path):
    """The skip must not swallow the tree under test.

    Born green, so it is mutation-proven at birth: widening the skip to any
    path containing `worktrees` (rather than the `.claude/worktrees` prefix)
    makes this fail while the test above still passes, which is the asymmetry
    that matters.
    """
    _write_skill(tmp_path, "demo", "demo-skill")
    assert len(discover_skills(tmp_path)) == 1
    assert len(discover_plugins(tmp_path)) == 1


def test_worktrees_outside_dot_claude_are_still_scanned(tmp_path):
    """`worktrees` is not a reserved word — only the `.claude/worktrees` path is.

    A plugin legitimately named `worktrees`, or a directory of that name used
    for something else, stays visible. The skip is a path rule, not a name ban.
    """
    _write_skill(tmp_path, "worktrees", "worktrees-helper")
    assert len(discover_skills(tmp_path)) == 1
