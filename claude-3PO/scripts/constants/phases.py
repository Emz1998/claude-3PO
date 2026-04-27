"""Phase-name constants shared across guards and dispatchers.

``REVIEW_PHASES`` is kept as an empty stub for forward-compat consumers; the
trimmed 7-phase MVP no longer has any agent-report review phases.
"""

# Stub kept for forward-compat — no review phases in the trimmed workflow.
REVIEW_PHASES: frozenset[str] = frozenset()
