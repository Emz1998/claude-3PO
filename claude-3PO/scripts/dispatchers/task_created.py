#!/usr/bin/env python3
"""TaskCreated hook — validate new tasks against the workflow plan and record them.

Serves the Claude Code ``TaskCreated`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Run ``TaskCreatedGuard`` to check the new task against the planned
       build/implement task list.
    3. On ``"block"``: append a violations.md row and ``Hook.block`` (``exit 2``)
       so Claude sees the rejection and course-corrects.
    4. On ``"allow"``: apply task effects via
       :func:`utils.hooks.task_created.apply_task_effects` — record the matched
       build subject and/or attach the task as a subtask of its matched
       implement-workflow parent.

Env override: ``TASK_CREATED_STATE_PATH`` redirects state.json (used by tests).
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from handlers.guardrails.task_created_guard import TaskCreatedGuard
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation
from utils.hooks.task_created import apply_task_effects
from config import Config

STATE_PATH = Path(os.environ.get(
    "TASK_CREATED_STATE_PATH",
    str(SCRIPTS_DIR / "state.json"),
))


def main() -> None:
    """Entry point — runs once per TaskCreated event.

    Early-exit cascade: no session_id → no active workflow → otherwise validate
    the task and either block (with a violation row) or apply the matched
    side-effects.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    guard = TaskCreatedGuard(hook_input, config, state)
    decision, message = guard.validate()

    if decision == "block":
        log_violation(
            session_id=session_id,
            workflow_type=state.get("workflow_type", "implement"),
            story_id=state.get("story_id"),
            prompt_summary=state.get("prompt_summary"),
            phase=state.current_phase,
            tool="TaskCreate",
            action=hook_input.get("task_subject", ""),
            reason=message,
        )
        Hook.block(message)
    else:
        apply_task_effects(guard, state)

    sys.exit(0)


if __name__ == "__main__":
    main()
