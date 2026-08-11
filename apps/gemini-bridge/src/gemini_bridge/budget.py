"""What a call will cost, before you make it.

The bridge's defaults are already the cheap ones -- Flash, `thinking_level:
minimal`, default media resolution -- so the thing that actually runs up a bill
is not a setting anyone chose. It is **clip length**, which nobody sees until
the invoice. A minute of video is about 4,200 input tokens; a ten-minute screen
recording someone attached without trimming is most of a dollar's worth of
input on a question that wanted fifteen seconds of it.

So this module exists to put a number on screen before the send, not to
enforce a policy. It warns and never refuses: the caller can see the estimate
and stop, and a hard ceiling would have to guess a budget it cannot know.

**Every number here is an estimate and is labelled as one.** Three Google doc
pages give three different video token rates differing by about 4x (see
`references/api.md`), so this is deliberately an order of magnitude for
deciding whether to trim, not an accounting figure. The exact count comes back
in `usage.json` after the fact, which is the only number worth trusting.

No prices, ever. A dollar figure in code goes stale silently and looks
authoritative while it does it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

from .media import Attachment

# Sampling is fixed at 1 FPS, and low/medium/default all cost the same.
VIDEO_TOKENS_PER_SECOND = 70
VIDEO_TOKENS_PER_SECOND_HIGH = 280

# A table, not `280 if resolution == "high" else 70`. That form priced
# `ultra_high` -- an accepted video resolution, offered by `--resolution`,
# validated by `recipes`, and carried on the content block -- at the *cheapest*
# rate, so the single most expensive setting produced an estimate four times
# under `high` and slipped a gate that `high` triggers. A ladder selected by
# equality against one rung breaks the moment a rung is added, and this one had
# already been added.
#
# `ultra_high` follows the image ladder's doubling. It is a guess, and it is
# deliberately a high one: an estimate that feeds a spend gate must never
# under-count, because under-counting is the direction that spends money.
VIDEO_TOKEN_RATES = {
    None: VIDEO_TOKENS_PER_SECOND,
    "low": VIDEO_TOKENS_PER_SECOND,
    "medium": VIDEO_TOKENS_PER_SECOND,
    "high": VIDEO_TOKENS_PER_SECOND_HIGH,
    "ultra_high": VIDEO_TOKENS_PER_SECOND_HIGH * 2,
}

# Audio has no published per-frame figure in anything probed; this is a rough
# working number and is why audio estimates are marked approximate too.
AUDIO_TOKENS_PER_SECOND = 25

# When ffprobe is unavailable, duration is guessed from size, and the guess
# feeds the spend gate -- so it must assume the LOW-bitrate end of plausible,
# not the typical one, because under-counting is the direction that spends
# money (the video-rate table above states the same rule). 30s/MB assumes
# ~270kbps: screen recordings of mostly-static content commonly run
# 100-300kbps, where the old 10s/MB (~800kbps) under-counted a 20-minute
# recording below the gate. Over for ordinary footage, which costs a needless
# authorization; no finite constant can bound a pathological file, which is
# why the manifest line says the duration is unknown. Audio: 150s/MB covers
# voice-note bitrates (~48kbps) the old 60s/MB figure halved.
FALLBACK_VIDEO_SECONDS_PER_MB = 30
FALLBACK_AUDIO_SECONDS_PER_MB = 150

IMAGE_TOKENS = {"low": 280, "medium": 560, "high": 1120, "ultra_high": 2240}
DEFAULT_IMAGE_TOKENS = IMAGE_TOKENS["high"]  # the API's default, not ours
DOCUMENT_TOKENS_PER_MB = 3000  # very rough; pages per MB vary wildly

# Nothing is free. Without a floor, a small file rounds to zero tokens and the
# estimate reads as "this costs nothing" -- which is both wrong and exactly the
# wrong direction for a number whose job is to make spending visible. One
# sampled frame, one second of audio, one page of PDF.
MIN_TOKENS = {"video": VIDEO_TOKENS_PER_SECOND, "audio": AUDIO_TOKENS_PER_SECOND,
              "document": 560}

# Above this, say something. Chosen as "about five minutes of video" -- long
# enough not to nag on ordinary clips, short enough to catch the ten-minute
# recording nobody meant to send whole.
WARN_TOKENS = 20_000

PROBE_TIMEOUT_S = 10


@dataclass(frozen=True)
class Estimate:
    tokens: int
    duration_s: float | None  # None when ffprobe is unavailable or failed
    exact: bool = False  # never true today; here so callers cannot assume

    def line(self, att: Attachment) -> str:
        if self.duration_s:
            mins, secs = divmod(int(self.duration_s), 60)
            return (f"{mins}m{secs:02d}s  ~{self.tokens:,} input tokens "
                    "(estimate)")
        if att.kind in {"video", "audio"}:
            # The manifest is the one moment the user can still stop the call,
            # and length is the one input the gate cannot bound without
            # ffprobe. A line with no duration and no marker reads as a normal
            # estimate; this one says it is a guess.
            return (f"~{self.tokens:,} input tokens (estimate; duration "
                    "unknown -- no ffprobe, sized from bytes)")
        return f"~{self.tokens:,} input tokens (estimate)"


# ffprobe spawns a process with a 10s timeout, and `estimate` is called from
# the per-file line, the total, the gate's tier decision, and the warning --
# up to three or four times per file per command. Keyed on identity, not just
# path, so a file rewritten mid-run is not answered from the old reading.
_DURATION_CACHE: dict[tuple[str, int, float], float | None] = {}


def duration_seconds(att: Attachment) -> float | None:
    """Media length via ffprobe, or None if it cannot be determined.

    ffprobe is read-only and does not transcode, so this is cheap and safe --
    but it is optional. Its absence degrades the estimate to a size-based
    guess rather than failing the call, because a missing local tool must
    never be the reason a paid feature stops working.
    """
    if att.kind not in {"video", "audio"} or not shutil.which("ffprobe"):
        return None
    try:
        stat = att.path.stat()
        key = (str(att.path), stat.st_size, stat.st_mtime)
    except OSError:
        return None
    if key in _DURATION_CACHE:
        return _DURATION_CACHE[key]
    _DURATION_CACHE[key] = value = _probe_duration(att)
    return value


def _probe_duration(att: Attachment) -> float | None:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(att.path),
            ],
            capture_output=True, text=True, timeout=PROBE_TIMEOUT_S, check=False,
        )
        if out.returncode != 0:
            return None
        value = json.loads(out.stdout).get("format", {}).get("duration")
        return float(value) if value else None
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        return None


def estimate(att: Attachment) -> Estimate:
    """A deliberately rough input-token figure for one attachment."""
    raw = _estimate(att)
    floor = MIN_TOKENS.get(att.kind, 0)
    if raw.tokens >= floor:
        return raw
    return Estimate(tokens=floor, duration_s=raw.duration_s, exact=raw.exact)


def _estimate(att: Attachment) -> Estimate:
    if att.kind == "video":
        # An unknown value bills at the highest known rate, not the lowest: a
        # resolution this table has not caught up with is the case where
        # guessing cheap is how the gate gets bypassed.
        rate = VIDEO_TOKEN_RATES.get(
            att.resolution, max(VIDEO_TOKEN_RATES.values())
        )
        seconds = duration_seconds(att)
        if seconds is None:
            # No ffprobe. The constant explains its own direction of error;
            # the printed line says the duration is unknown.
            seconds = att.size_bytes / 1e6 * FALLBACK_VIDEO_SECONDS_PER_MB
            return Estimate(tokens=int(seconds * rate), duration_s=None)
        return Estimate(tokens=int(seconds * rate), duration_s=seconds)

    if att.kind == "audio":
        seconds = duration_seconds(att)
        if seconds is None:
            seconds = att.size_bytes / 1e6 * FALLBACK_AUDIO_SECONDS_PER_MB
            return Estimate(tokens=int(seconds * AUDIO_TOKENS_PER_SECOND),
                            duration_s=None)
        return Estimate(tokens=int(seconds * AUDIO_TOKENS_PER_SECOND),
                        duration_s=seconds)

    if att.kind == "image":
        return Estimate(
            tokens=IMAGE_TOKENS.get(att.resolution or "", DEFAULT_IMAGE_TOKENS),
            duration_s=None,
        )

    return Estimate(
        tokens=int(att.size_bytes / 1e6 * DOCUMENT_TOKENS_PER_MB), duration_s=None
    )


# Roughly four characters per token for English prose. Wrong for code, CJK, or
# base64 -- all of which pack differently -- so this is the same order-of-
# magnitude figure the rest of the module deals in, not an accounting number.
TEXT_CHARS_PER_TOKEN = 4


def text_tokens(*texts: str | None) -> int:
    """The input tokens carried by the request's text, rounded up.

    Text was the one billed input this module did not count, and the omission
    was not academic: the spend gate reads its threshold from here, so a
    multi-megabyte `--prompt-file` -- roughly a million tokens -- classified as
    cheap and went out under the ordinary permission prompt. A question typed
    on the command line rounds to nothing and changes no verdict, which is why
    counting it costs nothing to add.
    """
    chars = sum(len(t) for t in texts if t)
    return -(-chars // TEXT_CHARS_PER_TOKEN)


def total(attachments: list[Attachment]) -> int:
    return sum(estimate(a).tokens for a in attachments)


def advice(attachments: list[Attachment], tokens: int) -> str | None:
    """The one line worth printing when a call looks expensive.

    Names the specific lever rather than saying "this is large", because the
    fix differs: a long video wants trimming, a pile of images wants a lower
    resolution.
    """
    if tokens < WARN_TOKENS:
        return None
    if not attachments:
        # Reachable since the estimate started counting text. Naming
        # `--resolution` on a call with nothing attached is advice the caller
        # cannot act on, which is the failure this function exists to avoid.
        return (
            f"~{tokens:,} estimated input tokens, all of it prompt text. Send "
            "the part of it the question is actually about."
        )
    video = [a for a in attachments if a.kind == "video"]
    if video:
        longest = max(video, key=lambda a: estimate(a).tokens)
        return (
            f"~{tokens:,} estimated input tokens; {longest.path.name} is the "
            "bulk of it. Clip length is the cost -- `ffmpeg -ss START -to END "
            "-i in.mp4 -c copy out.mp4` trims without re-encoding."
        )
    return (
        f"~{tokens:,} estimated input tokens. Lower --resolution, or attach "
        "reference files with -c instead of -f, if this is more than the "
        "question needs."
    )
