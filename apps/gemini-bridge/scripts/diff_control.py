#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=2.3.0", "pyyaml>=6"]
# ///
"""Control harness for comparison recipes.

Tracked deliberately. SKILL.md tells you to validate a new comparison recipe
against a null pair before trusting it -- this is the tool that does that, and
the measured resolution guidance SKILL.md ships came from running it. A
measurement whose instrument is untracked is an assertion, so it lives here now
rather than in gitignored scratch.

The question is not "can Gemini spot a difference" -- that was answered. The
questions that decide whether the recipe is trustworthy are:

  1. Does it invent differences when there are none?  (false positives)
  2. Does `low` resolution miss things `high` catches?  (does high earn 4x?)
  3. Are verdicts stable across repeat runs?           (is it deterministic enough?)

Every real pair contributes a matched null pair (the first image against
itself), so the false-positive rate is measured on exactly the material the
recipe is used on, not on a synthetic stand-in.

    ./diff_control.py --pair BEFORE.jpg AFTER.jpg --pair a.png b.png
    ./diff_control.py --dir some/evidence      # auto-pairs *_BEFORE/*_AFTER
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

RECIPE = Path(
    "apps/gemini-bridge/skills/gemini-multimodal/references/recipes/perceptual-diff.md"
)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
QUESTION = "Compare these two images. The first image, then the second image."


def load_recipe(path: Path) -> tuple[dict, str]:
    m = FRONTMATTER.match(path.read_text())
    if not m:
        sys.exit(f"{path}: no frontmatter")
    return yaml.safe_load(m.group(1)), m.group(2).strip()


def resolve_key() -> str:
    cfg = Path.home() / ".config" / "gemini-bridge" / "config.toml"
    if cfg.is_file():
        with cfg.open("rb") as fh:
            cmd = tomllib.load(fh).get("auth", {}).get("key_command")
        if cmd:
            return subprocess.run(
                shlex.split(cmd), capture_output=True, text=True, check=True
            ).stdout.strip()
    import os

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("no key")
    return key


def block(path: Path, resolution: str) -> dict:
    return {
        "type": "image",
        "data": base64.b64encode(path.read_bytes()).decode(),
        "mime_type": mimetypes.guess_type(str(path))[0] or "image/png",
        "resolution": resolution,
    }


def autopair(directory: Path) -> list[tuple[Path, Path]]:
    pairs = []
    for before in sorted(directory.glob("*BEFORE*")):
        after = Path(str(before).replace("BEFORE", "AFTER"))
        if after.is_file():
            pairs.append((before, after))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, action="append", default=[], metavar=("A", "B"))
    ap.add_argument("--dir", help="auto-pair *BEFORE*/*AFTER* files in a directory")
    ap.add_argument("--repeat", type=int, default=2)
    args = ap.parse_args()

    from google import genai

    meta, system_instruction = load_recipe(RECIPE)
    api = genai.Client(api_key=resolve_key())

    pairs = [(Path(a), Path(b)) for a, b in args.pair]
    if args.dir:
        pairs += autopair(Path(args.dir))
    if not pairs:
        sys.exit("no pairs given")

    def ask(left: Path, right: Path, resolution: str) -> tuple[dict, int]:
        r = api.interactions.create(
            model=meta["model"],
            system_instruction=system_instruction,
            store=False,
            input=[
                block(left, resolution),
                block(right, resolution),
                {"type": "text", "text": QUESTION},
            ],
            generation_config={
                "thinking_level": meta["thinking_level"],
                "seed": meta.get("seed"),
            },
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": meta["schema"],
            },
        )
        return json.loads(r.output_text), getattr(r.usage, "total_input_tokens", 0)

    rows = []
    print(f"{'case':<34} {'cond':<5} {'res':<5} {'identical':<10} {'conf':<7} {'n':<3} {'tok':>6}")
    print("-" * 78)

    for left, right in pairs:
        case = left.stem.replace("_BEFORE", "").replace("BEFORE", "")[:32]
        for resolution in ("low", "high"):
            # null uses the SAME material the real case uses, so the
            # false-positive rate is measured where it matters.
            for cond, a, b in (("null", left, left), ("real", left, right)):
                verdicts = []
                for _ in range(args.repeat):
                    v, tok = ask(a, b, resolution)
                    verdicts.append(v)
                    print(
                        f"{case:<34} {cond:<5} {resolution:<5} "
                        f"{str(v['identical']):<10} {v['confidence']:<7} "
                        f"{len(v['differences']):<3} {tok:>6}"
                    )
                expected = cond == "null"
                got = [v["identical"] for v in verdicts]
                rows.append(
                    {
                        "case": case,
                        "cond": cond,
                        "res": resolution,
                        "pass": all(g == expected for g in got),
                        "stable": len(set(got)) == 1,
                        "n_diff": [len(v["differences"]) for v in verdicts],
                        "conf": {v["confidence"] for v in verdicts},
                    }
                )

    print("\n" + "=" * 78)
    failures = [r for r in rows if not r["pass"]]
    unstable = [r for r in rows if not r["stable"]]
    for r in rows:
        flag = "PASS" if r["pass"] else "FAIL"
        wobble = "" if r["stable"] else "  UNSTABLE"
        print(f"{r['case']:<34} {r['cond']:<5} {r['res']:<5} {flag}{wobble}  n={r['n_diff']}")

    # Does high find anything low missed? That is the only thing that would
    # justify paying 4x per image.
    print("\nlow vs high on real pairs:")
    for case in sorted({r["case"] for r in rows}):
        lo = next((r for r in rows if r["case"] == case and r["cond"] == "real" and r["res"] == "low"), None)
        hi = next((r for r in rows if r["case"] == case and r["cond"] == "real" and r["res"] == "high"), None)
        if lo and hi:
            print(f"  {case:<32} low n={lo['n_diff']}  high n={hi['n_diff']}"
                  f"{'   <- high found more' if max(hi['n_diff']) > max(lo['n_diff']) else ''}")

    confidences = sorted({c for r in rows for c in r["conf"]})
    print(f"\nconfidence values observed: {confidences}")
    print(f"failures: {len(failures)}  unstable: {len(unstable)}  total cases: {len(rows)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
