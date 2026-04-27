"""no_coding_guard.py — PreToolUse hook that blocks code edits when forbidden.

Two policies enforced together for every active skill:
  1. If the skill has a "read-only" mode → no code writes ever.
  2. If tasks have not been created yet → no code writes yet.
Non-code files fall through and the hook allows the tool call.
"""

import sys
from pathlib import Path  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from lib.store import StateStore  # type: ignore
from constants import CODE_EXTENSIONS  # type: ignore


def is_code_file(file_path: str) -> bool:
    return file_path.endswith(tuple(CODE_EXTENSIONS))


def get_read_only_skills(config: Config) -> list[str]:
    return config.get_skills_by_mode("read-only")


def is_coding_allowed(
    file_path: str, skill: str, config: Config, state: StateStore
) -> tuple[bool, str] | None:
    # Out of scope: non-code files are never blocked here
    if not is_code_file(file_path):
        return None
    errors: list[str] = []
    # Policy 1: read-only skills (research, explore, …) cannot write code
    if skill in get_read_only_skills(config):
        errors.append("Coding is not allowed if the skill is read-only")
    # Policy 2: code writes require tasks to exist first
    if not state.tasks_created:
        errors.append("Coding is not allowed if tasks are not yet created")
    if errors:
        return False, ", ".join(errors)
    return True, "Coding is allowed"


def main() -> None:
    state = StateStore()
    config = Config()
    # Pull the path the upcoming tool call wants to write/edit
    hook_input = Hook.read_stdin()
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    for skill in state.active_skill_names():
        result = is_coding_allowed(file_path, skill, config, state)
        # None → not a code file; nothing for this guard to enforce
        if result is None:
            return
        allowed, error = result
        if not allowed:
            Hook.block(error)
            return


if __name__ == "__main__":
    main()
