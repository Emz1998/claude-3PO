import sys
import json
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from workflow.hook import Hook  # type: ignore
from workflow.session_state import SessionState  # type: ignore
from workflow.state_store import StateStore  # type: ignore


def get_tasks(story_id: str) -> list[dict]:
    try:
        result = subprocess.run(
            [
                "python3",
                "github_project/project_manager.py",
                "list",
                "--story",
                story_id,
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def validate_match(tasks: list[dict], raw_input: dict) -> tuple[bool, str]:
    subject = raw_input["tool_input"]["subject"]
    description = raw_input["tool_input"]["description"]

    for task in tasks:
        if task["title"] == subject and task["description"] == description:
            return True, "Task matches"

    expected = "\n".join(
        f"- title: {t['title']} | description: {t['description']}" for t in tasks
    )
    return (
        False,
        f"Task does not match any expected task.\nExpected one of:\n{expected}",
    )


def task_create_guardrail(raw_input: dict, session: SessionState) -> None:
    story_id = session.story_id
    if not story_id:
        Hook.block("No active story found in session. Cannot validate task.")
    tasks = get_tasks(story_id)

    is_valid, reason = validate_match(tasks, raw_input)
    if not is_valid:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }
        Hook.advanced_output(output)


def convert_task_id_to_index(task_id: str) -> int:
    return int(task_id.split("-")[1])


def validate_task_list(
    raw_tasks: list[dict],
    tasks: list[dict],
) -> tuple[bool, str]:
    if all(
        any(
            raw_task["subject"] == task["title"]
            and raw_task["blockedBy"] == task["blocked_by"]
            for task in tasks
        )
        for raw_task in raw_tasks
    ):
        return True, "Task list matches"

    expected = "\n".join(
        f"- title: {t['title']} | description: {t['description']}" for t in tasks
    )
    return (
        False,
        f"Task does not match any expected task.\nExpected one of:\n{expected}",
    )


def main():
    raw_input = Hook.read_stdin()
    session = SessionState(raw_input.get("session_id", ""))

    tool_name = raw_input.get("tool_name", "")
    if not tool_name:
        raise ValueError("Tool name is required")

    match tool_name:
        case "TaskCreate":
            task_create_guardrail(raw_input, session)
        case _:
            raise ValueError(f"Invalid tool name: {tool_name}")


if __name__ == "__main__":
    raw_input = Hook.read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")

    if hook_event_name != "PostToolUse":
        sys.exit(0)

    log_path = Path(__file__).parent / " tasks.log"

    with open(log_path, "a") as f:
        f.write(json.dumps(raw_input, indent=4))
        f.write("\n")
