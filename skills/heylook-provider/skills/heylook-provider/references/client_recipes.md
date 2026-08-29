# Client recipes

Working code for the parts that are heylook-specific: SSE framing with no
`[DONE]`, block-typed output, and the client-side resize the Messages wire
requires. Adapt rather than copy wholesale — the parts worth keeping are the
event handling and the block separation.

## Python: streaming client

```python
import json
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

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    out = Result()
    with httpx.Client(timeout=httpx.Timeout(None, connect=10.0)) as client:
        with client.stream("POST", f"{base}/v1/messages", json=body, headers=headers) as r:
            if r.status_code >= 400:
                r.read()
                raise _http_error(r)

            block_type = None
            for event, data in _sse(r.iter_lines()):
                if event == "content_block_start":
                    block_type = data["content_block"]["type"]

                elif event == "content_block_delta":
                    # Key on delta.type, not on the block index: index is a
                    # running counter across the message, not a stable slot.
                    delta = data["delta"]
                    if delta["type"] == "thinking_delta":
                        out.thinking += delta["text"]
                    else:
                        out.text += delta["text"]
                        if on_text:
                            on_text(delta["text"])

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


def _http_error(r: httpx.Response) -> Exception:
    try:
        payload = r.json()
    except Exception:
        return RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code == 503:
        retry = r.headers.get("Retry-After")
        return RuntimeError(f"model_overloaded; retry after {retry}s")
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
        except RuntimeError as e:
            if "model_overloaded" not in str(e) or i == attempts - 1:
                raise
            time.sleep(min(2 ** i, 30))
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
          const d = payload.delta;
          if (d.type === "thinking_delta") out.thinking += d.text;
          else {
            out.text += d.text;
            onText?.(d.text);
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
        source_type: "base64",          // flat, not Anthropic's nested source
        media_type: "image/jpeg",
        data: base64,                   // raw, no "data:" prefix
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
    img = ImageOps.exif_transpose(img)      # apply EXIF orientation
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)  # never enlarges

    keep_png = (img.format or "").upper() == "PNG"
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

**How much resolution to send is a model question, not a transport one.**
Dynamic-resolution towers consume whatever they are given and charge for it
in vision tokens and prefill; fixed-input towers discard the surplus.
2048px is a default that keeps screenshot text legible while taking a phone
photo down by roughly an order of magnitude. Raise it only if fine detail is
the point, and prefer `vision_tokens` when the goal is capping cost.
