"""Command line interface.

stdout is deliberately small. Tool output lands in Claude's context and stays
there for the rest of the session, so a full scene description printed here
would be thousands of tokens that cannot be reclaimed. The answer goes to
`response.md` in the run directory and is read deliberately.

There is no `purge` command. `interactions.delete` returns HTTP 501 Not
Implemented -- verified live -- so stored interactions cannot be removed
programmatically. The project retention window in AI Studio is the only cleanup
that exists, which is why `stateful` defaults to false on every recipe.

Uploaded files are the exception and have their own command: `files.delete`
works, so `uploads --delete` is real cleanup rather than disclosure. Keeping
the two on separate commands is deliberate -- collapsing them would imply the
same remedy applies to both, and for interactions it does not.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from os import environ
from pathlib import Path
from typing import Any

import orjson

from . import (
    auth,
    authorization,
    budget,
    client as call_mod,
    content,
    files,
    ledger,
    media,
    privacy,
    prompts,
    recipes,
    runs,
)
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


def _effective_recipe(
    args: argparse.Namespace, recipe_dirs: list[Path]
) -> recipes.Recipe:
    """The recipe the call actually runs with: CLI flag > recipe value > default.

    With no -r, the call is `adhoc` -- a Recipe-shaped bundle with no stance
    unless --system/--system-file supplied one. With -r, the stance flags are
    refused: the run directory and ledger are labeled with the recipe's name,
    and a swapped-out system instruction under that name mislabels the run.
    """
    system_text = args.system
    if args.system_file:
        try:
            system_text = Path(args.system_file).read_text().strip()
        except OSError as exc:
            raise recipes.RecipeError(f"could not read {args.system_file}: {exc}")

    if args.recipe:
        if system_text is not None:
            raise recipes.RecipeError(
                "--system/--system-file cannot be combined with --recipe: the "
                "run stays labeled with the recipe's name, so replacing its "
                "stance would mislabel the record. Pass one or the other."
            )
        recipe = recipes.load(args.recipe, recipe_dirs)
    else:
        recipe = recipes.Recipe(name="adhoc", system_instruction=system_text or "")

    schema = None
    if args.schema_file:
        try:
            schema = orjson.loads(Path(args.schema_file).read_bytes())
        except (OSError, orjson.JSONDecodeError) as exc:
            raise recipes.RecipeError(
                f"could not load schema from {args.schema_file}: {exc}"
            )
        if not isinstance(schema, dict):
            raise recipes.RecipeError(
                f"{args.schema_file}: a response schema must be a JSON object"
            )

    labels = dict(recipe.labels)
    for raw in args.label:
        key, sep, value = raw.partition("=")
        if not sep or not key:
            raise recipes.RecipeError(f"label {raw!r} is not KEY=VALUE")
        labels[key] = value

    overrides: dict[str, Any] = {}
    if args.thinking_level:
        overrides["thinking_level"] = args.thinking_level
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.max_output_tokens is not None:
        overrides["max_output_tokens"] = args.max_output_tokens
    if args.service_tier:
        overrides["service_tier"] = args.service_tier
    if args.store:
        overrides["stateful"] = True
    if schema is not None:
        overrides["schema"] = schema
    if labels != recipe.labels:
        overrides["labels"] = labels
    return replace(recipe, **overrides) if overrides else recipe


def cmd_ask(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or Path.cwd()).resolve()
    cfg = Config.load(project_root)

    try:
        recipe = _effective_recipe(args, _recipe_dirs(cfg))
    except recipes.RecipeError as exc:
        return _fail(str(exc))

    question = args.question
    if args.prompt_file:
        question = Path(args.prompt_file).read_text().strip()

    # A question is required, but "required" does not have to mean "refused".
    # With media attached and nothing asked, fall back to a kind-appropriate
    # default and say loudly what that costs -- the caller composing this
    # command has context no default can have, and is the only party that can
    # turn "describe this video" into a question worth paying for.
    #
    # The kinds come from filenames alone, before any guard has run, so that
    # this decision cannot depend on reading a file the path guard is about to
    # refuse. Unknown extensions simply do not contribute a kind; `inspect`
    # reports the real error a few lines below, where it is actionable.
    used_default_prompt = False
    if not question:
        if not (args.file or args.context):
            return _fail(
                "no question: pass one positionally or via --prompt-file. "
                "(A question is only optional when there is media attached.)"
            )
        kinds = media.guess_kinds([*args.file, *args.context])
        question = prompts.default_question(kinds)
        used_default_prompt = True
        print(f"WARNING {prompts.default_notice(kinds)}", file=sys.stderr)

    # The prompt is composed by Claude, which has been reading the user's
    # files. The path guard says nothing about it, so a secret pasted into a
    # question used to be sent unchecked -- and a sent interaction cannot be
    # recalled.
    #
    # Computed once and recorded in the ledger: the scan can be off via the
    # CLI flag OR via project config, and recording only the flag left config
    # runs labelled allow_prompt_secrets=false -- the audit field pointing
    # away from the unscanned runs it exists to find.
    # The flag waives the BLOCK, not the LOOK: scanning still runs under
    # --allow-prompt-secrets so the finding is on screen while the call can
    # still be stopped. It used to skip the scan entirely, which removed that
    # one moment for exactly the runs that needed it. Only the config opt-out
    # (scan_prompt = false) skips scanning altogether -- it says "this project
    # does not scan", not "this finding is a false positive".
    #
    # prompt_scanned still records enforcement, computed once for the ledger:
    # False means the scan did not gate the send, whichever route -- the flag
    # on this call or the standing config opt-out -- so bypass runs stay
    # findable by the audit filter the README names.
    prompt_scanned = bool(cfg.scan_prompt and not args.allow_prompt_secrets)
    if cfg.scan_prompt:
        # Every outgoing text channel. The system instruction is sent verbatim
        # (from a recipe body, --system, or --system-file -- all previously- or
        # never-scanned routes), and schema descriptions and label values
        # travel in the request too; the 0.6.x ledger fix taught that a channel
        # left out of this list stays unscanned until someone names it.
        outgoing = [("prompt", question)]
        if recipe.system_instruction:
            source = f"recipe {recipe.name!r}" if args.recipe else "system instruction"
            outgoing.append((source, recipe.system_instruction))
        if recipe.schema:
            outgoing.append(("schema", orjson.dumps(recipe.schema).decode()))
        if recipe.labels:
            outgoing.append(
                ("labels", " ".join(f"{k}={v}" for k, v in recipe.labels.items()))
            )
        blocked = False
        for label, text in outgoing:
            findings = content.scan(text)
            for f in findings:
                print(f"{'BLOCKED' if f.blocking else 'WARNING'} {label} contains "
                      f"what looks like a {f}", file=sys.stderr)
            blocked = blocked or bool(content.blocking(findings))
        if blocked and not args.allow_prompt_secrets:
            return _fail(
                "refusing to send: secret-shaped content found. Remove it, or "
                "pass --allow-prompt-secrets if these are false positives. "
                "Sent interactions cannot be deleted through the API."
            )
        if blocked:
            print(
                "WARNING sending despite the finding(s) above: "
                "--allow-prompt-secrets is active. A sent interaction cannot "
                "be deleted through the API.",
                file=sys.stderr,
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

    pending_upload = [a for a in attachments if media.needs_upload(a)]

    # Built once here, before anything leaves the machine, with a placeholder
    # standing in for handles that do not exist yet. Two jobs: it is what
    # `--dry-run` reports on, and it is where request-shape errors surface
    # (`--continue-from` without `--store`, most of all) while they still cost
    # nothing. Rebuilt below with the real handles once the uploads land --
    # cheap, and far better than discovering an illegal combination after
    # pushing 200MB of video across the wire.
    try:
        request = call_mod.build_request(
            recipe,
            question,
            [
                replace(a, uri=media.DRY_RUN_URI) if media.needs_upload(a) else a
                for a in attachments
            ],
            previous_interaction_id=args.continue_from,
            model_override=args.model or cfg.default_model,
        )
    except call_mod.CallError as exc:
        return _fail(str(exc))

    if args.dry_run:
        print(f"recipe      {recipe.name}  ({recipe.path or 'no recipe file'})")
        print(f"model       {request['model']}")
        print(f"thinking    {request.get('generation_config', {}).get('thinking_level')}")
        print(f"store       {request['store']}"
              f"{'  (NOT deletable once stored)' if request['store'] else ''}")
        print(f"schema      {'yes' if request.get('response_format') else 'no'}")
        for att in attachments:
            route = "upload" if media.needs_upload(att) else "inline"
            print(f"attach      {att.kind:9} {att.resolution or '-':5} "
                  f"{att.size_bytes / 1024:8.1f}KB  {route}  {att.path}")
            print(f"            {budget.estimate(att).line(att)}")
        if attachments:
            print(f"estimate    ~{budget.total(attachments):,} input tokens total "
                  "(rough; exact counts come back in usage.json)")
        if pending_upload:
            print(f"upload      {len(pending_upload)} file(s) would be sent to the "
                  "Files API and held for 48h  (not done: --dry-run)")
        shown = question[:100]
        for f in content.scan(question):
            if f.blocking:
                shown = "<withheld: contains secret-shaped content>"
                break
        print(f"question    {shown}"
              f"{'  (generic default)' if used_default_prompt else ''}")
        # Whether the real call would be gated, answered on the one path that
        # sends nothing. Finding this out by being refused costs a round trip;
        # finding it out here costs nothing.
        tier, why = authorization.classify(
            estimated_tokens=budget.total(attachments),
            thinking_level=request.get("generation_config", {}).get("thinking_level"),
            stateful=recipe.stateful,
            max_unauthorized_tokens=cfg.max_unauthorized_tokens,
        )
        if tier == "expensive" and cfg.require_authorization:
            print(f"gate        needs {authorization.AUTHORIZE_COMMAND} "
                  f"-- {why}")
        else:
            print("gate        none; runs under the ordinary permission prompt")
        return 0

    # Said before the send, not after, so it is still actionable. The defaults
    # in this tool are already the cheap ones; what runs up a bill is clip
    # length, which is invisible until the invoice.
    estimated_tokens = budget.total(attachments)
    warning = budget.advice(attachments, estimated_tokens)
    if warning:
        print(f"WARNING {warning}", file=sys.stderr)

    # The spend gate, before credentials are even resolved. An expensive or
    # irreversible call needs an authorization only a user-typed slash command
    # can mint; a cheap one runs under the ordinary Bash permission prompt as
    # it always has. Placed here because it must precede every irrevocable
    # step -- the upload most of all, which discloses bytes for 48h whether or
    # not the interaction that follows succeeds.
    tier, why = authorization.classify(
        estimated_tokens=estimated_tokens,
        thinking_level=request.get("generation_config", {}).get("thinking_level"),
        stateful=recipe.stateful,
        max_unauthorized_tokens=cfg.max_unauthorized_tokens,
    )
    authorization_tier = tier
    if tier == "expensive" and cfg.require_authorization:
        decision = authorization.claim(
            estimated_tokens=estimated_tokens,
            ttl_seconds=cfg.authorization_ttl_seconds,
        )
        authorization_tier = decision.tier
        if not decision.allowed:
            return _fail(f"{why}, so {decision.reason}")

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

    # The run directory is created BEFORE the uploads, not after. An upload is
    # already a disclosure -- the bytes are at Google for 48 hours whether or
    # not the interaction that was going to use them ever happens -- so the
    # local record of it has to exist before it can be orphaned.
    try:
        run = runs.RunDir.create(project_root, recipe.name)
        run.write_prompt(recipe.system_instruction, question)
    except OSError as exc:
        return _fail(f"could not create the run directory under {project_root}: {exc}")

    runs_root = run.path.parent

    def _record_failure(status: str, error: str) -> None:
        ledger.record(
            runs_root, run_id=run.path.name, recipe=recipe.name,
            model=request["model"], status=status, usage=None,
            attachments=[a.manifest_entry(project_root) for a in attachments],
            duration_ms=0, stateful=recipe.stateful,
            service_tier=recipe.service_tier,
            thinking_level=request.get("generation_config", {}).get("thinking_level"),
            credential_kind=creds.kind, error=error,
            allow_prompt_secrets=args.allow_prompt_secrets,
            prompt_scanned=prompt_scanned,
            authorization_tier=authorization_tier,
        )

    if pending_upload:
        cache = files.Cache.load(runs_root)
        resolved: list[media.Attachment] = []
        performed: list[files.Upload] = []

        def _persist_uploads() -> None:
            """Cache first, run record second.

            Both hold the handles, but only the cache is what `uploads
            --delete` reads -- it is the difference between an orphaned upload
            being removable and having to wait out 48 hours. `Cache.save`
            already swallows its own errors, so the run-dir copy is the one
            that needs a guard here, and it degrades to a warning rather than
            taking down a call whose bytes have already been sent.
            """
            cache.save()
            try:
                run.write_uploads([u.record() for u in performed])
            except OSError as exc:
                print(f"WARNING could not write uploads.json: {exc}", file=sys.stderr)

        for att in attachments:
            if not media.needs_upload(att):
                resolved.append(att)
                continue
            try:
                up = files.ensure_uploaded(
                    api, att, cache, timeout_s=args.upload_timeout
                )
            except files.UploadError as exc:
                # Whatever already uploaded is recorded before bailing out:
                # those handles are live at Google and `uploads --delete` is
                # the only way to take them back early.
                _persist_uploads()
                run.write_error(str(exc))
                _record_failure("upload_failed", str(exc))
                return _fail(f"{exc}\n  run: {run.path}")
            performed.append(up)
            # The server's mime type wins: it describes the file it is holding,
            # ours only describes the extension.
            resolved.append(replace(att, uri=up.uri, mime_type=up.mime_type))
            print(f"upload  {up.display_name}  "
                  f"{'reused' if up.reused else 'new'}  {up.name}")
        attachments = resolved
        _persist_uploads()
        if any(not u.reused for u in performed):
            print("        uploads live 48h at Google; "
                  "`gemini-bridge uploads --delete` removes them now")

        # Rebuilt with the real handles. Everything else about the request was
        # already validated above.
        try:
            request = call_mod.build_request(
                recipe,
                question,
                attachments,
                previous_interaction_id=args.continue_from,
                model_override=args.model or cfg.default_model,
            )
        except (call_mod.CallError, media.MediaError) as exc:
            run.write_error(str(exc))
            _record_failure("failed", str(exc))
            return _fail(f"{exc}\n  run: {run.path}")

    try:
        run.write_request(call_mod.redact_for_record(request, attachments, project_root))
    except OSError as exc:
        return _fail(f"could not write the run record under {run.path}: {exc}")

    try:
        result = call_mod.call(api, request)
    except Exception as exc:  # noqa: BLE001 - record then surface
        run.write_error(f"{type(exc).__name__}: {exc}")
        _record_failure("failed", str(exc))
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
    #
    # Bound to a local before the guard rather than read inside the lambda: a
    # closure over `result.interaction_id` re-reads the attribute when it runs,
    # so the value written is not provably the value that passed the check.
    interaction_id = result.interaction_id
    if interaction_id:
        _persist("interaction.id", lambda: run.write_interaction_id(interaction_id))
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
        allow_prompt_secrets=args.allow_prompt_secrets,
        prompt_scanned=prompt_scanned,
        interaction_id=interaction_id,
        authorization_tier=authorization_tier,
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


def cmd_formats(args: argparse.Namespace) -> int:
    """What can be attached, and how each kind travels.

    Derived from the tables in `media.py` rather than written down anywhere, so
    it cannot drift from what the CLI will actually accept. That is the whole
    reason it exists as a command instead of a section in a reference file: a
    documented list of supported formats is a copy, and the only thing watching
    a copy is whoever next notices it is wrong.
    """
    print(f"{'kind':<9} {'route':<7} accepted mime types")
    for kind, mimes in (
        ("image", media.IMAGE_MIME),
        ("video", media.VIDEO_MIME),
        ("audio", media.AUDIO_MIME),
        ("document", media.DOCUMENT_MIME),
    ):
        route = "upload" if kind in media.UPLOAD_KINDS else "inline"
        print(f"{kind:<9} {route:<7} {', '.join(sorted(mimes))}")

    print(f"\nAnything larger than {media.INLINE_LIMIT_BYTES / 1e6:.0f}MB is "
          "uploaded whatever its kind.")
    print("Uploads: 2GB per file, 20GB per project, deleted automatically after "
          "48h.")
    print("--resolution applies to image and video only; audio and documents "
          "have no such field.")

    print("\nThe type is taken from the file extension. These are the "
          "extensions whose\nsystem mime name differs from what the API "
          "accepts, and are remapped:")
    for wrong, right in sorted(media.MIME_ALIASES.items()):
        print(f"  {wrong:<20} -> {right}")
    print("\nAn extension outside these tables is refused before anything is "
          "sent. Convert\nit first -- .mkv and .m4v are the common surprises, "
          "and `ffmpeg -c copy` remuxes\nboth to .mp4 without re-encoding.")
    return 0


def cmd_uploads(args: argparse.Namespace) -> int:
    """List -- and optionally delete -- files this project pushed to Google.

    The counterpart to `stored`, and deliberately the opposite of it in one
    respect: `stored` is a pure disclosure list because interactions cannot be
    deleted (501), whereas `files.delete` works. So this one can actually act,
    and the 48h expiry is a backstop rather than the only cleanup.

    It reads the local cache, which records only what this project uploaded.
    That is the point -- the alternative would be enumerating every file in the
    account, including ones other tools own.
    """
    project_root = Path(args.project_root or Path.cwd()).resolve()
    runs_root = project_root / runs.RUNS_DIRNAME
    cache = files.Cache.load(runs_root)
    now = time.time()
    live = cache.live(now)

    if not live:
        print(f"no live uploads recorded under {runs_root}")
        print("(entries are dropped once they are within 30 minutes of the "
              "48h expiry, so an empty list can also mean everything aged out)")
        return 0

    if not args.delete:
        print(f"{len(live)} upload(s) held at Google by this project:\n")
        print(f"{'file':<32} {'size':>9} {'expires in':>11}  handle")
        for up in live:
            hours = (up.expires_at() - now) / 3600
            print(f"{up.display_name[:32]:<32} {up.size_bytes / 1e6:>8.1f}MB "
                  f"{hours:>10.1f}h  {up.name}")
        print("\nUnlike stored interactions, these CAN be deleted: re-run with "
              "--delete.")
        print("They expire on their own 48h after upload.")
        return 0

    try:
        creds = auth.resolve(args.key_command, Config.load(project_root).key_command)
    except auth.AuthError as exc:
        return _fail(str(exc))

    from google import genai

    try:
        api = genai.Client(**creds.client_kwargs())
    except Exception as exc:  # noqa: BLE001 - never echo a key-shaped value
        return _fail(f"could not construct the API client: {type(exc).__name__}")

    failures = 0
    for up in live:
        try:
            files.delete(api, up.name)
        except files.UploadError as exc:
            failures += 1
            print(f"WARNING {exc}", file=sys.stderr)
            continue
        # Dropped only on a confirmed delete. A handle left in the cache after
        # a failed delete is retryable; one dropped optimistically is an
        # orphan nothing can name.
        cache.drop(up.sha256)
        print(f"deleted {up.display_name}  {up.name}")
    cache.save()
    return 1 if failures else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or Path.cwd()).resolve()
    cfg = Config.load(project_root)
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

    if cfg.require_authorization:
        print(f"spend gate     : on -- calls over "
              f"{cfg.max_unauthorized_tokens:,} estimated tokens, or using "
              f"--store or raised thinking,\n                 need "
              f"{authorization.AUTHORIZE_COMMAND} "
              f"(valid {cfg.authorization_ttl_seconds}s, single use)")
    else:
        print("spend gate     : OFF -- every call runs under the ordinary "
              "permission prompt only")

    live = files.Cache.load(project_root / runs.RUNS_DIRNAME).live(time.time())
    print(f"uploads held   : {len(live)} file(s) at Google"
          f"{'  (`uploads --delete` removes them)' if live else ''}")

    exists, ignored = runs.ignore_status(project_root)
    if not exists:
        print("runs tree      : none yet")
    elif ignored:
        print("runs tree      : present, self-ignored")
    else:
        print("runs tree      : present but NOT self-ignored")
        print(f"                 {project_root / runs.RUNS_DIRNAME}/.gitignore is "
              "missing, so prompts and")
        print("                 responses are stageable by `git add .`. The next "
              "call rewrites it;")
        print("                 restore it now, or add .gemini-runs/ to the "
              "project's .gitignore.")

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

    ask = sub.add_parser("ask", help="ask a question, with or without a recipe")
    ask.add_argument("question", nargs="?", default="")
    ask.add_argument("-r", "--recipe",
                     help="named stance to run under; omit for an ad-hoc call")
    ask.add_argument("-f", "--file", action="append", default=[],
                     help="subject file; repeatable")
    ask.add_argument("-c", "--context", action="append", default=[],
                     help="context file, attached at the cheaper resolution; repeatable")
    ask.add_argument("--prompt-file", help="read the question from a file")
    ask.add_argument("--model")
    ask.add_argument("--resolution", choices=sorted(recipes.RESOLUTIONS))
    ask.add_argument("--context-resolution", choices=sorted(recipes.RESOLUTIONS))
    ask.add_argument("--continue-from", metavar="INTERACTION_ID")
    stance = ask.add_mutually_exclusive_group()
    stance.add_argument("--system", metavar="TEXT",
                        help="system instruction for an ad-hoc call")
    stance.add_argument("--system-file", metavar="PATH",
                        help="read the system instruction from a file")
    ask.add_argument("--thinking-level", choices=sorted(recipes.THINKING_LEVELS))
    ask.add_argument("--seed", type=int)
    ask.add_argument("--max-output-tokens", type=int)
    ask.add_argument("--service-tier", choices=sorted(recipes.SERVICE_TIERS))
    ask.add_argument(
        "--store", action="store_true",
        help="store the interaction server-side to allow --continue-from later "
             "(stored interactions CANNOT be deleted)",
    )
    ask.add_argument("--schema-file", metavar="PATH",
                     help="JSON Schema file; the reply comes back as JSON")
    ask.add_argument(
        "--upload-timeout", type=float, default=files.DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help="how long to wait for an uploaded file to finish processing "
             f"(default {files.DEFAULT_TIMEOUT_S:.0f}s; long videos need more)",
    )
    ask.add_argument("--label", action="append", default=[], metavar="KEY=VALUE",
                     help="request label; repeatable")
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

    fmt = sub.add_parser(
        "formats", help="what can be attached, and how each kind travels"
    )
    fmt.set_defaults(func=cmd_formats)

    up = sub.add_parser(
        "uploads",
        help="list files this project uploaded to the Files API (these CAN be "
             "deleted, unlike interactions)",
    )
    up.add_argument("--delete", action="store_true",
                    help="delete them server-side now instead of waiting 48h")
    up.set_defaults(func=cmd_uploads)

    doc = sub.add_parser("doctor", help="check config, credentials, and recipes")
    doc.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
