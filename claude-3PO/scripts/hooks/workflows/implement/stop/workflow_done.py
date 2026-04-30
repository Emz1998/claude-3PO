"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.store import StateStore  # type: ignore
from typing import Any, cast, Callable  # type: ignore
from utils.run_pr_check import run_pr_view  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def skills_done(state: StateStore, config: Config) -> tuple[bool, str]:
    required_skills = config.get_phase_names_by_workflow(state.workflow_type)
    completed_skills = state.completed_skills()
    all_skills_completed = all(
        skill["name"] in required_skills for skill in completed_skills
    )

    skills_diff = set(required_skills) - set(completed_skills)
    if not all_skills_completed:
        return False, f"Workflow is not done, missing skills: {skills_diff}"
    return True, "Workflow is done"


def main() -> None:
    state = StateStore()
    config = Config()

    validators = [skills_done(state, config), run_pr_view()]

    errors: list[str] = []

    for done, error in validators:
        if not done:
            errors.append(error)

    if errors:
        Hook.block("\n".join(errors))
        return


if __name__ == "__main__":
    main()
