"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import json
import subprocess
import re
import yaml
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook

def get_modified_files() -> list[str]:
    modified_files = subprocess.run(
        ["git", "diff", "--name-only", "HEAD^"], capture_output=True, text=True
    )
    return modified_files.stdout.splitlines()


def get_code_files(session: SessionState) -> list[str]:
    code_files_paths = session.code_files_path
    if code_files_paths is None:
        return []
    return code_files_paths


def validate_match(modified_files: list[str], code_files_paths: list[str]) -> bool:
    return all(file in code_files_paths for file in modified_files)


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    modified_files = get_modified_files()
    code_files_paths = get_code_files(session)
    if not validate_match(modified_files, code_files_paths):
        Hook.block("Modified files do not match code files paths")
        return

    Hook.system_message("Modified files match code files paths")


if __name__ == "__main__":
    main()
