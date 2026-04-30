"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.state_store import StateStore  # type: ignore
from utils.order_validation import validate_order  # type: ignore
from lib.resolver import Resolver  # type: ignore
from typing import Any
from constants.constants import TEST_COMMANDS  # type: ignore
import subprocess
import json

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"

TEST_COMMAND_MAP: dict[str, list[str]] = {
    "pytest": ["pytest", "--json-report"],
    "vitest": ["vitest", "run", "--reporter=json"],
}


def get_bash_result(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_response", {}).get("stdout", "")


def get_bash_command(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("command", "")


def extract_test_lib_name(command: str) -> str:
    return command.split(" ")[0]


def is_test_command(command: str) -> bool:
    return extract_test_lib_name(command) in TEST_COMMANDS


def run_test(command: str) -> str:
    lib_name = extract_test_lib_name(command)
    argv = TEST_COMMAND_MAP[lib_name]
    return subprocess.run(argv, capture_output=True, text=True).stdout


def is_test_passing(lib_name: str, result: str) -> bool:
    json_result = json.loads(result)
    if lib_name == "pytest":
        return json_result.get("summary", {}).get("passed", 0) > 0
    elif lib_name == "vitest":
        return json_result.get("numPassedTests", 0) > 0
    else:
        return False


def main() -> None:
    hook_input = Hook.read_stdin()
    command = get_bash_command(hook_input)
    state = StateStore()
    if not is_test_command(command):
        return

    result = run_test(command)

    if not is_test_passing(extract_test_lib_name(command), result):

        state.update_tests_status("fail")
        return

    state.update_tests_status("pass")


if __name__ == "__main__":
    main()
