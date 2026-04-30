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
from utils.review_scores import extract_scores, scores_valid, scores_passing  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"

REVIEW_TYPE_MAP: dict[
    str, Literal["plan", "tests", "code", "security", "requirements"]
] = {
    "CodeReviewer": "code",
    "SecurityReviewer": "security",
    "Validator": "requirements",
    "TestReviewer": "tests",
    "PlanReviewer": "plan",
}

CONTEXTUAL_PHASE_MAP: dict[str, Literal["explore", "research"]] = {
    "Explore": "explore",
    "Research": "research",
}


def is_agent_response_valid(
    agent_name: str, response: str, state: StateStore
) -> tuple[bool, str]:
    template = retrieve_template(agent_name)
    ok, diff = template_conformance_check(template, response)
    if not ok:
        return (
            False,
            f"Agent response is not valid\n\n{diff}",
        )
    return True, "Agent response is valid"


def resolve_review_phase(agent_name: str) -> None:
    state = StateStore()
    review_type = REVIEW_TYPE_MAP[agent_name]
    if not state.all_reviews_passed(review_type):
        return
    state.update_phase_status(name="review", status="completed")


def is_contextual_agent(agent_name: str) -> bool:
    return agent_name in CONTEXTUAL_PHASE_MAP.keys()


def resolve_contextual_phase(
    agent_name: Literal[
        "Explore",
        "Research",
    ],
) -> None:
    state = StateStore()
    contextual_phase = CONTEXTUAL_PHASE_MAP[agent_name]
    if not state.is_agent_completed(agent_name):
        return
    state.update_phase_status(name=contextual_phase, status="completed")


def main() -> None:
    hook_input = Hook.read_stdin()
    agent_name = hook_input.get("agent_type", str)
    response = hook_input.get("last_assistant_message", str)
    state = StateStore()

    if is_contextual_agent(agent_name):
        resolve_contextual_phase(agent_name)
        return

    is_valid, message = is_agent_response_valid(agent_name, response, state)
    if not is_valid:
        Hook.block(message)
        return

    review_type = REVIEW_TYPE_MAP[agent_name]

    passed, message = scores_passing(hook_input.get("scores", {}))
    if not passed:
        state.update_review(review_type=review_type, status="completed", verdict="fail")
        Hook.block(message)
        return

    resolve_review_phase(agent_name)


if __name__ == "__main__":
    main()
