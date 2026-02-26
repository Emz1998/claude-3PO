#!/usr/bin/env python3
"""Inject context into hook output for /build command."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from workflow.sprint_config import SprintConfig
from workflow.sprint_manager import SprintManager
from utils import read_file, read_stdin_json

sys.path.insert(0, str(Path(__file__).parent))
from start_parallel_session import parallel_sessions  # type: ignore


def validate_input(prompt: str) -> bool:
    if not prompt:
        return False
    if not prompt.startswith("/build"):
        return False

    return True


def start_parallel_sessions(prompts: list[str]) -> None:
    parallel_sessions(prompts)


def main() -> None:
    """Inject workflow context into session."""
    # hook_input = read_stdin_json()
    # if not hook_input:
    #     return
    # if hook_input.get("hook_event_name") != "UserPromptSubmit":
    #     return

    prompt = "/build"

    if not validate_input(prompt):
        return

    sprint_manager = SprintManager()
    ready_stories = sprint_manager.get_ready_stories()
    if not ready_stories:
        print("No ready stories found.")
        return

    prompts = [f"'/implement {story}'" for story in ready_stories]
    print(prompts)

    start_parallel_sessions(prompts)


if __name__ == "__main__":
    main()
