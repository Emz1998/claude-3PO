import sys

from pathlib import Path

import shutil


sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.stdin import read_stdin_json  # type: ignore


def main() -> None:
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "PostToolUse":
        return
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Write":
        return
    hook_file_path = hook_input.get("file_path", "")
    hook_parent_dir_path = Path(hook_file_path).parent
    hook_file_name = Path(hook_file_path).name
    original_plans_dir_path = "/home/emhar/.claude/plans"

    if not Path(hook_file_path).exists():
        print(f"Hook file path does not exist: {hook_file_path}")
        return

    if str(hook_parent_dir_path) != original_plans_dir_path:
        return

    mirrored_dir_path = Path.cwd() / ".claude/plans"
    mirrored_dir_path.mkdir(parents=True, exist_ok=True)

    for f in mirrored_dir_path.iterdir():
        f.unlink()

    new_mirrored_path = mirrored_dir_path / hook_file_name
    shutil.copy2(hook_file_path, new_mirrored_path)


if __name__ == "__main__":
    main()
