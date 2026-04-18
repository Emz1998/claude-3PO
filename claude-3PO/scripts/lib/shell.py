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
from typing_extensions import Literal


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




def _codex_argv(prompt:str) -> list[str]:
    """Build the argv list for a headless ``codex exec`` invocation.

    Example:
        >>> _codex_argv("read-only")[:2]
        ['codex', 'exec']
    """
    
    return [
        "codex",
        "exec", prompt,
        "--skip-git-repo-check",
        "-",
    ]




def _build_argv(name: Literal["codex", "claude"], prompt: str) -> list[str]:
    """Helper to build argv for either a headless Claude or Codex invocation."""
    if name == "claude":
        return _claude_argv(prompt, DEFAULT_ALLOWED_TOOLS)
    if name == "codex":

        return _codex_argv(prompt)
    raise ValueError(f"Unsupported agent name: {name}")


def invoke_headless_agent(name: Literal["codex", "claude"], prompt: str, timeout: int, cwd: Path | None = None) -> str | None:
    """
    Helper to invoke either a headless Claude or Codex agent based on *name*.

    Args:
        name (Literal["codex", "claude"]): Which agent to invoke.
        prompt (str): Prompt text for the agent.
        timeout (int): Max seconds before the subprocess is killed.
        cwd (Path | None): Working directory; ``None`` uses the current.
        sandbox (str): Codex sandbox mode. Defaults to ``"read-only"``.

    Returns:
        str | None: Stripped stdout on success, ``None`` on any failure.    
    
    Example:
        >>> invoke_headless_agent("claude", "Review this plan", timeout=60)  # doctest: +SKIP  
    """

    argv = _build_argv(name, prompt)
    try:
        result = subprocess.run(
            argv, input=prompt, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None