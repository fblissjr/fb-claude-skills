"""Credential resolution.

One of the two seams that differ between the Gemini Developer API and Vertex
(the other is `media.py`). Keep provider assumptions here, not sprinkled through
the call path -- Vertex funding via Google Developer Program credits is a live
option we deliberately did not foreclose.

Deliberately secret-manager agnostic. The tool does not know or care what holds
the key: it runs a command you supply and reads the key from that command's
stdout. That covers 1Password, pass, gopass, the macOS keychain, Bitwarden,
Doppler, sops, a decrypt script, or anything else that can print a secret. The
plain environment-variable path stays as the zero-setup fallback, so nobody is
required to install anything.

Nothing about which manager is used, or how the secret is addressed within it,
is recorded, logged, or written to disk -- the command line usually contains the
vault and item name, so the run record keeps only a coarse provenance label.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from os import environ

KEY_COMMAND_ENV = "GEMINI_BRIDGE_KEY_COMMAND"
API_KEY_ENVS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

COMMAND_TIMEOUT_S = 60  # generous: some managers prompt for biometric unlock


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    """How to reach the API. `api_key` is the Developer API path.

    `kind` is deliberately coarse. Run directories land inside whatever project
    is being analysed, and that project is usually a git repo. A key command
    typically names a vault and item, so it must never reach disk. An
    environment variable name is not sensitive and survives intact; it is the
    value that matters, and the value is never recorded.
    """

    api_key: str
    kind: str  # "key-command" or "env:VARNAME"

    def client_kwargs(self) -> dict:
        return {"api_key": self.api_key}

    def __repr__(self) -> str:  # keep the key out of tracebacks and logs
        return f"Credentials(kind={self.kind!r}, api_key=<redacted>)"


def _run_key_command(command: str) -> str:
    """Run a user-supplied command and take its stdout as the key.

    Parsed with shlex and executed without a shell, so quoted arguments work
    but shell metacharacters are not interpreted. The command comes from the
    user's own configuration -- the same trust level as their shell profile,
    and the same mechanism git uses for credential helpers.
    """
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise AuthError(f"key command is not parseable: {exc}") from exc
    if not argv:
        raise AuthError("key command is empty")

    if not shutil.which(argv[0]):
        raise AuthError(f"key command not found on PATH: {argv[0]}")

    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, check=False,
            timeout=COMMAND_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise AuthError(
            f"key command timed out after {COMMAND_TIMEOUT_S}s "
            "(waiting on an unlock prompt?)"
        ) from exc

    if proc.returncode != 0:
        # stderr routinely echoes the secret reference back, so it is not
        # surfaced. Re-run the command by hand to see the real error.
        hint = ""
        if len(argv) > 2:
            # Commonest cause by far: an item or path containing a space, split
            # into separate arguments because the inner quotes were omitted.
            # Said generically -- naming the arguments would leak the reference.
            hint = (
                " If any argument contains a space, quote it inside the command "
                "string."
            )
        raise AuthError(
            f"key command failed (exit {proc.returncode}). "
            f"Run it directly to see why.{hint}"
        )

    secret = proc.stdout.strip()
    if not secret:
        raise AuthError("key command produced no output")
    return secret


def resolve(
    key_command: str | None = None, config_key_command: str | None = None
) -> Credentials:
    """Resolve credentials.

    Order: the --key-command argument, then the key-command environment
    variable, then the user config file, then the plain API key environment
    variables. The command path is preferred where available because the secret
    is fetched per call rather than exported into every process the shell
    spawns -- but it is entirely optional.
    """
    command = key_command or environ.get(KEY_COMMAND_ENV) or config_key_command
    if command:
        return Credentials(api_key=_run_key_command(command), kind="key-command")

    for var in API_KEY_ENVS:
        value = environ.get(var)
        if value:
            return Credentials(api_key=value, kind=f"env:{var}")

    raise AuthError(
        "no credentials. Either export "
        f"{API_KEY_ENVS[0]}, or point {KEY_COMMAND_ENV} at a command that "
        "prints your API key (any secret manager works), or pass "
        "--key-command."
    )
