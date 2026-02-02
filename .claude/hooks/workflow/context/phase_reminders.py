#!/usr/bin/env python3
"""Phase reminder loader with external file support."""

from pathlib import Path

REMINDERS_DIR = Path(__file__).parent.parent / "config" / "reminders"

_reminder_cache: dict[str, str] = {}

# Minimal fallback defaults for backward compatibility
DEFAULT_REMINDERS: dict[str, str] = {
    "explore": "## Phase: EXPLORE\nUnderstand codebase before planning.",
    "plan": "## Phase: PLAN\nCreate implementation plan.",
    "plan-consult": "## Phase: PLAN-CONSULT\nReview and validate the plan.",
    "finalize-plan": "## Phase: FINALIZE-PLAN\nFinalize plan with feedback.",
    "write-test": "## Phase: WRITE-TEST\nCreate failing tests (TDD Red).",
    "review-test": "## Phase: REVIEW-TEST\nValidate test quality.",
    "write-code": "## Phase: WRITE-CODE\nWrite code to pass tests (TDD Green).",
    "code-review": "## Phase: CODE-REVIEW\nReview implementation quality.",
    "refactor": "## Phase: REFACTOR\nImprove code quality (TDD Refactor).",
    "validate": "## Phase: VALIDATE\nFinal validation before commit.",
    "commit": "## Phase: COMMIT\nCommit validated changes.",
}


def get_phase_reminder(phase: str, use_cache: bool = True) -> str | None:
    """Get reminder for a phase from external file or fallback.

    Args:
        phase: The workflow phase name
        use_cache: Whether to use cached content (default True)

    Returns:
        The reminder content string, or None if phase not found
    """
    global _reminder_cache

    if use_cache and phase in _reminder_cache:
        return _reminder_cache[phase]

    # Try to load from file
    reminder_file = REMINDERS_DIR / f"{phase}.md"
    if reminder_file.exists():
        content = reminder_file.read_text().strip()
        _reminder_cache[phase] = content
        return content

    # Fallback to default
    return DEFAULT_REMINDERS.get(phase)


def clear_cache() -> None:
    """Clear reminder cache for hot reload."""
    global _reminder_cache
    _reminder_cache = {}


def get_all_phase_reminders() -> dict[str, str]:
    """Get all phase reminders from files and defaults.

    Returns:
        Dictionary of phase name to reminder content
    """
    reminders: dict[str, str] = {}
    for phase in get_available_phases():
        reminder = get_phase_reminder(phase)
        if reminder:
            reminders[phase] = reminder
    return reminders


def get_available_phases() -> list[str]:
    """Get list of phases with reminders.

    Returns:
        Sorted list of phase names from both files and defaults
    """
    phases = set(DEFAULT_REMINDERS.keys())
    if REMINDERS_DIR.exists():
        phases.update(f.stem for f in REMINDERS_DIR.glob("*.md"))
    return sorted(phases)
