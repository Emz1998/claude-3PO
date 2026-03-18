from workflow.models.hook_input import PreToolUseInput, PostToolUseInput
from typing import Any


def normalize_block_data(
    raw_tool_name: str, raw_tool_input: dict[str, Any]
) -> tuple[str, Any]:
    raw_tool_name = raw_tool_name.lower()

    match raw_tool_name:
        case "skill":
            skill_name = raw_tool_input.get("skill", None)
            return (raw_tool_name, skill_name)
        case "agent":
            agent_name = raw_tool_input.get("subagent_type", None)
            return (raw_tool_name, agent_name)
        case "write" | "edit":
            file_path = raw_tool_input.get("file_path", None)
            return (raw_tool_name, file_path)
        case "bash":
            raw_tool_name = "command"
            command = raw_tool_input.get("command", None)
            return (raw_tool_name, command)

        case "exitplanmode":
            return (raw_tool_name, None)

        case _:
            raise ValueError(f"Invalid tool name: {raw_tool_name}")
