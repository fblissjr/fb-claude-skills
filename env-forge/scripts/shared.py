"""
Shared constants and utilities for env-forge scripts.

Used by catalog.py and materialize.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import orjson

REPO_ID = "Snowflake/AgentWorldModel-1K"
CACHE_DIR = Path(".env-forge/cache")
DEFAULT_OUTPUT_BASE = Path(".env-forge/environments")

# Individual JSONL file names
SCENARIO_FILE = "gen_scenario.jsonl"
TASKS_FILE = "gen_tasks.jsonl"
DB_FILE = "gen_db.jsonl"
SAMPLE_FILE = "gen_sample.jsonl"
SPEC_FILE = "gen_spec.jsonl"
ENVS_FILE = "gen_envs.jsonl"
VERIFIER_FILE = "gen_verifier.jsonl"

# All JSONL files in the dataset
ALL_JSONL_FILES = [
    SCENARIO_FILE,
    TASKS_FILE,
    DB_FILE,
    SAMPLE_FILE,
    SPEC_FILE,
    ENVS_FILE,
    VERIFIER_FILE,
]


def ensure_dir(path: Path) -> None:
    """Create directory and parents if they don't exist."""
    path.mkdir(parents=True, exist_ok=True)


def download_file(filename: str, refresh: bool = False) -> Path:
    """Download a JSONL file from HF, caching locally.

    Args:
        filename: Name of the file in the HF dataset.
        refresh: If True, re-download even if cached locally.
    """
    cached = CACHE_DIR / filename
    if cached.exists() and not refresh:
        return cached

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "Error: huggingface_hub not installed. Run: uv add huggingface_hub",
            file=sys.stderr,
        )
        sys.exit(1)

    ensure_dir(CACHE_DIR)
    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        repo_type="dataset",
        local_dir=str(CACHE_DIR),
    )
    return Path(path)


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts using orjson."""
    records = []
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(orjson.loads(line))
    return records
