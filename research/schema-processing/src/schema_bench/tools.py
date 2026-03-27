"""Tool installation checks and version capture."""

from __future__ import annotations

import os
import shutil
import subprocess

# Ensure cargo and go binaries are on PATH
_extra_paths = [
    os.path.expanduser("~/.cargo/bin"),
    os.path.expanduser("~/go/bin"),
]
for p in _extra_paths:
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + ":" + os.environ.get("PATH", "")


TOOL_BINARIES = {
    "jq": "jq",
    "jg": "jg",
    "jaq": "jaq",
    "gron": "gron",
    "hyperfine": "hyperfine",
}

VERSION_FLAGS = {
    "jq": "--version",
    "jg": "--version",
    "jaq": "--version",
    "gron": "--version",
    "hyperfine": "--version",
}


def check_tools() -> dict[str, str | None]:
    """Check which tools are installed. Returns {tool: version_string | None}."""
    result = {}
    for name, binary in TOOL_BINARIES.items():
        path = shutil.which(binary)
        if path is None:
            result[name] = None
            continue
        try:
            flag = VERSION_FLAGS.get(name, "--version")
            proc = subprocess.run(
                [binary, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = (proc.stdout.strip() or proc.stderr.strip()).split("\n")[0]
            result[name] = version
        except Exception:
            result[name] = "installed (version unknown)"
    return result


def print_tool_status() -> dict[str, str | None]:
    """Print tool availability and return versions dict."""
    versions = check_tools()
    print("Tool availability:")
    for name, version in versions.items():
        if version:
            print(f"  {name}: {version}")
        else:
            print(f"  {name}: NOT FOUND")
    missing = [n for n, v in versions.items() if v is None]
    if missing:
        print(f"\nMissing tools: {', '.join(missing)}")
        print("Run: bash scripts/install_tools.sh")
    return versions
