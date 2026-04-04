"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.config import DEFAULT_STATE_PATH, PLAN_REVIEW_THRESHOLD, PLAN_REVIEW_MAX
from workflow.state_store import StateStore
from workflow.logger import log


# ---------------------------------------------------------------------------
# Agent recording
# ---------------------------------------------------------------------------


def record_agent(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    """Append an agent entry as 'running' to state.agents[]."""

    def _update(state: dict) -> None:
        state.setdefault("agents", []).append(
            {
                "agent_type": agent_type,
                "status": "running",
                "tool_use_id": tool_use_id,
            }
        )

    store.update(_update)


def record_agent_phase_advance(store: StateStore) -> None:
    """Advance phase from write-code to validate (when Validator is launched)."""

    def _advance(s: dict) -> None:
        s["phase"] = "validate"

    store.update(_advance)


# ---------------------------------------------------------------------------
# Write recording (PostToolUse Write/Edit)
# ---------------------------------------------------------------------------


def record_write(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle PostToolUse Write/Edit — track plan writes, test files, report writes."""
    from workflow.guards.write_guard import (
        get_file_path,
        is_code_file,
        is_plan_file,
        is_report_file,
        is_test_file,
    )

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    file_path = get_file_path(hook_input)
    phase = state.get("phase", "")

    # write-codebase → plan: advance when CODEBASE.md is written
    if phase == "write-codebase" and file_path.endswith("CODEBASE.md"):

        def _advance_codebase(s: dict) -> None:
            s["codebase_written"] = True
            s["phase"] = "plan"

        store.update(_advance_codebase)
        return "allow", ""

    # Track all written files for read_guard's files_written constraint
    if file_path:

        def _track_written(s: dict) -> None:
            files = s.setdefault("files_written", [])
            if file_path not in files:
                files.append(file_path)

        store.update(_track_written)

    # Track plan file writes
    if is_plan_file(file_path) and phase in ("write-plan", "review"):

        def _record_plan(s: dict) -> None:
            s["plan_file"] = file_path
            s["plan_written"] = True
            s["phase"] = "review"

        store.update(_record_plan)
        return "allow", ""

    # Track test file writes
    if is_test_file(file_path) and phase == "write-tests" and is_code_file(file_path):

        def _record_test(s: dict) -> None:
            files = s.setdefault("test_files_created", [])
            if file_path not in files:
                files.append(file_path)

        store.update(_record_test)
        return "allow", ""

    # Handle code writes in ci-check — trigger regression to write-code
    if is_code_file(file_path) and not is_test_file(file_path) and phase == "ci-check":

        def _regress(s: dict) -> None:
            s["phase"] = "write-code"
            s["ci_status"] = "pending"
            s["ci_check_executed"] = False
            s["validation_result"] = None
            s["pr_status"] = "pending"

        store.update(_regress)
        return "allow", ""

    # Track report writes
    if is_report_file(file_path) and phase == "report":

        def _complete_report(s: dict) -> None:
            s["report_written"] = True
            s["phase"] = "completed"

        store.update(_complete_report)
        return "allow", ""

    return "allow", ""


# ---------------------------------------------------------------------------
# Bash recording (PostToolUse Bash)
# ---------------------------------------------------------------------------


def _parse_ci_output(output: str) -> str:
    """Parse gh pr checks output to determine CI status.

    Returns "passed", "failed", or "pending".

    gh pr checks output format: "name\\tstatus\\tduration\\turl\\t" per line.
    Status values: pass, fail, pending, queued, in_progress, etc.
    Uses simple tab-delimited keyword search — no column-position dependency.
    """
    if not output or not output.strip():
        log("record_bash:pending", output=output)
        return "pending"

    # Any line with a fail status → failed
    if "\tfail" in output:
        log("record_bash:failed", output=output)
        return "failed"

    # Any line with pending/queued/in_progress → still pending
    if (
        "\tpending" in output
        or "\tqueued" in output
        or "\tin_progress" in output
        or "\twaiting" in output
    ):
        log("record_bash:pending", output=output)
        return "pending"

    # If we see pass statuses and nothing failed/pending → passed
    if "\tpass" in output:
        log("record_bash:pass", output=output)
        return "passed"

    # Summary format fallback (gh pr checks --watch)
    if "All checks were successful" in output:
        log("record_bash:all_checks_successful", output=output)
        return "passed"
    if "Some checks were not successful" in output:
        log("record_bash:some_checks_not_successful", output=output)
        return "failed"

    log("record_bash:pending", output=output)
    return "pending"


def record_bash(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle Bash PostToolUse — track test runs, PR creation, CI checks."""
    from workflow.guards.bash_guard import is_ci_check, is_pr_command, is_test_run

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")
    tool_response = hook_input.get("tool_response", {})
    output = tool_response.get("stdout", "") or tool_response.get("output", "")
    phase = state.get("phase", "")

    # Track test-run commands
    if is_test_run(command):
        store.set("test_run_executed", True)
        return "allow", ""

    # Track PR creation
    if is_pr_command(command) and phase == "pr-create":

        def _record_pr(s: dict) -> None:
            s["pr_status"] = "created"
            s["phase"] = "ci-check"

        store.update(_record_pr)
        return "allow", ""

    # Track CI checks
    if is_ci_check(command):

        def _record_ci(s: dict) -> None:
            ci_result = _parse_ci_output(output)
            if ci_result == "passed":
                s["ci_check_executed"] = True
                s["ci_status"] = "passed"
                s["phase"] = "report"
            elif ci_result == "failed":
                s["ci_check_executed"] = True
                s["ci_status"] = "failed"
            # "pending" → don't set ci_check_executed, allow re-check

        store.update(_record_ci)
        return "allow", ""

    return "allow", ""


# ---------------------------------------------------------------------------
# Task recording
# ---------------------------------------------------------------------------


def record_task_created(store: StateStore) -> None:
    """Increment tasks_created counter."""

    def _increment(s: dict) -> None:
        s["tasks_created"] = s.get("tasks_created", 0) + 1

    store.update(_increment)


# ---------------------------------------------------------------------------
# SubagentStop recording (replaces review_guard.handle)
# ---------------------------------------------------------------------------


def parse_scores(text: str) -> dict[str, int | None]:
    """Extract confidence and quality scores from free-form reviewer text."""
    confidence = None
    quality = None

    def _last_score(label: str) -> int | None:
        patterns = [
            rf"{label}\s*(?:score|rating)?\s*(?:\*\*)?\s*[:=\-]?\s*(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
            rf"{label}\s*(?:score|rating)?\s+(?:is\s+)?(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
        ]
        matches: list[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        if not matches:
            return None
        return int(matches[-1])

    confidence = _last_score("confidence")
    quality = _last_score("quality")
    return {"confidence": confidence, "quality": quality}


def _required_explore_agents(state: dict) -> dict[str, int]:
    """Return the required agent types/counts for explore phase."""
    required = {}
    if not state.get("skip_explore"):
        required["Explore"] = 3
    if not state.get("skip_research"):
        required["Research"] = 2
    return required


def _count_completed(agents: list[dict], agent_type: str) -> int:
    return sum(
        1
        for a in agents
        if a.get("agent_type") == agent_type and a.get("status") == "completed"
    )


def _mark_first_running_completed(agents: list[dict], agent_type: str) -> None:
    for a in agents:
        if a.get("agent_type") == agent_type and a.get("status") == "running":
            a["status"] = "completed"
            break


def _extract_verdict(message: str) -> str:
    """Extract Pass/Fail from the last non-empty line of an agent message."""
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return "Fail"
    last = lines[-1]
    if last == "Pass":
        return "Pass"
    return "Fail"


def record_subagent_stop(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle SubagentStop: mark agent completed, auto-advance phases.

    Always returns ("allow", "") — never blocks a subagent from stopping.
    """
    agent_type: str = hook_input.get("agent_type", "")
    last_message: str = hook_input.get("last_assistant_message", "")

    def _process(state: dict) -> None:
        if not state.get("workflow_active"):
            return

        phase = state.get("phase", "")
        agents = state.get("agents", [])

        # Mark first matching running agent as completed
        _mark_first_running_completed(agents, agent_type)

        # Explore / Research: check if all done -> advance to write-codebase
        if agent_type in ("Explore", "Research") and phase == "explore":
            required = _required_explore_agents(state)
            all_done = all(
                _count_completed(agents, atype) >= cnt
                for atype, cnt in required.items()
            )
            if all_done:
                state["phase"] = "write-codebase"

        # Plan: advance to write-plan
        elif agent_type == "Plan" and phase == "plan":
            state["phase"] = "write-plan"

        # PlanReview: parse scores, advance or iterate
        elif agent_type == "PlanReview" and phase == "review":
            scores = parse_scores(last_message)
            state["plan_review_scores"] = scores
            iteration = state.get("plan_review_iteration", 0)

            passed = (
                scores["confidence"] is not None
                and scores["quality"] is not None
                and scores["confidence"] >= PLAN_REVIEW_THRESHOLD["confidence"]
                and scores["quality"] >= PLAN_REVIEW_THRESHOLD["quality"]
            )

            if passed:
                state["plan_review_status"] = "approved"
                state["phase"] = "present-plan"
            elif iteration + 1 >= PLAN_REVIEW_MAX:
                state["plan_review_status"] = "max_iterations_reached"
                state["plan_review_iteration"] = iteration + 1
                state["phase"] = "failed"
            else:
                state["plan_review_status"] = "revision_needed"
                state["plan_review_iteration"] = iteration + 1

        # TestReviewer: Parse Pass/Fail -> advance or stay
        elif agent_type == "TestReviewer" and phase == "write-tests":
            verdict = _extract_verdict(last_message)
            if verdict == "Pass":
                state["test_review_result"] = "Pass"
                state["phase"] = "write-code"
            else:
                state["test_review_result"] = "Fail"

        # Validator: Parse Pass/Fail -> advance or return to write-code
        elif agent_type == "Validator" and phase == "validate":
            verdict = _extract_verdict(last_message)
            if verdict == "Pass":
                state["validation_result"] = "Pass"
                state["phase"] = "pr-create"
            else:
                state["validation_result"] = "Fail"
                state["phase"] = "write-code"

    store.update(_process)
    return "allow", ""


# ---------------------------------------------------------------------------
# ExitPlanMode recording (PostToolUse ExitPlanMode / SessionStart:clear)
# ---------------------------------------------------------------------------


def advance_after_plan_approval(store: StateStore) -> str | None:
    """Determine and set the next phase after user approves the plan.

    Returns the next phase name, or None if no advancement needed.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return None
    if state.get("workflow_type") == "plan":
        return None

    story_id = state.get("story_id")
    tdd = state.get("tdd", False)

    if story_id:
        next_phase = "task-create"
    elif tdd:
        next_phase = "write-tests"
    else:
        next_phase = "write-code"

    store.set("phase", next_phase)
    return next_phase


def record_exit_plan_mode(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """PostToolUse ExitPlanMode: advance phase based on workflow type."""
    state = store.load()
    if state.get("phase") != "present-plan":
        return "allow", ""
    advance_after_plan_approval(store)
    return "allow", ""


# ---------------------------------------------------------------------------
# Agent recording from hook input (PreToolUse Agent)
# ---------------------------------------------------------------------------


def record_agent_from_hook(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Record an agent launch from raw hook_input. Always returns allow."""
    tool_input = hook_input.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "")
    tool_use_id = hook_input.get("tool_use_id", "")

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    if agent_type == "Validator" and state.get("phase") == "write-code":
        record_agent_phase_advance(store)

    record_agent(store, agent_type, tool_use_id)
    return "allow", ""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    env = os.environ.get("RECORDER_STATE_PATH")
    return Path(env) if env else DEFAULT_STATE_PATH


def _dispatch(hook_input: dict, state_path: Path) -> tuple[str, str]:
    store = StateStore(state_path)
    event = hook_input.get("hook_event_name", "")
    tool = hook_input.get("tool_name", "")

    if event == "PreToolUse":
        if tool == "Agent":
            return record_agent_from_hook(hook_input, store)

    if event == "PostToolUse":
        if tool in ("Write", "Edit"):
            return record_write(hook_input, store)
        if tool == "Bash":
            return record_bash(hook_input, store)
        if tool == "ExitPlanMode":
            return record_exit_plan_mode(hook_input, store)

    if event == "TaskCreated":
        record_task_created(store)
        return "allow", ""

    if event == "SubagentStop":
        return record_subagent_stop(hook_input, store)

    return "allow", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Workflow recorder hook")
    parser.add_argument("--hook-input", type=str, help="JSON hook input string")
    args = parser.parse_args()

    if not args.hook_input:
        parser.print_help()
        sys.exit(1)

    try:
        hook_input = json.loads(args.hook_input)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    state_path = _state_path()
    decision, _ = _dispatch(hook_input, state_path)
    print(decision)
    sys.exit(0)


if __name__ == "__main__":
    main()
