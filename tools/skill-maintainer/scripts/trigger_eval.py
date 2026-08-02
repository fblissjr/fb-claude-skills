#!/usr/bin/env python3
"""Trigger-rate measurement for skill descriptions.

Adapted from skill-creator's scripts/run_eval.py. Two differences, both
deliberate:

1. Two modes. "real" detects whether the actually-installed skill fires
   (no synthetic command file, so an installed twin cannot steal the
   trigger and be miscounted as a miss). "synthetic" reproduces stock
   run_eval.py behaviour for skills that are not installed.
2. Full-turn scan. Stock run_eval.py returns False at the first tool call
   that is not Skill/Read, so a natural Read -> Skill -> Edit sequence
   scores as a miss. This scans every assistant message in the turn.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def run_single_query(
    query: str,
    mode: str,
    target: str,
    description: str,
    timeout: int,
    cwd: str,
) -> bool:
    """Run one query; return whether the target skill was invoked."""
    command_file = None
    detect = target

    try:
        if mode == "synthetic":
            unique_id = uuid.uuid4().hex[:8]
            detect = f"{target}-skill-{unique_id}"
            commands_dir = Path(cwd) / ".claude" / "commands"
            commands_dir.mkdir(parents=True, exist_ok=True)
            command_file = commands_dir / f"{detect}.md"
            indented = "\n  ".join(description.split("\n"))
            command_file.write_text(
                f"---\ndescription: |\n  {indented}\n---\n\n"
                f"# {target}\n\nThis skill handles: {description}\n"
            )

        cmd = [
            "claude", "-p", query,
            "--output-format", "stream-json",
            "--verbose",
        ]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, env=env,
                cwd=cwd, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "assistant":
                continue
            for item in event.get("message", {}).get("content", []):
                if item.get("type") != "tool_use":
                    continue
                blob = json.dumps(item.get("input", {}))
                if item.get("name") in ("Skill", "Read") and detect in blob:
                    return True
        return False
    finally:
        if command_file is not None and command_file.exists():
            command_file.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--mode", choices=["real", "synthetic"], required=True)
    ap.add_argument("--target", required=True,
                    help="real: installed skill id e.g. writing:voice-match. "
                         "synthetic: bare skill name")
    ap.add_argument("--description", default="", help="synthetic mode only")
    ap.add_argument("--cwd", required=True, help="neutral dir to run queries in")
    ap.add_argument("--runs-per-query", type=int, default=3)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--trigger-threshold", type=float, default=0.5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    triggers: dict[str, list[bool]] = {}
    items: dict[str, dict] = {}

    with ProcessPoolExecutor(max_workers=args.num_workers) as ex:
        futures = {}
        for item in eval_set:
            for _ in range(args.runs_per_query):
                fut = ex.submit(
                    run_single_query, item["query"], args.mode, args.target,
                    args.description, args.timeout, args.cwd,
                )
                futures[fut] = item
        for fut in as_completed(futures):
            item = futures[fut]
            q = item["query"]
            items[q] = item
            triggers.setdefault(q, [])
            try:
                triggers[q].append(fut.result())
            except Exception as e:
                print(f"warn: {e}", file=sys.stderr)
                triggers[q].append(False)

    results = []
    for q, runs in triggers.items():
        rate = sum(runs) / len(runs)
        should = items[q]["should_trigger"]
        results.append({
            "query": q,
            "should_trigger": should,
            "trigger_rate": rate,
            "triggers": sum(runs),
            "runs": len(runs),
            "pass": rate >= args.trigger_threshold if should
                    else rate < args.trigger_threshold,
        })

    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]
    out = {
        "target": args.target,
        "mode": args.mode,
        "results": sorted(results, key=lambda r: (not r["should_trigger"], r["query"])),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["pass"]),
            "recall": round(sum(1 for r in pos if r["pass"]) / len(pos), 3) if pos else None,
            "positives": len(pos),
            "false_trigger_rate": round(sum(1 for r in neg if not r["pass"]) / len(neg), 3) if neg else None,
            "negatives": len(neg),
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["summary"], indent=2))


if __name__ == "__main__":
    main()
