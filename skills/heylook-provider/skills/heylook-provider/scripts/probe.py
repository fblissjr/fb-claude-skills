#!/usr/bin/env python3
"""Print a capability matrix for a running heylook server.

Model ids are install-local -- heylook's registry is override-only, so the
roster reflects whatever the operator has downloaded. This resolves what is
actually served, so a client never ships a literal id.

Usage:
    python3 probe.py [--base http://localhost:8000] [--json] [--need vision]

Exit codes:
    0  read the server, and every --need is served
    1  could not read the server: unreachable, refused, or not answering
       heylook's shapes. The message says which
    2  read the server, but no served model has every --need. An empty
       roster counts

The code is derived once and both renderers return it, because the two used
to disagree: `--need vision` against an empty roster exited 0 in text mode
and 2 in --json.

Auth: --api-key, else $HEYLOOK_API_KEY. The gate is loopback-exempt, so it
matters exactly when probing another machine. The key is never printed.

Standard library only; no install step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

EXIT_OK = 0
EXIT_UNREADABLE = 1
EXIT_UNMATCHED = 2


class Unreadable(Exception):
    """A server we could not read. `hint` is the operator's next move.

    Distinct from "no model matched": that is an answer, this is the absence
    of one, and they send the operator to different places.
    """

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint


def fetch(base: str, path: str, timeout: float, api_key: str | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=timeout
        ) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "unknown")
    except urllib.error.HTTPError as e:
        # HTTPError subclasses URLError subclasses OSError, so it must be
        # caught FIRST -- a 401 from a running server is not a dead server.
        if e.code in (401, 403):
            raise Unreadable(
                f"{base} answered HTTP {e.code} for {path}.",
                "that gate is HEYLOOK_API_KEY. Pass --api-key or set "
                "HEYLOOK_API_KEY -- it is loopback-exempt, so it applies "
                "only when you probe from another machine.",
            ) from e
        raise Unreadable(
            f"{base} answered HTTP {e.code} for {path}.",
            f"a heylook server serves {path}. Check the base URL and port.",
        ) from e
    except (urllib.error.URLError, OSError) as e:
        raise Unreadable(
            f"cannot reach {base}: {e}",
            "start the server with `heylookllm` on the host machine.",
        ) from e

    try:
        payload = json.loads(body.decode())
    except (ValueError, UnicodeDecodeError) as e:
        # JSONDecodeError is a ValueError, so the OSError arm above never
        # sees it. The realistic trigger is another service already on :8000.
        raise Unreadable(
            f"{base} returned a non-JSON body for {path} (content-type: {ctype}).",
            "is that a heylook server?",
        ) from e

    if not isinstance(payload, dict):
        raise Unreadable(
            f"{base} returned {type(payload).__name__}, not an object, for {path}.",
            "is that a heylook server?",
        )
    return payload


def models_from(payload: dict, base: str) -> list[dict]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise Unreadable(
            f"{base} returned /v1/models with no `data` list.",
            "is that a heylook server?",
        )
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("id"):
            raise Unreadable(
                f"{base} returned a /v1/models row (index {i}) with no `id`.",
                "the roster is unusable: an id is what a client would send.",
            )
    return rows


def _samplers(caps: dict) -> list:
    available = (caps.get("samplers") or {}).get("available") or []
    return available if isinstance(available, list) else []


def _sampler_names(caps: dict) -> list[str]:
    return [
        n
        for n in (s.get("name") if isinstance(s, dict) else str(s) for s in _samplers(caps))
        if n
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--api-key", default=None,
                    help="bearer token; defaults to $HEYLOOK_API_KEY. Never printed")
    ap.add_argument("--need", action="append", default=[], metavar="CAP",
                    help="require this capability; repeatable. Exit 2 if unmatched")
    args = ap.parse_args(argv)

    api_key = args.api_key or os.environ.get("HEYLOOK_API_KEY") or None

    try:
        models = models_from(fetch(args.base, "/v1/models", args.timeout, api_key), args.base)
    except Unreadable as e:
        print(str(e), file=sys.stderr)
        if e.hint:
            print(e.hint, file=sys.stderr)
        return EXIT_UNREADABLE

    # Capabilities are best-effort extra context; a server that answers
    # /v1/models but not this is still usable.
    try:
        caps = fetch(args.base, "/v1/capabilities", args.timeout, api_key)
    except Unreadable:
        caps = {}

    need = set(args.need)
    matched = [m for m in models if need <= set(m.get("capabilities") or [])]

    # Derived once. Both renderers return this; they used to disagree.
    status = EXIT_OK if matched or not need else EXIT_UNMATCHED

    if args.json:
        json.dump({"base": args.base,
                   "server_version": caps.get("server_version"),
                   "samplers": _sampler_names(caps),
                   "models": models,
                   "matched": [m["id"] for m in matched]},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return status

    print(f"heylook {caps.get('server_version', 'unknown')} at {args.base}")
    names = _sampler_names(caps)
    if names:
        print(f"samplers: {', '.join(names)}")
    print()

    if not models:
        print("no models served. check the [scan] folders in models.toml.")
    else:
        matched_ids = {m["id"] for m in matched}
        width = max(len(m["id"]) for m in models)
        print(f"{'MODEL'.ljust(width)}  {'PROVIDER':<14}  CAPABILITIES")
        print(f"{'-' * width}  {'-' * 14}  {'-' * 40}")
        for m in sorted(models, key=lambda r: r["id"]):
            cap = ",".join(m.get("capabilities") or []) or "-"
            mark = "*" if need and m["id"] in matched_ids else ""
            print(f"{m['id'].ljust(width)}  {(m.get('provider') or '-'):<14}  {cap}{mark}".rstrip())

    if need:
        print()
        if matched:
            print(f"* serves {sorted(need)}: {', '.join(m['id'] for m in matched)}")
        else:
            print(f"no served model has {sorted(need)}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
