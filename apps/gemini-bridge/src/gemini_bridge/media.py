"""Turning local files into Interactions API content blocks.

One of three files carrying provider assumptions, with `auth.py` and
`files.py`. Images and documents attach inline as base64: the bytes travel in
the request, no upload step, nothing left behind on Google's side afterwards.

Video and audio go the other way: they reach the API as a `uri` for a file
uploaded first, which `files.py` obtains. That is not a size decision. It is
the only shape probed to work (probe 11), and inline video is unverified --
the house rule here is that a static source is a hypothesis and only a live
call is authority, so the unprobed path does not ship. Anything past the
inline cap is routed the same way regardless of kind, which is what makes a
90MB PDF work.

What the Interactions API does NOT offer for video, confirmed against the
generated SDK types rather than the docs: no fps, no start_offset, no
end_offset. `VideoContent` is `data | mime_type | resolution | type | uri` and
nothing else; the legacy `video_metadata` field is explicitly unavailable here.
**Sampling is fixed at 1 FPS.** Trimming and retiming are therefore the
caller's, with ffmpeg, before the file gets here -- see
`references/video.md`. This module deliberately does not shell out to ffmpeg:
a transcode is a lossy, minutes-long, silently-destructive step, and doing it
implicitly inside an attach would mean the bytes analysed are not the bytes
named on the command line.
"""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Verified against the generated SDK content types.
IMAGE_MIME = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/gif",
    "image/bmp",
    "image/tiff",
}
VIDEO_MIME = {
    "video/mp4",
    "video/mpeg",
    "video/mpg",
    "video/mov",
    "video/avi",
    "video/x-flv",
    "video/webm",
    "video/wmv",
    "video/3gpp",
}
AUDIO_MIME = {
    "audio/wav",
    "audio/mp3",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/mpeg",
    "audio/m4a",
    "audio/l16",
    "audio/opus",
    "audio/alaw",
    "audio/mulaw",
}
DOCUMENT_MIME = {"application/pdf", "text/csv"}

# Inline data is capped at 100MB by the API, and base64 inflates by ~33%.
INLINE_LIMIT_BYTES = 70 * 1024 * 1024

# Kinds that never go inline, whatever their size. See the module docstring:
# this is a verification decision, not a size one.
UPLOAD_KINDS = frozenset({"video", "audio"})

# Stands in for a real handle while `--dry-run` assembles the request it is
# about to not send. Distinctive on purpose: if one of these ever reaches the
# wire or a run directory, the string says exactly what went wrong. Nothing
# writes to disk on the dry-run path, so it should never be seen.
DRY_RUN_URI = "pending-upload://dry-run"


class MediaError(ValueError):
    pass


@dataclass(frozen=True)
class Attachment:
    path: Path
    kind: str  # image | video | audio | document
    mime_type: str
    size_bytes: int
    resolution: str | None = None
    # Set once the file has been uploaded; None means "still local".
    uri: str | None = None

    def manifest_entry(self, relative_to: Path | None = None) -> dict[str, Any]:
        """What goes in request.json -- never the base64 payload.

        The path is recorded relative to the project when possible. Run
        directories are written inside the user's own project and can be copied
        or shared, and the raw argument was whatever was typed -- an absolute
        path puts the local username on disk for no benefit.
        """
        path = self.path
        if relative_to:
            try:
                path = path.resolve().relative_to(Path(relative_to).resolve())
            except ValueError:
                path = Path(path.name)  # outside the project: keep only the name
        return {
            "path": str(path),
            "kind": self.kind,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "resolution": self.resolution,
            # Recorded because it is the one part of a run that outlives the
            # run: an uploaded file sits at Google for 48h, and this is the
            # handle that identifies it there.
            "uri": self.uri,
        }


# `mimetypes` answers with the platform's table, which does not agree with the
# list above -- and does not agree with itself across platforms, since it reads
# /etc/mime.types where that exists. Every entry here is a name Python returns
# for a format the API does accept, under a spelling it does not. Without the
# mapping the file is rejected as an unsupported type, which reads as "Gemini
# cannot take .wav" rather than "we asked for the wrong string".
MIME_ALIASES = {
    "video/quicktime": "video/mov",
    "video/x-msvideo": "video/avi",
    "video/x-ms-wmv": "video/wmv",
    "audio/x-wav": "audio/wav",
    "audio/x-aiff": "audio/aiff",
    "audio/mp4": "audio/m4a",
    # .3gp is a container that usually carries video, and `video/3gpp` is the
    # only 3gpp spelling the API accepts -- there is no audio/3gpp to route to.
    "audio/3gpp": "video/3gpp",
}


def _sniff(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        raise MediaError(f"cannot determine mime type for {path}")
    return MIME_ALIASES.get(mime, mime)


def classify(mime: str) -> str:
    if mime in IMAGE_MIME:
        return "image"
    if mime in VIDEO_MIME:
        return "video"
    if mime in AUDIO_MIME:
        return "audio"
    if mime in DOCUMENT_MIME:
        return "document"
    raise MediaError(f"unsupported mime type {mime!r}")


def guess_kinds(paths: list[str]) -> list[str]:
    """Kinds inferred from filenames alone -- no disk access, no failures.

    Used to pick a default question before the guards have run, so it must not
    care whether the files exist, are readable, or are even a supported type.
    Anything it cannot place is simply left out; `inspect` reports the real
    error later, at the point where that error is actionable.
    """
    out = []
    for raw in paths:
        try:
            out.append(classify(_sniff(Path(raw))))
        except MediaError:
            continue
    return out


def inspect(path: str | Path, resolution: str | None = None) -> Attachment:
    p = Path(path)
    if not p.is_file():
        raise MediaError(f"not a file: {p}")
    mime = _sniff(p)
    return Attachment(
        path=p,
        kind=classify(mime),
        mime_type=mime,
        size_bytes=p.stat().st_size,
        resolution=resolution,
    )


def needs_upload(att: Attachment) -> bool:
    """Whether this attachment has to go through the Files API.

    Two independent reasons, and both are checked here so that callers never
    have to know which one applied: the kind is one the API only accepts by
    uri, or the file is simply too big to inline.
    """
    return att.kind in UPLOAD_KINDS or att.size_bytes > INLINE_LIMIT_BYTES


def to_content_block(att: Attachment) -> dict[str, Any]:
    """A content block: a uri reference if the file was uploaded, else inline."""
    if att.uri:
        block: dict[str, Any] = {
            "type": att.kind,
            "uri": att.uri,
            "mime_type": att.mime_type,
        }
        # Audio takes no resolution -- AudioContent has no such field, and
        # sending one is a 400 rather than an ignored extra.
        if att.resolution and att.kind in {"image", "video"}:
            block["resolution"] = att.resolution
        return block

    if needs_upload(att):
        raise MediaError(
            f"{att.path} must be uploaded before it can be attached "
            f"({att.kind}, {att.size_bytes / 1e6:.1f}MB). This is a bug in the "
            "caller: resolve uploads before building the request."
        )
    # Re-stat rather than trusting the size captured at inspect() time. The two
    # happen at different moments, and the cached figure guards a cap that is
    # then applied to a fresh read -- a file that grew in between would pass the
    # check and still be sent in full. Reading also has to be guarded: a
    # screenshot cleaned up by another process between argument parsing and the
    # send would otherwise surface as a bare FileNotFoundError, uncaught,
    # before any run directory exists.
    try:
        size = att.path.stat().st_size
        if size > INLINE_LIMIT_BYTES:
            raise MediaError(
                f"{att.path} is {size / 1e6:.1f}MB; inline attachment is capped "
                "near 100MB after base64 expansion. It was under the cap when "
                "it was measured, so it grew mid-call -- re-run and it will be "
                "routed through the Files API instead."
            )
        payload = att.path.read_bytes()
    except OSError as exc:
        raise MediaError(f"could not read {att.path}: {exc}") from exc

    block = {
        "type": att.kind,
        "data": base64.b64encode(payload).decode(),
        "mime_type": att.mime_type,
    }
    if att.resolution and att.kind in {"image", "video"}:
        block["resolution"] = att.resolution
    return block


def resolve_attachments(
    paths: list[str],
    subject_resolution: str | None,
    context_paths: list[str] | None = None,
    context_resolution: str | None = None,
) -> list[Attachment]:
    """Subjects get the recipe's resolution; context images can get a cheaper one.

    Per-content-item resolution is Gemini 3 only, and it is the whole point:
    spend tokens on what is being examined, not on the reference material
    sitting beside it.
    """
    out = [inspect(p, subject_resolution) for p in paths]
    out += [inspect(p, context_resolution) for p in (context_paths or [])]
    return out
