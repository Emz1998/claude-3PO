#!/usr/bin/env python3
"""PostToolUse hook — record successful tool results, then run resolvers.

Serves the Claude Code ``PostToolUse`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. ``Recorder.record`` updates state from the tool's ``tool_input`` /
       ``tool_result`` (writes, edits, test runs, etc.).
    3. ``resolve`` advances the workflow (e.g. mark a phase complete, auto-start
       the next phase) based on the freshly recorded state.

Special-case: when the tool is ``AskUserQuestion`` and the current phase is
``clarify``, the resumed headless-Claude session is invoked with the latest
Q&A so the model can re-evaluate clarity. A verdict of ``clear`` completes
the phase; ``vague`` increments ``iteration_count`` and the loop continues
(see :func:`utils.hooks.post_tool_use.handle_clarify_resume`).

Exit code semantics:

- ``Hook.block`` (``exit 2``) is used when ``Recorder.record`` raises
  ``ValueError`` — the tool succeeded but the resulting state is invalid, so we
  surface the message back to Claude as a course-correction.
- ``Hook.discontinue`` (``exit 0`` with ``continue: false``) is used when the
  resolver raises ``ValueError`` — the workflow has reached a terminal state
  that should stop the run cleanly rather than nudge the model.
- Plain ``exit 0`` for every other path.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from utils.hooks.post_tool_use import handle_clarify_resume
from utils.recorder import Recorder
from utils.resolver import resolve
from config import Config


def main() -> None:
    """Entry point — runs once per PostToolUse event.

    Early-exit cascade (each step ``exit 0`` if it short-circuits):
    no session_id → no active workflow → otherwise record + resolve. The
    Recorder/resolver split is intentional: Recorder mutates state from the
    tool's outcome, then ``resolve`` interprets that state to advance phases.

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

    if hook_input.get("tool_name") == "AskUserQuestion":
        handle_clarify_resume(hook_input, state)

    try:
        Recorder(state).record(hook_input, config)
    except ValueError as e:
        Hook.block(str(e))

    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))

    sys.exit(0)


if __name__ == "__main__":
    main()
