import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, write_file, read_file  # type: ignore

FILE_PATHS = {
    "Task": Path("input-schemas/post_tool/task.log"),
    "Read": Path("input-schemas/post_tool/read.log"),
    "TodoWrite": Path("input-schemas/post_tool/todo_write.log"),
    "EnterPlanMode": Path("input-schemas/post_tool/enter_plan_mode.log"),
    "ExitPlanMode": Path("input-schemas/post_tool/exit_plan_mode.log"),
    "Skill": Path("input-schemas/post_tool/skill.log"),
    "Bash": Path("input-schemas/post_tool/bash.log"),
    "Glob": Path("input-schemas/post_tool/glob.log"),
    "Grep": Path("input-schemas/post_tool/grep.log"),
    "Write": Path("input-schemas/post_tool/write.log"),
    "Edit": Path("input-schemas/post_tool/edit.log"),
    "WebSearch": Path("input-schemas/post_tool/web_search.log"),
    "WebFetch": Path("input-schemas/post_tool/web_fetch.log"),
    "AskUserQuestion": Path("input-schemas/post_tool/ask_user_question.log"),
    "LSP": Path("input-schemas/post_tool/lsp.log"),
    "MultiEdit": Path("input-schemas/post_tool/multi_edit.log"),
}


def write_test_file(input_data: dict, output_path: Path) -> None:
    hook_input = input_data
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(output_path), json.dumps(hook_input, indent=4))
    print(f"Successfully wrote to {output_path}")


def main() -> None:
    hook_input = read_stdin_json()
    tool_name = hook_input.get("tool_name", "")
    write_test_file(hook_input, FILE_PATHS[tool_name])


if __name__ == "__main__":
    main()
