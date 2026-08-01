"""Command line interface.

stdout is deliberately small. Tool output lands in Claude's context and stays
there for the rest of the session, so a full scene description printed here
would be thousands of tokens that cannot be reclaimed. The answer goes to
`response.md` in the run directory and is read deliberately.

There is no `purge` command. `interactions.delete` returns HTTP 501 Not
Implemented -- verified live -- so stored interactions cannot be removed
programmatically. The project retention window in AI Studio is the only cleanup
that exists, which is why `stateful` defaults to false on every recipe.
"""

from __future__ import annotations

import argparse
import sys
from os import environ
from pathlib import Path

from . import auth, client as call_mod, content, ledger, media, privacy, recipes, runs
from .config import Config

RECIPE_SUBPATH = Path("skills") / "gemini-multimodal" / "references" / "recipes"


def _bundled_recipe_dirs() -> list[Path]:
    """Where the shipped recipes live.

    Two layouts to satisfy: an editable install from the repo, where the
    package sits at <plugin>/src/gemini_bridge, and a plugin install, where
    Claude Code exports CLAUDE_PLUGIN_ROOT. A wheel installed into site-packages
    has neither, and falls back to config-declared directories only.
    """
    candidates = []
    plugin_root = environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidates.append(Path(plugin_root) / RECIPE_SUBPATH)
    # parents: [0] gemini_bridge, [1] src, [2] the plugin root
    candidates.append(Path(__file__).resolve().parents[2] / RECIPE_SUBPATH)
    return [c for c in candidates if c.is_dir()]


def _recipe_dirs(cfg: Config) -> list[Path]:
    return [*cfg.recipe_dirs, *_bundled_recipe_dirs()]


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def cmd_ask(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or Path.cwd()).resolve()
    cfg = Config.load(project_root)

    try:
        recipe = recipes.load(args.recipe, _recipe_dirs(cfg))
    except recipes.RecipeError as exc:
        return _fail(str(exc))

    question = args.question
    if args.prompt_file:
        question = Path(args.prompt_file).read_text().strip()
    if not question:
        return _fail("no question: pass one positionally or via --prompt-file")

    # The prompt is composed by Claude, which has been reading the user's
    # files. The path guard says nothing about it, so a secret pasted into a
    # question used to be sent unchecked -- and a sent interaction cannot be
    # recalled.
    if cfg.scan_prompt and not args.allow_prompt_secrets:
        # Both halves of the outgoing text. The recipe body becomes the
        # system_instruction and is sent verbatim on every call -- it was
        # unscanned by anything, and `--recipe /some/path.md` accepts an
        # arbitrary file, so a recipe was a completely uncovered channel.
        blocked = False
        for label, text in (
            ("prompt", question),
            (f"recipe {recipe.name!r}", recipe.system_instruction),
        ):
            findings = content.scan(text)
            for f in findings:
                print(f"{'BLOCKED' if f.blocking else 'WARNING'} {label} contains "
                      f"what looks like a {f}", file=sys.stderr)
            blocked = blocked or bool(content.blocking(findings))
        if blocked:
            return _fail(
                "refusing to send: secret-shaped content found. Remove it, or "
                "pass --allow-prompt-secrets if these are false positives. "
                "Sent interactions cannot be deleted through the API."
            )

    # The path guard runs BEFORE media inspection, on the raw arguments.
    # Ordered the other way round, a file the guard exists to block -- id_rsa,
    # something.pem -- was rejected first for having an unrecognised mime type,
    # so most default patterns could never fire and the user got a confusing
    # error instead of a refusal. Type support is irrelevant to whether a file
    # should be sent.
    patterns = privacy.effective_patterns(
        cfg.sensitive_paths, cfg.use_default_sensitive_paths
    )
    for raw in [*args.file, *args.context]:
        hit = privacy.is_sensitive(Path(raw), patterns)
        if hit:
            return _fail(
                f"{raw} matches sensitive path pattern {hit!r}. "
                "Sent interactions cannot be deleted through the API, so this "
                "is refused rather than sent."
            )

    try:
        attachments = media.resolve_attachments(
            args.file,
            args.resolution or recipe.resolution,
            args.context,
            args.context_resolution or recipe.context_resolution,
        )
    except media.MediaError as exc:
        return _fail(str(exc))

    try:
        request = call_mod.build_request(
            recipe,
            question,
            attachments,
            previous_interaction_id=args.continue_from,
            model_override=args.model or cfg.default_model,
        )
    except call_mod.CallError as exc:
        return _fail(str(exc))

    if args.dry_run:
        print(f"recipe      {recipe.name}  ({recipe.path})")
        print(f"model       {request['model']}")
        print(f"thinking    {request.get('generation_config', {}).get('thinking_level')}")
        print(f"store       {request['store']}"
              f"{'  (NOT deletable once stored)' if request['store'] else ''}")
        print(f"schema      {'yes' if request.get('response_format') else 'no'}")
        for att in attachments:
            print(f"attach      {att.kind:9} {att.resolution or '-':5} "
                  f"{att.size_bytes / 1024:8.1f}KB  {att.path}")
        shown = question[:100]
        for f in content.scan(question):
            if f.blocking:
                shown = "<withheld: contains secret-shaped content>"
                break
        print(f"question    {shown}")
        return 0

    try:
        creds = auth.resolve(args.key_command, cfg.key_command)
    except auth.AuthError as exc:
        return _fail(str(exc))

    from google import genai

    try:
        api = genai.Client(**creds.client_kwargs())
    except Exception as exc:  # noqa: BLE001
        # Never let an SDK constructor traceback reach stderr: a client-side
        # key-format error is exactly the kind that embeds the bad value in its
        # message, and this is the one path where the key is still in hand.
        return _fail(f"could not construct the API client: {type(exc).__name__}")

    try:
        run = runs.RunDir.create(project_root, recipe.name)
        run.write_prompt(recipe.system_instruction, question)
        run.write_request(call_mod.redact_for_record(request, attachments, project_root))
    except OSError as exc:
        return _fail(f"could not create the run directory under {project_root}: {exc}")

    runs_root = run.path.parent
    try:
        result = call_mod.call(api, request)
    except Exception as exc:  # noqa: BLE001 - record then surface
        run.write_error(f"{type(exc).__name__}: {exc}")
        ledger.record(
            runs_root, run_id=run.path.name, recipe=recipe.name,
            model=request["model"], status="failed", usage=None,
            attachments=[a.manifest_entry(project_root) for a in attachments],
            duration_ms=0, stateful=recipe.stateful,
            service_tier=recipe.service_tier,
            thinking_level=request.get("generation_config", {}).get("thinking_level"),
            credential_kind=creds.kind, error=str(exc),
        )
        return _fail(f"{type(exc).__name__}: {exc}\n  run: {run.path}")

    # The call is billed and, if stored, permanent -- delete returns 501. So
    # every write is guarded individually and the ledger is written regardless:
    # a full disk between the response and the first write used to lose the
    # answer, the usage record, and the interaction id together, with nothing
    # on disk to say the call had ever happened.
    persist_failures: list[str] = []

    def _persist(label: str, fn) -> None:
        try:
            fn()
        except OSError as exc:
            persist_failures.append(f"{label}: {exc}")

    # The id first: it is the only thing that cannot be regenerated by
    # re-running, and the only handle on a stored interaction.
    if result.interaction_id:
        _persist("interaction.id", lambda: run.write_interaction_id(result.interaction_id))
    _persist("response.md", lambda: run.write_response(result.text))
    _persist("usage.json", lambda: run.write_usage(result.usage))
    if result.structured is not None:
        _persist("response.json", lambda: run.write_structured(result.structured))

    ledger.record(
        runs_root, run_id=run.path.name, recipe=recipe.name,
        model=request["model"], status=result.status, usage=result.usage,
        attachments=[a.manifest_entry(project_root) for a in attachments],
        duration_ms=result.duration_ms, stateful=recipe.stateful,
        service_tier=recipe.service_tier,
        thinking_level=request.get("generation_config", {}).get("thinking_level"),
        credential_kind=creds.kind,
    )

    u = result.usage
    print(f"run     {run.path}")
    print(f"status  {result.status}  ({result.duration_ms}ms)")
    print(f"tokens  in={u.get('total_input_tokens')} out={u.get('total_output_tokens')} "
          f"thought={u.get('total_thought_tokens')}")
    if result.interaction_id:
        print("stored  yes -- cannot be deleted; expires with the project "
              "retention window")
    for w in result.warnings:
        print(f"WARNING {w}", file=sys.stderr)
    if result.parse_error:
        print(f"WARNING {result.parse_error}", file=sys.stderr)

    if persist_failures:
        for f in persist_failures:
            print(f"WARNING could not write {f}", file=sys.stderr)
        if any(f.startswith("response.md") for f in persist_failures):
            # Last resort. Normally the answer stays out of stdout because tool
            # output persists in context, but a paid answer that reached
            # neither disk nor the screen is simply lost.
            print("--- response could not be saved, printing it instead ---",
                  file=sys.stderr)
            print(result.text, file=sys.stderr)
        return 3

    if result.structured is not None:
        print(f"json    {run.path / 'response.json'}")
    print(f"answer  {run.path / 'response.md'}")
    return 0 if result.ok else 2


def cmd_recipes(args: argparse.Namespace) -> int:
    cfg = Config.load(Path(args.project_root or Path.cwd()).resolve())
    for directory in _recipe_dirs(cfg):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            try:
                r = recipes.parse(path.read_text(), path.stem, path)
            except recipes.RecipeError as exc:
                print(f"{path.stem:20} INVALID: {exc}")
                continue
            print(f"{r.name:20} {r.model:20} thinking={r.thinking_level or 'minimal':8} "
                  f"res={r.resolution or '-':6} stateful={r.stateful}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    root = Path(args.project_root or Path.cwd()).resolve() / runs.RUNS_DIRNAME
    entries = ledger.read(root)
    if not entries:
        print(f"no calls recorded under {root}")
        return 0
    print(f"{'recipe':<20} {'calls':>6} {'input':>9} {'output':>8} {'thought':>9} {'err':>4}")
    for name, s in sorted(ledger.summarize(entries).items()):
        print(f"{name:<20} {s['calls']:>6} {s['input']:>9} {s['output']:>8} "
              f"{s['thought']:>9} {s['errors']:>4}")
    print("\ntokens only; cost is derived downstream against current pricing")
    return 0


def cmd_stored(args: argparse.Namespace) -> int:
    """List runs holding a stored interaction.

    These cannot be deleted -- the API returns 501 -- so this is not a purge
    list, it is a disclosure list: what exists server-side until the project
    retention window expires.
    """
    root = Path(args.project_root or Path.cwd()).resolve()
    stored = runs.stored_runs(root)
    if not stored:
        print(f"no stored interactions recorded under {root}")
        return 0
    print(f"{len(stored)} stored interaction(s). These CANNOT be deleted; they")
    print("expire with the project retention window set in AI Studio.\n")
    for run in stored:
        print(f"{run.path.name:<40} {run.interaction_id}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = Config.load(Path(args.project_root or Path.cwd()).resolve())
    print(f"config sources : {[str(p) for p in cfg.sources] or 'none'}")
    print(f"default model  : {cfg.default_model or '(recipe default)'}")
    try:
        creds = auth.resolve(args.key_command, cfg.key_command)
        print(f"credentials    : ok via {creds.kind}")
    except auth.AuthError as exc:
        print(f"credentials    : FAILED -- {exc}")
        return 1
    n = sum(1 for d in _recipe_dirs(cfg) if d.is_dir() for _ in d.glob("*.md"))
    print(f"recipes        : {n} found")

    patterns = privacy.effective_patterns(
        cfg.sensitive_paths, cfg.use_default_sensitive_paths
    )
    print(f"path guard     : {len(patterns)} pattern(s) "
          f"({len(cfg.sensitive_paths)} from config, "
          f"{len(patterns) - len(cfg.sensitive_paths)} built in)")
    print(f"prompt scan    : {'on' if cfg.scan_prompt else 'OFF'}")
    print()
    print("Anything sent is retained for the project's retention window and")
    print("CANNOT be deleted -- interactions.delete returns 501. Set that window")
    print("in AI Studio; it is the only cleanup that exists.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gemini-bridge",
        description="Send a multimodal task to Gemini and get a structured answer back.",
    )
    p.add_argument("--project-root", help="defaults to the current directory")
    p.add_argument("--key-command", help="command that prints the API key")
    sub = p.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="run a recipe against files")
    ask.add_argument("question", nargs="?", default="")
    ask.add_argument("-r", "--recipe", required=True)
    ask.add_argument("-f", "--file", action="append", default=[],
                     help="subject file; repeatable")
    ask.add_argument("-c", "--context", action="append", default=[],
                     help="context file, attached at the cheaper resolution; repeatable")
    ask.add_argument("--prompt-file", help="read the question from a file")
    ask.add_argument("--model")
    ask.add_argument("--resolution", choices=sorted(recipes.RESOLUTIONS))
    ask.add_argument("--context-resolution", choices=sorted(recipes.RESOLUTIONS))
    ask.add_argument("--continue-from", metavar="INTERACTION_ID")
    ask.add_argument(
        "--allow-prompt-secrets", action="store_true",
        help="send even if the prompt looks like it contains a secret",
    )
    ask.add_argument("--dry-run", action="store_true",
                     help="print what would be sent, call nothing")
    ask.set_defaults(func=cmd_ask)

    lst = sub.add_parser("recipes", help="list available recipes")
    lst.set_defaults(func=cmd_recipes)

    st = sub.add_parser("stats", help="summarize the call ledger")
    st.set_defaults(func=cmd_stats)

    sto = sub.add_parser(
        "stored",
        help="list interactions stored server-side (they cannot be deleted)",
    )
    sto.set_defaults(func=cmd_stored)

    doc = sub.add_parser("doctor", help="check config, credentials, and recipes")
    doc.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
