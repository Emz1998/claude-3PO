#!/usr/bin/env python3
"""PreToolUse hook — gate every tool call through the matching guardrail.

Serves the Claude Code ``PreToolUse`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Look up the per-tool guard in ``TOOL_GUARDS`` (keyed by ``tool_name``).
       Tools without a guard are silently allowed.
    3. Run the guard. On ``"block"`` log the violation and call
       ``Hook.advanced_block`` — emits a ``permissionDecision: deny`` JSON
       payload so the Claude Code UI shows a structured denial reason.
    4. On ``"allow"`` finish with ``Hook.system_message`` so the optional guard
       message reaches the model regardless of decision.

The Skill side-effect pass used to live inside ``PhaseGuard``; it was extracted
so the guard stays a pure pass/fail validator and the dispatcher owns the
post-Allow mutations (SRP refactor).
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from handlers.guardrails import TOOL_GUARDS
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation, extract_action
from utils.hooks.pre_tool_use import resolve_violation_phase
from config import Config


def main() -> None:
    """Entry point — runs once per PreToolUse event.

    Early-exit cascade: no session_id → no active workflow → no guard registered
    for this tool → run the guard and either ``advanced_block`` (deny) or
    ``system_message`` (allow, optionally with a status nudge).

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.json")
    if not state.get("workflow_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    guard = TOOL_GUARDS.get(tool_name)
    if not guard:
        sys.exit(0)

    config = Config()
    decision, message = guard(hook_input, config, state)

    if decision == "block":
        log_violation(
            session_id=session_id,
            workflow_type=state.get("workflow_type", "implement"),
            story_id=state.get("story_id"),
            prompt_summary=state.get("prompt_summary"),
            phase=resolve_violation_phase(state, config, tool_name, hook_input),
            tool=tool_name,
            action=extract_action(tool_name, hook_input),
            reason=message,
        )
        Hook.advanced_block("PreToolUse", message)
    else:
        Hook.system_message(message)


if __name__ == "__main__":
    main()
