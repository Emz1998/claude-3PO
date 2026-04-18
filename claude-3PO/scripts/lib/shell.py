"""shell.py — Subprocess wrappers for git and headless Claude invocations.

Both helpers swallow rather than raise: ``run_git`` returns the
``CompletedProcess`` so callers can inspect ``returncode`` themselves, and
``invoke_claude`` returns ``None`` on any failure (timeout, missing binary,
non-zero exit, empty stdout). Workflow code generally treats Claude
invocation failures as advisory rather than fatal — fail-open by design,
since the headless call is usually for context enrichment, not for control.
"""

import subprocess
from pathlib import Path


DEFAULT_ALLOWED_TOOLS = "Read,Grep,Glob"


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Run ``git <args>`` inside *cwd* and return the result without raising.

    Args:
        args (list[str]): Argv tail (everything after ``git``).
        cwd (Path): Working directory for the git invocation.

    Returns:
        subprocess.CompletedProcess: Fully populated result; callers inspect
        ``returncode``, ``stdout``, and ``stderr`` themselves.

    Example:
        >>> run_git(["status", "--porcelain"], Path.cwd())  # doctest: +SKIP
    """
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )


def invoke_claude(
    prompt: str,
    timeout: int,
    cwd: Path | None = None,
    allowed_tools: str = DEFAULT_ALLOWED_TOOLS,
) -> str | None:
    """
    Run a headless ``claude -p ...`` invocation and return stripped stdout.

    Returns ``None`` on any failure mode — timeout, missing ``claude`` binary,
    non-zero exit, or empty stdout — so callers can use the result as an
    optional enrichment without try/except scaffolding. The default tool
    allowlist is read-only (``Read,Grep,Glob``) to keep nested invocations
    side-effect free.

    Args:
        prompt (str): Prompt to send to Claude.
        timeout (int): Max seconds before the subprocess is killed.
        cwd (Path | None): Working directory; ``None`` uses the current.
        allowed_tools (str): Comma-separated tool allowlist passed to ``claude``.

    Returns:
        str | None: Stripped stdout on success, ``None`` on any failure.

    Example:
        >>> invoke_claude("List Python files", timeout=10)  # doctest: +SKIP
    """
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
    """Build the argv list for a headless ``claude`` invocation.

    Example:
        >>> _claude_argv("hello", "Read,Grep")[:2]
        ['claude', '-p']
    """
    return [
        "claude",
        "-p", prompt,
        "--tools", allowed_tools,
        "--allowedTools", allowed_tools,
        "--output-format", "text",
    ]
