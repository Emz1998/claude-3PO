from typing import Any
import sys
from pathlib import Path

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from utils.state import get_state  # type: ignore


def get_tool_call_status(state_path: Path) -> dict[str, Any]:
    return get_state("tool_call_status", state_path)


def get_write_tool_call_status(state_path: Path) -> dict[str, Any]:
    tool_call_status = get_tool_call_status(state_path)
    if tool_call_status["tool_name"] != "Write":
        return {}
    return tool_call_status


def get_out_of_scope_state(state_path: Path) -> list[str]:
    return get_state("out_of_scope", state_path)


if __name__ == "__main__":
    state_path = Path(".claude/hooks/states/subagents/main-agent.json")
    write_tool_call_status = get_write_tool_call_status(state_path)
    print(write_tool_call_status)
