import sys
import json
import subprocess
from pathlib import Path
from filelock import FileLock

sys.path.append(str(Path(__file__).parent.parent.parent))
from workflow.hook import Hook  # type: ignore
from workflow.session_state import SessionState  # type: ignore
from workflow.lib.file_manager import FileManager  # type: ignore

TASK_DATA_FILE_PATH = Path(__file__).parent / "tasks.json"
LOCK = FileLock(TASK_DATA_FILE_PATH.with_suffix(".lock"))


def get_tasks(story_id: str) -> list[dict]:
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


def validate_match(tasks: list[dict], raw_input: dict) -> tuple[bool, str]:
    subject = raw_input["tool_input"]["subject"]
    description = raw_input["tool_input"]["description"]

    for task in tasks:
        title_match = task["title"] == subject
        description_match = task["description"] == description

        if title_match and description_match:
            return True, "Task matches"

        if not title_match and not description_match:
            return (
                False,
                f"Task title '{task['title']}' and description '{task['description']}' do not match '{subject}' and '{description}' respectively",
            )
        if not title_match:
            return False, f"Task title '{task['title']}' does not match '{subject}'"
        if not description_match:
            return (
                False,
                f"Task description '{task['description']}' does not match '{description}'",
            )

    return False, "No matching task found"


def load_tasks() -> list[dict]:
    with LOCK:
        try:
            loaded_tasks = TASK_DATA_FILE_PATH.read_text()
            return json.loads(loaded_tasks)
        except (json.JSONDecodeError, FileNotFoundError):
            return []


def save_tasks(tasks: list[dict]) -> None:
    with LOCK:
        TASK_DATA_FILE_PATH.write_text(json.dumps(tasks))


def get_last_task_id(tasks: list[dict]) -> int:
    if not tasks:
        return 0
    return tasks[-1]["taskId"]


def convert_task_id_to_index(task_id: str) -> int:
    task_key = task_id

    number = int(task_key.split("-")[1])

    return number


def add_task(subject: str, description: str) -> None:
    task_id = get_last_task_id(load_tasks()) + 1
    raw_input = {
        "taskId": task_id,
        "subject": subject,
        "description": description,
    }
    tasks = load_tasks()
    tasks.append(raw_input)
    save_tasks(tasks)


def task_create_guardrail(raw_input: dict, session: SessionState) -> None:

    story_id = session.story_id
    tasks = get_tasks(story_id)

    is_valid, reason = validate_match(tasks, raw_input)
    if not is_valid:
        Hook.block(reason)

    add_task(
        raw_input["tool_input"]["subject"],
        raw_input["tool_input"]["description"],
    )


def validate_blocked_by(
    raw_task_id: str,
    raw_blocked_by: str,
    tasks: list[dict],
) -> tuple[bool, str]:
    for task in tasks:
        task_id = convert_task_id_to_index(task["key"])
        blocked_by = convert_task_id_to_index(task["blocked_by"])

        if int(raw_task_id) != task_id:
            continue

        if int(raw_blocked_by) != blocked_by:
            return (
                False,
                f"Wrong dependency for task {task['taskId']}. Expected {blocked_by}, got {raw_blocked_by}.",
            )
    return True, "All dependencies are valid"


def task_update_guardrail(raw_input: dict, session: SessionState) -> None:

    story_id = session.story_id
    tasks = get_tasks(story_id)

    raw_task_id = raw_input["tool_input"]["taskId"]
    raw_blocked_by = raw_input["tool_input"]["addBlockedBy"]

    is_valid, reason = validate_blocked_by(
        raw_task_id,
        raw_blocked_by,
        tasks,
    )
    if not is_valid:
        Hook.block(reason)


def main():
    raw_input = Hook.read_stdin()
    session = SessionState("123")

    tool_name = raw_input.get("tool_name", "")
    if not tool_name:
        raise ValueError("Tool name is required")

    match tool_name:
        case "TaskCreate":
            task_create_guardrail(raw_input, session)
        case "TaskUpdate":
            task_update_guardrail(raw_input, session)
        case _:
            raise ValueError(f"Invalid tool name: {tool_name}")


if __name__ == "__main__":
    main()
