"""Phase-name constants shared across guards and dispatchers."""

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
