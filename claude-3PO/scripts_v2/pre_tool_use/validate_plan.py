"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from pathlib import Path
from utils.hook import Hook  # type: ignore
from lib.conformance_check import template_conformance_check  # type: ignore
from utils.session_id_checker import session_id_matches  # type: ignore
from lib.store import StateStore  # type: ignore

TEMPLATE_PATH = Path.cwd() / "claude-3PO" / "templates" / "plan.md"
THRESHOLDS = {
    "confidence_score": 80,
    "quality_score": 80,
}


def validate_plan(content: str, template: str) -> tuple[bool, str]:
    template = Path(template).read_text()
    identical, diff = template_conformance_check(content, template)
    if not identical:
        return False, diff
    return True, "Template conforms"


def extract_scores(content: str) -> dict[str, int]:
    scores = {
        "confidence_score": 0,
        "quality_score": 0,
    }
    for line in content.split("\n"):
        if line.startswith("Confidence Score:"):
            scores["confidence_score"] = int(line.split(":")[1].strip())
        if line.startswith("Quality Score:"):
            scores["quality_score"] = int(line.split(":")[1].strip())
    return scores


def scores_valid(scores: dict[str, int]) -> tuple[bool, str]:
    if scores["confidence_score"] < 0 or scores["confidence_score"] > 100:
        return False, "Confidence score must be between 0 and 100"
    if scores["quality_score"] < 0 or scores["quality_score"] > 100:
        return False, "Quality score must be between 0 and 100"
    return True, "Valid Scores"


def scores_passing(scores: dict[str, int]) -> tuple[bool, str]:
    if scores["confidence_score"] < THRESHOLDS["confidence_score"]:
        return False, "Confidence score is below threshold"
    if scores["quality_score"] < THRESHOLDS["quality_score"]:
        return False, "Quality score is below threshold"
    return True, "Scores are passing"


def main() -> None:

    hook_input = Hook.read_stdin()
    content = hook_input.get("tool_input", {}).get("content", "")
    template = Path(TEMPLATE_PATH).read_text()
    if not session_id_matches(hook_input.get("session_id", "")):
        Hook.system_message("Session ID does not match state session ID. Skipping")
        return

    errors: list[str] = []

    if not validate_plan(content, template):
        errors.append("Plan does not conform to template")

    scores = extract_scores(content)
    if not scores_valid(scores):
        errors.append("Scores are not valid")

    if errors:
        Hook.block("\n".join(errors))
        return

    if not scores_passing(scores):
        state = StateStore()
        state.add_review(
            scores["confidence_score"],
            scores["quality_score"],
            "in_progress",
            "fail",
        )

    if not errors:
        state = StateStore()
        state.add_review(
            scores["confidence_score"],
            scores["quality_score"],
            "completed",
            "pass",
        )


if __name__ == "__main__":
    main()
