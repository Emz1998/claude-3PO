from typing import Any, Literal
import sys
from pathlib import Path

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from utils.state import set_state, get_state  # type: ignore


def set_tool_call_status(
    hook_event_name: str,
    tool_name: str,
    state_path: Path,
) -> None:
    tool_state = get_state("tool_call_status", state_path) or {}
    tool_state["tool_name"] = tool_name
    if hook_event_name == "PreToolUse":
        tool_state["status"] = "in_progress"
        set_state(
            "tool_call_status",
            tool_state,
            state_path,
        )
    elif hook_event_name == "PostToolUse":
        tool_state["status"] = "completed"
        set_state(
            "tool_call_status",
            tool_state,
            state_path,
        )

    return None


def set_tool_call_decision(
    hook_event_name: str,
    tool_name: str,
    decision: Literal["allow", "block"],
    state_path: Path,
) -> None:
    tool_call_status = get_state("tool_call_status", state_path) or {}
    if hook_event_name != "PreToolUse":
        return
    if tool_call_status["tool_name"] != tool_name:
        return
    tool_call_status["decision"] = decision

    set_state(
        "tool_call_status",
        tool_call_status,
        state_path,
    )
    return None


def set_additional_tool_call_data(
    hook_event_name: str,
    tool_name: str,
    data: dict[str, Any],
    state_path: Path,
) -> None:
    tool_call_status = get_state("tool_call_status", state_path) or {}
    if hook_event_name != "PreToolUse":
        return
    if tool_call_status["tool_name"] != tool_name:
        return
    tool_call_status = get_state("tool_call_status", state_path) or {}
    tool_call_status.update(data)
    set_state(
        "tool_call_status",
        tool_call_status,
        state_path,
    )
    return None


def set_write_tool_call_state(
    hook_event_name: str,
    tool_name: str,
    file_path: str,
    decision: Literal["allow", "block"],
    state_path: Path,
) -> None:
    tool_call_status = get_state("tool_call_status", state_path) or {}
    additional_data = {
        "file_path": file_path,
    }
    if hook_event_name != "PreToolUse":
        return
    if tool_call_status["tool_name"] != tool_name:
        return
    set_additional_tool_call_data(
        hook_event_name, tool_name, additional_data, state_path
    )
    set_tool_call_decision(hook_event_name, tool_name, decision, state_path)
    return None


def set_read_tool_call_state(
    hook_event_name: str,
    tool_name: str,
    data: dict[str, Any],
    state_path: Path,
) -> None:
    set_additional_tool_call_data(hook_event_name, tool_name, data, state_path)
    return None


def set_out_of_scope(
    out_of_scope_name: str,
    state_path: Path,
) -> None:
    out_of_scope = get_state("out_of_scope", state_path) or []
    out_of_scope.append(out_of_scope_name)
    set_state(
        "out_of_scope",
        out_of_scope,
        state_path,
    )
    return None


def set_no_coding_scope_state(
    state_path: Path,
) -> None:
    scope = get_state("scope", state_path) or {}
    scope["coding"] = False
    set_state(
        "scope",
        scope,
        state_path,
    )
    return None


def set_hook_resolution_state(
    hook_resolution: Literal["blocked", "allowed"],
    state_path: Path,
) -> None:
    tool_call_status = get_state("tool_call_status", state_path) or {}
    tool_call_status["resolution"] = hook_resolution
    set_state(
        "tool_call_status",
        hook_resolution,
        state_path,
    )


def set_task_status(
    dependency_id: str,
    status: Literal["not_started", "in_progress", "completed", "blocked"],
    state_path: Path,
) -> None:
    dependencies_status = get_state("dependencies_status", state_path) or {}
    dependencies_status[dependency_id] = status
    set_state("dependencies_status", dependencies_status, state_path)
    return None


if __name__ == "__main__":
    state_path = Path(".claude/hooks/states/subagents/main-agent.json")
    # set_write_tool_call_state("PostToolUse", "Write", "test.txt", state_path)
    set_scope_state("coding", True, state_path)
