#!/usr/bin/env python3
"""PostToolUseFailure hook — record state from *failed* Bash invocations.

Serves the Claude Code ``PostToolUseFailure`` event, scoped to ``Bash`` only
(the matcher is configured in ``hooks.json``). Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Treat the failed command as a test execution and record it via
       ``Recorder.record_test_execution`` for the current phase.
    3. Run ``resolve`` so the workflow can still advance off this signal.

Why this exists: a TDD-style failing test is *expected* to exit non-zero, but
still represents a real "tests were executed" event for the build/implement
flow. Without this hook the failing run would be discarded and the phase would
look like it never reached its test step.

Constraints:

- Does NOT parse ``tool_result`` — it is unavailable on tool failure.
- Does NOT call ``Hook.block`` — surfacing a block here would double-up on the
  failure Claude already sees from Bash itself.
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
    """Entry point — runs once per Bash PostToolUseFailure event.

    Always exits 0. Records the failed Bash command as a test execution for
    the current phase so TDD red-state runs still count toward phase progress,
    then resolves to let the workflow advance.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
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
