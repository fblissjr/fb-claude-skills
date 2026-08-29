#!/usr/bin/env python3
"""Print a capability matrix for a running heylook server.

Model ids are install-local -- heylook's registry is override-only, so the
roster reflects whatever the operator has downloaded. This resolves what is
actually served, so a client never ships a literal id.

Usage:
    python3 probe.py [--base http://localhost:8000] [--json] [--need vision]

Exit codes: 0 reachable, 1 unreachable, 2 no model matched --need.
Standard library only; no install step.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def fetch(base: str, path: str, timeout: float) -> dict:
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}", headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--need", action="append", default=[], metavar="CAP",
                    help="require this capability; repeatable. Exit 2 if unmatched")
    args = ap.parse_args()

    try:
        models = fetch(args.base, "/v1/models", args.timeout).get("data", [])
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"unreachable: {args.base} ({e})", file=sys.stderr)
        print("start the server with `heylookllm` on the host machine.", file=sys.stderr)
        return 1

    # Capabilities are best-effort extra context; a server that answers
    # /v1/models but not this is still usable.
    try:
        caps = fetch(args.base, "/v1/capabilities", args.timeout)
    except Exception:
        caps = {}

    need = set(args.need)
    matched = [m for m in models
               if need <= set(m.get("capabilities") or [])]

    if args.json:
        json.dump({"base": args.base,
                   "server_version": caps.get("server_version"),
                   "samplers": [s.get("name") if isinstance(s, dict) else s
                                for s in _samplers(caps)],
                   "models": models,
                   "matched": [m["id"] for m in matched]},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if matched or not need else 2

    version = caps.get("server_version", "unknown")
    print(f"heylook {version} at {args.base}")

    samplers = _samplers(caps)
    if samplers:
        names = [s.get("name") if isinstance(s, dict) else str(s) for s in samplers]
        print(f"samplers: {', '.join(n for n in names if n)}")
    print()

    if not models:
        print("no models served. check the [scan] folders in models.toml.")
        return 0

    width = max(len(m["id"]) for m in models)
    print(f"{'MODEL'.ljust(width)}  {'PROVIDER':<14}  CAPABILITIES")
    print(f"{'-' * width}  {'-' * 14}  {'-' * 40}")
    for m in sorted(models, key=lambda r: r["id"]):
        cap = ",".join(m.get("capabilities") or []) or "-"
        mark = "*" if need and m in matched else ""
        print(f"{m['id'].ljust(width)}  {(m.get('provider') or '-'):<14}  {cap}{mark}".rstrip())

    if need:
        print()
        if matched:
            print(f"* serves {sorted(need)}: {', '.join(m['id'] for m in matched)}")
        else:
            print(f"no served model has {sorted(need)}")
            return 2
    return 0


def _samplers(caps: dict) -> list:
    available = (caps.get("samplers") or {}).get("available") or []
    return available if isinstance(available, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
