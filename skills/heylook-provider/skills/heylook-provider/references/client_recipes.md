# Client recipes

Working code for the parts that are heylook-specific: SSE framing with no
`[DONE]`, block-typed output, and the client-side resize the Messages wire
requires. Adapt rather than copy wholesale — the parts worth keeping are the
event handling and the block separation.

Both streaming clients below were executed against a server emitting the
grammar in `wire_reference.md`, covering the thinking/text split,
`message_stop` termination, the in-band `error` event, and a 503 with
`Retry-After`. The Pillow resize recipe has a harness that extracts this
file's own code block rather than copying it and runs it on Pillow 12.3.0
across PNG and JPEG on both sides of `MAX_EDGE` plus an EXIF-orientation
case: `uv run pytest skills/heylook-provider/tests/`. Nothing runs it
automatically — the repo has no CI and `skill-maintain test` carries no
pytest dependency by design — so it is a check you can re-run, not a gate
that will notice drift on its own. The `sharp` recipe was not executed; its
settings are transcribed from heylook's own frontend.

That split is not bookkeeping. The Pillow recipe shipped with a bug the note
predicted: `keep_png` read `.format` after `exif_transpose`, which returns a
new image whose `.format` is `None`, so every PNG was re-encoded to JPEG and
the PNG branch had never run.

## Python: streaming client

```python
import json
import uuid
from dataclasses import dataclass, field

import httpx


@dataclass
class Result:
    text: str = ""
    thinking: str = ""
    stop_reason: str | None = None
    usage: dict = field(default_factory=dict)
    performance: dict = field(default_factory=dict)


def stream_message(
    base: str,
    model: str,
    messages: list[dict],
    *,
    system: str | None = None,
    api_key: str | None = None,
    on_text=None,
    **sampling,
) -> Result:
    """Stream POST /v1/messages. Omitted sampling keys fall through to the
    server's own cascade, which is the intended way to call it."""
    body = {"model": model, "messages": messages, "stream": True}
    if system:
        body["system"] = system
    body.update({k: v for k, v in sampling.items() if v is not None})

    headers = {
        "Content-Type": "application/json",
        # Correlates the server's logs and is the handle
        # DELETE /v1/requests/{id} cancels by. Fresh per request, not per
        # session: cancelling an id cancels every in-flight request sharing
        # it. A UUID satisfies [A-Za-z0-9._:-]{1,128}; an id the server
        # rejects is replaced with a generated one, and the response header
        # X-Request-ID carries whichever was actually tracked -- read it off
        # `r.headers` if a later cancel 404s unexpectedly.
        "X-Request-ID": str(uuid.uuid4()),
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    out = Result()
    with httpx.Client(timeout=httpx.Timeout(None, connect=10.0)) as client:
        with client.stream("POST", f"{base}/v1/messages", json=body, headers=headers) as r:
            if r.status_code >= 400:
                r.read()
                raise _http_error(r)

            for event, data in _sse(r.iter_lines()):
                if event == "content_block_delta":
                    # Key on delta.type, not on the block index: index is a
                    # running counter across the message, not a stable slot.
                    # And key on the types you HANDLE -- an else branch that
                    # assumes text_delta breaks on Anthropic's signature_delta
                    # (KeyError here, the literal "undefined" appended in JS).
                    delta = data["delta"]
                    if delta["type"] == "thinking_delta":
                        # `thinking` is Anthropic's field; heylook also sends
                        # `text`. `or`, not .get(key, default): an explicit
                        # JSON null is present-but-None, so a default-on-
                        # absence lookup would return None and blow up on +=.
                        out.thinking += delta.get("thinking") or delta.get("text") or ""
                    elif delta["type"] == "text_delta":
                        chunk = delta.get("text") or ""
                        out.text += chunk
                        if on_text and chunk:
                            on_text(chunk)

                elif event == "message_delta":
                    out.stop_reason = data["delta"].get("stop_reason")
                    out.usage = data.get("usage", {})

                elif event == "message_stop":
                    # Terminates the stream. There is no [DONE] sentinel.
                    out.performance = data.get("performance", {})
                    break

                elif event == "error":
                    err = data["error"]
                    raise RuntimeError(f"{err.get('type')}: {err.get('message')}")

    return out


def _sse(lines):
    """Yield (event, parsed_data) pairs from an SSE line iterator."""
    event = None
    for line in lines:
        if not line:
            event = None
            continue
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: ") and event:
            yield event, json.loads(line[6:])


class Overloaded(RuntimeError):
    """503. Normal operation on a server that serialises generation for one
    user, so it is a queue signal rather than a failure."""

    def __init__(self, retry_after: float | None = None):
        super().__init__("model_overloaded")
        self.retry_after = retry_after


def _http_error(r: httpx.Response) -> Exception:
    # 503 is decided BEFORE the body is parsed: the retry path must not
    # depend on the error body happening to be JSON.
    if r.status_code == 503:
        try:
            retry = float(r.headers.get("Retry-After", ""))
        except ValueError:
            retry = None
        return Overloaded(retry)
    try:
        payload = r.json()
    except Exception:
        return RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    detail = payload.get("detail") or payload.get("error", {}).get("message")
    return RuntimeError(f"HTTP {r.status_code}: {detail}")
```

Retry on 503 rather than failing — the server serialises generation for one
user, so a queued request is expected traffic:

```python
import time

def with_backoff(fn, attempts=5):
    for i in range(attempts):
        try:
            return fn()
        except Overloaded as e:
            if i == attempts - 1:
                raise
            # The server sends Retry-After because it knows its own queue
            # depth. Exponential growth is the fallback for when it does not.
            # Floor at 1s: `Retry-After: 0` is legal and would otherwise
            # sleep zero, turning backoff into a hot loop against a server
            # that has just said it is saturated.
            time.sleep(min(max(e.retry_after or 2 ** i, 1), 30))
```

## Python: discovery and capability gating

```python
import httpx

def pick_model(base: str, *, need: set[str] = frozenset({"chat"})) -> str:
    """Resolve a model id at runtime. Ids are install-local -- a literal id
    in source is a 400 on someone else's machine."""
    rows = httpx.get(f"{base}/v1/models", timeout=10).json()["data"]
    for row in rows:
        # `capabilities` is what the server will serve; `modalities` is what
        # the checkpoint declared. They diverge (MLX strips audio towers).
        if need <= set(row.get("capabilities", [])):
            return row["id"]
    raise LookupError(f"no served model has {sorted(need)}; have: "
                      f"{[(r['id'], r.get('capabilities')) for r in rows]}")

vision_model = pick_model(base, need={"chat", "vision"})
```

## TypeScript: streaming client

```ts
type Block = { type: "text" | "thinking" };

export interface StreamResult {
  text: string;
  thinking: string;
  stopReason?: string;
  usage?: Record<string, number>;
  performance?: Record<string, number>;
}

export async function streamMessage(
  base: string,
  body: Record<string, unknown>,
  onText?: (chunk: string) => void,
  apiKey?: string,
): Promise<StreamResult> {
  const res = await fetch(`${base}/v1/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Correlates the server's logs and is the handle
      // DELETE /v1/requests/{id} cancels by. Fresh per request, not per
      // session: cancelling an id cancels every request sharing it.
      // randomUUID() satisfies [A-Za-z0-9._:-]{1,128}; the response's
      // X-Request-ID header carries whichever id was actually tracked.
      "X-Request-ID": crypto.randomUUID(),
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({ ...body, stream: true }),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    if (res.status === 503) {
      throw Object.assign(new Error("model_overloaded"), {
        retryAfter: Number(res.headers.get("Retry-After")) || 1,
      });
    }
    throw new Error(`HTTP ${res.status}: ${payload.detail ?? res.statusText}`);
  }

  const out: StreamResult = { text: "", thinking: "" };
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      const frames = buf.split("\n\n");
      buf = frames.pop() ?? "";

      for (const frame of frames) {
        let event = "";
        let data = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("event: ")) event = line.slice(7);
          else if (line.startsWith("data: ")) data = line.slice(6);
        }
        if (!event || !data) continue;
        const payload = JSON.parse(data);

        if (event === "content_block_delta") {
          // Key on the delta types you handle. An else branch that assumes
          // text_delta appends the literal "undefined" when Anthropic sends
          // signature_delta on a thinking block.
          const d = payload.delta;
          if (d.type === "thinking_delta") {
            out.thinking += d.thinking ?? d.text ?? "";
          } else if (d.type === "text_delta") {
            const chunk = d.text ?? "";
            out.text += chunk;
            if (chunk) onText?.(chunk);
          }
        } else if (event === "message_delta") {
          out.stopReason = payload.delta?.stop_reason;
          out.usage = payload.usage;
        } else if (event === "message_stop") {
          // Terminal. No [DONE] sentinel follows.
          out.performance = payload.performance;
          return out;
        } else if (event === "error") {
          throw new Error(`${payload.error.type}: ${payload.error.message}`);
        }
      }
    }
  } finally {
    // Releases the HTTP connection when the caller aborts mid-stream.
    reader.cancel().catch(() => {});
  }

  return out;
}
```

## Building a multimodal request

```ts
const body = {
  model: visionModelId,                 // from /v1/models, never a literal
  system: "You write prompts for a video model.",
  messages: [{
    role: "user",
    content: [
      { type: "text", text: instruction },
      {
        type: "image",
        source: {                       // Anthropic's nested source
          type: "base64",
          media_type: "image/jpeg",
          data: base64,                 // raw, no "data:" prefix
        },
      },
    ],
  }],
  max_tokens: 1024,
  vision_tokens: 1024,                  // cap visual budget directly
};
```

## Image resize — Node, sharp

`/v1/messages` has no server-side resize, so this runs before the request is
built. The numbers match what heylook's own frontend uses.

```ts
import sharp from "sharp";

const MAX_EDGE = 2048;   // above what a fixed-input tower consumes
const QUALITY = 85;      // no visible loss at normal viewing

export async function prepareImage(input: Buffer | string) {
  const img = sharp(input, { failOn: "none" }).rotate(); // rotate() applies EXIF
  const meta = await img.metadata();

  // PNG in, PNG out: a re-encoded screenshot shows JPEG ringing, and flat UI
  // colours are what PNG compresses well. Everything else becomes JPEG.
  const keepPng = meta.format === "png";

  const resized = img.resize({
    width: MAX_EDGE,
    height: MAX_EDGE,
    fit: "inside",
    withoutEnlargement: true,
  });

  const buf = keepPng
    ? await resized.png({ compressionLevel: 9 }).toBuffer()
    : await resized.jpeg({ quality: QUALITY }).toBuffer();

  return {
    data: buf.toString("base64"),                     // raw base64, no prefix
    media_type: keepPng ? "image/png" : "image/jpeg",
  };
}
```

`.rotate()` with no argument applies the EXIF orientation tag and is
load-bearing, not a nicety: phone cameras routinely store a landscape sensor
read plus a rotation flag, and a decode that ignores it hands the model a
sideways image.

## Image resize — Python, Pillow

```python
import base64, io
from PIL import Image, ImageOps

MAX_EDGE = 2048
QUALITY = 85


def prepare_image(path_or_bytes) -> tuple[str, str]:
    """Return (base64 data, media_type). Raw base64, no data: prefix."""
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes
    img = Image.open(src)

    # Read .format BEFORE transforming. exif_transpose returns a NEW image
    # whose .format is None, so the same check after it is always False and
    # every screenshot silently becomes JPEG.
    keep_png = (img.format or "").upper() == "PNG"

    img = ImageOps.exif_transpose(img)      # apply EXIF orientation
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)  # never enlarges
    buf = io.BytesIO()
    if keep_png:
        img.save(buf, format="PNG", optimize=True)
        media_type = "image/png"
    else:
        img.convert("RGB").save(buf, format="JPEG", quality=QUALITY)
        media_type = "image/jpeg"

    return base64.b64encode(buf.getvalue()).decode(), media_type
```

`thumbnail` resizes in place and never enlarges, so a small image passes
through untouched.

`.format` is set by `Image.open` and by nothing else. Every operation that
returns a new image drops it, and `exif_transpose` returns a new image even
when there is no orientation tag to apply, so the read has to happen first.
`sharp` has no equivalent trap: its `metadata()` describes the input.

**How much resolution to send is a model question, not a transport one.**
Dynamic-resolution towers consume whatever they are given and charge for it
in vision tokens and prefill; fixed-input towers discard the surplus.
2048px is a default that keeps screenshot text legible while taking a phone
photo down by roughly an order of magnitude. Raise it only if fine detail is
the point, and prefer `vision_tokens` when the goal is capping cost.
