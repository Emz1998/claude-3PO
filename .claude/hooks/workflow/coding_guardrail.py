"""coding_guardrail.py — Coding workflow guardrail CLI hook.

Enforces post-plan implementation workflow using a dedicated `coding_workflow`
namespace inside the shared workflow state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "state.json"
PR_COMMAND_PATTERNS = [r"\bgh\s+pr\s+create\b", r"\bgit\s+push\b"]
TEST_PATH_PATTERNS = [
    re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)"),
    re.compile(r"(^|/)(test_.*\.py|.*_test\.py)$"),
    re.compile(r"(^|/).*\.(test|spec)\.(js|jsx|ts|tsx)$"),
]


def _state_path() -> Path:
    env = os.environ.get("CODING_GUARDRAIL_STATE_PATH")
    return Path(env) if env else DEFAULT_STATE_PATH


def _default_coding_workflow(tdd: bool) -> dict:
    phase = "write-tests" if tdd else "write-code"
    return {
        "coding_workflow_active": True,
        "phase": phase,
        "TDD": tdd,
        "activated_by_exit_plan_mode": True,
        "review": {
            "tests": {
                "review_called": False,
                "status": "pending",
                "last_result": None,
            },
            "validation": {
                "review_called": False,
                "status": "pending",
                "last_result": None,
            },
        },
        "agents": [],
        "tests": {
            "status": "pending",
            "files_created": [],
        },
        "implementation": {
            "status": "pending",
        },
        "pr": {
            "status": "pending",
            "command": None,
        },
    }


def _active_coding_workflow(state: dict) -> dict | None:
    if not state.get("workflow_active", False):
        return None
    workflow = state.get("coding_workflow")
    if not workflow or not workflow.get("coding_workflow_active"):
        return None
    return workflow


def _is_test_file(file_path: str) -> bool:
    if not file_path:
        return False
    normalized = file_path.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in TEST_PATH_PATTERNS)


def _is_code_file(file_path: str) -> bool:
    return Path(file_path).suffix in {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".swift",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".sh",
    }


def _is_pr_command(command: str) -> bool:
    return any(re.search(pattern, command) for pattern in PR_COMMAND_PATTERNS)


def _record_agent(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    def _update(state: dict) -> None:
        workflow = state.get("coding_workflow", {})
        agents = workflow.setdefault("agents", [])
        iteration = 1 + sum(
            1 for agent in agents if agent.get("agent_type") == agent_type
        )
        agents.append(
            {
                "agent_type": agent_type,
                "status": "running",
                "tool_use_id": tool_use_id,
                "iteration": iteration,
            }
        )
        if agent_type == "TestReviewer":
            workflow["review"]["tests"]["review_called"] = True
            workflow["review"]["tests"]["status"] = "under_review"
        elif agent_type == "Validator":
            workflow["phase"] = "validate"
            workflow["implementation"]["status"] = "completed"
            workflow["review"]["validation"]["review_called"] = True
            workflow["review"]["validation"]["status"] = "under_review"
        state["coding_workflow"] = workflow

    store.update(_update)


def _mark_first_running_completed(agents: list[dict], agent_type: str) -> None:
    for agent in agents:
        if agent.get("agent_type") == agent_type and agent.get("status") == "running":
            agent["status"] = "completed"
            break


def _handle_post_exit_plan_mode(store: StateStore) -> tuple[str, str]:
    state = store.load()
    if not state.get("workflow_active", False):
        return "allow", ""

    tdd = bool(state.get("TDD", False))

    def _update(data: dict) -> None:
        data["workflow_type"] = "implement"
        data["coding_workflow"] = _default_coding_workflow(tdd)

    store.update(_update)
    return "allow", ""


def _handle_write_or_edit(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    # if "/.claude/" in file_path or file_path.startswith(".claude/"):
    #     return "allow", ""
    if not _is_code_file(file_path):
        return "allow", ""

    phase = workflow.get("phase")
    is_test_file = _is_test_file(file_path)

    if phase == "write-tests":
        tests_review = workflow["review"]["tests"]
        if not is_test_file:
            if tests_review.get("last_result") == "Fail":
                return (
                    "block",
                    "Cannot write implementation code while TestReviewer result is Fail",
                )
            return (
                "block",
                "Cannot write implementation code before TestReviewer has passed",
            )

        def _update(data: dict) -> None:
            coding = data["coding_workflow"]
            tests = coding["tests"]
            tests["status"] = "created"
            files_created = tests.setdefault("files_created", [])
            if file_path not in files_created:
                files_created.append(file_path)
            review = coding["review"]["tests"]
            if review.get("last_result") == "Fail":
                review["status"] = "pending"
            data["coding_workflow"] = coding

        store.update(_update)
        return "allow", ""

    if phase == "write-code":
        if workflow.get("TDD", False):
            tests_review = workflow["review"]["tests"]
            if not tests_review.get("review_called"):
                return (
                    "block",
                    "Cannot write implementation code before TestReviewer is called",
                )
            if tests_review.get("last_result") != "Pass":
                return (
                    "block",
                    "Cannot write implementation code while TestReviewer result is Fail",
                )
        if is_test_file:
            return "allow", ""

        def _update(data: dict) -> None:
            coding = data["coding_workflow"]
            coding["implementation"]["status"] = "in_progress"
            data["coding_workflow"] = coding

        store.update(_update)
        return "allow", ""

    if phase in {"validate", "pr-create", "completed"} and not is_test_file:
        return "block", f"Cannot modify implementation files during '{phase}' phase"

    return "allow", ""


def _handle_agent(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    agent_type = hook_input.get("tool_input", {}).get("subagent_type", "")
    tool_use_id = hook_input.get("tool_use_id", "")
    phase = workflow.get("phase")

    if phase == "write-tests":
        if agent_type != "TestReviewer":
            if agent_type == "Validator":
                return "block", "Validator is only allowed during validate phase"
            return "block", "Only TestReviewer is allowed during the test review gate"
        if workflow["tests"].get("status") not in {"created", "failing"}:
            return (
                "block",
                "Tests must be written by the main agent before TestReviewer can run",
            )
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    if phase == "validate":
        if agent_type != "Validator":
            return "block", "Only Validator is allowed during validate phase"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    if phase == "write-code":
        if agent_type != "Validator":
            return "block", f"Agent '{agent_type}' not allowed in phase 'write-code'"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    return "block", f"Agent '{agent_type}' not allowed in phase '{phase}'"


def _handle_subagent_stop(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    agent_type = hook_input.get("agent_type", "")
    verdict = hook_input.get("last_assistant_message", "").strip()

    def _update(data: dict) -> None:
        coding = data["coding_workflow"]
        _mark_first_running_completed(coding.get("agents", []), agent_type)

        if agent_type == "TestReviewer":
            review = coding["review"]["tests"]
            if verdict == "Pass":
                review["status"] = "approved"
                review["last_result"] = "Pass"
                coding["tests"]["status"] = "approved"
                coding["phase"] = "write-code"
            else:
                review["status"] = "failing"
                review["last_result"] = "Fail"
                coding["tests"]["status"] = "failing"
                coding["phase"] = "write-tests"

        if agent_type == "Validator":
            review = coding["review"]["validation"]
            if verdict == "Pass":
                review["status"] = "approved"
                review["last_result"] = "Pass"
                coding["implementation"]["status"] = "completed"
                coding["phase"] = "pr-create"
            else:
                review["status"] = "failing"
                review["last_result"] = "Fail"
                coding["phase"] = "write-code"

        data["coding_workflow"] = coding

    store.update(_update)
    return "allow", ""


def _handle_pre_bash(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")
    if not _is_pr_command(command):
        return "allow", ""
    if workflow.get("review", {}).get("validation", {}).get("last_result") != "Pass":
        return "block", "Cannot create PR before validation passes"
    if workflow.get("phase") != "pr-create":
        return "block", "PR commands are only allowed during 'pr-create' phase"
    return "allow", ""


def _handle_post_bash(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")
    if not _is_pr_command(command):
        return "allow", ""

    def _update(data: dict) -> None:
        coding = data["coding_workflow"]
        coding["pr"]["status"] = "created"
        coding["pr"]["command"] = command
        coding["phase"] = "completed"
        data["coding_workflow"] = coding

    store.update(_update)
    return "allow", ""


def _handle_stop(hook_input: dict, store: StateStore) -> tuple[str, str]:
    if hook_input.get("stop_hook_active"):
        return "allow", ""

    state = store.load()
    workflow = _active_coding_workflow(state)
    if not workflow:
        return "allow", ""

    reasons: list[str] = []
    if workflow.get("TDD", False):
        tests_review = workflow["review"]["tests"]
        if not tests_review.get("review_called"):
            reasons.append("test review has not been called")
        elif tests_review.get("last_result") == "Fail":
            reasons.append("tests are failing")
        elif tests_review.get("last_result") != "Pass":
            reasons.append("tests are not approved")

    validation_review = workflow["review"]["validation"]
    if validation_review.get("last_result") == "Fail":
        reasons.append("validation is failing")
    elif validation_review.get("last_result") != "Pass":
        reasons.append("validation has not passed")

    if workflow.get("pr", {}).get("status") != "created":
        reasons.append("PR has not been created")

    if reasons:
        return "block", "Cannot stop: " + ", ".join(reasons)
    return "allow", ""


def _dispatch(hook_input: dict, state_path: Path) -> tuple[str, str]:
    store = StateStore(state_path)
    event = hook_input.get("hook_event_name", "")
    tool = hook_input.get("tool_name", "")

    if event == "PreToolUse":
        if tool == "Agent":
            return _handle_agent(hook_input, store)
        if tool in {"Write", "Edit"}:
            return _handle_write_or_edit(hook_input, store)
        if tool == "Bash":
            return _handle_pre_bash(hook_input, store)

    if event == "PostToolUse":
        if tool == "ExitPlanMode":
            return _handle_post_exit_plan_mode(store)
        if tool == "Bash":
            return _handle_post_bash(hook_input, store)

    if event == "SubagentStop":
        return _handle_subagent_stop(hook_input, store)

    if event == "Stop":
        return _handle_stop(hook_input, store)

    return "allow", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding workflow guardrail hook")
    parser.add_argument("--hook-input", type=str, help="JSON hook input string")
    parser.add_argument(
        "--reason", action="store_true", help="Include block reason in output"
    )
    args = parser.parse_args()

    if not args.hook_input:
        parser.print_help()
        sys.exit(1)

    try:
        hook_input = json.loads(args.hook_input)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    decision, reason = _dispatch(hook_input, _state_path())
    if decision == "allow":
        print("allow")
    else:
        print(f"block, {reason}" if args.reason else "block")
    sys.exit(0)


if __name__ == "__main__":
    main()
