import json
import os
import subprocess
import time
from pathlib import Path

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.workflow_log import log


def main() -> None:
    hook_input = Hook.read_stdin()
    session_id = hook_input.get("session_id")
    Hook.advanced_output({"systemMessage": f"Session ID: {session_id}"})


if __name__ == "__main__":
    main()
