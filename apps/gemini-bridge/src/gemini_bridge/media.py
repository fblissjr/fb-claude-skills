"""Turning local files into Interactions API content blocks.

The second provider seam (see auth.py). v0.1 attaches images inline as base64,
which is correct for the image workloads and avoids the Files API entirely --
that matters because `client.files.upload` raises on Vertex clients, so keeping
inline as the default keeps the Vertex door open.

Video arrives in phase 4 and needs the Files API plus ffmpeg preprocessing: the
Interactions API exposes no fps, start_offset, or end_offset (the `video_metadata`
field of the legacy generateContent API is explicitly unavailable here), and
sampling is fixed at 1 FPS. Trimming and retiming are therefore ours to do.
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


class MediaError(ValueError):
    pass


@dataclass(frozen=True)
class Attachment:
    path: Path
    kind: str  # image | video | audio | document
    mime_type: str
    size_bytes: int
    resolution: str | None = None

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
        }


def _sniff(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime == "video/quicktime":  # what mimetypes calls .mov
        mime = "video/mov"
    if not mime:
        raise MediaError(f"cannot determine mime type for {path}")
    return mime


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


def to_content_block(att: Attachment) -> dict[str, Any]:
    """Inline base64 content block. Raises for anything needing the Files API."""
    if att.kind in {"video", "audio"}:
        raise MediaError(
            f"{att.kind} requires the Files API, not implemented until phase 4: "
            f"{att.path}"
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
                "near 100MB after base64 expansion. Needs the Files API."
            )
        payload = att.path.read_bytes()
    except OSError as exc:
        raise MediaError(f"could not read {att.path}: {exc}") from exc

    block: dict[str, Any] = {
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
