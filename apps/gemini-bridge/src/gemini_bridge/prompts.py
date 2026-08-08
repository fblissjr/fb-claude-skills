"""What to ask when the caller did not say.

A question is required, and the good ones are written by the agent making the
call -- it has been reading the user's code, it knows what the video is *for*,
and it is the only party that can say "check whether the drawer animation
overshoots" instead of "describe this video". A generic prompt against a
capable model returns a generic answer, and paying for a scene description
nobody asked for is the most common way this bridge wastes money.

So the defaults here are a floor, not a feature. They exist because refusing a
call that has a video attached and no question is unhelpful pedantry, and
because a caller who genuinely wants an open-ended look should not have to
invent boilerplate. Every use of one prints a warning naming what a contextual
question would have added, on the theory that the fix belongs in front of the
person who can make it.

The wording of each default is doing real work and is not filler:

- **Timestamps.** Without an explicit instruction the model narrates prose, and
  prose about a video is nearly unusable to a caller who wants to seek to the
  moment described.
- **Observed, not inferred.** The caller cannot see the media. A plausible
  guess presented as an observation is worse than "cannot tell", because it
  cannot be checked. This mirrors the stance in the `general` recipe.
- **Ordered.** "What happens" invites a summary; "in order" produces a
  timeline, which is what almost every downstream use of a video needs.
"""

from __future__ import annotations

# Sampling is fixed at 1 FPS on this API, so anything shorter than a second can
# fall between frames. Saying so in the prompt gets the caveat back in the
# answer instead of a confident claim about a 3-frame transition.
_VIDEO = (
    "Analyze this video and describe what happens, in order. Give a timestamp "
    "(MM:SS) for each distinct beat, and cover on-screen text, UI state "
    "changes, camera or cursor movement, and anything audible. Report only "
    "what you can actually observe; if something is too fast or too small to "
    "resolve, say so rather than inferring it. Note that frames are sampled "
    "about once per second, so call out anything that may have fallen between "
    "samples."
)

_AUDIO = (
    "Transcribe this audio and describe what it contains. Give a timestamp "
    "(MM:SS) for each speaker turn or distinct section, and note tone, "
    "non-speech sound, and anything inaudible. Do not guess at words you "
    "cannot make out -- mark them as unclear."
)

_IMAGE = (
    "Describe what is in this image, specifically enough that someone who "
    "cannot see it could act on the description. Be precise about location "
    "and quantity. Report only what is actually visible."
)

_DOCUMENT = (
    "Summarize this document: what it is, how it is structured, and what it "
    "actually says. Quote exactly where the wording matters. Report only what "
    "is in the document."
)

_GENERIC = (
    "Describe what the attached media contains, specifically enough that "
    "someone who cannot see or hear it could act on the description. Report "
    "only what you can actually observe."
)

DEFAULTS = {
    "video": _VIDEO,
    "audio": _AUDIO,
    "image": _IMAGE,
    "document": _DOCUMENT,
}


def default_question(kinds: list[str]) -> str:
    """The fallback question for a set of attachment kinds.

    A mixed set falls back to the generic wording rather than picking a
    winner: the video default tells the model to timestamp everything, which
    is wrong advice for the PDF sitting next to it.
    """
    distinct = set(kinds)
    if len(distinct) == 1:
        return DEFAULTS.get(distinct.pop(), _GENERIC)
    return _GENERIC


def default_notice(kinds: list[str]) -> str:
    """The warning printed whenever a default is used.

    Names the specific thing the caller could have supplied, because "consider
    a better prompt" is advice nobody acts on. The two levers are the question
    and `--system`, and the second is the one callers forget exists.
    """
    distinct = sorted(set(kinds))
    what = distinct[0] if len(distinct) == 1 else "attached media"
    return (
        f"no question was given, so a generic {what} prompt is being used. "
        "This is the weakest way to use the bridge: say what you are actually "
        "looking for, and pass --system with the stance for the task "
        "(what the file is, what decision the answer feeds, what to ignore). "
        "A contextual question costs nothing extra and changes the answer "
        "completely."
    )
