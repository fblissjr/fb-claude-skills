"""path-privacy's hooks, exercised end to end as shell.

path-privacy: skip-file -- fixtures for the leak check itself, so this file is
full of deliberately leak-shaped paths and a fake full name.

CLAIM OF THIS FILE. The PreToolUse hook, the git entry scripts and the
SessionStart hook each make a promise about friction or coverage. Each test
below pins one promise, and its comment says what breaks if it is deleted.

Fixtures never touch the machine's real identity. Every subprocess runs with
an isolated git config (no global, no system file) and, where tilde forms
matter, a fake HOME. The full name under test is "Jane Q. Example"; nothing
here reads or prints the running user's own `user.name`.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "skills/path-privacy"
HOOKS = PLUGIN / "hooks"
SCRIPTS = PLUGIN / "skills/path-privacy/scripts"
PRE_TOOL_USE = HOOKS / "path-privacy-pre-tool-use.sh"
SESSION_START = HOOKS / "path-privacy-session-start.sh"
SCANNER = SCRIPTS / "find-external-paths.sh"
PRE_COMMIT = SCRIPTS / "git-pre-commit"
COMMIT_MSG = SCRIPTS / "git-commit-msg"
INSTALLER = SCRIPTS / "install-git-hooks.sh"

FULL_NAME = "Jane Q. Example"
HANDLE = "jqexample"

pytestmark = pytest.mark.skipif(
    shutil.which("rg") is None or shutil.which("jq") is None,
    reason="path-privacy needs ripgrep and jq",
)


# --- harness -----------------------------------------------------------------


def _env(tmp_path: Path, home: Path | None = None, **extra: str) -> dict:
    """An environment that cannot see the real git identity."""
    empty = tmp_path / "empty-gitconfig"
    empty.touch()
    env = dict(os.environ)
    env.update(GIT_CONFIG_GLOBAL=str(empty), GIT_CONFIG_NOSYSTEM="1")
    env.pop("CLAUDE_PROJECT_DIR", None)
    if home is not None:
        env["HOME"] = str(home)
    env.update(extra)
    return env


def _repo(tmp_path: Path, where: Path | None = None, name: str | None = FULL_NAME) -> Path:
    repo = where or (tmp_path / "repo")
    repo.mkdir(parents=True, exist_ok=True)
    env = _env(tmp_path)
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "jane@example.com"],
                   check=True, env=env)
    if name is not None:
        subprocess.run(["git", "-C", str(repo), "config", "user.name", name],
                       check=True, env=env)
    return repo


def _pre_tool_use(tmp_path: Path, repo: Path, tool: str, tool_input: dict,
                  home: Path | None = None) -> subprocess.CompletedProcess:
    payload = {"tool_name": tool, "tool_input": tool_input, "hook_event_name": "PreToolUse"}
    return subprocess.run(
        ["bash", str(PRE_TOOL_USE)], input=json.dumps(payload),
        capture_output=True, text=True,
        env=_env(tmp_path, home=home, CLAUDE_PROJECT_DIR=str(repo)),
    )


def _write(tmp_path, repo, rel, content, home=None):
    return _pre_tool_use(tmp_path, repo, "Write",
                         {"file_path": str(repo / rel), "content": content}, home=home)


def _output(r: subprocess.CompletedProcess) -> dict:
    return json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else {}


def _scan(tmp_path: Path, text: str, home: Path | None = None) -> int:
    root = tmp_path / "scanroot"
    root.mkdir(exist_ok=True)
    r = subprocess.run([str(SCANNER), "--against-root", str(root), "--text", text],
                       capture_output=True, text=True, env=_env(tmp_path, home=home))
    return r.returncode


# --- 1. fix instead of block: in-repo absolute paths are rewritten ------------


def test_write_rewrites_absolute_in_repo_path_to_relative(tmp_path):
    # Claim: an absolute path INSIDE the repo is fixed in place via updatedInput,
    # not blocked and not waved through. Delete this and the hook can regress to
    # letting the username-bearing form land (what the whole-tree audit flags).
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "docs/a.md", f"see {repo}/docs/b.md for more\n")
    assert r.returncode == 0, r.stderr
    out = _output(r)
    assert out["updatedInput"]["content"] == "see docs/b.md for more\n"
    assert out["updatedInput"]["file_path"] == str(repo / "docs/a.md")
    # Rewriting must not loosen permissions: no decision means the normal flow.
    assert "permissionDecision" not in out
    assert "rewrote" in out["additionalContext"]


def test_edit_rewrites_new_string_and_keeps_every_other_field(tmp_path):
    # Claim: updatedInput REPLACES the whole input, so old_string and
    # replace_all must survive untouched. Dropping them fails schema validation
    # upstream, which turns a fix into a deny.
    repo = _repo(tmp_path)
    (repo / "a.md").write_text("old line\n")
    r = _pre_tool_use(tmp_path, repo, "Edit", {
        "file_path": str(repo / "a.md"), "old_string": "old line",
        "new_string": f"cd {repo}/scripts && ./run.sh", "replace_all": True})
    out = _output(r)
    assert out["updatedInput"] == {
        "file_path": str(repo / "a.md"), "old_string": "old line",
        "new_string": "cd scripts && ./run.sh", "replace_all": True}


def test_home_relative_forms_of_the_repo_root_are_rewritten(tmp_path):
    # Claim: `~/...` and `$HOME/...` spellings of the repo are the same leak of
    # layout and get the same fix. Without it only the absolute spelling is fixed.
    home = tmp_path / "Users" / "janeexample"
    repo = _repo(tmp_path, where=home / "code" / "proj")
    r = _write(tmp_path, repo, "n.md", "~/code/proj/src/a.py and $HOME/code/proj/b.py\n",
               home=home)
    assert _output(r)["updatedInput"]["content"] == "src/a.py and b.py\n"


def test_bare_repo_root_becomes_dot(tmp_path):
    # Claim: the root itself, not followed by a path, becomes `.`, so a
    # `cd <root> && ...` stays a working command.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "run.sh", f'cd "{repo}" && make\n')
    assert _output(r)["updatedInput"]["content"] == 'cd "." && make\n'


def test_sibling_directory_sharing_the_root_prefix_is_not_rewritten(tmp_path):
    # Claim: the match is anchored on a path boundary. `<root>-old/x` is a
    # different directory; rewriting it would corrupt the text.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "n.md", f"backup at {repo}-old/x\n")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_clean_write_emits_nothing(tmp_path):
    # Claim (pin of kept behaviour): a write with nothing to fix produces no
    # output at all. Any stdout here is context spent on every clean edit.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "n.md", "plain text, relative/path.md\n")
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""


def test_leak_still_blocks_and_carries_the_quiet_fix_rule(tmp_path):
    # Claim: a real leak still hard-blocks (kept behaviour), and the block
    # message now carries the one rule the retired SessionStart directive
    # existed for: the fix stays out of commit messages and the changelog.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "n.md", "see /Users/realpersonname/secret/x\n")
    assert r.returncode == 2
    assert "n.md:1: /Users/realpersonname/secret/x" in r.stderr
    assert "changelog" in r.stderr


# --- 2. full-name guard -------------------------------------------------------


def test_write_containing_the_full_name_is_blocked_without_echoing_it(tmp_path):
    # Claim: the git user.name full name cannot be written into a tracked file,
    # and the block message never repeats the name it is protecting.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "AUTHORS.md", f"Maintained by {FULL_NAME}.\n")
    assert r.returncode == 2
    assert "AUTHORS.md:1" in r.stderr
    assert "Jane" not in r.stderr and "Example" not in r.stderr


@pytest.mark.parametrize("spelling", [
    "jane q. example", "JANE EXAMPLE", "Jane Q Example", "jane.example",
    "jane-example", "jane_example", "janeexample",
])
def test_full_name_match_is_case_insensitive_and_separator_flexible(tmp_path, spelling):
    # Claim: the guard catches the spellings a name actually takes -- any case,
    # middle initial optional, joined by space, dot, dash, underscore or
    # nothing (the home-directory form).
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "n.md", f"x {spelling} y\n")
    assert r.returncode == 2, f"missed spelling: {spelling}"


@pytest.mark.parametrize("text", [
    f"by {HANDLE} (jane@example.com)",   # handle and email are allowed
    "Jane Examples is a different word",  # right boundary
    "Janet Example",                      # left token boundary
])
def test_handle_email_and_near_misses_are_allowed(tmp_path, text):
    # Claim: the guard is the full name only. The handle and email are
    # explicitly allowed, and a longer word containing the name is not it.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "n.md", text + "\n")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("text", ["Joann Lee signed off", "Ann Leeds signed off"])
def test_a_different_name_containing_the_guarded_one_is_allowed(tmp_path, text):
    # Claim: both ends of the match are word-bounded. "Joann Lee" and "Ann
    # Leeds" are other people; without the bounds a short name blocks theirs.
    repo = _repo(tmp_path, name="Ann Lee")
    r = _write(tmp_path, repo, "n.md", text + "\n")
    assert r.returncode == 0, r.stderr


def test_single_token_user_name_is_treated_as_a_handle(tmp_path):
    # Claim: a user.name with one word is a handle, not a full name, so there
    # is nothing to guard. Without this every mention of a handle blocks.
    repo = _repo(tmp_path, name=HANDLE)
    r = _write(tmp_path, repo, "n.md", f"{HANDLE} wrote this\n")
    assert r.returncode == 0


def test_license_file_may_carry_the_name(tmp_path):
    # Claim: LICENSE copyright lines are the owner's own exception.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "LICENSE", f"Copyright (c) 2026 {FULL_NAME}\n")
    assert r.returncode == 0


def test_skip_file_marker_does_not_exempt_the_name(tmp_path):
    # Claim: the marker exists for path-shaped fixtures. It is not an opt-out
    # from the name guard, or every marked file becomes a hiding place.
    repo = _repo(tmp_path)
    r = _write(tmp_path, repo, "t.py", f"# path-privacy: skip-file\nNAME = '{FULL_NAME}'\n")
    assert r.returncode == 2


def test_bash_git_command_with_the_full_name_is_blocked(tmp_path):
    # Claim: commit messages reach the repo without Write/Edit; the name guard
    # covers the git and gh commands that carry them.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": f'git commit -m "thanks to {FULL_NAME}"'})
    assert r.returncode == 2
    assert "Jane" not in r.stderr


def test_git_command_path_that_spells_the_name_joined_is_not_the_name(tmp_path):
    # Claim: the name guard reads a git command's message and branch text, not
    # the whole command. A home directory named after the owner ("janeexample",
    # first and last name joined) appears in every absolute path passed to
    # `git -C`; scanning the whole command blocked all of them. Breaks if the
    # guard goes back to scanning the full command text.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": "git -C /Users/janeexample/work/repo status --short"})
    assert r.returncode == 0, r.stderr


def test_gh_title_with_the_full_name_is_still_blocked(tmp_path):
    # Claim: narrowing the scan to message text keeps PR titles covered.
    # Breaks if --title stops being part of the scanned text.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": f'gh pr create --title "Fix from {FULL_NAME}" --body "x"'})
    assert r.returncode == 2
    assert "Jane" not in r.stderr


@pytest.mark.parametrize("command", [
    f'gh pr create -t "Fix from {FULL_NAME}" -b "x"',
    f'gh issue comment 5 -b "thanks {FULL_NAME}"',
    'gh api repos/o/r/issues/1/comments -f body="thanks Jane Example"',
    "git tag janeexample-release",
    "git push origin HEAD:refs/heads/jane-example",
])
def test_name_in_text_that_reaches_github_without_a_git_hook_is_blocked(tmp_path, command):
    # Claim: gh bodies, short -t/-b flags, tag names and pushed ref names go
    # public with no git hook behind them, so the name guard reads the whole
    # command, not only the extracted message text. Breaks if the guard is
    # narrowed to message text again.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": command})
    assert r.returncode == 2, command
    assert "Jane" not in r.stderr


def test_heredoc_in_a_command_that_does_not_commit_is_not_a_message(tmp_path):
    # Claim: heredoc bodies are scanned as message text only when the command
    # commits, tags, or opens/edits a PR or issue. A script fed to python or cat
    # through a heredoc, in a command that merely mentions git, is not a
    # message. Breaks if every heredoc in any git-mentioning command is scanned.
    repo = _repo(tmp_path)
    cmd = ("git status >/dev/null; python3 - <<'EOF'\n"
           "print('/Users/janeexample/elsewhere/notes.md')\nEOF")
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("command", [
    'gh pr create -t "by $(git config user.name)" -b x',
    'gh issue comment 5 -b "thanks `git config --get user.name`"',
    'git tag "$(git config user.name | tr " " -)-v1"',
])
def test_name_spliced_in_by_substitution_is_blocked(tmp_path, command):
    # Claim: the hook sees text before the shell expands it, so a user.name
    # lookup spliced into a gh/tag/ref command sends the name unseen; it is
    # blocked outright. Breaks if substitution of user.name is let through.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": command})
    assert r.returncode == 2, command


def test_name_block_message_does_not_suggest_substitution(tmp_path):
    # Claim: the block message must not tell the model to splice the name in
    # with $(git config user.name) -- that is the bypass above. Breaks if the
    # message names the lookup.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": f'gh pr create -t "Fix from {FULL_NAME}" -b x'})
    assert r.returncode == 2
    assert "git config user.name" not in r.stderr


def test_reading_user_name_outside_a_publishing_command_is_allowed(tmp_path):
    # Claim: looking the name up is fine when the command publishes nothing.
    # Breaks if every mention of user.name in a git command blocks.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": 'git log --author="$(git config user.name)" -3'})
    assert r.returncode == 0, r.stderr


def test_claude_project_dir_encoding_of_the_home_path_is_not_the_name(tmp_path):
    # Claim: Claude Code names project folders by the path with dashes for
    # slashes (-Users-<user>-work-repo), so an owner whose username is the
    # name joined spells it there too; that encoding is masked like
    # /Users/<user>. Breaks if only the slash form of a home path is masked.
    repo = _repo(tmp_path)
    cmd = "git -C ~/.claude/projects/-Users-janeexample-work-repo/memory status"
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 0, r.stderr


def test_script_heredoc_that_mentions_git_commit_is_not_command_text(tmp_path):
    # Claim: a heredoc body is a script unless the command outside it writes a
    # message, so text inside it -- "git commit", the name, a path -- neither
    # opts the command into scanning nor matches. Specimen from 2026-09-24: a
    # python heredoc editing a memory file that mentioned `git commit`.
    # Breaks if the git/gh gate or the name scan reads script bodies.
    repo = _repo(tmp_path)
    cmd = ("cd /tmp && python3 - <<'EOF'\n"
           "note = 'a pin commit is ALLOW=1 git commit, per Jane Example'\n"
           "print('/Users/janeexample/elsewhere/notes.md')\nEOF")
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 0, r.stderr


def test_heredoc_fed_to_a_shell_is_still_command_text(tmp_path):
    # Claim: a heredoc fed to bash/sh/zsh is commands, not a script body, so a
    # gh call inside it is still scanned. Breaks if every heredoc is dropped.
    repo = _repo(tmp_path)
    cmd = ("bash <<'EOF'\n"
           f'gh issue comment 5 -b "thanks {FULL_NAME}"\nEOF')
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 2, r.stderr


def test_heredoc_commit_message_with_the_name_is_blocked(tmp_path):
    # Claim: a command that commits keeps its heredoc body as message text for
    # the name scan too. Breaks if heredoc bodies are dropped unconditionally.
    repo = _repo(tmp_path)
    cmd = ("git commit -F - <<'EOF'\n"
           f"fix, reported by {FULL_NAME}\nEOF")
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 2, r.stderr
    assert "Jane" not in r.stderr


def test_heredoc_commit_message_is_still_scanned(tmp_path):
    # Claim: the heredoc form Claude Code uses for commit messages stays covered.
    # Breaks if narrowing heredoc scanning drops real commit messages.
    repo = _repo(tmp_path)
    cmd = ("git commit -m \"$(cat <<'EOF'\n"
           "notes at /Users/janeexample/elsewhere/notes.md\nEOF\n)\"")
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 2


def _commit_msg(tmp_path, repo, message) -> subprocess.CompletedProcess:
    msg = tmp_path / "MSG"
    msg.write_text(message)
    return subprocess.run([str(COMMIT_MSG), str(msg)], cwd=repo, capture_output=True,
                          text=True, env=_env(tmp_path))


def test_commit_msg_hook_blocks_the_full_name(tmp_path):
    # Claim: the authoritative gate enforces the name too, for commits made
    # outside Claude, and does not echo it.
    repo = _repo(tmp_path)
    r = _commit_msg(tmp_path, repo, f"docs: credit {FULL_NAME}\n")
    assert r.returncode == 1
    assert "Jane" not in r.stderr


def test_commit_msg_hook_allows_a_signed_off_by_trailer(tmp_path):
    # Claim: `git commit -s` writes the name from git config -- automatic
    # author metadata, the owner's stated exception.
    repo = _repo(tmp_path)
    r = _commit_msg(tmp_path, repo, f"docs: edit\n\nSigned-off-by: {FULL_NAME} <jane@example.com>\n")
    assert r.returncode == 0, r.stderr


def _git(tmp_path, repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          env=_env(tmp_path), check=True)


def _pre_commit(tmp_path, repo):
    return subprocess.run([str(PRE_COMMIT)], cwd=repo, capture_output=True, text=True,
                          env=_env(tmp_path))


def test_pre_commit_blocks_the_name_on_added_lines_only(tmp_path):
    # Claim: the commit gate blocks a newly added line with the name, but a
    # line already in history does not block an unrelated change to the same
    # file. Whole-file matching would ambush every commit touching that file.
    repo = _repo(tmp_path)
    (repo / "pyproject.toml").write_text(f'authors = ["{FULL_NAME}"]\n')
    _git(tmp_path, repo, "add", "-A")
    _git(tmp_path, repo, "commit", "-q", "--no-verify", "-m", "seed")

    (repo / "pyproject.toml").write_text(f'authors = ["{FULL_NAME}"]\nversion = "1"\n')
    _git(tmp_path, repo, "add", "-A")
    assert _pre_commit(tmp_path, repo).returncode == 0

    (repo / "NOTES.md").write_text(f"ask {FULL_NAME}\n")
    _git(tmp_path, repo, "add", "-A")
    r = _pre_commit(tmp_path, repo)
    assert r.returncode == 1
    assert "NOTES.md:1" in r.stderr + r.stdout
    assert "Jane" not in r.stderr + r.stdout


# --- 3. fewer false positives in the path scanner ----------------------------


@pytest.mark.parametrize("text", [
    "~/.claude/plans/x.md",
    "$HOME/.config/tool/settings",
    "${HOME}/.cache/x",
    "~/Library/Caches/huggingface/hub",
    "~/AppData/Local/huggingface/hub",
])
def test_generic_home_locations_are_not_leaks(tmp_path, text):
    # Claim: a dot-directory or OS-standard directory under home names no user
    # and no project. These were the largest class of blocks measured.
    home = tmp_path / "Users" / "janeexample"
    assert _scan(tmp_path, f"see {text}", home=home) == 0


@pytest.mark.parametrize("text", ['cd "$HOME"', "$HOME/$sub/x", "~/$1", "HOME is $HOME, then"])
def test_bare_home_and_variable_segments_are_not_leaks(tmp_path, text):
    # Claim: shell code that uses $HOME, or appends a runtime variable, names
    # nothing. Blocking it blocked ordinary scripts.
    home = tmp_path / "Users" / "janeexample"
    assert _scan(tmp_path, text, home=home) == 0


@pytest.mark.parametrize("text", ["~/code/secret-project/x", "$HOME/development/OtherRepo"])
def test_named_directory_under_home_still_leaks(tmp_path, text):
    # Claim (pin of kept behaviour): a named, non-dot directory under home
    # reveals layout and project names. The relaxation above must not reach it.
    home = tmp_path / "Users" / "janeexample"
    assert _scan(tmp_path, text, home=home) == 1


def test_generic_location_embedding_the_username_still_leaks(tmp_path):
    # Claim: the dot-directory allowance ends where the path spells the
    # username, as Claude's own project directories do.
    home = tmp_path / "Users" / "janeexample"
    assert _scan(tmp_path, "~/.claude/projects/-Users-janeexample-code-proj/x", home=home) == 1


def test_mangled_home_path_is_a_leak(tmp_path):
    # Claim: the dash-joined home form (`-Users-<user>-...`, as in session
    # scratch directories) carries the username with no /Users/ to match.
    home = tmp_path / "Users" / "janeexample"
    assert _scan(tmp_path, "scratch: /private/tmp/claude-501/-Users-janeexample-code-proj/s",
                 home=home) == 1


@pytest.mark.parametrize("text", ["/Users/dev/x", "/Users/alice/proj", "/home/runner/work/x",
                                  "/Users/Shared/data"])
def test_documentation_and_system_accounts_are_placeholders(tmp_path, text):
    # Claim: the scanner accepts the same stand-in and system account names
    # the whole-tree audit does, so docs and fixtures stop tripping the gate.
    assert _scan(tmp_path, text) == 0


@pytest.mark.parametrize("mode", ["text", "file"])
def test_a_failing_ripgrep_is_never_a_clean_result(tmp_path, mode):
    # Claim: when ripgrep itself fails (exit 2, or killed), the scanner does
    # not report "clean". Each call used to end `|| true`, so a failed rg read
    # as "no candidates"; observed on 2026-09-24 as rg killed (137) partway
    # through a long Write, the lines after it silently unscanned.
    shim = tmp_path / "shim"
    shim.mkdir()
    fake = shim / "rg"
    fake.write_text("#!/bin/sh\nexit 2\n")
    fake.chmod(0o755)
    root = tmp_path / "scanroot"
    root.mkdir()
    target = root / "doc.md"
    target.write_text("see /Users/realpersonname/x\n")
    args = ["--text", target.read_text()] if mode == "text" else ["-f", str(target)]
    env = _env(tmp_path, PATH=f"{shim}:{os.environ['PATH']}")
    r = subprocess.run([str(SCANNER), "--against-root", str(root), *args],
                       capture_output=True, text=True, env=env)
    assert r.returncode != 0, "a failed ripgrep was reported as a clean scan"


# --- 4. commit messages the Bash check used to miss --------------------------


def test_heredoc_commit_message_is_scanned(tmp_path):
    # Claim: the default Claude Code commit shape, -m "$(cat <<'EOF' ... EOF)",
    # is scanned. Before, the line-by-line extraction never saw its body, so
    # every such commit fell through to the commit-msg hook.
    repo = _repo(tmp_path)
    cmd = "git commit -m \"$(cat <<'EOF'\nfix\n\nsee ~/code/secret-project/x\nEOF\n)\""
    r = _pre_tool_use(tmp_path, repo, "Bash", {"command": cmd})
    assert r.returncode == 2, r.stderr


def test_paths_outside_the_message_are_not_scanned(tmp_path):
    # Claim (pin of kept behaviour): only message and branch text is scanned,
    # never the whole command, which is full of legitimate absolute paths.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": 'git -C /Users/realpersonname/repo commit -m "docs: edit"'})
    assert r.returncode == 0


def test_single_quoted_message_still_blocks(tmp_path):
    # Claim (pin of kept behaviour): the plain -m '...' form is still caught.
    repo = _repo(tmp_path)
    r = _pre_tool_use(tmp_path, repo, "Bash",
                      {"command": "git commit -m 'see /Users/realpersonname/x'"})
    assert r.returncode == 2


# --- 5. SessionStart emits nothing in the steady state -----------------------


def _session_start(tmp_path, repo):
    payload = {"cwd": str(repo), "source": "startup", "hook_event_name": "SessionStart"}
    return subprocess.run(["bash", str(SESSION_START)], input=json.dumps(payload),
                          capture_output=True, text=True, env=_env(tmp_path))


def test_session_start_is_silent_in_a_gated_current_repo(tmp_path):
    # Claim: with the gate installed and current, SessionStart adds zero bytes
    # of context. The rule it used to state is enforced by the hooks, and the
    # one unenforceable part rides on the block messages instead.
    repo = _repo(tmp_path)
    subprocess.run([str(INSTALLER), "-C", str(repo)], capture_output=True, check=True,
                   env=_env(tmp_path))
    r = _session_start(tmp_path, repo)
    assert r.returncode == 0 and r.stdout == ""


def test_missing_gate_notice_is_shown_once_per_repo(tmp_path):
    # Claim: an ungated repo is reported once, not on every startup. The
    # notice fired on every session start in every such repo before.
    repo = _repo(tmp_path)
    first = _session_start(tmp_path, repo)
    ctx = json.loads(first.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "no commit gate" in ctx
    second = _session_start(tmp_path, repo)
    assert second.stdout == ""


# --- 6. a global hooks dispatcher that chains to each repo's own hooks -------
#
# A global core.hooksPath replaces .git/hooks for every repo on the machine. A
# dispatcher there that runs each repo's own <git-common-dir>/hooks/<name>
# declares it with a `.chains-to-repo-hooks` file. Under such a dispatcher
# `--git-path hooks` names the dispatcher, not the directory the gate lives in.


def _dispatcher(tmp_path, marker=True, hooks=("pre-commit", "commit-msg")) -> Path:
    d = tmp_path / "global-hooks"
    d.mkdir()
    if marker:
        (d / ".chains-to-repo-hooks").write_text("")
    for name in hooks:
        f = d / name
        f.write_text('#!/usr/bin/env bash\n'
                     'h="$(git rev-parse --path-format=absolute --git-common-dir)/hooks/${0##*/}"\n'
                     '[ -x "$h" ] && exec "$h" "$@"\n'
                     'exit 0\n')
        f.chmod(0o755)
    return d


def _global_env(tmp_path, hooks_dir: Path) -> dict:
    cfg = tmp_path / "global-gitconfig"
    cfg.write_text(f"[core]\n\thooksPath = {hooks_dir}\n")
    return _env(tmp_path, GIT_CONFIG_GLOBAL=str(cfg))


def test_install_under_a_chaining_dispatcher_gates_real_commits(tmp_path):
    # Claim: under a chaining global dispatcher the installer writes into the
    # repo's own hooks dir, leaves the dispatcher alone, and a real `git
    # commit` carrying the name is blocked through it. Before, the installer
    # refused ("would gate EVERY repo"), so no repo on the machine could have
    # the gate at all.
    repo = _repo(tmp_path)
    disp = _dispatcher(tmp_path)
    env = _global_env(tmp_path, disp)
    r = subprocess.run([str(INSTALLER), "-C", str(repo)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    for h in ("pre-commit", "commit-msg"):
        assert "path-privacy:wrapper" in (repo / ".git/hooks" / h).read_text()
        assert "path-privacy:wrapper" not in (disp / h).read_text()
    doctor = subprocess.run([str(INSTALLER), "-C", str(repo), "--doctor"],
                            capture_output=True, text=True, env=env)
    assert doctor.returncode == 0, doctor.stdout

    (repo / "NOTES.md").write_text(f"ask {FULL_NAME}\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    c = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "notes"],
                       capture_output=True, text=True, env=env)
    assert c.returncode != 0
    assert "Jane" not in c.stderr + c.stdout


def test_session_start_sees_the_gate_behind_a_chaining_dispatcher(tmp_path):
    # Claim: SessionStart looks for the gate where the dispatcher runs it. It
    # used to look in the dispatcher's own directory and report "no commit
    # gate" in a gated repo.
    repo = _repo(tmp_path)
    env = _global_env(tmp_path, _dispatcher(tmp_path))
    subprocess.run([str(INSTALLER), "-C", str(repo)], capture_output=True, check=True, env=env)
    payload = {"cwd": str(repo), "source": "startup", "hook_event_name": "SessionStart"}
    r = subprocess.run(["bash", str(SESSION_START)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout == ""


@pytest.mark.parametrize("marker,hooks", [
    (False, ("pre-commit", "commit-msg")),   # no declaration: not a chaining dispatcher
    (True, ("pre-commit",)),                 # declared, but git would never run a repo commit-msg
])
def test_global_hooks_path_that_does_not_chain_still_refuses(tmp_path, marker, hooks):
    # Claim: only a declared dispatcher that has both hooks redirects the
    # install. Any other global hooksPath is still refused, because writing
    # into it gates every repo and a repo-dir install would never run.
    repo = _repo(tmp_path)
    env = _global_env(tmp_path, _dispatcher(tmp_path, marker=marker, hooks=hooks))
    r = subprocess.run([str(INSTALLER), "-C", str(repo)], capture_output=True, text=True, env=env)
    assert r.returncode == 2
    assert "Refusing" in r.stderr
    assert not (repo / ".git/hooks/commit-msg").exists()
