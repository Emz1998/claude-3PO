#!/usr/bin/env python3
"""PostToolUseFailure hook — records state from failed Bash commands.

Only handles Bash failures (matched in hooks.json). Records test execution
so that TDD-style failing tests still mark the phase as executed.
Does NOT parse tool_result (unavailable on failure) or call Hook.block().
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from utils.recorder import Recorder
from utils.resolver import resolve
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    phase = state.current_phase
    command = hook_input.get("tool_input", {}).get("command", "")

    recorder = Recorder(state)
    recorder.record_test_execution(phase, command)

    resolve(config, state)
    sys.exit(0)


if __name__ == "__main__":
    main()
