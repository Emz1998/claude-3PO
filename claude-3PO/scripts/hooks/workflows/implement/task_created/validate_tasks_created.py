"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.state_store import StateStore  # type: ignore
from typing import Any, cast, Callable
from lib.conformance_check import template_conformance_check  # type: ignore
from utils.template_retriever import retrieve_template  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def main() -> None:
    state = StateStore()
    state.set_tasks_created(True)


if __name__ == "__main__":
    main()
