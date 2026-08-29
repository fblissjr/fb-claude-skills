"""Per-repo configuration and state directory management."""

from datetime import date
from pathlib import Path

import orjson

CONFIG_DIR = ".skill-maintainer"
CONFIG_FILE = "config.json"
STATE_DIR = "state"

DEFAULT_UPSTREAM_URLS = [
    "https://code.claude.com/docs/en/skills",
    "https://code.claude.com/docs/en/plugins",
    "https://code.claude.com/docs/en/plugins-reference",
    "https://code.claude.com/docs/en/discover-plugins",
    "https://code.claude.com/docs/en/plugin-marketplaces",
    "https://code.claude.com/docs/en/hooks-guide",
    "https://code.claude.com/docs/en/hooks",
    "https://code.claude.com/docs/en/sub-agents",
    "https://code.claude.com/docs/en/memory",
]

DEFAULT_LLMS_FULL_URL = "https://code.claude.com/docs/llms-full.txt"


def config_dir(root: Path) -> Path:
    return root / CONFIG_DIR


def state_dir(root: Path) -> Path:
    return config_dir(root) / STATE_DIR


def hashes_file(root: Path) -> Path:
    return state_dir(root) / "upstream_hashes.json"


def changes_log(root: Path) -> Path:
    return state_dir(root) / "changes.jsonl"


def pages_dir(root: Path) -> Path:
    """Directory holding last-seen content snapshots of watched upstream pages."""
    return state_dir(root) / "pages"


def url_to_slug(url: str) -> str:
    """Convert an upstream URL to a filesystem-safe slug.

    >>> url_to_slug("https://code.claude.com/docs/en/skills")
    'skills'
    >>> url_to_slug("https://code.claude.com/docs/en/hooks-guide")
    'hooks-guide'
    """
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in tail)


def fetch_marker(root: Path) -> Path:
    """Records when upstream pages were last actually fetched.

    Deliberately a separate file with exactly ONE writer (`upstream.py`, after a
    successful fetch). `upstream_hashes.json` cannot answer this: `sources.py`
    rewrites it on every run to store tracked-repo HEADs while fetching zero
    pages, so its mtime dates the last git pull, not the last fetch. The
    upstream fetch arm read that mtime and reported `fetched 0d ago` immediately
    after a `skill-maintain sources` run (2026-08-07) -- a green produced by an
    operation that touched no documentation page.
    """
    return state_dir(root) / "last_fetch"


def record_fetch(root: Path, when: date | None = None) -> None:
    """Stamp a successful upstream fetch. Called only by `upstream.py`."""
    p = fetch_marker(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((when or date.today()).isoformat(), encoding="utf-8")


def load_fetch_date(root: Path) -> date | None:
    """Date of the last recorded fetch, or None if unknown.

    Returns None rather than raising on a missing or unparseable marker: the
    caller runs inside `test_repo_hygiene`, which has no exception boundary, so
    raising here would take out every other repo arm instead of reporting one.
    None means "unknown", which the arm must treat as not-fresh rather than
    assuming the best.
    """
    p = fetch_marker(root)
    try:
        return date.fromisoformat(p.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


BUNDLED_BEST_PRACTICES = Path("skills") / "skill-maintainer" / "references" / "best_practices.md"


def bundled_best_practices(root: Path) -> Path | None:
    """The plugin-bundled best_practices.md, or None outside the source repo.

    This is the copy that ships and the copy `init` seeds new repos from, so it
    is the authority wherever a repo has not deliberately taken a local one.
    """
    candidate = root / BUNDLED_BEST_PRACTICES
    return candidate if candidate.exists() else None


def best_practices_file(root: Path) -> Path:
    """Resolve the rules file: a deliberate per-repo copy, else the bundled one.

    `init-maintenance/SKILL.md` has always documented this order -- "`init` does
    not write a best_practices.md into the repo. The plugin's bundled
    references/best_practices.md is the copy /maintain reads" -- but the code
    returned only the per-repo path. Both consumers (the provenance join in
    `upstream`, and its test arm) are guarded by `.exists()`, so a repo without a
    local copy skipped the join silently rather than falling back. Returning the
    per-repo path when absent-and-no-bundle keeps that message pointing at the
    place a user would create one.
    """
    local = config_dir(root) / "best_practices.md"
    if local.exists():
        return local
    return bundled_best_practices(root) or local


def load_config(root: Path) -> dict:
    """Load .skill-maintainer/config.json, returning defaults if missing."""
    cfg_path = config_dir(root) / CONFIG_FILE
    if cfg_path.exists():
        return orjson.loads(cfg_path.read_bytes())
    return {}


def get_upstream_urls(root: Path) -> list[str]:
    cfg = load_config(root)
    return cfg.get("upstream_urls", DEFAULT_UPSTREAM_URLS)


def get_llms_full_url(root: Path) -> str:
    cfg = load_config(root)
    return cfg.get("llms_full_url", DEFAULT_LLMS_FULL_URL)


def get_tracked_repos(root: Path) -> list[str]:
    cfg = load_config(root)
    return cfg.get("tracked_repos", [])


def load_hashes(root: Path) -> dict:
    """Load upstream_hashes.json state."""
    hf = hashes_file(root)
    if hf.exists():
        return orjson.loads(hf.read_bytes())
    return {}


def save_hashes(root: Path, hashes: dict) -> None:
    """Save upstream_hashes.json state."""
    hf = hashes_file(root)
    hf.parent.mkdir(parents=True, exist_ok=True)
    hf.write_bytes(orjson.dumps(hashes, option=orjson.OPT_INDENT_2))


def append_event(root: Path, event: dict) -> None:
    """Append a single event dict to changes.jsonl."""
    log_path = changes_log(root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as f:
        f.write(orjson.dumps(event) + b"\n")


def init_config(root: Path) -> Path:
    """Create a default .skill-maintainer/config.json if it doesn't exist."""
    cfg_dir = config_dir(root)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    state_dir(root).mkdir(parents=True, exist_ok=True)

    cfg_path = cfg_dir / CONFIG_FILE
    if not cfg_path.exists():
        default = {
            "upstream_urls": DEFAULT_UPSTREAM_URLS,
            "llms_full_url": DEFAULT_LLMS_FULL_URL,
            "tracked_repos": [],
        }
        cfg_path.write_bytes(orjson.dumps(default, option=orjson.OPT_INDENT_2))
    return cfg_path
