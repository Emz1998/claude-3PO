"""utils.hooks.post_tool_use — orchestration helpers for the PostToolUse hook.

Extracted from ``dispatchers/post_tool_use.py`` so the dispatcher file holds
only ``main()``. The clarify-phase resume path lives here because it's the
only branch the dispatcher triggers before handing control to Recorder.
"""

from lib import subprocess_agents
from lib.state_store import StateStore


def build_qa_payload(hook_input: dict) -> str:
    """Serialize the latest AskUserQuestion question/answer pair into plain text.

    The resumed headless session already has the full prior conversation —
    only the new turn needs to be sent. Format is intentionally simple
    plain-text so the headless model can read it without a JSON parse.

    Args:
        hook_input (dict): PostToolUse payload for an AskUserQuestion event.

    Returns:
        str: Multi-line ``Q: <question>\\nA: <answer>`` block.

    Example:
        >>> build_qa_payload({"tool_input": {"questions": [{"question": "Q?"}]},
        ...                   "tool_response": {"answers": {"Q?": "A!"}}})
        'Q: Q?\\nA: A!'
    """
    tool_input = hook_input.get("tool_input", {}) or {}
    tool_response = hook_input.get("tool_response", {}) or {}
    answers = tool_response.get("answers", {}) or {}
    # Walk questions in order and pair each with its answer — the resumed
    # headless session expects a stable Q/A ordering.
    lines: list[str] = []
    for q in tool_input.get("questions", []):
        text = q.get("question", "") if isinstance(q, dict) else str(q)
        ans = answers.get(text, "")
        lines.append(f"Q: {text}\nA: {ans}")
    return "\n\n".join(lines)


def handle_clarify_resume(hook_input: dict, state: StateStore) -> None:
    """Resume the clarify headless session after an AskUserQuestion answer.

    No-ops unless the current phase is ``clarify`` (so a stray
    AskUserQuestion in another phase doesn't trigger a headless call).
    Increments ``iteration_count`` on every resume; on a ``clear`` verdict
    flips the phase to ``completed`` so ``auto_start_next`` can advance.

    Args:
        hook_input (dict): PostToolUse payload (must include the
            AskUserQuestion ``tool_input`` and ``tool_response``).
        state (StateStore): Live workflow state for this session.

    Example:
        >>> handle_clarify_resume(hook_input, state)  # doctest: +SKIP

    SideEffect:
        Bumps ``iteration_count`` on the clarify phase; may flip it to
        ``completed`` when the headless verdict is ``clear``.
    """
    # Guard chain: need an in-progress clarify phase with a live session id;
    # missing either means the resume path doesn't apply to this event.
    phase = state.build.get_clarify_phase()
    if not phase or phase.get("status") != "in_progress":
        return
    sid = phase.get("headless_session_id", "")
    if not sid:
        return
    qa = build_qa_payload(hook_input)
    verdict = subprocess_agents.run_resume(sid, qa)
    state.build.bump_clarify_iteration()
    if verdict == "clear":
        state.set_phase_completed("clarify")
