"""Scaffolding helpers for `skill-maintain init`.

Today: install the pre-commit git hook from the bundled sample. The sample lives in the
package itself (`skill_maintainer/templates/pre-commit.sample`), not in the plugin
directory, so the CLI works standalone when installed via `uv add git+...` into another
repo.
"""

from importlib import resources
from pathlib import Path


def install_pre_commit_hook(root: Path, force: bool = False) -> str:
    """Install the bundled pre-commit hook into <root>/.git/hooks/pre-commit.

    Returns a one-line status string suitable for printing.

    Behavior:
    - Skip if `<root>/.git` does not exist (not a git repo).
    - Skip if the target hook file already exists, unless `force=True`.
    - When `force=True` and a different hook is present, preserve it as `pre-commit.local`
      before overwriting.
    """
    git_dir = root / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        return "skipped: not a git repository"

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    target = hooks_dir / "pre-commit"

    sample_text = (
        resources.files("skill_maintainer.templates")
        .joinpath("pre-commit.sample")
        .read_text(encoding="utf-8")
    )

    if target.exists():
        if target.read_text(encoding="utf-8") == sample_text:
            return f"already up to date: {target}"
        if not force:
            return f"skipped: {target} exists (use --force-hook to overwrite)"
        backup = target.with_suffix(".local")
        target.rename(backup)
        target.write_text(sample_text, encoding="utf-8")
        target.chmod(0o755)
        return f"installed: {target} (previous saved as {backup.name})"

    target.write_text(sample_text, encoding="utf-8")
    target.chmod(0o755)
    return f"installed: {target}"
