"""Generative tests for the path guard.

Motivated by a bad track record rather than a hunch: this function was rewritten
three times in one session, and each fix revealed the previous one broken in a
way that looked correct. Hand-picked cases kept passing while the guard leaked,
because the cases were chosen by the same person holding the wrong mental model.

So these do not assert specific pairs. They generate paths, derive patterns that
a reasonable person would expect to block each one, and assert the guard never
under-blocks. Under-blocking is the only direction that matters: a false
positive costs one refused call, a false negative sends material that cannot be
recalled.

Seeded, so a failure is reproducible.
"""

from __future__ import annotations

import random
import string
from pathlib import Path

import pytest

from gemini_bridge.privacy import is_sensitive

SEED = 20260801
DEPTH = (1, 5)
NAME_ALPHABET = string.ascii_letters + string.digits + "-_"


def _name(rng: random.Random) -> str:
    return "".join(rng.choice(NAME_ALPHABET) for _ in range(rng.randint(3, 12)))


def _paths(count: int) -> list[Path]:
    rng = random.Random(SEED)
    out = []
    for _ in range(count):
        parts = [_name(rng) for _ in range(rng.randint(*DEPTH))]
        out.append(Path("/" + "/".join(parts) + f"/{_name(rng)}.png"))
    return out


def _patterns_that_must_block(path: Path) -> list[str]:
    """Forms a person would reasonably expect to block this path.

    Every one of these was, at some point today, silently not matching.
    """
    parts = [p for p in path.parts if p != "/"]
    directory = parts[0]
    return [
        directory,                    # bare directory name
        directory.upper(),            # case mismatch (default fs is insensitive)
        directory.lower(),
        f"{directory}/*",             # glob under a directory
        f"{directory}/**",            # the other glob people write
        f"*/{directory}/*",           # anchored anywhere
        str(path),                    # the exact path
        f"*{path.suffix}",            # by extension
        str(path.parent) + "/*",      # the containing directory
    ]


@pytest.mark.parametrize("path", _paths(40), ids=str)
def test_guard_never_under_blocks(path):
    for pattern in _patterns_that_must_block(path):
        assert is_sensitive(path, [pattern]) == pattern, (
            f"LEAK: pattern {pattern!r} failed to block {path}"
        )


@pytest.mark.parametrize("path", _paths(20), ids=str)
def test_unrelated_patterns_do_not_block(path):
    """Sanity in the other direction.

    Over-blocking is safe but not free -- a guard that blocks everything gets
    switched off, which is a leak by another route.
    """
    for pattern in ["zzz-no-such-directory", "*.tiff-not-used", "quux/*"]:
        assert is_sensitive(path, [pattern]) is None


@pytest.mark.parametrize("path", _paths(10), ids=str)
def test_first_matching_pattern_is_reported(path):
    directory = [p for p in path.parts if p != "/"][0]
    hit = is_sensitive(path, ["no-match-a", directory, "no-match-b"])
    assert hit == directory


def test_empty_and_degenerate_patterns_block_nothing():
    # Regression: normalising "" produced ".", which matched every file with an
    # extension. Indiscriminate over-blocking is still a defect.
    for path in _paths(10):
        assert is_sensitive(path, ["", "   ", "/", "//"]) is None
