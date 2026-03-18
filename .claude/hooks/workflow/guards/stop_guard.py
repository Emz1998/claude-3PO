"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import StopInput
from workflow.config import get as cfg
from workflow.constants.phases import CI_PASS, CI_FAIL


def poll_ci_status(pr_number: int) -> str:
    """Poll CI status via gh cli. Returns 'pass' or 'fail'."""
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--json", "state"],
            capture_output=True,
            text=True,
            check=True,
        )
        import json

        checks = json.loads(result.stdout)
        if all(c.get("state") == "SUCCESS" for c in checks):
            return CI_PASS
        return CI_FAIL
    except Exception:
        return CI_FAIL


def call_code_reviewer(session: SessionState) -> None:
    """Call the code-reviewer subagent."""
    session.set(
        "fully_blocked",
        {
            "status": "active",
            "reason": "CI check failed. Please invoke the code-reviewer subagent to review the code then refactor the code until the CI check passes.",
            "exception": [["agent", "code-reviewer"]],
        },
    )


class StopGuard:
    def __init__(self, hook_input: StopInput):
        self._hook_input = hook_input
        self._session = SessionState(hook_input.session_id)

    def run(self) -> None:
        is_workflow_active = check_workflow_gate()
        if not is_workflow_active:
            Hook.block("Workflow is not active.")
            return

        pr_status = self._session.get("pr", {}).get("status", "inactive")

        fully_blocked = self._session.get("fully_blocked", {})
        if fully_blocked.get("status") == "active":
            Hook.block(fully_blocked.get("fully_blocked is active"))
            return

        if pr_status != "created":
            Hook.block("PR has not been created yet.")
            return

        pr_number = self._session.get("pr", {}).get("number")

        if pr_number is None:
            Hook.block("PR number is not found. Please create a pull request first.")
            return

        failure_count = self._session.get("ci", {}).get("failure_count", 0)
        if failure_count >= 3:
            self._session.set_force_stop(
                "CI check has failed 3 times. Escalating to the user"
            )
            Hook.success_response("CI check has failed 3 times. Escalating to the user")
            return

        ci_status = poll_ci_status(pr_number)
        if ci_status == "fail":
            self._session.set(
                "ci",
                {
                    "status": "failed",
                    "failure_count": self._session.get("ci", {}).get("failure_count", 0)
                    + 1,
                },
            )
            Hook.block(
                "CI check failed. Please invoke the troubleshooter agent to diagnose and resolve the issue then refactor the code until the CI check passes."
            )
            return


if __name__ == "__main__":
    hook_input = StopInput.model_validate(Hook.read_stdin())
    StopGuard(hook_input).run()
