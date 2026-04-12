"""agent_report_guard.py — SubagentStop guard for agent reports.

Validates content first (scores/verdict + required sections),
then records everything and resolves. If content is invalid,
blocks immediately — nothing gets recorded.
"""

from typing import Literal

from utils.validators import (
    is_agent_report_valid,
    scores_valid,
    verdict_valid,
    validate_review_sections,
)
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

        # 1. Validate content structure (blocks if invalid)
        _, message = is_agent_report_valid(
            hook_input, state, extract_scores, extract_verdict
        )

        # Validate sections for code/test review
        files, tests = validate_review_sections(content, phase)

        # 2. Record scores/verdict
        if phase in ("plan-review", "code-review"):
            _, extracted = scores_valid(content, extract_scores)
            record_scores(phase, extracted, state)

        if phase == "test-review":
            _, verdict = verdict_valid(content, extract_verdict)
            record_test_review_result(verdict, state)

        # 3. Record file lists for revision enforcement
        if phase == "code-review" and files:
            state.set_files_to_revise(files)
            state.set_code_tests_to_revise(tests)
        elif phase == "test-review" and files:
            state.set_test_files_to_revise(files)

        # 4. Resolve state
        resolve(config, state)

        return "allow", message
    except ValueError as e:
        return "block", str(e)
