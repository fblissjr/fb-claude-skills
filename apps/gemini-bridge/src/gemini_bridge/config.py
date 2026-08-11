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

# 2.5x the default per-approval ceiling -- roughly two hours of default-rate
# video -- chosen so no ordinary session meets it and a runaway loop of
# individually-cheap calls does.
DEFAULT_SESSION_CAP_TOKENS = 500_000


def user_config_path() -> Path:
    """Respects XDG_CONFIG_HOME, falls back to the conventional location."""
    base = environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP_NAME / "config.toml"


def _load_toml(path: Path) -> dict:
    """Read a config file, or raise ConfigError with the path in the message.

    Wrapped because every command loads config before doing anything else, so
    an unwrapped TOMLDecodeError was a traceback on the first line of every
    invocation until the typo was found. Fail-closed was never in question --
    nothing runs without config -- but a refusal here has to terminate in a
    sentence a person can act on, like every other refusal in this CLI.
    """
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"{path} could not be read: {exc}") from exc


@dataclass
class Config:
    key_command: str | None = None
    default_model: str | None = None
    recipe_dirs: list[Path] = field(default_factory=list)
    sensitive_paths: list[str] = field(default_factory=list)
    use_default_sensitive_paths: bool = True
    scan_prompt: bool = True
    # The spend gate. On by default: video shipped in 0.8.0, so there is no
    # established behaviour to break, and an unauthorized call that uploads
    # forty minutes of footage is exactly what it exists to prevent. Cheap
    # calls are untouched, so the common path does not change.
    require_authorization: bool = True
    max_unauthorized_tokens: int = 20_000
    authorization_ttl_seconds: int = 600
    # Cumulative per session, counted in authorization's session state (not
    # the project ledger -- see session_spent_tokens for why). `false` in
    # TOML disables it; 0 does not (0 gates every call, see classify).
    max_session_tokens: int | None = DEFAULT_SESSION_CAP_TOKENS
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

            # Project-level, deliberately: "how much may be spent without
            # asking" is a property of the project being analysed, not of the
            # machine. Unlike the key command, it is safe to commit -- it
            # carries no secret and a shared repo benefits from agreeing on it.
            authz = project.get("authorization", {})
            cfg.require_authorization = authz.get("required", True)
            # Wrapped for the same reason as _load_toml: these feed the spend
            # gate, and a string where a number belongs was an uncaught
            # ValueError rather than a message naming the file and the key.
            try:
                cfg.max_unauthorized_tokens = int(
                    authz.get("max_unauthorized_tokens", 20_000)
                )
                cfg.authorization_ttl_seconds = int(authz.get("ttl_seconds", 600))
            except (TypeError, ValueError) as exc:
                raise ConfigError(
                    f"{project_path}: [authorization] max_unauthorized_tokens "
                    f"and ttl_seconds must be integers: {exc}"
                ) from exc

            # Validated OUTSIDE the try above: ConfigError subclasses
            # ValueError, so raising it inside got caught by that except and
            # re-wrapped into a self-contradicting composite ("must be
            # integers ... or false to disable"). Type-checked rather than
            # int()-coerced, because coercion accepted the wrong shapes with
            # the wrong meanings: `true` became a live one-token cap (bool
            # subclasses int), `-1` -- the common "unlimited" idiom -- became
            # a cap that gates every call, and floats truncated silently.
            # `false` disables; 0 stays a live gate-everything cap (see
            # classify for why zero must never read as disabled).
            session_cap = authz.get(
                "max_session_tokens", DEFAULT_SESSION_CAP_TOKENS
            )
            if session_cap is False:
                cfg.max_session_tokens = None
            elif (isinstance(session_cap, bool)
                    or not isinstance(session_cap, int) or session_cap < 0):
                raise ConfigError(
                    f"{project_path}: [authorization] max_session_tokens must "
                    "be a non-negative integer, or false to disable the cap "
                    f"(got {session_cap!r})"
                )
            else:
                cfg.max_session_tokens = session_cap

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

[authorization]
# Expensive or irreversible calls need a user-typed
# /gemini-bridge:gemini-authorize. Cheap ones run under the ordinary
# permission prompt. Set required = false to disable the gate entirely.
# required = true
# max_unauthorized_tokens = 20000
# ttl_seconds = 600
# max_session_tokens = 500000  # cumulative per session; false disables

[recipes]
# dirs = ["prompts/gemini"]

[defaults]
# model = "gemini-3.6-flash"
"""
