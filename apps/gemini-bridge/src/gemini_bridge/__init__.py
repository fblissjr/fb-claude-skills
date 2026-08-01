"""gemini-bridge: hand a multimodal task to Gemini, get a structured answer back.

Submodules are imported here so `from gemini_bridge import client` resolves for
type checkers as well as at runtime. None of them import the Google SDK at
module scope -- that is deferred to the point of the call, so `--dry-run`,
`recipes`, and `stats` work without it installed.
"""

from . import auth, client, config, content, ledger, media, privacy, recipes, runs

__all__ = [
    "auth", "client", "config", "content", "ledger", "media", "privacy",
    "recipes", "runs",
]
