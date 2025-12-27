#!/usr/bin/env python3
"""Guard phase transitions in implement workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore[import-not-found]
    get_cache,
    set_cache,
    extract_slash_command_name,
    read_stdin_json,
    load_cache,
    write_cache,
)


def track_phases(phase: str) -> None:
    """Track completed phases in cache."""
    cache = load_cache()
    phases_completed = cache.get("phases_completed", [])
    if phase and phase not in phases_completed:
        phases_completed.append(phase)
        cache["phases_completed"] = phases_completed
        write_cache(cache)


DEFAULT_PHASES = [
    "roadmap:query",
    "explore",
    "discuss",
    "plan",
    "code",
    "log:sc",
    "log:milestone",
]


def get_transition_message(msg_type: str, skipped: list[str] | None = None) -> str:
    """Get phase transition message."""
    messages = {
        "rollback": "Cannot go back to previous phase.",
        "skip": f"Cannot skip phase(s): {', '.join(skipped or [])}",
        "unknown": "Unknown phase.",
        "allow": "Phase transition allowed.",
    }
    return messages.get(msg_type, "")


def is_valid_phase_transition(
    next_phase: str,
    all_phases: list[str] = DEFAULT_PHASES,
) -> bool:
    """Check if transition to next phase is valid."""
    current_phase = get_cache("current_phase") or "initial"

    # Handle unknown next_phase
    if next_phase not in all_phases:
        print(get_transition_message("unknown"), file=sys.stderr)
        return False

    # Handle initial state - allow any valid phase
    if current_phase == "initial":
        return True

    # Handle invalid current_phase - reset to first phase and validate
    if current_phase not in all_phases:
        print(
            f"Warning: Invalid current_phase '{current_phase}', resetting to 'explore'",
            file=sys.stderr,
        )
        set_cache("current_phase", "explore")
        current_phase = "explore"

    current_idx = all_phases.index(current_phase)
    next_idx = all_phases.index(next_phase)

    # Allow same or next in sequence
    if next_idx in (current_idx, current_idx + 1):
        return True

    # Block backwards
    if next_idx < current_idx:
        print(get_transition_message("rollback"), file=sys.stderr)
        return False

    # Block skipping
    skipped = all_phases[current_idx + 1 : next_idx]
    print(get_transition_message("skip", skipped), file=sys.stderr)
    return False


def validate_phase_transition(hook_input: dict) -> None:
    """Main phase transition validation."""
    if not get_cache("build_skill_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    print(tool_input)

    if not tool_name:
        sys.exit(0)

    # Extract phase/command based on tool type or prompt
    next_phase = ""
    if tool_name == "Skill" and isinstance(tool_input, dict):
        # Skill tool: extract from skill field
        next_phase = tool_input.get("skill", "")
        print(next_phase)

    if not next_phase:
        sys.exit(0)

    if not is_valid_phase_transition(next_phase):
        sys.exit(2)

    set_cache("current_phase", next_phase)
    track_phases(next_phase)
    print(f"Phase: {next_phase}")
    sys.exit(0)


def main() -> None:
    """Entry point."""
    hook_input = read_stdin_json()
    validate_phase_transition(hook_input)


if __name__ == "__main__":
    main()
    print("is this working?")
