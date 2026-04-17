#!/usr/bin/env python3
"""TaskCreated hook dispatcher — validates and records task creation."""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation
from config import Config
from guardrails.task_created_guard import TaskCreatedGuard
from utils.recorder import Recorder

STATE_PATH = Path(os.environ.get(
    "TASK_CREATED_STATE_PATH",
    str(SCRIPTS_DIR / "state.jsonl"),
))


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    guard = TaskCreatedGuard(hook_input, config, state)
    decision, message = guard.validate()

    if decision == "block":
        log_violation(
            session_id=session_id,
            workflow_type=state.get("workflow_type", "build"),
            story_id=state.get("story_id"),
            prompt_summary=state.get("prompt_summary"),
            phase=state.current_phase,
            tool="TaskCreate",
            action=hook_input.get("task_subject", ""),
            reason=message,
        )
        Hook.block(message)
    else:
        _apply_task_effects(guard, state)

    sys.exit(0)


def _apply_task_effects(guard: TaskCreatedGuard, state: StateStore) -> None:
    recorder = Recorder(state)
    if guard.matched_build_subject:
        recorder.record_created_task(guard.matched_build_subject)
    if guard.matched_implement_parent_id and guard.matched_implement_payload:
        recorder.record_subtask(
            guard.matched_implement_parent_id, guard.matched_implement_payload
        )


if __name__ == "__main__":
    main()
