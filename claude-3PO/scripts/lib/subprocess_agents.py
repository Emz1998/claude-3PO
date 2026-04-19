"""subprocess_agents.py — Subprocess wrappers for git and headless agents.

Consolidates two related concerns around shelling out to sibling agents and
git:

* **Generic subprocess wrappers** (``run_git``, ``invoke_headless_agent``) —
  thin helpers around ``subprocess.run`` that swallow errors rather than
  raise, so workflow code can treat "agent failed" and "agent said nothing"
  the same way. Fail-open by design for the Claude/Codex helpers, because
  those calls enrich context rather than gate control.
* **Clarity check** (``run_initial``, ``run_resume``) — dedicated headless
  Claude session for the ``/build`` clarification loop. Uses
  ``--output-format json`` so session ids can be captured and the same
  conversation can be resumed across turns. The verdict vocabulary is only
  ``"clear"`` / ``"vague"`` — anything else (parse errors, subprocess errors,
  unknown verdict tokens) is treated as ``"vague"`` (fail-closed), so a flaky
  headless run can't silently skip the clarification gate.
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Tuple
from typing_extensions import Literal


# ---------------------------------------------------------------------------
# Generic subprocess wrappers (git + headless claude/codex)
# ---------------------------------------------------------------------------


DEFAULT_ALLOWED_TOOLS = "Read,Grep,Glob"


GIT_TIMEOUT_SECONDS = 30


def run_git(
    args: list[str], cwd: Path, timeout: int = GIT_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess:
    """
    Run ``git <args>`` inside *cwd* and return the result without raising.

    A timeout is mandatory in practice: the auto-commit hook and the
    PostToolUse path both call this synchronously and would otherwise hang
    the live session on a stuck git operation (e.g. a credential prompt
    with no TTY). On timeout we return a synthesized non-zero result so
    callers that check ``returncode`` fall through their error branch
    instead of seeing a raised exception.

    Args:
        args (list[str]): Argv tail (everything after ``git``).
        cwd (Path): Working directory for the git invocation.
        timeout (int): Max seconds before the subprocess is killed.

    Returns:
        subprocess.CompletedProcess: Fully populated result; callers inspect
        ``returncode``, ``stdout``, and ``stderr`` themselves.

    Example:
        >>> run_git(["status", "--porcelain"], Path.cwd())  # doctest: +SKIP
    """
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        # Synthesize a failure so callers treat timeout the same as any other
        # non-zero git result — no exception handling required at call sites.
        return subprocess.CompletedProcess(
            args=e.cmd, returncode=124, stdout="", stderr=f"git timed out after {timeout}s",
        )


def _build_argv(name: Literal["codex", "claude"], prompt: str) -> list[str]:
    """Build argv for either a headless Claude or Codex invocation.

    Args:
        name (Literal["codex", "claude"]): Which agent to invoke.
        prompt (str): Prompt text passed positionally (and via stdin too).

    Returns:
        list[str]: Subprocess argv.

    Example:
        >>> _build_argv("claude", "hi")[:2]
        ['claude', '-p']
    """
    if name == "claude":
        return [
            "claude", "-p", prompt,
            "--tools", DEFAULT_ALLOWED_TOOLS,
            "--allowedTools", DEFAULT_ALLOWED_TOOLS,
            "--output-format", "text",
        ]
    if name == "codex":
        return ["codex", "exec", prompt, "--skip-git-repo-check", "-"]
    raise ValueError(f"Unsupported agent name: {name}")


def invoke_headless_agent(
    name: Literal["codex", "claude"],
    prompt: str,
    timeout: int,
    cwd: Path | None = None,
) -> str | None:
    """
    Helper to invoke either a headless Claude or Codex agent based on *name*.

    Args:
        name (Literal["codex", "claude"]): Which agent to invoke.
        prompt (str): Prompt text for the agent.
        timeout (int): Max seconds before the subprocess is killed.
        cwd (Path | None): Working directory; ``None`` uses the current.

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


# ---------------------------------------------------------------------------
# Clarity check (headless Claude clarity reviewer)
# ---------------------------------------------------------------------------


_CLARITY_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "templates" / "clarity-review.md"
)


@lru_cache(maxsize=1)
def _read_review_prompt() -> str:
    """Load (and cache) the system prompt sent to headless Claude.

    The template doesn't change mid-process, so cache the read. The minimal
    fallback covers test environments where the template isn't shipped.

    Returns:
        str: Contents of ``templates/clarity-review.md``, or a minimal fallback.

    Example:
        >>> _read_review_prompt()  # doctest: +SKIP
    """
    try:
        return _CLARITY_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Reply with exactly one token: clear or vague."


def _build_initial_payload(user_prompt: str) -> str:
    """Combine the review prompt with the user's prompt for the first call.

    Args:
        user_prompt (str): The user's original ``/build`` instructions.

    Returns:
        str: Stdin payload for ``claude -p``.

    Example:
        >>> _build_initial_payload("add /logout")  # doctest: +SKIP
    """
    review_prompt = _read_review_prompt()
    return f"{review_prompt}\n\n---\nUser prompt:\n{user_prompt}\n"


def _parse_verdict(stdout: str) -> Tuple[str, str]:
    """Pull (session_id, verdict) out of a `claude -p --output-format json` payload.

    Returns ``("", "vague")`` on any parse failure so callers fail closed.

    Args:
        stdout (str): Raw stdout from the headless ``claude`` process.

    Returns:
        Tuple[str, str]: ``(session_id, verdict)`` where verdict is
        ``"clear"`` or ``"vague"``.

    Example:
        >>> _parse_verdict('{"session_id":"s","result":"clear"}')
        ('s', 'clear')
    """
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return "", "vague"
    sid = data.get("session_id", "")
    raw = (data.get("result") or "").strip().lower()
    verdict = "clear" if raw == "clear" else "vague"
    return sid, verdict


def _run_claude(cmd: list[str], stdin_payload: str) -> str:
    """Execute the headless ``claude`` CLI and return its stdout.

    Returns ``""`` (which parses as ``vague``) on non-zero exit so the
    workflow fails closed rather than treating an error as ``clear``.

    Args:
        cmd (list[str]): Argv list (must start with the ``claude`` binary).
        stdin_payload (str): Text fed to the process's stdin.

    Returns:
        str: Process stdout, or ``""`` on failure.

    Example:
        >>> _run_claude(["claude", "-p", "--output-format", "json"], "hi")  # doctest: +SKIP
    """
    result = subprocess.run(
        cmd,
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def run_initial(user_prompt: str) -> Tuple[str, str]:
    """Run the first headless clarity review for a fresh ``/build`` invocation.

    Args:
        user_prompt (str): The user's free-text ``/build`` instructions.

    Returns:
        Tuple[str, str]: ``(headless_session_id, verdict)``. ``verdict``
        is one of ``"clear"`` / ``"vague"``. Session id is empty when
        the headless run errored.

    Raises:
        subprocess.TimeoutExpired: Propagated if the headless call hangs
        beyond the 120s timeout (rare; kept un-caught so the operator
        sees the failure rather than a silent vague).

    Example:
        >>> run_initial("add /logout endpoint")  # doctest: +SKIP
        ('sess_abc123', 'clear')
    """
    cmd = ["claude", "-p", "--output-format", "json"]
    stdout = _run_claude(cmd, _build_initial_payload(user_prompt))
    return _parse_verdict(stdout)


def run_resume(headless_session_id: str, qa_payload: str) -> str:
    """Resume the headless session with a Q&A turn and re-evaluate clarity.

    Args:
        headless_session_id (str): Session id captured by :func:`run_initial`.
        qa_payload (str): The latest question/answer pair (the resumed
            session already has all prior history; only the new turn is sent).

    Returns:
        str: ``"clear"`` or ``"vague"``.

    Raises:
        subprocess.TimeoutExpired: Propagated on hang past 120s.

    Example:
        >>> run_resume("sess_abc", "Q: which file?\\nA: src/auth.py")  # doctest: +SKIP
        'clear'
    """
    cmd = [
        "claude", "-p", "--output-format", "json",
        "--resume", headless_session_id,
    ]
    stdout = _run_claude(cmd, qa_payload)
    _, verdict = _parse_verdict(stdout)
    return verdict
