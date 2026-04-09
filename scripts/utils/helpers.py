from urllib.parse import urlparse
from typing import Literal, Callable, Pattern, Any

from pathlib import Path
import tomllib

from config import Config


def load_config() -> dict[str, Any]:
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    return config


def is_content_valid(
    content: str,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
) -> bool:
    scores = extractor(content)

    confidence_score = scores["confidence_score"]
    quality_score = scores["quality_score"]

    if confidence_score is None or quality_score is None:
        raise ValueError("Confidence and quality scores are required")

    return True


def is_tasks_creation_allowed(phase: str, hook_event_name: str) -> bool:
    """Validate the tasks creation."""
    if hook_event_name == "TaskCreated" and phase != "create-tasks":
        raise ValueError(f"Tasks creation not allowed in phase: {phase}")
    return True


def count_completed_agents(agents: list[dict], agent_type: str) -> int:
    return sum(
        1
        for agent in agents
        if agent.get("agent_type") == agent_type and agent.get("status") == "completed"
    )


def _parse_ci_output(output: str) -> str:
    """Parse gh pr checks output to determine CI status.

    Returns "passed", "failed", or "pending".

    gh pr checks output format: "name\\tstatus\\tduration\\turl\\t" per line.
    Status values: pass, fail, pending, queued, in_progress, etc.
    Uses simple tab-delimited keyword search — no column-position dependency.
    """
    if not output or not output.strip():
        return "pending"

    # Any line with a fail status → failed
    if "\tfail" in output:
        return "failed"

    # Any line with pending/queued/in_progress → still pending
    if (
        "\tpending" in output
        or "\tqueued" in output
        or "\tin_progress" in output
        or "\twaiting" in output
    ):
        return "pending"

    # If we see pass statuses and nothing failed/pending → passed
    if "\tpass" in output:
        return "passed"

    # Summary format fallback (gh pr checks --watch)
    if "All checks were successful" in output:
        return "passed"
    if "Some checks were not successful" in output:
        return "failed"

    return "pending"


def validate_order(prev_item: str | None, next_item: str, order: list[str]) -> str:
    """Validate transition based on item order."""
    if next_item not in order:
        raise ValueError(f"Invalid next item '{next_item}'")

    if prev_item is None:
        if next_item == order[0]:
            return "Allowed to start with '{order[0]}'"
        raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")

    if prev_item not in order:
        raise ValueError(f"Invalid previous item: '{prev_item}'")

    prev_idx = order.index(prev_item)
    next_idx = order.index(next_item)

    if next_idx < prev_idx:
        raise ValueError(f"Cannot go backwards from '{prev_item}' to '{next_item}'")

    if next_idx > prev_idx + 1:
        skipped = order[prev_idx + 1 : next_idx]
        raise ValueError(f"Must complete {skipped} before '{next_item}'")

    return "Phase is allowed to transition to '{next_item}'"


def get_agents(state: dict[str, Any]) -> list[dict]:
    return state.get("agents", [])


def is_revision_needed(
    file_type: Literal["plan", "report", "tests", "code"],
    confidence_score: int,
    quality_score: int,
    config: Config,
) -> bool:
    confidence_threshold = config.get_score_threshold(file_type, "confidence_score")
    quality_threshold = config.get_score_threshold(file_type, "quality")

    if confidence_score < confidence_threshold and quality_score < quality_threshold:
        raise ValueError(f"Scores are below the threshold for {file_type}")

    if confidence_score < confidence_threshold:
        raise ValueError(f"Confidence score is below the threshold for {file_type}")
    if quality_score < quality_threshold:
        raise ValueError(f"Quality score is below the threshold for {file_type}")
    return True
