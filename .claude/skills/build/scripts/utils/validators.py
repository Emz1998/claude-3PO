"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

from pathlib import Path
from typing import Literal, get_args, Any
import sys
import tomllib


from scripts.constants import (
    VALID_PR_COMMANDS,
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
)


def load_config() -> dict[str, Any]:
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    return config


def is_pr_commands_allowed(state: dict[str, Any], hook_input: dict) -> str:

    phase = state.get("phase", "")
    """Validate the PR command."""

    tool_name = hook_input.get("tool_name", "")

    if tool_name != "Bash":
        raise ValueError(f"Invalid tool name: {tool_name}")

    if phase != "pr-create":
        return "Skipping, not in PR create phase"

    command = hook_input.get("tool_input", {}).get("command", "")
    if command not in VALID_PR_COMMANDS:
        raise ValueError(f"Invalid PR command: {command}")

    return f"PR command {command} is allowed in phase: {phase}"


def is_file_write_allowed(
    state: dict[str, Any], hook_input: dict, config: dict[str, Any]
) -> str:
    """Validate the code files. If extensions are not supported, raise an error."""

    # ------------------------------------------------
    # Config
    # ------------------------------------------------
    config = load_config()
    plan_file_path = config.get("PLAN_FILE_PATH", "")
    test_file_path = config.get("TEST_FILE_PATH", "")
    code_file_path = config.get("CODE_FILE_PATH", "")
    report_file_path = config.get("REPORT_FILE_PATH", "")

    # ------------------------------------------------
    # Validate the file write
    # ------------------------------------------------
    phase = state.get("phase", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if hook_event_name != "PreToolUse":
        raise ValueError(f"Invalid hook event name: {hook_event_name}")

    if tool_name != "Write":
        raise ValueError(f"Invalid tool name: {tool_name}")

    file_path = tool_input.get("file_path", "")

    if phase not in ("write-plan", "write-test", "write-code", "write-report"):
        raise ValueError(f"File write not allowed in phase: {phase}")

    if phase == "write-plan":
        if file_path != plan_file_path:
            raise ValueError(
                f"Writing in '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed path in {phase} is: {plan_file_path}"
            )

    if phase == "write-test":
        if not any(
            file_path.match(test_pattern) for test_pattern in TEST_FILE_PATTERNS
        ):
            test_files = [test.get("file_path", "") for test in state.get("tests", [])]
            raise ValueError(
                f"Writing test file in the path '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed paths in {phase} are: {test_files}"
            )

    if phase == "write-code":
        if not any(
            file_path.suffix in code_extension for code_extension in CODE_EXTENSIONS
        ):
            code_files = state.get("code_files", [])
            raise ValueError(
                f"Writing code file in the path '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed paths in {phase} are: {code_files}"
            )

    if phase == "write-report":
        if file_path != REPORT_FILE_PATH:
            raise ValueError(
                f"Writing report file in the path '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed path in {phase} is: {REPORT_FILE_PATH}"
            )

    return f"File write allowed in phase: {phase}"


def is_file_edit_allowed(
    hook_input: dict, state: dict[str, Any], config: dict[str, Any]
) -> str:
    phase = state.get("phase", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    """Validate the code files. If extensions are not supported, raise an error."""

    if hook_event_name != "PreToolUse":
        raise ValueError(f"Invalid hook event name: {hook_event_name}")

    if tool_name != "Edit":
        return "Skipping, not an Edit tool"

    file_path = tool_input.get("file_path", "")

    if phase not in ("plan-review", "test-review", "code-review"):
        raise ValueError(f"File edit not allowed in phase: {phase}")

    if phase == "plan-review":
        if file_path != PLAN_FILE_PATH:
            raise ValueError(
                f"Editing plan file for {file_path} is not allowed in phase: {phase}"
            )

    if phase == "test-review":
        if file_path != TEST_FILE_PATH:
            raise ValueError(
                f"Editing test file for {file_path} is not allowed in phase: {phase}"
            )

    if phase == "code-review":
        if file_path != CODE_FILE_PATH:
            raise ValueError(
                f"Editing code file for {file_path} is not allowed in phase: {phase}"
            )

    return f"File edit allowed in phase: {phase}"


def is_agent_allowed(state: dict[str, Any], hook_input: dict) -> str:
    phase = state.get("phase", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if hook_event_name != "PreToolUse":
        raise ValueError(f"Invalid hook event name: {hook_event_name}")

    if tool_name != "Agent":
        return "Skipping, not an Agent tool"

    agent_type = tool_input.get("agent_type", "")

    expected_agents = REQUIRED_AGENTS[phase]

    if agent_type not in expected_agents:
        raise ValueError(f"Invalid agent type: {agent_type}")
    return f"{agent_type} agent is allowed in phase: {phase}"


def validate(hook_input: dict, state: dict[str, Any]) -> tuple[str, str]:

    phase = state.get("phase", "")

    try:
        validators = [
            is_file_write_allowed,
            is_file_edit_allowed,
            is_agent_allowed,
            is_pr_commands_allowed,
        ]

        for validator in validators:
            if validator(state, hook_input):
                return "allow", validator(phase, hook_input)
    except ValueError as e:
        return "block", str(e)
    except Exception as e:
        return "block", str(e)

    return "allow", "All validators passed"


if __name__ == "__main__":
    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "test.txt",
        },
    }
    state = {
        "phase": "write-plan",
    }
    print(validate(hook_input, state))
