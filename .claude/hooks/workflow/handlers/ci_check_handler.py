"""PostToolUse handler — updates CI status after /push skill."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput
from workflow.config import get as cfg
from workflow.constants.phases import CI_PASS, CI_FAIL


def poll_ci_status(pr_number: int) -> str:
    """Poll CI status via gh cli. Returns 'pass' or 'fail'."""
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--json", "state"],
            capture_output=True, text=True, check=True,
        )
        import json
        checks = json.loads(result.stdout)
        if all(c.get("state") == "SUCCESS" for c in checks):
            return CI_PASS
        return CI_FAIL
    except Exception:
        return CI_FAIL


class CiCheckHandler:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        # Only trigger on /push skill
        if self._hook_input.tool_name != "Skill":
            return
        if self._hook_input.tool_input.skill != "push":
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        pr_number = session.get("pr", {}).get("number")
        if not pr_number:
            return

        ci_status = poll_ci_status(pr_number)
        max_iterations = cfg("validation.ci_max_iterations", 2)
        current_iteration = session.get("ci", {}).get("iteration_count", 0)

        if ci_status == CI_PASS:
            def update_pass(s: dict) -> None:
                s["ci"]["status"] = CI_PASS
            session_state.update_session(story_id, update_pass)
        else:
            if current_iteration >= max_iterations:
                def update_escalate(s: dict) -> None:
                    s["ci"]["status"] = CI_FAIL
                    s["ci"]["escalate_to_user"] = True
                session_state.update_session(story_id, update_escalate)
            else:
                def update_fail(s: dict) -> None:
                    s["ci"]["status"] = CI_FAIL
                    s["ci"]["iteration_count"] += 1
                session_state.update_session(story_id, update_fail)


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    CiCheckHandler(hook_input).run()
