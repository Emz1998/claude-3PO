"""reviewer.py — Template-agnostic headless reviewer.

Drives a headless Claude or Codex agent through a self-correcting review
loop: each round parses the agent's JSONL output, asks a caller-supplied
conformance check whether the response is acceptable, and — if not —
feeds the check's feedback back as a correction prompt until the response
conforms or attempts are exhausted.

Both the conformance check and the correction-prompt builder are
parameters, so the same loop drives plan review, code review, or any
other format-gated review without knowing the format. The common
markdown-template case is handled by the ``template_tree_check``
factory included here.
"""

import json
from pathlib import Path
from typing import Callable
from typing_extensions import Literal

from lib.subprocess_agents import (  # type: ignore
    invoke_headless_agent,
    ClaudeOptions,
    CodexOptions,
)
from lib.extractors.markdown import trees_identical, build_md_tree  # type: ignore


# ---------------------------------------------------------------------------
# Constants + type aliases
# ---------------------------------------------------------------------------


MAX_REVIEW_ATTEMPTS = 3
REVIEW_TIMEOUT_SECONDS = 120
# Conformance check: given the agent's response, returns (is_ok, feedback).
# When is_ok is True the loop returns the response; when False, *feedback*
# is passed to the correction_builder to compose the next prompt.
ConformanceCheck = Callable[[str], tuple[bool, str]]
# Correction builders take the conformance feedback and return the next prompt.
CorrectionBuilder = Callable[[str], str]
_DIFF_SEPARATOR = "\n\n------------------------------------\n\n"


def _review_options(
    llm: Literal["codex", "claude"],
    session_id: str | None,
    model: str | None = None,
) -> ClaudeOptions | CodexOptions:
    """
    Build agent options for the review loop (JSONL output mode).

    The review loop always needs JSONL so it can extract a session id for
    the next round — claude uses ``--output-format json``, codex uses
    ``--json``.

    Args:
        llm (Literal["codex", "claude"]): Agent flavor.
        session_id (str | None): Session pin for resume.
        model (str | None): Optional model override.

    Returns:
        ClaudeOptions | CodexOptions: Flavor-specific options with JSONL forced on.

    Example:
        >>> _review_options("codex", None).json_output
        True
        Return: True
    """
    if llm == "claude":
        # Claude reviewers default to haiku when no model is specified.
        return ClaudeOptions(
            model=model or "haiku",
            output_format="json",
            session_id=session_id,
        )
    return CodexOptions(json_output=True, session_id=session_id, model=model)


# ---------------------------------------------------------------------------
# JSONL parsing helpers
# ---------------------------------------------------------------------------


def _get_session_id(output: str) -> str:
    """
    Extract the session id (codex's ``thread_id``) from a JSONL blob.

    Codex streams one JSON object per line; the first line containing
    ``thread_id`` pins the session for resumable correction rounds.

    Args:
        output (str): Raw agent stdout (line-delimited JSON).

    Returns:
        str: Session id when found, empty string otherwise.

    Raises:
        json.JSONDecodeError: If a ``{``-prefixed line is not valid JSON.

    Example:
        >>> _get_session_id('{"thread_id": "abc"}\\n')
        'abc'
        Return: 'abc'
    """
    # Scan JSONL lines for the first populated thread_id — later lines may omit it.
    for line in output.split("\n"):
        if not line.startswith("{"):
            continue
        data = json.loads(line)
        sid = data.get("thread_id", "")
        if sid:
            return sid
    return ""


def _get_response(output: str) -> str:
    """
    Extract the final ``item.text`` payload from a JSONL agent response.

    Agents emit multiple item lines (status, partial text, final text); the
    last non-empty one is the completed reviewer answer.

    Args:
        output (str): Raw agent stdout (line-delimited JSON).

    Returns:
        str: Last non-empty ``item.text`` string, or empty string if none.

    Raises:
        json.JSONDecodeError: If a ``{``-prefixed line is not valid JSON.

    Example:
        >>> _get_response('{"item":{"text":"final"}}')
        'final'
        Return: 'final'
    """
    # Keep overwriting so we land on the last emitted text chunk.
    response = ""
    for line in output.split("\n"):
        if not line.startswith("{"):
            continue
        data = json.loads(line)
        text = data.get("item", {}).get("text", "")
        if text:
            response = text
    return response


# ---------------------------------------------------------------------------
# Conformance-check factory for the common markdown-template case
# ---------------------------------------------------------------------------


def template_tree_check(template: Path) -> ConformanceCheck:
    """
    Build a ConformanceCheck that matches responses against *template*'s md tree.

    The returned callable reads *template* each invocation so callers can
    edit the template mid-session and pick up the new structure without
    rebuilding the check.

    Args:
        template (Path): Path to the markdown template file.

    Returns:
        ConformanceCheck: ``(response) -> (is_ok, stitched_diff_str)``.

    Raises:
        FileNotFoundError: When the check is *called* and *template* is missing.

    Example:
        >>> check = template_tree_check(Path("plan.md"))  # doctest: +SKIP
        >>> check("# Wrong")  # doctest: +SKIP
        (False, '...')
        Return: (False, '...')
    """

    def _check(response: str) -> tuple[bool, str]:
        # Tree-level compare so trivial whitespace/wording drift doesn't retrigger a round.
        ok, diff = trees_identical(
            build_md_tree(template.read_text()),
            build_md_tree(response),
        )
        return ok, _DIFF_SEPARATOR.join(diff)

    return _check


# ---------------------------------------------------------------------------
# Public reviewer
# ---------------------------------------------------------------------------


def invoke_reviewer(
    llm: Literal["codex", "claude"],
    prompt: str,
    conforms: ConformanceCheck,
    correction_builder: CorrectionBuilder,
    *,
    session_id: str | None = None,
    timeout: int = REVIEW_TIMEOUT_SECONDS,
    attempts_left: int = MAX_REVIEW_ATTEMPTS,
) -> str:
    """
    Run a self-correcting, format-agnostic review via a headless agent.

    The reviewer calls *llm*, parses the JSONL response, asks *conforms*
    whether the response is acceptable, and — if not — recurses with a
    correction prompt built by *correction_builder* from the feedback that
    *conforms* returned, resuming the pinned session. Returns the response
    string when *conforms* returns True or attempts run out; returns a
    sentinel ``"<llm> reviewer failed…"`` string on invocation or session
    errors (callers treat sentinels and real responses uniformly — the
    fail-open convention shared across this module).

    Args:
        llm (Literal["codex", "claude"]): Headless agent to invoke.
        prompt (str): Initial (or correction) prompt text.
        conforms (ConformanceCheck): Decides whether the response is
            acceptable; returns ``(is_ok, feedback)``.
        correction_builder (CorrectionBuilder): Builds the next prompt from
            the conformance feedback when the response is unacceptable.
        session_id (str | None): Resume an existing session when set.
        timeout (int): Seconds before the subprocess is killed.
        attempts_left (int): Remaining correction rounds including this one.

    Returns:
        str: Agent response, or a failure sentinel containing *llm*.

    Raises:
        json.JSONDecodeError: If the agent emits malformed JSONL.

    Example:
        >>> invoke_reviewer("codex", "p", lambda r: (True, ""), lambda d: "fix")  # doctest: +SKIP
        Return: '...'
    """
    # One invocation → parse → check → recurse-or-return.
    raw = invoke_headless_agent(
        prompt,
        _review_options(llm, session_id),
        timeout=timeout,
    )
    if raw is None:
        return f"{llm} reviewer failed to respond"
    sid = _get_session_id(raw)
    if not sid:
        return f"{llm} reviewer failed to get session id"
    response = _get_response(raw)
    # Caller-supplied check decides acceptability + supplies correction feedback.
    ok, feedback = conforms(response)
    if ok or attempts_left <= 1:
        return response
    # Retry: feed the feedback into the correction builder, resume the pinned session.
    return invoke_reviewer(
        llm,
        correction_builder(feedback),
        conforms,
        correction_builder,
        session_id=sid,
        timeout=timeout,
        attempts_left=attempts_left - 1,
    )


def invoke_agent(
    llm: Literal["codex", "claude"],
    agent_name: str,
    prompt: str,
    conforms: ConformanceCheck,
    correction_builder: CorrectionBuilder,
    *,
    model: str | None = None,
    session_id: str | None = None,
    timeout: int = REVIEW_TIMEOUT_SECONDS,
    attempts_left: int = MAX_REVIEW_ATTEMPTS,
) -> str:
    """
    Run a self-correcting, format-agnostic agent via a headless agent.

    The agent calls *llm*, parses the JSONL response, asks *conforms*
    whether the response is acceptable, and — if not — recurses with a
    correction prompt built by *correction_builder* from the feedback that
    *conforms* returned, resuming the pinned session. Returns the response string when *conforms* returns True or attempts run out; returns a sentinel ``"<llm> {model} {agent_name} failed…"`` string on invocation or session errors (callers treat sentinels and real responses uniformly — the fail-open convention shared across this module).

    Args:
        llm (Literal["codex", "claude"]): Headless agent to invoke.
        agent_name (str): Name of the agent to invoke.
        prompt (str): Initial prompt text.
        conforms (ConformanceCheck): Decides whether the response is acceptable; returns ``(is_ok, feedback)``.
        correction_builder (CorrectionBuilder): Builds the next prompt from the conformance feedback when the response is unacceptable.
        model (str | None): Model to use.
        session_id (str | None): Resume an existing session when set.
        timeout (int): Seconds before the subprocess is killed.
        attempts_left (int): Remaining attempts including this one.

    Returns:
        str: Agent response, or a failure sentinel containing *llm*.

    Raises:
        json.JSONDecodeError: If the agent emits malformed JSONL.

    Example:
        >>> invoke_reviewer("codex", "p", lambda r: (True, ""), lambda d: "fix")  # doctest: +SKIP
        Return: '...'
    """
    # One invocation → parse → check → recurse-or-return.
    raw = invoke_headless_agent(
        prompt,
        _review_options(llm, session_id, model=model),
        timeout=timeout,
    )
    if raw is None:
        return f"{llm} {model} {agent_name} failed to respond"
    sid = _get_session_id(raw)
    if not sid:
        return f"{llm} {model} {agent_name} failed to get session id"
    response = _get_response(raw)
    # Caller-supplied check decides acceptability + supplies correction feedback.
    ok, feedback = conforms(response)
    if ok or attempts_left <= 1:
        return response
    # Retry: feed the feedback into the correction builder, resume the pinned session.
    return invoke_agent(
        llm,
        agent_name,
        correction_builder(feedback),
        conforms,
        correction_builder,
        session_id=sid,
        timeout=timeout,
        attempts_left=attempts_left - 1,
        model=model,
    )
