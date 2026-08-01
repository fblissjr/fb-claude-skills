"""Sensitive-path matching.

Separated out because it is a safety check, and a safety check that silently
fails is worse than none: it produces confidence without protection.

The first implementation used `Path.match`, which anchors at the right-hand end
of the path. Every pattern a person would naturally write failed to block
nested files:

    Path("/home/me/private/deep/secret.png").match("private/*")   -> False
    Path("/home/me/private/deep/secret.png").match("private/**")  -> False
    Path("/home/me/secrets/key.png").match("secrets")             -> False

Matching here is against the resolved absolute path with `fnmatch`, whose `*`
crosses directory separators. That over-matches rather than under-matches, which
is the correct direction for a blocklist: a false positive costs one refused
call, a false negative sends material that cannot be recalled, because stored
interactions cannot be deleted.
"""

from __future__ import annotations

import os
import unicodedata
from fnmatch import fnmatch
from pathlib import Path

GLOB_CHARS = "*?["

# On by default, because a blocklist nobody configures protects nobody. These
# are file shapes that are secrets or nothing -- there is no legitimate reason
# to hand a private key to an image-comparison model, so refusing costs a user
# who genuinely wants to nothing but an explicit override.
#
# Deliberately narrow. Every entry that could plausibly match something a user
# actually wants to send makes the whole guard something they switch off.
DEFAULT_SENSITIVE_PATHS: tuple[str, ...] = (
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    ".env",
    ".env.*",
    "*.kdbx",
    ".ssh",
    ".gnupg",
    ".aws",
    "credentials.json",
    "service-account*.json",
)


def _normalise(text: str) -> str:
    """Expand and case-fold, so both sides of a comparison are treated alike.

    Two separate failures came from normalising only one side:

    1. The candidate path was expanded but the pattern was not, so a
       home-relative pattern or a variable-prefixed one matched nothing at
       all -- and those are the forms this repo's own path conventions train
       people to write.
    2. Matching was case-sensitive while the default macOS filesystem is not,
       so a pattern differing only in case failed to block a file reachable
       under either spelling.

    Both were invisible: the guard reported no match and the file was sent.

    Case folding is an explicit `.lower()`, not `os.path.normcase`, because
    normcase is a NO-OP on POSIX -- it only folds on Windows. Using it here
    looked like a fix and changed nothing. Folding unconditionally over-blocks
    on a genuinely case-sensitive filesystem, which is the correct direction
    for a blocklist: a false positive costs one refused call.
    """
    # NFC first: macOS stores accented filenames decomposed (NFD) while a
    # pattern typed into a config file is composed (NFC). The two are the
    # same text to a person and different bytes to fnmatch, so a directory
    # with an accent in its name silently failed to match.
    expanded = os.path.expandvars(str(Path(text).expanduser()))
    return unicodedata.normalize("NFC", expanded).lower()


def is_sensitive(path: Path, patterns: list[str]) -> str | None:
    """Return the first pattern that blocks `path`, or None.

    A pattern with no glob characters is treated as a name: it matches if it is
    any component of the path, or appears anywhere in it. A pattern with globs
    is matched against the whole resolved path, and against the path with any
    prefix, so a pattern naming a directory blocks everything beneath it
    wherever that directory sits.

    The returned value is the caller's original pattern text, not the
    normalised form, so the error message shows what the user actually wrote.
    """
    resolved = path.expanduser().resolve()
    text = _normalise(str(resolved))
    parts = {unicodedata.normalize("NFC", p).lower() for p in resolved.parts}

    for pattern in patterns:
        # Blank check BEFORE normalising: Path("") is ".", which would then
        # match any path containing a dot -- every file with an extension.
        raw = pattern.strip().rstrip("/")
        if not raw:
            continue
        cleaned = _normalise(raw).rstrip("/")
        if not cleaned or cleaned == ".":
            continue

        if not any(c in cleaned for c in GLOB_CHARS):
            if cleaned in parts or cleaned in text:
                return pattern
            continue

        candidates = (cleaned, f"*/{cleaned}", f"*{cleaned}", f"*/{cleaned}/*")
        if any(fnmatch(text, c) for c in candidates):
            return pattern

    return None


def effective_patterns(configured: list[str], use_defaults: bool = True) -> list[str]:
    """User patterns plus the built-in ones, unless defaults are switched off."""
    return [*configured, *(DEFAULT_SENSITIVE_PATHS if use_defaults else ())]
