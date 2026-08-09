"""The run directory: the handoff contract between Gemini, Claude, and you.

Every invocation leaves a complete, inspectable record on disk. Claude reads
`response.md` deliberately rather than having the whole answer dumped into its
context via stdout -- tool output persists for the rest of the session, so a
40KB scene description printed to stdout is ~10k tokens you cannot get back.

The directory also carries the parameter set, not just the interaction id.
`system_instruction` and `generation_config` are interaction-scoped: a follow-up
that does not re-send them silently runs with no system instruction and
different settings. And since the API offers no way to list stored interactions
-- only create, get, cancel, delete -- this directory is the ONLY record of what
there is to purge.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

RUNS_DIRNAME = ".gemini-runs"


def _slug(text: str, limit: int = 32) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:limit].rstrip("-")) or "run"


def _dump(path: Path, obj: Any) -> None:
    path.write_bytes(orjson.dumps(obj, option=orjson.OPT_INDENT_2))
    _restrict(path)


def _restrict(path: Path) -> None:
    """Owner-only.

    A run directory is a complete local record of what was sent, and when the
    prompt-scan override is used that includes the secret it was overridden
    for, in plaintext with no retention window. Default umask left these
    world-readable and sweepable into any backup or synced folder.
    """
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _ensure_ignored(runs_root: Path) -> None:
    """Self-ignore the runs tree.

    Run directories are written into whatever project is being analysed, and
    that project is usually a git repo. They hold prompts, model responses, and
    the media manifest -- none of which belongs in someone's commit history by
    accident. Writing `*` here means the tree excludes itself without the user
    having to remember to edit their .gitignore.
    """
    marker = runs_root / ".gitignore"
    if not marker.exists():
        marker.write_text("# Written by gemini-bridge. Run output is local-only.\n*\n")


def ensure_runs_root(root: Path) -> Path:
    """The runs tree, created and self-ignored.

    Public because the ledger is written on paths that never create a run
    directory -- a call refused by the spend gate sends nothing, so it has no
    run of its own, but it is still an audit event that has to land somewhere.
    `ledger.record` swallows OSError by design, so without this the row was
    silently dropped whenever this was the project's first call.
    """
    runs_root = root / RUNS_DIRNAME
    runs_root.mkdir(parents=True, exist_ok=True)
    _ensure_ignored(runs_root)
    return runs_root


@dataclass
class RunDir:
    path: Path

    @classmethod
    def create(
        cls, root: Path, recipe_name: str, now: dt.datetime | None = None
    ) -> RunDir:
        now = now or dt.datetime.now()
        runs_root = ensure_runs_root(root)
        stamp = now.strftime("%Y%m%dT%H%M%S")
        base = runs_root / f"{stamp}-{_slug(recipe_name)}"
        candidate, n = base, 1
        while candidate.exists():
            candidate = Path(f"{base}-{n}")
            n += 1
        candidate.mkdir(parents=True, mode=0o700)
        return cls(candidate)

    # -- writes ---------------------------------------------------------

    def write_request(self, request: dict[str, Any]) -> None:
        _dump(self.path / "request.json", request)

    def write_prompt(self, system_instruction: str, question: str) -> None:
        self.prompt_path.write_text(
            f"# system_instruction\n\n{system_instruction}\n\n"
            f"# question\n\n{question}\n"
        )
        _restrict(self.prompt_path)

    def write_response(self, text: str) -> None:
        target = self.path / "response.md"
        target.write_text(text if text.endswith("\n") else text + "\n")
        _restrict(target)

    def write_structured(self, obj: Any) -> None:
        _dump(self.path / "response.json", obj)

    def write_usage(self, usage: dict[str, Any]) -> None:
        _dump(self.path / "usage.json", usage)

    def write_uploads(self, records: list[dict[str, Any]]) -> None:
        """The Files API handles this run created or reused.

        Written only when a run actually uploaded something -- the caller sits
        behind that check, so the absence of this file means "no uploads",
        not "unknown". The docstring used to claim it was written even when
        empty, which no caller ever did; a reader trusting that would have
        read a missing file as a bug.

        Unlike an interaction, an upload can be deleted, and this is the local
        half of what makes that possible.
        """
        _dump(self.path / "uploads.json", records)

    def write_interaction_id(self, interaction_id: str) -> None:
        (self.path / "interaction.id").write_text(interaction_id + "\n")

    def write_error(self, message: str) -> None:
        (self.path / "error.txt").write_text(message + "\n")

    # -- reads ----------------------------------------------------------

    @property
    def prompt_path(self) -> Path:
        return self.path / "prompt.md"

    @property
    def interaction_id(self) -> str | None:
        f = self.path / "interaction.id"
        return f.read_text().strip() if f.exists() else None

    @property
    def request(self) -> dict[str, Any]:
        return orjson.loads((self.path / "request.json").read_bytes())


def ignore_status(root: Path) -> tuple[bool, bool]:
    """(runs tree exists, it is self-ignored).

    The `*` marker written at creation is the ONLY thing keeping prompts and
    responses out of `git add .` -- a project's root .gitignore knows nothing
    about this tool. Deleting the marker leaves the tree exposed until the next
    call rewrites it, and nothing surfaces that. `doctor` reports it so the
    window is visible rather than silent.
    """
    runs_root = root / RUNS_DIRNAME
    if not runs_root.is_dir():
        return False, True
    return True, (runs_root / ".gitignore").is_file()


def find_runs(root: Path) -> list[RunDir]:
    base = root / RUNS_DIRNAME
    if not base.is_dir():
        return []
    return [RunDir(p) for p in sorted(base.iterdir()) if p.is_dir()]


def stored_runs(root: Path) -> list[RunDir]:
    """Runs holding a stored interaction id -- i.e. anything purgeable."""
    return [r for r in find_runs(root) if r.interaction_id]
