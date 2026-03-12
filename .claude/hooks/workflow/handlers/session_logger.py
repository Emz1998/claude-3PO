"""PostToolUse handler — appends JSONL log entries per tool use."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput


def get_log_path(story_id: str) -> Path:
    """Return the log file path for a given story ID."""
    from workflow.config import get as cfg
    sessions_dir = cfg("sessions_dir", ".claude/sessions")
    return Path(sessions_dir) / story_id / "log.jsonl"


class SessionLogger:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        phase = session.get("phase", {}).get("current", "unknown") if session else "unknown"

        log_path = get_log_path(story_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session": story_id,
            "event": self._hook_input.tool_name,
            "phase": phase,
        }

        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    SessionLogger(hook_input).run()
