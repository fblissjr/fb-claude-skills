"""Scanning outgoing text for things that should not leave the machine.

The path guard in `privacy.py` inspects which FILES are attached. It says
nothing about the prompt -- and the prompt is composed by Claude, which has
been reading the user's files. A secret pasted into a question was sent with no
check at all, while a configured `sensitive_paths` implied the tool was
vetting what it transmitted. A misleading guard is worse than an absent one.

Patterns are adapted from this repo's `scan-for-secrets` skill so the two agree
on what a secret looks like. Kept as a copy rather than a runtime dependency:
that skill is a shell script meant for a human-driven pre-share sweep, and this
needs to run in-process on every call.

Unlike the path guard, this is ON by default. A blocklist nobody configures
protects nobody, and the failure here is irreversible -- stored interactions
cannot be deleted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Several patterns below end a greedy character class with a literal the class
# excludes, and those are written possessively (`++`, `*+`, `{10,}+`).
#
# Not a micro-optimisation: greedily, each start position consumes to the end
# of the text and then backtracks one character at a time looking for a
# delimiter that is not there. On input with no separator to break the run that
# is quadratic, and it was measured at ~275 seconds for a 400KB prompt -- the
# CLI sitting there producing nothing, on the guard path, before anything was
# sent. A base64 blob, a minified bundle, a hex digest or a data: URI pasted
# into `--prompt-file` is exactly that shape.
#
# Possessive is safe here *only* because the following literal is excluded from
# the class it follows, so the backtracking it removes could never have reached
# a match. `[A-Za-z0-9.-]+\.` in the email pattern is deliberately left greedy:
# `.` IS in that class, and the backtracking is what finds the last dot.
# Requires Python 3.11+, which `requires-python` already pins.
#
# (name, compiled pattern, whether a hit should block rather than warn)
_SPECS: list[tuple[str, str, bool]] = [
    # High confidence: these shapes are secrets or nothing.
    # The class must allow - and _ : OpenAI's current dashboard keys are
    # sk-proj-, sk-svcacct-, sk-admin-, and Stripe uses sk_live_ / rk_live_.
    # A pattern of sk-[A-Za-z0-9]{20,} missed every modern key it was named for.
    ("openai-style key", r"sk-[A-Za-z0-9_-]{20,}", True),
    ("stripe key", r"[srp]k_(?:live|test)_[A-Za-z0-9]{16,}", True),
    ("anthropic-style key", r"sk-ant-[A-Za-z0-9_-]{20,}", True),
    ("github token", r"gh[pousr]_[A-Za-z0-9]{36,}", True),
    # GitHub's recommended format since 2022; the classic pattern misses it.
    ("github fine-grained token", r"github_pat_[A-Za-z0-9_]{50,}", True),
    ("npm token", r"npm_[A-Za-z0-9]{36,}", True),
    ("sendgrid key", r"SG\.[A-Za-z0-9_-]{20,}+\.[A-Za-z0-9_-]{20,}", True),
    # A connection string with an inline password -- pasted constantly when
    # debugging, and the password is the whole secret.
    ("connection string with password",
     r"(?<![a-z0-9+.-])[a-z][a-z0-9+.-]*+://[^\s:/@]++:[^\s:/@]++@[^\s/]+", True),
    ("slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}", True),
    ("google api key", r"AIza[A-Za-z0-9_-]{35}", True),
    ("aws access key", r"AKIA[0-9A-Z]{16}", True),
    ("jwt", r"eyJ[A-Za-z0-9_-]{10,}+\.eyJ[A-Za-z0-9_-]{10,}+\.[A-Za-z0-9_-]{10,}", True),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", True),
    ("ssh fingerprint", r"SHA256:[A-Za-z0-9+/]{43}=?", True),
    ("secret reference", r"\bop://[^\s\"']+", True),
    # Lower confidence: legitimate in some prompts, so warn rather than block.
    ("email address", r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]++@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", False),
    ("absolute home path", r"/(?:Users|home)/[^/\s\"']++/", False),
]

PATTERNS = [(name, re.compile(rx), blocking) for name, rx, blocking in _SPECS]


@dataclass(frozen=True)
class Finding:
    name: str
    blocking: bool
    excerpt: str  # already redacted

    def __str__(self) -> str:
        return f"{self.name} ({self.excerpt})"


def _redact(match: str) -> str:
    """Show enough to locate it, never enough to use it.

    An error message naming what it found is useless if the user cannot tell
    which string it means; printing the whole match relocates the secret into a
    terminal, a transcript, and possibly a bug report.

    Never reveals more than a third of the string, and never more than 10
    characters total. A fixed head+tail formula looked safe on long matches and
    exposed 10 of 15 characters on a short one -- leaving a five-character
    brute-force space -- because the formula did not scale with the input.
    """
    budget = min(len(match) // 3, 10)
    if budget < 4:
        return "..."
    head = budget - budget // 2
    tail = budget // 2
    return f"{match[:head]}...{match[-tail:]}"


def scan(text: str) -> list[Finding]:
    """Return every match, redacted. Empty means nothing recognised."""
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for name, pattern, blocking in PATTERNS:
        for match in pattern.findall(text):
            value = match if isinstance(match, str) else match[0]
            key = (name, value)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(name, blocking, _redact(value)))
    return findings


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.blocking]


def redact_secrets(text: str) -> str:
    """Scrub blocking matches out of text that is about to travel.

    For error messages. The client-constructor path reduces failures to a type
    name because a key-format error embeds the value; the call and upload
    paths surface `str(exc)` -- into stderr, error.txt, and the ledger's error
    field at once -- and an SDK error can echo request details. Only blocking
    shapes are removed: emails and paths are warn-level in the scanner because
    they are legitimate in prose, and in an error message the path usually IS
    the diagnostic. The replacement names what was scrubbed so the message
    stays actionable without relocating the value.
    """
    for name, pattern, is_blocking in PATTERNS:
        if not is_blocking:
            continue
        text = pattern.sub(f"<redacted {name}>", text)
    return text
