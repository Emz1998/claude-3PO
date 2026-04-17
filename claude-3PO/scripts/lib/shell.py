"""Subprocess wrappers for git and headless Claude invocations."""

import subprocess
from pathlib import Path


DEFAULT_ALLOWED_TOOLS = "Read,Grep,Glob"


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command; return the CompletedProcess (no exception on non-zero)."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )


def invoke_claude(
    prompt: str,
    timeout: int,
    cwd: Path | None = None,
    allowed_tools: str = DEFAULT_ALLOWED_TOOLS,
) -> str | None:
    """Run headless Claude; return stripped stdout or None on any failure."""
    argv = _claude_argv(prompt, allowed_tools)
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def _claude_argv(prompt: str, allowed_tools: str) -> list[str]:
    return [
        "claude",
        "-p", prompt,
        "--tools", allowed_tools,
        "--allowedTools", allowed_tools,
        "--output-format", "text",
    ]
