"""Phase-name constants shared across guards and dispatchers."""

# Phases where SubagentStop validates an agent report against the expected
# template before the workflow is allowed to advance to the next phase.
REVIEW_PHASES: frozenset[str] = frozenset({
    "plan-review",
    "test-review",
    "tests-review",
    "code-review",
    "quality-check",
    "validate",
    "architect",
    "backlog",
})
