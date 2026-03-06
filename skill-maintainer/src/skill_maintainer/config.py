"""Per-repo configuration and state directory management."""

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


def best_practices_file(root: Path) -> Path:
    return config_dir(root) / "best_practices.md"


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
