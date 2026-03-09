"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.models.hook_input import StopInput
from workflow.constants.phases import STATUS_DONE


class StopGuard:
    def __init__(self, hook_input: StopInput):
        self._hook_input = hook_input
        self._is_workflow_active = check_workflow_gate()

    def run(self) -> None:
        if not self._is_workflow_active:
            return

        state = StateStore(state_path=cfg("paths.workflow_state"))
        sessions = state.get("implement_sessions") or {}
        story_id = sessions.get(self._hook_input.session_id)
        if not story_id:
            return

        # Check if that specific story is Done
        result = subprocess.run(
            ["python", "github_project/project_manager.py", "list",
             "--status", STATUS_DONE, "-k"],
            capture_output=True, text=True,
        )
        done_keys = [s.strip() for s in result.stdout.strip().split(",") if s.strip()] if result.stdout.strip() else []
        if story_id not in done_keys:
            Hook.block(f"Story '{story_id}' is not completed.")


if __name__ == "__main__":
    hook_input = StopInput.model_validate(Hook.read_stdin())
    StopGuard(hook_input).run()
