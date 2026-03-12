"""PreToolUse guard — validates workflow phase transitions.

Invoked via skill frontmatter: python3 phase_guard.py <predecessor> <current>
Checks that the session's current phase matches the expected predecessor.
Also checks control.hold and control.blocked_until_phase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate


class PhaseGuard:
    def __init__(self, predecessor: str, current: str):
        self._predecessor = predecessor
        self._current = current

    def run(self) -> None:
        if not check_workflow_gate():
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        # Check hold
        control = session.get("control", {})
        if control.get("hold", False):
            Hook.block(f"Session '{story_id}' is on hold.")

        # Check blocked_until_phase
        blocked_until = control.get("blocked_until_phase")
        if blocked_until:
            Hook.block(f"Session '{story_id}' is blocked until phase '{blocked_until}'.")

        # Validate phase transition
        current_phase = session.get("phase", {}).get("current")
        if current_phase != self._predecessor:
            Hook.block(
                f"Invalid phase transition: expected '{self._predecessor}' "
                f"but current phase is '{current_phase}'."
            )

        # Record transition
        def update_phase(s: dict) -> None:
            s["phase"]["previous"] = s["phase"]["current"]
            s["phase"]["current"] = self._current

        session_state.update_session(story_id, update_phase)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("predecessor")
    parser.add_argument("current")
    args = parser.parse_args()

    Hook.read_stdin()  # consume stdin
    guard = PhaseGuard(args.predecessor, args.current)
    guard.run()
