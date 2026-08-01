#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["orjson>=3.10"]
# ///
"""Build the advisor's view of a session from its transcript JSONL.

The API advisor tool hands the advisor model the executor's live context for
free. Claude Code has no equivalent: a subagent either inherits context (fork,
same model) or takes a model override (fresh, no context). Never both. This
script is the bridge -- it reconstructs a bounded view of the session from the
transcript file on disk so a stronger-model subagent can read it.

It is a lossy reconstruction on purpose. A raw transcript in this repo reached
13 MB; the live context window it came from never held that, because tool
results get truncated and compacted away. Feeding the raw file to an advisor
would cost more than the advice is worth and bury the signal.

What survives, in priority order:
  1. The task -- the first human message, verbatim.
  2. Steering -- every later human message, verbatim. These are the corrections
     and constraints, the highest-signal bytes in the file.
  3. The now -- the last few exchanges at high fidelity.
  4. Errors -- failed tool calls anywhere in the run.
  5. The middle -- compressed to one line per tool call.

Output is markdown on stdout. A size report goes to stderr so the caller can
see the cost before paying it.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson

# Tool calls whose inputs name a file we should track as "touched".
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}

# Keys a tool uses to name its target file, in preference order. One list, used
# by both the trajectory summary and the touched-files collector -- they
# previously kept separate copies and disagreed: the collector checked only
# `file_path`, so NotebookEdit (which uses `notebook_path`) rendered in the
# trajectory but never appeared under "Files written or edited".
PATH_KEYS = ("file_path", "path", "notebook_path")


def target_path(tool_input: Any) -> str | None:
    """The file a tool call names, if it names one."""
    if not isinstance(tool_input, dict):
        return None
    for key in PATH_KEYS:
        if tool_input.get(key):
            return str(tool_input[key])
    return None

# Injected wrappers that are noise to an advisor: they are harness bookkeeping,
# not anything the executor decided to do.
NOISE_MARKERS = ("<system-reminder>", "<command-name>", "<local-command-")


def clip(text: str, limit: int) -> str:
    """Truncate, marking the cut so the advisor knows it is reading a fragment."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}\n[... {len(text) - limit} chars elided ...]"


def strip_noise(text: str) -> str:
    """Drop harness-injected blocks that the executor never authored."""
    for marker in NOISE_MARKERS:
        if marker in text:
            head, _, _ = text.partition(marker)
            text = head
    return text.strip()


def block_text(block: Any) -> str:
    """Pull displayable text out of a content block or a raw string."""
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return ""
    if "text" in block and isinstance(block["text"], str):
        return block["text"]
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block_text(b) for b in content)
    return ""


@dataclass
class Event:
    """One turn's worth of transcript, normalized."""

    kind: str  # "human" | "assistant"
    index: int
    text: str = ""
    tool_calls: list[tuple[str, str]] = field(default_factory=list)  # (name, summary)
    errors: list[str] = field(default_factory=list)


def summarize_input(name: str, tool_input: Any) -> str:
    """One line describing what a tool call actually did.

    Full inputs are the bulk of a transcript -- a single Write carries the
    entire file. The advisor needs to know a file was written and which one,
    not its contents; it has Read to go look if that matters.
    """
    if not isinstance(tool_input, dict):
        return ""
    # Delegation is worth more detail than a path: which agent, and what for.
    if name in ("Agent", "Task"):
        return clip(
            f"{tool_input.get('subagent_type', 'agent')}: "
            f"{tool_input.get('description') or tool_input.get('prompt', '')}",
            200,
        )
    named = target_path(tool_input)
    if named:
        return named
    for key in ("command", "pattern", "query", "url", "prompt", "description"):
        if key in tool_input:
            return clip(str(tool_input[key]), 200)
    return clip(orjson.dumps(tool_input).decode(), 200)


def load_events(
    path: Path, include_sidechains: bool
) -> tuple[list[Event], dict[str, Any]]:
    """Parse the transcript into ordered events plus session metadata."""
    events: list[Event] = []
    meta: dict[str, Any] = {}
    touched: list[str] = []
    # tool_use id -> tool name, so a tool_result can be attributed to its call.
    call_names: dict[str, str] = {}

    with path.open("rb") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = orjson.loads(raw)
            except orjson.JSONDecodeError:
                continue  # a partially flushed final line is normal, not fatal
            if not isinstance(record, dict):
                continue

            kind = record.get("type")
            if kind not in ("user", "assistant"):
                continue
            if record.get("isSidechain") and not include_sidechains:
                continue

            for key in ("sessionId", "cwd", "gitBranch", "version", "effort"):
                if record.get(key) is not None:
                    meta[key] = record[key]

            message = record.get("message")
            if not isinstance(message, dict):
                # A record can parse as valid JSON and still carry an
                # unexpected `message` shape. Skipping degrades the digest by
                # one turn; raising aborts the whole run and blocks the consult.
                continue
            content = message.get("content")
            event = Event(kind="assistant" if kind == "assistant" else "human", index=len(events))
            # Promotion to human is sticky. A single user-role message can batch
            # an AskUserQuestion result together with an ordinary tool result,
            # and processing the ordinary one second used to flip `kind` back to
            # tool_output -- which then dropped the whole event, user's answer
            # included. Same failure class as the bug that shipped in 0.1.0,
            # one ordering away.
            promoted_to_human = False

            if isinstance(content, str):
                event.text = strip_noise(content)
            elif isinstance(content, list):
                texts: list[str] = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        texts.append(block.get("text", ""))
                    elif btype == "tool_use":
                        name = str(block.get("name", "?"))
                        call_names[str(block.get("id", ""))] = name
                        event.tool_calls.append(
                            (name, summarize_input(name, block.get("input") or {}))
                        )
                        if name in WRITE_TOOLS:
                            target = target_path(block.get("input"))
                            if target:
                                touched.append(target)
                    elif btype == "tool_result":
                        called = call_names.get(str(block.get("tool_use_id", "")), "?")
                        # AskUserQuestion returns through the tool channel, but
                        # its content is the user speaking -- usually the
                        # binding constraint of the whole run. Classifying it
                        # as tool output silently drops the most important
                        # bytes in the file, so promote it back to human.
                        if called == "AskUserQuestion":
                            event.kind = "human"
                            promoted_to_human = True
                            texts.append(block_text(block))
                            continue
                        # Any other user record carrying tool_result blocks is
                        # the harness returning output, not a person speaking --
                        # unless this event already carried a user answer.
                        if not promoted_to_human:
                            event.kind = "tool_output"
                        if block.get("is_error"):
                            event.errors.append(
                                f"{called}: {clip(block_text(block), 200)}"
                            )
                    # thinking blocks are skipped: the transcript stores them
                    # encrypted, with an empty `thinking` field.
                event.text = strip_noise("\n".join(t for t in texts if t))

            if event.kind == "tool_output" and not event.errors:
                continue  # pure tool output with nothing to flag
            if not (event.text or event.tool_calls or event.errors):
                continue
            events.append(event)

    meta["touched"] = list(dict.fromkeys(touched))
    return events, meta


def render(events: list[Event], meta: dict[str, Any], budget: int) -> str:
    """Assemble the advisor view within a character budget.

    Allocation is deliberate rather than proportional: the task and the human
    steering messages are never compressed, because losing a constraint the
    user stated is the one failure mode that makes advice actively harmful.
    The trajectory absorbs whatever is left.
    """
    humans = [e for e in events if e.kind == "human" and e.text]
    assistants = [e for e in events if e.kind == "assistant"]
    errors = [msg for e in events for msg in e.errors]

    out: list[str] = ["# Executor session transcript (reconstructed)", ""]
    out.append(
        "You are reading a compressed reconstruction of another agent's session, "
        "not a live context window. Tool outputs are truncated. Absence of "
        "detail is an artifact of compression -- if a specific fact matters to "
        "your advice, read the file yourself rather than assuming it is missing."
    )
    out.append("")

    facts = [f"- Working directory: `{meta.get('cwd', 'unknown')}`"]
    if meta.get("gitBranch"):
        facts.append(f"- Git branch: `{meta['gitBranch']}`")
    if meta.get("effort"):
        effort = meta["effort"]
        level = effort.get("level") if isinstance(effort, dict) else effort
        facts.append(f"- Executor effort level: `{level}`")
    facts.append(f"- Turns: {len(humans)} human, {len(assistants)} assistant")
    out.extend(facts)
    out.append("")

    if humans:
        out.append("## The task, as stated")
        out.append("")
        out.append(clip(humans[0].text, 6000))
        out.append("")

    if len(humans) > 1:
        out.append("## Everything the user said afterwards")
        out.append("")
        out.append(
            "_Steering, corrections, and constraints. Treat these as binding._"
        )
        out.append("")
        for event in humans[1:]:
            out.append(f"- {clip(event.text, 1500)}")
        out.append("")

    if meta.get("touched"):
        out.append("## Files written or edited")
        out.append("")
        for target in meta["touched"]:
            out.append(f"- `{target}`")
        out.append("")

    if errors:
        out.append("## Failed tool calls")
        out.append("")
        out.append("_Recurring entries here usually mean the approach is not converging._")
        out.append("")
        for msg in errors[-12:]:
            out.append(f"- {msg}")
        out.append("")

    spent = len("\n".join(out))
    remaining = max(budget - spent, 2000)

    # Trajectory, newest first, until the budget runs out. Newest-first keeps
    # the current state -- the part advice attaches to -- when the run is long.
    trail: list[str] = []
    for event in reversed(assistants):
        chunk: list[str] = []
        if event.text:
            # Recent reasoning is worth more than old reasoning.
            depth = 1200 if len(trail) < 6 else 300
            chunk.append(clip(event.text, depth))
        for name, summary in event.tool_calls:
            chunk.append(f"  - `{name}` {summary}".rstrip())
        rendered = "\n".join(chunk)
        if not rendered:
            continue
        if sum(len(t) for t in trail) + len(rendered) > remaining:
            trail.append("\n[... earlier turns omitted to fit the budget ...]")
            break
        trail.append(rendered)

    if trail:
        out.append("## Trajectory, most recent first")
        out.append("")
        out.extend(f"{block}\n" for block in reversed(trail))

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path, help="path to the session JSONL")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=40000,
        help=(
            "soft character budget for the digest (default: 40000). Not a hard "
            "cap: the task statement and the user's own messages are never "
            "compressed, and the trajectory keeps a 2000-char floor, so a "
            "small budget can be exceeded. The reported size is the real one."
        ),
    )
    parser.add_argument(
        "--include-sidechains",
        action="store_true",
        help="include subagent traffic (excluded by default as noise)",
    )
    parser.add_argument("-o", "--output", type=Path, help="write here instead of stdout")
    args = parser.parse_args()

    if not args.transcript.is_file():
        print(f"advisor: no transcript at {args.transcript}", file=sys.stderr)
        return 1

    events, meta = load_events(args.transcript, args.include_sidechains)
    if not events:
        print("advisor: transcript held no usable turns", file=sys.stderr)
        return 1

    digest = render(events, meta, args.max_chars)

    if args.output:
        args.output.write_text(digest, encoding="utf-8")
    else:
        sys.stdout.write(digest)

    print(
        f"advisor: digest {len(digest):,} chars (~{len(digest) // 4:,} tokens) "
        f"from {args.transcript.stat().st_size:,} bytes of transcript",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
