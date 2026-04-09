from urllib.parse import urlparse
from typing import Literal, Callable, Pattern
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.config import SAFE_DOMAINS, SCORES_THRESHOLDS


def _is_safe_domain(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host:
            return False
        for domain in SAFE_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


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


def is_revision_needed(
    file_type: Literal["plan", "report", "tests", "code"],
    confidence_score: int,
    quality_score: int,
) -> bool:

    confidence_score_threshold = SCORES_THRESHOLDS[file_type]["confidence"]
    quality_score_threshold = SCORES_THRESHOLDS[file_type]["quality"]

    if (
        confidence_score < confidence_score_threshold
        and quality_score < quality_score_threshold
    ):
        raise ValueError(f"Scores are below the threshold for {file_type}")

    if confidence_score < confidence_score_threshold:
        raise ValueError(f"Confidence score is below the threshold for {file_type}")
    if quality_score < quality_score_threshold:
        raise ValueError(f"Quality score is below the threshold for {file_type}")
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
