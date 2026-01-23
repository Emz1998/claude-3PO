#!/usr/bin/env python3
"""Delete workflow cache file."""


from datetime import datetime
from math import exp
import sys
from pathlib import Path
import json
from typing import Any, Literal

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import read_stdin_json  # type: ignore
from utils.cache import set_cache, get_cache  # type: ignore
from utils.output import block_response, block_stoppage, allow_stoppage, print_and_exit  # type: ignore
from utils.project import build_project_path, BASE_PATH  # type: ignore

from roadmap.utils import (
    get_current_version,
    get_test_strategy,
)

# Test Strategy
TEST_STRATEGY = get_test_strategy() or "TDD"


# STATES PATHS
SUBAGENTS_STATE_PATH = Path(".claude/hooks/states/subagents.json")
MAIN_STATE_PATH = Path(".claude/hooks/states/main.json")
MAIN_AGENT_STATE_PATH = Path(".claude/hooks/states/subagents/main-agent.json")
CODING_PHASE_STATE_PATH = Path(".claude/hooks/states/phases/coding.json")

session_id = get_cache("session_id", MAIN_STATE_PATH)

PROJECT_BASE_PATH = BASE_PATH


# REPORT_FILE_PATH
REPORT_FILE_PATH = (
    PROJECT_BASE_PATH
    / "codebase-status"
    / f"codebase-status_{session_id}_{datetime.now().strftime('%m%d%Y')}.md"
)

# VALID_SUBAGENTS

VALID_SUBAGENTS = [
    "codebase-explorer",
    "backend-engineer",
    "quality-assurance",
    "devops",
    "architect",
    "research",
    "meta",
    "project-management",
    "design",
    "core",
]


def set_active_tool(hook_input: dict[str, Any]) -> None:
    tool_name = hook_input.get("tool_name", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_status = {
        "name": tool_name,
        "status": "inactive",
    }
    if hook_event_name == "PreToolUse":
        tool_status["status"] = "active"
        set_cache("recent_tool_status", tool_status, MAIN_AGENT_STATE_PATH)
    elif hook_event_name == "PostToolUse":
        tool_status["status"] = "inactive"
        set_cache("recent_tool_status", tool_status, MAIN_AGENT_STATE_PATH)


def get_completed_subagents() -> list[str]:
    subagents_status = get_cache("subagents_status", CODING_PHASE_STATE_PATH)
    return [
        subagent["name"]
        for subagent in subagents_status
        if subagent["status"] == "completed"
    ]


def validate_execution_order(
    current_subagent: Literal[
        "test-engineer",
        "version-manager",
        "main-agent",
        "code-reviewer",
        "code-specialist",
    ],
) -> None:
    last_completed_subagent = get_completed_subagents()[-1]
    test_strategy = get_test_strategy()
    version_manager_invocation = 0

    if last_completed_subagent is None:
        return

    subagent_order = [
        "test-engineer",
        "version-manager",
        "main-agent",
        "code-reviewer",
        "version-manager",
    ]

    if not test_strategy == "TDD":
        subagent_order = [
            "main-agent",
            "test-engineer",
            "version-manager",
            "code-reviewer",
            "version-manager",
        ]

    if current_subagent == "version-manager":
        version_manager_invocation += 1

    version_manager_exception = (
        current_subagent == "version-manager" and version_manager_invocation > 1
    )

    current_subagent_index = (
        subagent_order.index(current_subagent) if not version_manager_exception else 4
    )

    last_index = subagent_order.index(last_completed_subagent)
    print(last_index)
    expected_subagent = subagent_order[last_index + 1]
    print(expected_subagent)

    subagent_invocation_state = {
        "status": "success",
        "reason": "successful_transition",
        "message": f"Subagent {current_subagent} was invoked successfully.",
        "invoked": current_subagent,
        "expected": expected_subagent,
        "last_completed_subagent": last_completed_subagent,
    }

    set_cache("subagent_invocation", subagent_invocation_state, MAIN_AGENT_STATE_PATH)

    if last_completed_subagent not in subagent_order:
        set_cache(
            "subagent_invocation", subagent_invocation_state, MAIN_AGENT_STATE_PATH
        )
        return

    if current_subagent_index > last_index and current_subagent_index != last_index + 1:
        subagent_invocation_state["status"] = "failed"
        subagent_invocation_state["reason"] = "forward_transition_error"

        skipped_subagents = [
            skipped_subagent
            for skipped_subagent in subagent_order[
                last_index + 1 : current_subagent_index
            ]
        ]

        print(skipped_subagents)
        subagent_invocation_state["message"] = (
            f'Subagent(s) "{", ".join(skipped_subagents)}"were skipped. Expected "{expected_subagent}" but "{current_subagent}" was invoked.'
        )
        set_cache(
            "subagent_invocation", subagent_invocation_state, MAIN_AGENT_STATE_PATH
        )
        return

    if current_subagent_index < last_index:
        subagent_invocation_state["status"] = "failed"
        subagent_invocation_state["reason"] = "backward_transition_error"
        subagent_invocation_state["message"] = (
            f"Subagent {current_subagent} was invoked before {last_completed_subagent}."
        )
        set_cache(
            "subagent_invocation", subagent_invocation_state, MAIN_AGENT_STATE_PATH
        )
        return


def validator(hook_input: dict[str, Any]) -> None:
    current_workflow_phase = get_cache("current_workflow_phase", MAIN_STATE_PATH)
    is_test_engineer_done = get_cache("is_test_engineer_done", MAIN_AGENT_STATE_PATH)
    if current_workflow_phase != "coding":
        return

    if TEST_STRATEGY != "TDD":
        return

    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    subagent_name = tool_input.get("subagent_type", "")
    if hook_event_name != "PreToolUse":
        return
    if tool_name != "Task":
        return
    if subagent_name != "test-engineer":
        invalid_subagent_invocation = {
            "expected": "test-engineer",
            "received": subagent_name,
        }
        set_cache(
            "invalid_subagent_invocation", invalid_subagent_invocation, MAIN_STATE_PATH
        )

    if not is_test_engineer_done:
        block_response(
            "Test engineer is not done. Please wait for the test engineer to complete."
        )

    set_cache("is_todo_read", True, MAIN_AGENT_STATE_PATH)
    print("Todo file read successfully.")


def is_implement_active() -> bool:
    return get_cache("is_implement_active", MAIN_STATE_PATH)


def subagents_invocation_guardrail(hook_input: dict[str, Any]):
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    subagent_name = tool_input.get("subagent_type", "")

    if hook_event_name != "PreToolUse":
        return
    if tool_name != "Task":
        return


def file_write_guardrail(hook_input: dict[str, Any]) -> None:
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    if tool_name != "Write" or hook_event_name != "PreToolUse":
        return
    file_path = tool_input.get("file_path", "")
    if file_path != str(REPORT_FILE_PATH.absolute()):
        block_response(
            "Invalid file path. Please write the report to the correct path."
        )

    set_cache("is_report_written", True, MAIN_AGENT_STATE_PATH)
    print("Report written successfully.")


def _block_stoppage(hook_input: dict[str, Any]) -> None:
    hook_event_name = hook_input.get("hook_event_name", "")
    is_report_written = get_cache("is_report_written", MAIN_AGENT_STATE_PATH)
    if hook_event_name != "Stop":
        return
    if not is_report_written:
        block_response("Report is not written. Please write the report first.")

    set_cache("is_codebase_explorer_done", True, SUBAGENTS_STATE_PATH)
    print("Codebase explorer completed.")


def main() -> None:
    hook_input = test_bash_tool
    set_active_tool(hook_input)
    # dependencies_guardrail(hook_input)
    file_write_guardrail(hook_input)
    _block_stoppage(hook_input)


if __name__ == "__main__":
    validate_execution_order("main-agent")
