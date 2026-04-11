#!/usr/bin/env python3
"""Unified PreToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""


import argparse
from pathlib import Path
from typing import Any
import re
import sys


VALID_ACTIONS = ["create", "test", "refactor"]
VALID_HOOK_EVENTS = [
    "pre-tool",
    "post-tool",
    "user-prompt",
    "session-start",
    "session-end",
    "subagent-start",
    "subagent-stop",
    "task-created",
]
VALID_TOOL_NAMES = [
    "bash",
    "edit",
    "write",
    "read",
    "glob",
    "grep",
    "agent",
    "web-fetch",
    "web-search",
    "ask-user-question",
    "exit-plan-mode",
]

HOOK_EVENT_MAP = {
    "pre-tool": "PreToolUse",
    "post-tool": "PostToolUse",
    "user-prompt": "UserPrompt",
    "session-start": "SessionStart",
    "session-end": "SessionEnd",
    "subagent-start": "SubagentStart",
    "subagent-stop": "SubagentStop",
    "task-created": "TaskCreated",
}
FLAG_WITH_VALUE_PATTERN = r"(--\S+)\s+(\S+)"
FLAG_PATTERN = r"(--\S+)"

INSTRUCTIONS_DIR = Path(__file__).parent.parent / "instructions"
INPUT_SCHEMA_DIR = Path(__file__).parent.parent / "input-schemas"
POST_TOOL_DIR = INPUT_SCHEMA_DIR / "post_tool"
PRE_TOOL_DIR = INPUT_SCHEMA_DIR / "pre_tool"


def load_file(file_path: Path) -> str:
    if not file_path.parent.exists():
        INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        raise ValueError(f"Error: File path does not exist: {file_path}")

    with file_path.open(mode="r", encoding="utf-8") as file:
        return file.read()


def get_input_schema(hook_event: str, tool_name: str) -> str:
    if hook_event == "pre-tool":
        schema_path = PRE_TOOL_DIR / f"{tool_name.lower()}.log"
    elif hook_event == "post-tool":
        schema_path = POST_TOOL_DIR / f"{tool_name.lower()}.log"
    else:
        raise ValueError(
            f"Error: Invalid hook event. Valid hook events are {VALID_HOOK_EVENTS}"
        )
    with schema_path.open(mode="r", encoding="utf-8") as file:
        return file.read().strip()


def load_instructions(action: str) -> str:
    if action == "create":
        return load_file(INSTRUCTIONS_DIR / "create.md")
    elif action == "test":
        return load_file(INSTRUCTIONS_DIR / "test.md")
    elif action == "refactor":
        return load_file(INSTRUCTIONS_DIR / "refactor.md")
    else:
        raise ValueError(f"Error: Invalid action. Valid actions are {VALID_ACTIONS}")


def get_flags(prompt: str) -> dict[str, str]:
    result = {
        key[2:]: value  # remove first 2 characters "--"
        for key, value in re.findall(r"(--\S+)\s+(\S+)", prompt)
    }
    return result


def get_user_instructions(prompt: str) -> str:
    for key, value in get_flags(prompt).items():
        prompt.replace(key, "").strip()
        prompt.replace(value, "").strip()

    if not prompt:
        raise ValueError("Error: No instructions found in prompt")
    return prompt


def get_hook_event(prompt: str) -> str | None:
    flags = get_flags(prompt)
    action = get_action(prompt)
    if action != "test":
        return None
    if not flags:
        raise ValueError("Error: No hook event found in prompt")
    hook_event = flags.get("hook-event", "")
    if not hook_event:
        raise ValueError("Error: No hook event found in prompt")
    if hook_event not in VALID_HOOK_EVENTS:
        raise ValueError(
            f"Error: Invalid hook event. Valid hook events are {VALID_HOOK_EVENTS}"
        )
    return hook_event


def get_hook_file_path(prompt: str) -> str | None:
    flags = get_flags(prompt)
    action = get_action(prompt)
    if action != "test":
        return None
    if not flags:
        raise ValueError("Error: No hook file path found in prompt")
    hook_file_path = flags.get("file-path", "")
    if not hook_file_path:
        raise ValueError("Error: No hook file path found in prompt")
    if not Path(hook_file_path).exists():
        raise ValueError("Error: Hook file path does not exist")
    return hook_file_path


def get_tool_name(prompt: str) -> str | None:
    flags = get_flags(prompt)
    action = get_action(prompt)
    if action != "test":
        return None
    if not flags:
        raise ValueError("Error: No tool name found in prompt")
    tool_name = flags.get("tool-name", "")
    if not tool_name:
        raise ValueError("Error: No tool name found in prompt")
    if tool_name not in VALID_TOOL_NAMES:
        raise ValueError(
            f"Error: Invalid tool name. Valid tool names are {VALID_TOOL_NAMES}"
        )
    return tool_name


def get_action(prompt: str) -> str:
    split_prompt = prompt.split(" ", 1)
    if len(split_prompt) < 1:
        raise ValueError("Error: No action found in prompt")

    action = split_prompt[0].strip()

    if action not in VALID_ACTIONS:
        raise ValueError(f"Error: Invalid action. Valid actions are {VALID_ACTIONS}")
    return action


def get_mapped_hook_event(hook_event: str) -> str:
    if hook_event not in HOOK_EVENT_MAP:
        raise ValueError(
            f"Error: Invalid hook event. Valid hook events are {VALID_HOOK_EVENTS}"
        )
    return HOOK_EVENT_MAP[hook_event]


def build_instructions(
    action: str,
    user_instructions: str,
    hook_event: str | None = None,
    tool_name: str | None = None,
    hook_file_path: str | None = None,
) -> str:
    instructions = load_instructions(action)
    if action != "test":
        formatted_instructions = instructions.format(
            user_instructions=user_instructions
        )
        return formatted_instructions

    if hook_event is None or tool_name is None:
        raise ValueError("Error: Hook event and tool name are required for test action")
    input_schema = get_input_schema(hook_event, tool_name)
    formatted_instructions = instructions.format(
        user_instructions=user_instructions,
        tool_name=tool_name.capitalize(),
        hook_file_path=hook_file_path,
        payload=input_schema,
    )
    return formatted_instructions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "prompt",
        type=str,
        help="The prompt to test or create a hook for",
    )

    args = parser.parse_args()

    prompt = args.prompt

    try:
        action = get_action(prompt)
        user_instructions = get_user_instructions(prompt)
        hook_event = get_hook_event(prompt)
        tool_name = get_tool_name(prompt)
        hook_file_path = get_hook_file_path(prompt)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

    prompt = build_instructions(
        user_instructions=user_instructions,
        action=action,
        hook_event=hook_event,
        tool_name=tool_name,
        hook_file_path=hook_file_path,
    )
    print(prompt)


if __name__ == "__main__":
    main()
