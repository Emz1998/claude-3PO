"""agent_report_guard.py — Stop hook guard for agent reports.

Validates agent response contains scores or verdict,
then records them and runs the resolver.
"""

from typing import Literal

from utils.validators import is_agent_report_valid, scores_valid, verdict_valid
from utils.extractors import extract_scores, extract_verdict
from utils.recorder import record_scores, record_test_review_result
from utils.resolvers import resolve
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        phase = state.current_phase
        content = hook_input.get("last_assistant_message", "")

        _, message = is_agent_report_valid(
            hook_input, state, extract_scores, extract_verdict
        )

        # Record scores for plan/code review phases
        if phase in ("plan-review", "code-review"):
            _, extracted = scores_valid(content, extract_scores)
            record_scores(phase, extracted, state)

        # Record verdict for test review phase
        if phase == "test-review":
            _, verdict = verdict_valid(content, extract_verdict)
            record_test_review_result(verdict, state)

        # Resolve state after recording
        resolve(config, state)

        return "allow", message
    except ValueError as e:
        return "block", str(e)
