"""runners.py — Stop guard checks run via subprocess.

Each check reads state.json, validates a condition, and exits:
    exit 0 = pass
    exit 1 + stderr = fail

Used by stop.py to determine if the main agent can stop.
"""

import sys
from pathlib import Path

from .state_store import StateStore
from config import Config


def check_phases(config: Config, state: StateStore) -> None:
    """Are all required phases completed?"""
    phases = state.phases
    data = state.load()
    skip = data.get("skip", [])
    workflow_type = data.get("workflow_type", "build")
    workflow_phases = config.get_phases(workflow_type) or config.main_phases
    required = [p for p in workflow_phases if p not in skip]

    completed = {p["name"] for p in phases if p["status"] == "completed"}
    missing = [p for p in required if p not in completed]

    if missing:
        print(f"Phases not completed: {missing}", file=sys.stderr)
        sys.exit(1)


def check_tests(state: StateStore) -> None:
    """Are tests written, executed, and passing?"""
    skip = state.load().get("skip", [])

    if "write-tests" in skip and "test-review" in skip:
        return

    tests = state.tests

    if not tests.get("file_paths"):
        print("No test files written", file=sys.stderr)
        sys.exit(1)

    if not tests.get("executed"):
        print("Tests not executed", file=sys.stderr)
        sys.exit(1)

    last_review = state.last_test_review
    verdict = last_review.get("verdict") if last_review else None
    if verdict != "Pass":
        print(f"Test review verdict: {verdict}, expected: Pass", file=sys.stderr)
        sys.exit(1)


def check_ci(state: StateStore) -> None:
    """Is CI passing?"""
    skip = state.load().get("skip", [])

    if "ci-check" in skip:
        return

    status = state.ci.get("status", "pending")

    if status == "passed":
        return

    if status == "failed":
        print("CI checks failed", file=sys.stderr)
        sys.exit(1)

    print(f"CI status: {status}, expected: passed", file=sys.stderr)
    sys.exit(1)
