# Client recipes

Working code for the parts that are heylook-specific: SSE framing with no
`[DONE]`, block-typed output, and the client-side resize the Messages wire
requires. Adapt rather than copy wholesale — the parts worth keeping are the
event handling and the block separation.

Every Python block below was run against a live heylook at the version in
SKILL.md's frontmatter: the streaming client with a stop sequence, the
cancellable call, the conversation store, preset expansion against real
presets, thinking control, image-plan and the model switch. The TypeScript
client was executed against a server emitting the grammar in
`wire_reference.md` (the thinking/text split, `message_stop` termination, the
in-band `error` event, a 503 with `Retry-After`); its closing throw for a
stream that ends without `message_stop` was added after that run. The Pillow resize recipe has a harness that extracts this
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
    stop_sequence: str | None = None
    usage: dict = field(default_factory=dict)
    performance: dict = field(default_factory=dict)


def stream_message(
    base: str,
    model: str,
    messages: list[dict],
    *,
    system: str | None = None,
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
    out = Result()
    finished = False
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
                    out.stop_sequence = data["delta"].get("stop_sequence")
                    out.usage = data.get("usage", {})

                elif event == "message_stop":
                    # Terminates the stream. There is no [DONE] sentinel.
                    out.performance = data.get("performance", {})
                    finished = True
                    break

                elif event == "error":
                    err = data["error"]
                    raise RuntimeError(f"{err.get('type')}: {err.get('message')}")

                # Anything else -- `ping` every 5s of silence, `heylook_progress`
                # during prefill, an event type added later -- falls through.

    if not finished:
        # The connection closed before message_stop: `out.text` is a
        # fragment, not an answer.
        raise RuntimeError("stream ended without message_stop")
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
    # `capabilities` is what the server will serve; `modalities` is what the
    # checkpoint declared. They diverge (MLX strips audio towers).
    fit = [r["id"] for r in rows if need <= set(r.get("capabilities") or [])]
    if not fit:
        raise LookupError(f"no served model has {sorted(need)}; have: "
                          f"{[(r['id'], r.get('capabilities')) for r in rows]}")
    # Roster order says nothing about suitability: several rows can qualify,
    # including image-pipeline encoders and diffusion models. Prefer one that
    # is already resident (no load to pay); otherwise let the user choose.
    resident = httpx.get(f"{base}/v1/system/metrics", timeout=10).json().get("models") or {}
    return next((i for i in fit if i in resident), fit[0])

vision_model = pick_model(base, need={"chat", "vision"})
```

## Python: a non-streaming call you can cancel

Continues the streaming client module above (`_http_error`, `Overloaded`).
Hanging up does not stop a non-streaming run, because the server does not poll
for disconnects, so this holds its own request id and DELETEs it.

```python
import threading


class CancellableCall:
    """One non-streaming POST /v1/messages that another thread can stop."""

    def __init__(self, base: str, body: dict):
        self.base = base
        self.body = {**body, "stream": False}
        self.request_id = str(uuid.uuid4())  # fresh per request, never reused
        self.cancelled = False               # the response cannot tell you
        self.result: dict | None = None

    def run(self) -> dict:
        r = httpx.post(f"{self.base}/v1/messages", json=self.body,
                       headers={"X-Request-ID": self.request_id},
                       timeout=httpx.Timeout(None, connect=10.0))
        if r.status_code >= 400:
            raise _http_error(r)
        self.result = r.json()
        return self.result

    def cancel(self) -> bool:
        """True when a running generation was signalled. 404 means it had
        already finished: too late, not an error."""
        r = httpx.delete(f"{self.base}/v1/requests/{self.request_id}", timeout=10)
        if r.status_code == 404:
            return False
        r.raise_for_status()  # 422: malformed id, a bug in this class
        self.cancelled = r.json().get("cancelled", 0) > 0
        return self.cancelled
```

```python
call = CancellableCall(base, {"model": model_id, "messages": messages})
worker = threading.Thread(target=call.run)
worker.start()
# ... the user presses Stop:
call.cancel()
worker.join()
# call.result carries what was generated, with stop_reason "max_tokens"
# whether it was cancelled or ran out of budget; call.cancelled tells them apart.
```

## Python: conversation store

Continues the same module (`_sse`, `_http_error`). The server keeps the
history and builds each request from it; see `routes.md` for the routes and how
they differ from `/v1/messages`.

```python
def create_conversation(base: str, model_id: str, **fields) -> dict:
    """fields: title, system_prompt, params (store key names), applied_preset_id."""
    body = {"title": fields.pop("title", "untitled"), "model_id": model_id, **fields}
    r = httpx.post(f"{base}/v1/conversations", json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def generate(base: str, conv_id: str, user_content, *, on_text=None,
             **overrides) -> tuple[str, dict | None, list[dict]]:
    """Append a user turn and generate the reply. Returns (answer text, the
    heylook_saved payload, in-band errors).

    `overrides` use the STORE's key names: enable_thinking and
    thinking_budget_tokens, not thinking. Any other key is dropped silently."""
    body = {"mode": "append", "user_content": user_content, "overrides": overrides}
    text, saved, errors = "", None, []
    with httpx.Client(timeout=httpx.Timeout(None, connect=10.0)) as client:
        with client.stream("POST", f"{base}/v1/conversations/{conv_id}/generate",
                           json=body, headers={"X-Request-ID": str(uuid.uuid4())}) as r:
            if r.status_code >= 400:
                r.read()
                # 409 generation_in_progress: one run per conversation.
                raise _http_error(r)
            for event, data in _sse(r.iter_lines()):
                if event == "content_block_delta" and data["delta"]["type"] == "text_delta":
                    chunk = data["delta"].get("text") or ""
                    text += chunk
                    if on_text and chunk:
                        on_text(chunk)
                elif event == "error":
                    # NOT terminal here, unlike /v1/messages: heylook_saved
                    # still follows, and a partial reply is persisted.
                    errors.append(data["error"])
                elif event == "heylook_saved":
                    saved = data  # always the last event
                    break
    return text, saved, errors


def stop(base: str, conv_id: str) -> bool:
    """Stop the running generation; the partial persists. False when none runs.
    This is the only handle: DELETE /v1/requests/{id} does not reach a
    conversation generate."""
    r = httpx.delete(f"{base}/v1/conversations/{conv_id}/generate", timeout=10)
    return r.status_code == 200
```

```python
conv = create_conversation(base, model_id, title="notes", system_prompt="Be brief.")
text, saved, errors = generate(base, conv["id"], "Hello", max_tokens=200,
                               enable_thinking=False)
rows = saved["messages"]      # the rows THIS run wrote (the new user turn and
                              # the reply), not the whole thread; merge them into
                              # client state by id, never by counting positions
saved["end_reason"]           # "complete", "aborted" or "error"
httpx.delete(f"{base}/v1/conversations/{conv['id']}", timeout=10)
```

## Python: expanding a preset

A preset is expanded by the client; the server never applies one. There is no
route to fetch a single preset, so list and filter (the list is not paged).
`model_row` is the model's row from `/v1/models`.

```python
def expand_preset(base: str, preset_id: str, model_row: dict, request: dict) -> dict:
    """A /v1/messages body: the preset as the base, the caller's fields on top."""
    presets = httpx.get(f"{base}/v1/presets", timeout=10).json()["presets"]
    preset = next(p for p in presets if p["id"] == preset_id)
    params = dict(preset.get("params") or {})
    body = {}
    if preset.get("system_prompt"):
        body["system"] = preset["system_prompt"]

    # The two store names that differ from the wire. Both become `thinking`,
    # so they merge into one object when a preset carries both. Like the
    # store, drop a key whose capability the model lacks.
    caps = set(model_row.get("capabilities") or [])
    switch = params.pop("enable_thinking", None)
    budget = params.pop("thinking_budget_tokens", None)
    if budget is not None and "thinking_budget" in caps:
        body["thinking"] = {"budget_tokens": budget}
        if switch is not None:
            body["thinking"]["type"] = "enabled" if switch else "disabled"
    elif switch is not None and "thinking" in caps:
        body["thinking"] = switch

    # The store silently drops a depth the model does not offer;
    # /v1/messages answers 400, so filter it here.
    effort = params.pop("reasoning_effort", None)
    depth = ((model_row.get("engine") or {}).get("thinking") or {}).get("depth") or {}
    if effort is not None and (depth.get("unknown") == "verbatim"
                               or effort in (depth.get("values") or [])
                               or effort in (depth.get("aliases") or {})):
        body["reasoning_effort"] = effort

    body.update(params)          # every other key carries over unchanged
    return {**body, **request}   # the caller's own fields win
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
        // ping, heylook_progress and unknown event types are ignored.
      }
    }
  } finally {
    // Releases the HTTP connection when the caller aborts mid-stream.
    reader.cancel().catch(() => {});
  }

  // Reached only when the connection closed before message_stop.
  throw new Error("stream ended without message_stop");
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
  // No max_tokens: absent lets the model's own configured floor decide.
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

The Python standard library cannot decode or resize images, so a Python client
needs Pillow. The server applies no EXIF orientation of its own: a client that
cannot decode an image must send it already upright and within the cap.

`.format` is set by `Image.open` and by nothing else. Every operation that
returns a new image drops it, and `exif_transpose` returns a new image even
when there is no orientation tag to apply, so the read has to happen first.
`sharp` has no equivalent trap: its `metadata()` describes the input.

**How much resolution to send is a model question, not a transport one.**
Dynamic-resolution towers consume whatever they are given and charge for it
in prompt tokens and prefill; fixed-input towers discard the surplus. 2048px
is a default that keeps screenshot text legible while taking a phone photo
down by roughly an order of magnitude. To see what a size actually costs the
model, ask the engine (next section) rather than guessing.

Hold the image **bytes** and base64-encode only when building the request.
heylook's frontend measured three simultaneous base64 copies of every image
when it encoded early.

## Image cost: `/v1/models/{id}/image-plan`

The server does not resize, but it will tell you what an image costs a loaded
model and what size the engine will resize it to. heylook's own frontend uses
it this way:

1. Apply the client-side cap above.
2. Ask once for **both** sizes, the staged one and the original, in one call.
3. Show the cost as disclosure next to the image, never as a gate on sending.
4. Offer "fit to model": resize the **original** to the returned `target`, so
   the image is resampled once rather than twice.
5. Drop a result that arrives after the image or the model changed.

```python
def image_plan(base: str, model: str, sizes: list[tuple[int, int]]) -> list[dict] | None:
    """Rows of {size, tokens, target}; None when the model is not resident
    (409: planning never loads a model) -- treat that as "cost unknown"."""
    r = httpx.post(f"{base}/v1/models/{model}/image-plan",
                   json={"sizes": [list(s) for s in sizes]}, timeout=30)
    if r.status_code == 409:
        return None
    r.raise_for_status()
    return r.json()["images"]    # target is null on gguf
```

## Thinking control

heylook's frontend shows **one** thinking control per model, built from
`engine.thinking` on the model's `/v1/models` row:

`engine.thinking` is a plain object, not facts: `switch` is the template's
switch variable or null, `depth` is the object below or null, `template` names
the template copy read, and `budget` is `{enforced, reason}` or null.

- **Options**: Default (send neither field); Off and On (`thinking: false` /
  `true`) only when `switch` is non-null; and one level per value in
  `depth.values` that is not in `depth.off`. Values in `off` render the same
  prompt as thinking switched off, so they fold into Off rather than
  appearing as levels.
- **On** is offered only when `depth.default` is null or is itself in `off`;
  otherwise the default level already means on.
- **A level** is sent as `reasoning_effort` with the template's own word, never
  translated, and never gated on thinking being on.
- **`depth.unknown == "verbatim"`** with no switch: a text box, with `values`
  as suggestions, since the template accepts any word.
- **A budget input** (`thinking: {"budget_tokens": N}`) appears only when the
  model has the `thinking_budget` capability (`budget.enforced` is true on
  exactly those models, and `budget.reason` says how), and is hidden while
  thinking is off.
- **`depth.changes_prefix`**: say that changing the level mid-conversation
  re-processes the whole conversation, because the prompt prefix changes and
  the cache cannot be reused.

```python
def thinking_options(row: dict) -> list[tuple[str, dict]]:
    """(label, request fields) pairs for one model's thinking control."""
    thinking = (row.get("engine") or {}).get("thinking") or {}
    depth = thinking.get("depth") or {}
    off = set(depth.get("off") or [])
    opts = [("Default", {})]
    if thinking.get("switch"):
        opts.append(("Off", {"thinking": False}))
        if depth.get("default") is None or depth.get("default") in off:
            opts.append(("On", {"thinking": True}))
    opts += [(v, {"reasoning_effort": v})
             for v in depth.get("values") or [] if v not in off]
    return opts
```

## Model switch

Load the model before the first request to it, so the load is a labelled wait
instead of a silent one inside a generation:

```python
r = httpx.post(f"{base}/v1/models/{model}/load", params={"warm": "true"},
               headers={"X-Request-ID": str(uuid.uuid4())}, timeout=None)
# 400 unknown id, 503 busy (retry on Retry-After), 500 broken model.
# 200 with warmed: false is still loaded.
```

`warm=true` pays the Metal kernel JIT with a 1-token generation behind the
generation gate: do it on startup and on a model switch, never per request.
