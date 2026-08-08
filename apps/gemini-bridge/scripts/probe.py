#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=2.3.0"]
# ///
"""Live probe for the Gemini Interactions API.

Tracked deliberately. Every static source about this API was wrong about
something material -- the OpenAPI spec omits video, the generated SDK omits a
parameter the API accepts and ships a delete the server does not implement, and
the docs contradict themselves on video token rates. Only a live call is
authoritative, which makes this the instrument that settles any new parameter
before it is exposed. It lived in gitignored scratch until 2026-08-02, while two
tracked documents instructed readers to run it.

Settles the live unknowns that no amount of doc reading resolves. Each probe is
isolated: a failure reports and moves on, so one 400 does not hide the rest.

Attempts to delete every interaction it stores, but the delete is known to
fail: probe 8's own settled finding is that `interactions.delete` returns 501,
so anything stored persists for the project retention window. Only the
uploaded files are actually removed. Total spend is a few cents.

    export GEMINI_API_KEY=...            # or: --op-ref op://Vault/Item/field
    ./gemini_probe.py
    ./gemini_probe.py --image a.png --image b.png --video clip.mp4

What it answers:
  1  auth + basic call shape
  2  is `temperature` accepted or rejected  (docs and SDK disagree)
  3  is `seed` accepted
  4  does usage report thought tokens separately
  5  does response_format + JSON schema work
  6  does count_tokens agree with usage       (three doc pages disagree ~4x)
  7  does store=false really block previous_interaction_id
  8  does interactions.delete actually remove it
  9  is service_tier="flex" accepted
 10  image attach, per-item media resolution, and token cost by resolution
 11  video attach via files.upload
 12  audio attach via files.upload           (same road, separate content type)

Probe 11 is what the shipped video path is modelled on, so it is the arm to
re-run when that path misbehaves. Probe 12 exists because audio reaches the API
through identical machinery and was still never confirmed: "the same code
handles it" is a hypothesis about the server, not a fact about it, and this file
is where that distinction is enforced.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import tomllib
import traceback
from pathlib import Path

MODEL = "gemini-3.6-flash"

results: list[tuple[str, str, str]] = []
created_interactions: list[str] = []
uploaded_files: list[str] = []


def record(name: str, verdict: str, detail: str = "") -> None:
    results.append((name, verdict, detail))
    mark = {"YES": "+", "NO": "-", "ERR": "!", "INFO": " "}.get(verdict, "?")
    print(f"  [{mark}] {verdict:4}  {detail}")


def probe(name: str):
    """Decorator-ish helper: run fn, catch everything, keep going."""

    def wrap(fn):
        print(f"\n{name}")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - the whole point is to survive
            record(name, "ERR", f"{type(exc).__name__}: {exc}")
            if os.environ.get("PROBE_TRACE"):
                traceback.print_exc()
        return fn

    return wrap


def resolve_key(op_ref: str | None) -> str:
    """Prefer the user config so no secret reference lands on a command line.

    Command lines are recorded in session transcripts and shell history. The
    reference is not itself a secret, but there is no reason to scatter it.
    """
    command = None
    if op_ref:
        command = f"op read {shlex.quote(op_ref)}"
    else:
        cfg = Path.home() / ".config" / "gemini-bridge" / "config.toml"
        if cfg.is_file():
            with cfg.open("rb") as fh:
                command = tomllib.load(fh).get("auth", {}).get("key_command")

    if command:
        out = subprocess.run(
            shlex.split(command), capture_output=True, text=True, check=True
        )
        return out.stdout.strip()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("no key: set GEMINI_API_KEY or configure a key command")
    return key


def track(interaction) -> None:
    iid = getattr(interaction, "id", None)
    if iid:
        created_interactions.append(iid)


def usage_dict(interaction) -> dict:
    u = getattr(interaction, "usage", None)
    if u is None:
        return {}
    if hasattr(u, "model_dump"):
        return {k: v for k, v in u.model_dump().items() if v is not None}
    return dict(u)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--op-ref", help="1Password secret reference for the API key")
    ap.add_argument("--image", action="append", default=[], help="repeatable")
    ap.add_argument("--video", help="path to a short video file")
    ap.add_argument("--audio", help="path to a short audio file")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    from google import genai

    client = genai.Client(api_key=resolve_key(args.op_ref))
    model = args.model
    print(f"model: {model}")

    # -- 1 ---------------------------------------------------------------
    @probe("1. basic call + response shape")
    def _():
        r = client.interactions.create(
            model=model, input="Reply with exactly: ok", store=False
        )
        record("basic", "YES", f"output_text={r.output_text!r}")
        record("steps", "INFO", f"{[getattr(s, 'type', '?') for s in r.steps]}")

    # -- 2 ---------------------------------------------------------------
    @probe("2. temperature -- accepted or rejected?")
    def _():
        try:
            r = client.interactions.create(
                model=model,
                input="Say ok",
                store=False,
                generation_config={"temperature": 0.2},
            )
            record("temperature_accepted", "YES", f"not rejected -- output={r.output_text!r}")
        except Exception as exc:  # noqa: BLE001
            record("temperature_accepted", "NO", f"REJECTED -- {type(exc).__name__}: {exc}")
            return

        # Accepted is not the same as honored. Same seed, same prompt, two
        # temperatures: if the server ignores temperature, both runs collapse
        # to the same answer set.
        def sample(temp: float) -> set[str]:
            outs = set()
            for _n in range(4):
                r = client.interactions.create(
                    model=model,
                    input="Name one animal. One word, no punctuation.",
                    store=False,
                    generation_config={
                        "temperature": temp,
                        "thinking_level": "minimal",
                    },
                )
                outs.add((r.output_text or "").strip().lower())
            return outs

        cold, hot = sample(0.0), sample(2.0)
        record(
            "temperature_honored",
            "YES" if len(hot) > len(cold) else "INFO",
            f"t=0.0 -> {sorted(cold)} | t=2.0 -> {sorted(hot)}",
        )

    # -- 3 ---------------------------------------------------------------
    @probe("3. seed")
    def _():
        outs = []
        for _i in range(2):
            r = client.interactions.create(
                model=model,
                input="Name one color. One word.",
                store=False,
                generation_config={"seed": 42, "thinking_level": "minimal"},
            )
            outs.append((r.output_text or "").strip())
        same = outs[0] == outs[1]
        record("seed", "YES" if same else "INFO", f"{outs} identical={same}")

    # -- 4 ---------------------------------------------------------------
    @probe("4. thinking_level -- does usage break out thought tokens?")
    def _():
        r = client.interactions.create(
            model=model,
            input="What is 17 * 23? Answer with the number only.",
            store=False,
            # thinking_summaries is a literal 'auto' | 'none', NOT a bool.
            generation_config={"thinking_level": "high", "thinking_summaries": "auto"},
        )
        record("thinking_high", "YES", f"usage={usage_dict(r)}")
        low = client.interactions.create(
            model=model,
            input="What is 17 * 23? Answer with the number only.",
            store=False,
            generation_config={"thinking_level": "minimal"},
        )
        record("thinking_minimal", "INFO", f"usage={usage_dict(low)}")

    # -- 5 ---------------------------------------------------------------
    @probe("5. response_format + JSON schema")
    def _():
        schema = {
            "type": "object",
            "properties": {
                "color": {"type": "string"},
                "hex": {"type": "string"},
            },
            "required": ["color", "hex"],
        }
        r = client.interactions.create(
            model=model,
            input="Give me one color and its hex code.",
            store=False,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
        )
        parsed = json.loads(r.output_text)
        record("response_format", "YES", f"parsed={parsed}")

    # -- 6 ---------------------------------------------------------------
    @probe("6. count_tokens vs usage (text)")
    def _():
        text = "Explain photosynthesis in one sentence."
        ct = client.models.count_tokens(model=model, contents=[text])
        counted = getattr(ct, "total_tokens", None)
        r = client.interactions.create(model=model, input=text, store=False)
        u = usage_dict(r)
        actual = u.get("total_input_tokens")
        record(
            "count_tokens",
            "YES" if counted == actual else "INFO",
            f"count_tokens={counted} usage_input={actual} agree={counted == actual}",
        )

    # -- 7 ---------------------------------------------------------------
    @probe("7. store=false blocks previous_interaction_id?")
    def _():
        first = client.interactions.create(
            model=model, input="My name is Ada.", store=False
        )
        try:
            second = client.interactions.create(
                model=model,
                input="What is my name?",
                store=False,
                previous_interaction_id=first.id,
            )
            record(
                "store_false_chain",
                "YES",
                f"UNEXPECTEDLY ALLOWED -- output={second.output_text!r}",
            )
        except Exception as exc:  # noqa: BLE001
            record(
                "store_false_chain", "NO", f"blocked as documented -- {type(exc).__name__}"
            )

    # -- 8 ---------------------------------------------------------------
    @probe("8. store=true -> get -> delete -> get")
    def _():
        r = client.interactions.create(model=model, input="Remember: blue.", store=True)
        track(r)
        got = client.interactions.get(r.id)
        record("get", "YES", f"id={r.id} status={getattr(got, 'status', '?')}")

        # Chain BEFORE deleting -- both because delete may fail and because a
        # successful delete would invalidate the id we are chaining from.
        chained = client.interactions.create(
            model=model,
            input="What colour did I ask you to remember? One word.",
            store=True,
            previous_interaction_id=r.id,
        )
        track(chained)
        record("stateful_chain", "YES", f"recalled={chained.output_text!r}")

        try:
            client.interactions.delete(r.id)
        except Exception as exc:  # noqa: BLE001
            record(
                "delete",
                "NO",
                f"NOT IMPLEMENTED SERVER-SIDE -- {exc}. SDK has the method and the "
                "docs describe it, but the server refuses. Purge is impossible; "
                "the project retention window is the only cleanup.",
            )
            return
        created_interactions.remove(r.id)
        try:
            client.interactions.get(r.id)
            record("delete", "NO", "still retrievable after delete")
        except Exception as exc:  # noqa: BLE001
            record("delete", "YES", f"gone after delete ({type(exc).__name__})")

    # -- 9 ---------------------------------------------------------------
    @probe("9. service_tier=flex")
    def _():
        r = client.interactions.create(
            model=model, input="Say ok", store=False, service_tier="flex"
        )
        record("flex", "YES", f"accepted -- output={r.output_text!r}")

    # -- 10 --------------------------------------------------------------
    if args.image:

        @probe("10. image attach + per-item media resolution")
        def _():
            import base64
            import mimetypes

            blocks = []
            for path in args.image:
                mime = mimetypes.guess_type(path)[0] or "image/png"
                with open(path, "rb") as fh:
                    data = base64.b64encode(fh.read()).decode()
                blocks.append({"type": "image", "data": data, "mime_type": mime})

            for res in ("low", "high"):
                sized = [dict(b, resolution=res) for b in blocks]
                r = client.interactions.create(
                    model=model,
                    input=[
                        *sized,
                        {
                            "type": "text",
                            "text": "Describe any visual differences. Be specific.",
                        },
                    ],
                    store=False,
                )
                u = usage_dict(r)
                record(
                    f"image[{res}]",
                    "YES",
                    f"input_tokens={u.get('total_input_tokens')} "
                    f"answer={(r.output_text or '')[:120]!r}",
                )

    # -- 11 --------------------------------------------------------------
    if args.video:

        @probe("11. video via files.upload")
        def _():
            f = client.files.upload(file=args.video)
            uploaded_files.append(getattr(f, "name", ""))
            record("upload", "YES", f"uri={f.uri} mime={f.mime_type}")

            # Files need to finish processing before first use.
            for _ in range(30):
                state = str(getattr(client.files.get(name=f.name), "state", ""))
                if "ACTIVE" in state.upper():
                    break
                time.sleep(2)

            r = client.interactions.create(
                model=model,
                input=[
                    {
                        "type": "video",
                        "uri": f.uri,
                        "mime_type": f.mime_type,
                        "resolution": "low",
                    },
                    {"type": "text", "text": "Describe the scene in two sentences."},
                ],
                store=False,
            )
            u = usage_dict(r)
            record(
                "video",
                "YES",
                f"input_tokens={u.get('total_input_tokens')} "
                f"answer={(r.output_text or '')[:120]!r}",
            )

    # -- 12 --------------------------------------------------------------
    if args.audio:

        @probe("12. audio via files.upload")
        def _():
            f = client.files.upload(file=args.audio)
            uploaded_files.append(getattr(f, "name", ""))
            record("upload", "YES", f"uri={f.uri} mime={f.mime_type}")

            for _ in range(30):
                state = str(getattr(client.files.get(name=f.name), "state", ""))
                if "ACTIVE" in state.upper():
                    break
                time.sleep(2)

            # No `resolution` here on purpose. AudioContent has no such field,
            # and whether an extra key 400s or is ignored is exactly the sort of
            # thing only a live call settles -- so the shipped path strips it
            # and this probe matches the shipped path.
            r = client.interactions.create(
                model=model,
                input=[
                    {"type": "audio", "uri": f.uri, "mime_type": f.mime_type},
                    {"type": "text", "text": "Transcribe this. Note any silence."},
                ],
                store=False,
            )
            u = usage_dict(r)
            record(
                "audio",
                "YES",
                f"input_tokens={u.get('total_input_tokens')} "
                f"by_modality={u.get('input_tokens_by_modality')} "
                f"answer={(r.output_text or '')[:100]!r}",
            )

    # -- cleanup ---------------------------------------------------------
    print("\ncleanup")
    for iid in created_interactions:
        try:
            client.interactions.delete(iid)
            print(f"  deleted interaction {iid}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED to delete {iid}: {exc}")
    for name in uploaded_files:
        try:
            client.files.delete(name=name)
            print(f"  deleted file {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED to delete {name}: {exc}")

    print("\n" + "=" * 70)
    for name, verdict, detail in results:
        print(f"{verdict:4}  {name:22}  {detail[:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
