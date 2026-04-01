"""bash_guard.py — Phase-based Bash command enforcement using flat state model."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

PR_COMMAND_PATTERNS = [r"\bgh\s+pr\s+create\b", r"\bgit\s+push\b"]
TEST_RUN_PATTERNS = [r"\bpytest\b", r"\bnpm\s+test\b", r"\byarn\s+test\b",
                     r"\bgo\s+test\b", r"\bjest\b", r"\bvitest\b"]
CI_CHECK_PATTERNS = [r"\bgh\s+pr\s+checks\b", r"\bgh\s+run\s+view\b"]


def _is_pr_command(command: str) -> bool:
    return any(re.search(p, command) for p in PR_COMMAND_PATTERNS)


def _is_test_run(command: str) -> bool:
    return any(re.search(p, command) for p in TEST_RUN_PATTERNS)


def _is_ci_check(command: str) -> bool:
    return any(re.search(p, command) for p in CI_CHECK_PATTERNS)


def validate_pre(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Validate a Bash PreToolUse invocation.

    Blocks PR commands outside pr-create phase or without passing validation.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")

    if not _is_pr_command(command):
        return "allow", ""

    phase = state.get("phase", "")
    validation_result = state.get("validation_result")

    if phase != "pr-create":
        return "block", f"PR commands are only allowed during 'pr-create' phase (current: '{phase}')"

    if validation_result != "Pass":
        return "block", "Cannot create PR before validation passes"

    return "allow", ""


def handle_post(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle Bash PostToolUse — track test runs, PR creation, CI checks."""
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")
    output = hook_input.get("tool_response", {}).get("output", "")
    phase = state.get("phase", "")

    # Track test-run commands
    if _is_test_run(command):
        store.set("test_run_executed", True)
        return "allow", ""

    # Track PR creation
    if _is_pr_command(command) and phase == "pr-create":
        def _record_pr(s: dict) -> None:
            s["pr_status"] = "created"
            s["phase"] = "ci-check"
        store.update(_record_pr)
        return "allow", ""

    # Track CI checks
    if _is_ci_check(command):
        def _record_ci(s: dict) -> None:
            s["ci_check_executed"] = True
            if "All checks were successful" in output:
                s["ci_status"] = "passed"
                s["phase"] = "report"
            elif "Some checks were not successful" in output or "failed" in output.lower():
                s["ci_status"] = "failed"
                # Keep phase as ci-check
        store.update(_record_ci)
        return "allow", ""

    return "allow", ""


# Legacy: old guardrail.py calls validate() with a Path
def validate(hook_input: dict, state_path=None) -> tuple[str, str]:
    """Legacy compatibility shim for old guardrail.py."""
    store = StateStore(state_path or DEFAULT_STATE_PATH)
    return validate_pre(hook_input, store)
