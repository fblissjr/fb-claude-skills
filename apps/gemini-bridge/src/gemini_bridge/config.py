"""User and project configuration.

Two levels, because two different kinds of setting exist:

- **User config** holds how to reach the API -- the key command. That is a
  property of the machine, not of any project, and it should not have to be
  re-stated per repo or exported into every shell.
- **Project config** holds how this project wants to be analysed: where recipes
  live, which paths are too sensitive to send anywhere.

Neither file ever contains the API key. The user config holds a *command that
prints* the key; the key stays in whatever manager you already use.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from os import environ
from pathlib import Path

APP_NAME = "gemini-bridge"
PROJECT_CONFIG_NAME = ".gemini-bridge.toml"


def user_config_path() -> Path:
    """Respects XDG_CONFIG_HOME, falls back to the conventional location."""
    base = environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP_NAME / "config.toml"


def _load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


@dataclass
class Config:
    key_command: str | None = None
    default_model: str | None = None
    recipe_dirs: list[Path] = field(default_factory=list)
    sensitive_paths: list[str] = field(default_factory=list)
    use_default_sensitive_paths: bool = True
    scan_prompt: bool = True
    sources: list[Path] = field(default_factory=list)

    @classmethod
    def load(cls, project_root: Path | None = None) -> Config:
        """User config first, then project config overriding it.

        `key_command` is deliberately user-level only. A project file is often
        committed, and a key command names a vault and item -- it has no
        business in a shared repo.
        """
        cfg = cls()

        user_path = user_config_path()
        user = _load_toml(user_path)
        if user:
            cfg.sources.append(user_path)
        auth = user.get("auth", {})
        cfg.key_command = auth.get("key_command")
        cfg.default_model = user.get("defaults", {}).get("model")

        if project_root:
            project_path = project_root / PROJECT_CONFIG_NAME
            project = _load_toml(project_path)
            if project:
                cfg.sources.append(project_path)
            if "auth" in project:
                raise ConfigError(
                    f"{project_path}: [auth] does not belong in project config. "
                    "A key command names your vault and item, and project files "
                    "get committed. Put it in the user config instead: "
                    f"{user_path}"
                )
            defaults = project.get("defaults", {})
            cfg.default_model = defaults.get("model", cfg.default_model)
            cfg.recipe_dirs = [
                (project_root / p).resolve()
                for p in project.get("recipes", {}).get("dirs", [])
            ]
            privacy_cfg = project.get("privacy", {})
            cfg.sensitive_paths = privacy_cfg.get("sensitive_paths", [])
            # Opt-out rather than opt-in: the defaults cover file shapes that
            # are secrets or nothing, and a user who genuinely needs to send one
            # can say so explicitly.
            cfg.use_default_sensitive_paths = privacy_cfg.get("use_defaults", True)
            cfg.scan_prompt = privacy_cfg.get("scan_prompt", True)

        return cfg


class ConfigError(ValueError):
    pass


EXAMPLE_USER_CONFIG = """\
# gemini-bridge user config. Contains no secrets -- only a command that
# prints your API key. Any secret manager works; so does no secret manager,
# in which case leave this out and export GEMINI_API_KEY instead.

[auth]
# key_command = "pass show gemini/api-key"
# key_command = "security find-generic-password -w -s gemini"
# key_command = "doppler secrets get GEMINI_API_KEY --plain"

[defaults]
# model = "gemini-3.6-flash"
"""

EXAMPLE_PROJECT_CONFIG = """\
# gemini-bridge project config (.gemini-bridge.toml), committed with the repo.
# No [auth] section here -- a key command names a vault and an item, and this
# file gets committed. It belongs in the user config only.

[privacy]
# Files matching any of these are refused rather than sent. Stored
# interactions cannot be deleted, so refusing is the only protection.
# Patterns match anywhere in the resolved path, case-insensitively.
# A bare name matches any directory component.
sensitive_paths = ["secrets", "*.key", "credentials/*"]

[recipes]
# dirs = ["prompts/gemini"]

[defaults]
# model = "gemini-3.6-flash"
"""
