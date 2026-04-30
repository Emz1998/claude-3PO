"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "claude-3PO" / "scripts"))
from utils.hook import Hook  # type: ignore
from pathlib import Path  # type: ignore

from lib.conformance_check import template_conformance_check  # type: ignore

from datetime import datetime

TEMPLATE = """
# {title}

## Context

**Problem**: {problem}
**Goal**: {goal}

## Issues

-

## What to modify

- 
- 

"""


def is_agent_response_valid(response: str) -> tuple[bool, str]:
    template = TEMPLATE
    ok, diff = template_conformance_check(template, response)
    if not ok:
        return (
            False,
            f"Agent response is not valid\n\n{diff}",
        )
    return True, "Agent response is valid"


def test_log(message: str) -> None:
    test_log_path = Path.cwd() / "test.log"
    if not test_log_path.exists():
        test_log_path.touch()

    text = test_log_path.read_text()
    test_log_path.write_text(f"{text}\n{datetime.now().isoformat()} {message}")


def main() -> None:
    hook_input = Hook.read_stdin()
    response = hook_input.get("last_assistant_message", str)

    is_valid, message = is_agent_response_valid(response)
    if not is_valid:
        test_log(message)
        Hook.block(message)
        return


if __name__ == "__main__":
    main()
