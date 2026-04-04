"""stop_guard.py — Blocks Claude from stopping when workflow is incomplete.

- /plan workflow: allow stop after 'approved' phase
- /implement workflow: block unless phase == 'completed'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import PLAN_ALLOWED_STOP_PHASES
from workflow.session_store import SessionStore

# Implement workflow: collect reasons from state
def _collect_reasons(state: dict) -> list[str]:
    reasons = []
    tdd = state.get("tdd", False)

    if tdd and not state.get("test_run_executed"):
        reasons.append("tests have not been run")

    if state.get("validation_result") != "Pass":
        reasons.append("validation has not passed")

    if state.get("pr_status") != "created":
        reasons.append("PR has not been created")

    if not state.get("ci_check_executed"):
        reasons.append("CI has not been checked")

    if not state.get("report_written"):
        reasons.append("report has not been written — write it to .claude/reports/latest-report.md")

    return reasons


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a Stop event against the current workflow state.

    Returns ("allow", "") or ("block", reason).
    """
    # Prevent infinite loop if stop hook itself triggered this
    if hook_input.get("stop_hook_active"):
        return "allow", ""

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    workflow_type = state.get("workflow_type", "implement")
    phase = state.get("phase", "")

    # /plan workflow: allow once approved
    if workflow_type == "plan":
        if phase in PLAN_ALLOWED_STOP_PHASES:
            return "allow", ""
        return "block", f"Blocked: plan workflow not complete (current phase: '{phase}'). Must reach 'approved' before stopping."

    # /implement workflow: only allow when completed
    if phase == "completed":
        return "allow", ""

    reasons = _collect_reasons(state)
    if reasons:
        return "block", "Blocked: cannot stop -- " + ", ".join(reasons) + ". Complete these steps before stopping."

    return "block", f"Blocked: workflow not complete (current phase: '{phase}'). Continue working through remaining phases."
