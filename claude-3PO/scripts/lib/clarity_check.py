"""clarity_check.py — Headless-Claude prompt clarity reviewer.

Shells out to ``claude -p --output-format json`` to evaluate whether a
user's ``/build`` prompt is specific enough to act on. The same headless
session is reused across a clarification loop via ``--resume <session_id>``
so the model accumulates context conversationally instead of being
re-briefed each round.

The verdict vocabulary is exactly two tokens:

- ``"clear"`` — the prompt is actionable; proceed to /explore.
- ``"vague"`` — more clarification is needed.

Anything else (parse error, subprocess error, unknown verdict) is
treated as ``"vague"`` (fail-closed) so a flaky headless run can't
silently skip the clarification gate.
"""

import json
import subprocess
from pathlib import Path
from typing import Tuple


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "templates" / "clarity-review.md"
)


def _read_review_prompt() -> str:
    """Load the system prompt sent to headless Claude.

    Returns:
        str: Contents of ``templates/clarity-review.md``, or a minimal
        fallback if the file is missing (defensive — tests don't need it).

    Example:
        >>> _read_review_prompt()  # doctest: +SKIP
    """
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
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
    sid = data.get("session_id", "") or ""
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
