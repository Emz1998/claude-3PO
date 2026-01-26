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
from workflow.utils.state_setters import set_tool_call_status, set_tool_call_decision, set_write_tool_call_state  # type: ignore
from workflow.utils.state_getters import get_tool_call_status, get_out_of_scope_state  # type: ignore
from workflow.utils.guardrails import no_coding_guardrail  # type: ignore
from workflow.tests.hook_tests import test_read_tool, test_write_tool  # type: ignore

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


SubagentType = Literal[
    "test-engineer",
    "version-manager",
    "main-agent",
    "code-reviewer",
    "code-specialist",
]

TDD_SUBAGENT_ORDER = [
    "test-engineer",
    "version-manager",
    "main-agent",
    "code-reviewer",
    "version-manager",
]

NON_TDD_SUBAGENT_ORDER = [
    "main-agent",
    "test-engineer",
    "version-manager",
    "code-reviewer",
    "version-manager",
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


def get_subagent_order(test_strategy: str | None) -> list[str]:
    if test_strategy == "TDD":
        return TDD_SUBAGENT_ORDER
    return NON_TDD_SUBAGENT_ORDER


def create_invocation_state(
    current_subagent: str,
    expected_subagent: str,
    last_completed_subagent: str,
) -> dict[str, str]:
    return {
        "status": "success",
        "reason": "successful_transition",
        "message": f"Subagent {current_subagent} was invoked successfully.",
        "invoked": current_subagent,
        "expected": expected_subagent,
        "last_completed_subagent": last_completed_subagent,
    }


def save_invocation_state(state: dict[str, str]) -> None:
    set_cache("subagent_invocation", state, MAIN_AGENT_STATE_PATH)


def check_forward_transition_error(
    state: dict[str, str],
    current_index: int,
    last_index: int,
    subagent_order: list[str],
    current_subagent: str,
    expected_subagent: str,
) -> bool:
    is_forward_skip = current_index > last_index and current_index != last_index + 1
    if not is_forward_skip:
        return False

    skipped = subagent_order[last_index + 1 : current_index]
    state["status"] = "failed"
    state["reason"] = "forward_transition_error"
    state["message"] = (
        f'Subagent(s) "{", ".join(skipped)}" were skipped. '
        f'Expected "{expected_subagent}" but "{current_subagent}" was invoked.'
    )
    return True


def check_backward_transition_error(
    state: dict[str, str],
    current_index: int,
    last_index: int,
    current_subagent: str,
    last_completed_subagent: str,
) -> bool:
    if current_index >= last_index:
        return False

    state["status"] = "failed"
    state["reason"] = "backward_transition_error"
    state["message"] = (
        f"Subagent {current_subagent} was invoked before {last_completed_subagent}."
    )
    return True


def validate_execution_order(current_subagent: SubagentType) -> None:
    completed_subagents = get_completed_subagents()
    if not completed_subagents:
        return

    last_completed_subagent = completed_subagents[-1]
    if last_completed_subagent is None:
        return

    test_strategy = get_test_strategy()
    subagent_order = get_subagent_order(test_strategy)

    if last_completed_subagent not in subagent_order:
        return

    current_index = subagent_order.index(current_subagent)
    last_index = subagent_order.index(last_completed_subagent)
    expected_subagent = subagent_order[last_index + 1]

    state = create_invocation_state(
        current_subagent, expected_subagent, last_completed_subagent
    )

    check_forward_transition_error(
        state,
        current_index,
        last_index,
        subagent_order,
        current_subagent,
        expected_subagent,
    )
    check_backward_transition_error(
        state, current_index, last_index, current_subagent, last_completed_subagent
    )

    save_invocation_state(state)


def setup_validator() -> None:
    return None


def setup_state_logger(hook_input: dict[str, Any]) -> None:

    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    out_of_scope = get_out_of_scope_state(MAIN_AGENT_STATE_PATH)

    decision = (
        no_coding_guardrail(file_path, MAIN_AGENT_STATE_PATH)
        if "coding" in out_of_scope
        else "allow"
    )

    set_tool_call_status(hook_event_name, tool_name, MAIN_AGENT_STATE_PATH)
    set_write_tool_call_state(
        hook_event_name, tool_name, file_path, decision, MAIN_AGENT_STATE_PATH
    )

    return None


def is_implement_active() -> bool:
    return get_cache("is_implement_active", MAIN_STATE_PATH)


def setup_guardrails(hook_input: dict[str, Any]) -> None:
    


def main() -> None:
    hook_input = test_write_tool
    set_active_tool(hook_input)
    # dependencies_guardrail(hook_input)
    # file_write_guardrail(hook_input)
    # _block_stoppage(hook_input)


if __name__ == "__main__":
    setup_state_logger(test_write_tool)
