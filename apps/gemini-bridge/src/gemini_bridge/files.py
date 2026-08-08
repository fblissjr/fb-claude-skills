"""The Files API: media that cannot travel inline.

One of three files carrying provider assumptions, with `auth.py` (credentials)
and `media.py` (content blocks). `client.files.upload` belongs to the Gemini
Developer API and raises on a Vertex client, so every assumption about
uploading is kept here rather than spread through the call path. Images and
documents never reach this module at all -- they go inline -- which is what
keeps the surface this small.

Two facts shape the whole design, and both were established live rather than
from documentation:

- **Video reaches the Interactions API as a `uri`, not as bytes.** Probe 11 in
  `scripts/probe.py` is the verified call shape: upload, wait for the file to
  leave PROCESSING, then send `{"type": "video", "uri": ..., "mime_type": ...}`.
  An uploaded file is not usable the instant `upload` returns.
- **Uploads expire after 48 hours and, unlike interactions, they can actually
  be deleted.** `interactions.delete` returns 501; `files.delete` works. That
  asymmetry is why this module keeps a local record of every handle it creates
  -- it is the only thing that makes `gemini-bridge uploads --delete` possible,
  since the plugin should not have to enumerate a whole project's files to
  clean up after itself.

The cache exists because the motivating video case is iterative. Asking four
questions about one screen recording should upload it once, not four times: the
bytes are identical, the handle is valid for 48h, and re-uploading spends
wall-clock and the project's 20GB quota to arrive at the same URI. It is keyed
by content hash, so it can never serve a handle for different bytes -- edit the
file and the key changes. The only staleness it can suffer is server-side
(expired or deleted), which is why a cached handle is confirmed with a live
`files.get` before it is reused.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson

from .media import Attachment

CACHE_NAME = "upload-cache.json"

# The documented lifetime of an uploaded file. Independent of interaction
# storage (55 days), which is why store=false costs the conversation but not
# the upload.
LIFETIME_S = 48 * 3600

# Do not offer a handle that is about to expire. A file that lapses between the
# check and the call fails the interaction after the upload was skipped, which
# is the one outcome worse than re-uploading.
REUSE_MARGIN_S = 30 * 60

DEFAULT_TIMEOUT_S = 300
POLL_INTERVAL_S = 2.0

# 2GB per file, 20GB per project, per the Files API docs. Refused locally
# rather than after however long it takes to push 2GB over the wire.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

# Indirected through the module so a test can replace the clock without
# patching the stdlib and without every caller threading one through. Bound as
# defaults inside the function body rather than in its signature -- a default
# argument is evaluated once at import, which would make patching these do
# nothing.
_sleep = time.sleep
_now = time.time


class UploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Upload:
    """A server-side file handle.

    `name` is the delete key (`files/abc123`); `uri` is what goes in the content
    block. They are different strings and both are needed -- keeping only the
    uri would make the handle unremovable.

    `mime_type` is the server's, not ours. Our sniffer maps `.mov` to
    `video/mov` because that is what the Interactions API accepts, while the
    upload endpoint reports whatever it detected. The block must carry the
    server's value for the file it actually holds.
    """

    name: str
    uri: str
    mime_type: str
    sha256: str
    size_bytes: int
    uploaded_at: float
    display_name: str
    reused: bool = False

    def record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "uri": self.uri,
            "mime_type": self.mime_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "uploaded_at": self.uploaded_at,
            "display_name": self.display_name,
            "reused": self.reused,
        }

    def expires_at(self) -> float:
        return self.uploaded_at + LIFETIME_S


def digest(path: Path, chunk: int = 1024 * 1024) -> str:
    """Content hash, read in chunks -- these files are measured in gigabytes."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


@dataclass
class Cache:
    """Content hash -> handle, stored beside the run directories.

    Deliberately holds no paths, only basenames: the runs tree is written into
    whatever project is being analysed, and a full path there records the local
    username for no benefit the hash does not already provide.
    """

    path: Path
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, runs_root: Path) -> Cache:
        path = runs_root / CACHE_NAME
        try:
            raw = orjson.loads(path.read_bytes())
        except (OSError, orjson.JSONDecodeError):
            # A corrupt or absent cache is a cold cache, never a failed call.
            return cls(path=path)
        if not isinstance(raw, dict):
            return cls(path=path)
        entries = {k: v for k, v in raw.items() if isinstance(v, dict)}
        return cls(path=path, entries=entries)

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_bytes(
                orjson.dumps(self.entries, option=orjson.OPT_INDENT_2)
            )
            # Owner-only, like everything else in the runs tree: this names the
            # files a project has shipped to Google and when.
            self.path.chmod(0o600)
        except OSError:
            pass  # a lost cache costs an upload, never the call

    def get(self, sha: str, now: float) -> Upload | None:
        raw = self.entries.get(sha)
        if not raw:
            return None
        try:
            up = Upload(**{**raw, "reused": True})
        except TypeError:
            self.entries.pop(sha, None)  # written by an older, different shape
            return None
        if now >= up.expires_at() - REUSE_MARGIN_S:
            self.entries.pop(sha, None)
            return None
        return up

    def put(self, up: Upload) -> None:
        self.entries[up.sha256] = up.record()

    def drop(self, sha: str) -> None:
        self.entries.pop(sha, None)

    def live(self, now: float) -> list[Upload]:
        """Handles that have not aged out, newest first."""
        out = []
        for sha in list(self.entries):
            up = self.get(sha, now)
            if up:
                out.append(up)
        return sorted(out, key=lambda u: u.uploaded_at, reverse=True)


def _state(obj: Any) -> str:
    raw = getattr(obj, "state", "")
    return str(getattr(raw, "name", raw) or "").upper()


def _await_active(
    api: Any,
    name: str,
    *,
    timeout_s: float,
    sleep: Callable[[float], None],
    now: Callable[[], float],
) -> None:
    """Block until the uploaded file leaves PROCESSING.

    An upload is not usable the moment it returns, and sending its uri too
    early fails the interaction -- after the bytes were already spent. The
    deadline is real time rather than an iteration count so that a slow poll
    cannot silently multiply the wait.
    """
    deadline = now() + timeout_s
    while True:
        try:
            state = _state(api.files.get(name=name))
        except Exception as exc:  # any SDK error here is a failed wait
            raise UploadError(
                f"could not check upload state for {name}: {type(exc).__name__}"
            ) from exc
        if "ACTIVE" in state:
            return
        if "FAILED" in state:
            raise UploadError(
                f"the API reported the upload {name} as FAILED. The file was "
                "transferred but cannot be used; try re-encoding it."
            )
        if now() >= deadline:
            raise UploadError(
                f"upload {name} was still {state or 'unreported'} after "
                f"{timeout_s:.0f}s. It exists server-side and will expire on "
                "its own; raise --upload-timeout or send a shorter clip."
            )
        sleep(POLL_INTERVAL_S)


def _still_there(api: Any, name: str) -> bool:
    try:
        return "ACTIVE" in _state(api.files.get(name=name))
    except Exception:  # noqa: BLE001 - gone, expired, or unreachable: re-upload
        return False


def ensure_uploaded(
    api: Any,
    att: Attachment,
    cache: Cache,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], float] | None = None,
) -> Upload:
    """Return a live handle for `att`, uploading only if there isn't one.

    A cached handle is confirmed against the server before it is reused. The
    check costs one cheap metadata call and covers the two ways a cache entry
    goes wrong that the content hash cannot: the 48h expiry, and someone
    deleting the file (including `gemini-bridge uploads --delete` from another
    checkout of the same project).
    """
    sleep = sleep or _sleep
    now = now or _now

    if att.size_bytes > MAX_UPLOAD_BYTES:
        raise UploadError(
            f"{att.path} is {att.size_bytes / 1e9:.1f}GB; the Files API caps a "
            "single file at 2GB. Trim or re-encode it before sending."
        )

    try:
        sha = digest(att.path)
    except OSError as exc:
        raise UploadError(f"could not read {att.path}: {exc}") from exc

    cached = cache.get(sha, now())
    if cached:
        if _still_there(api, cached.name):
            return cached
        cache.drop(sha)

    try:
        handle = api.files.upload(file=str(att.path))
    except Exception as exc:  # the class is surfaced, never the payload
        raise UploadError(
            f"upload of {att.path.name} failed: {type(exc).__name__}: {exc}"
        ) from exc

    name = getattr(handle, "name", None)
    uri = getattr(handle, "uri", None)
    if not name or not uri:
        raise UploadError(
            f"the upload of {att.path.name} returned no handle (name={name!r} "
            f"uri={uri!r}); the bytes may have been transferred anyway"
        )

    _await_active(api, name, timeout_s=timeout_s, sleep=sleep, now=now)

    up = Upload(
        name=name,
        uri=uri,
        # The server's detected type wins over our extension sniff.
        mime_type=getattr(handle, "mime_type", None) or att.mime_type,
        sha256=sha,
        size_bytes=att.size_bytes,
        uploaded_at=now(),
        display_name=att.path.name,
    )
    cache.put(up)
    return up


def delete(api: Any, name: str) -> None:
    try:
        api.files.delete(name=name)
    except Exception as exc:
        raise UploadError(f"could not delete {name}: {type(exc).__name__}: {exc}") from exc
