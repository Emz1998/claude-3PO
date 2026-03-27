"""guardrail.py — Workflow guardrail CLI hook.

Validates agent/skill invocations against the current workflow state.

Usage:
    # Hook mode (pipe JSON from Claude Code):
    python3 guardrail.py --hook-input '{"hook_event_name":"PreToolUse",...}'

    # With reason printed on block:
    python3 guardrail.py --hook-input '...' --reason

    # Manual phase advancement:
    python3 guardrail.py --advance

Environment:
    GUARDRAIL_STATE_PATH — override the default state.json path
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the parent of 'workflow' package is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.guards import (
    agent_guard,
    bash_guard,
    phase_guard,
    review_guard,
    stop_guard,
    task_list_recorder,
    task_recorder,
    task_validator,
    write_guard,
)
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "state.json"


def _state_path() -> Path:
    env = os.environ.get("GUARDRAIL_STATE_PATH")
    return Path(env) if env else DEFAULT_STATE_PATH


def _advance(state_path: Path) -> None:
    """Advance the next pending phase to in_progress."""
    store = StateStore(state_path)
    advanced: list[str] = []

    def _transition(state: dict) -> None:
        phases: list[dict] = state.get("phases", [])
        if not phases:
            return
        statuses = [p["status"] for p in phases]
        if not any(s in ("completed", "in_progress") for s in statuses):
            phases[0]["status"] = "in_progress"
            advanced.append(phases[0]["name"])
            return
        last_completed_idx = None
        for i, phase in enumerate(phases):
            if phase["status"] == "completed":
                last_completed_idx = i
        if last_completed_idx is None:
            return
        next_idx = last_completed_idx + 1
        if next_idx < len(phases) and phases[next_idx]["status"] == "pending":
            phases[next_idx]["status"] = "in_progress"
            advanced.append(phases[next_idx]["name"])

    store.update(_transition)
    print(f"Advanced: {advanced[0]}" if advanced else "No phase to advance.")


def _dispatch(hook_input: dict, state_path: Path) -> tuple[str, str]:
    event = hook_input.get("hook_event_name", "")

    if event == "PreToolUse":
        tool = hook_input.get("tool_name", "")
        if tool == "Agent":
            return agent_guard.validate(hook_input, state_path)
        if tool == "Skill":
            return phase_guard.validate(hook_input, state_path)
        if tool in ("Write", "Edit"):
            return write_guard.validate(hook_input, state_path)
        if tool == "Bash":
            return bash_guard.validate(hook_input, state_path)

    if event == "PostToolUse":
        tool = hook_input.get("tool_name", "")
        if tool == "TaskCreate":
            return task_recorder.record(hook_input)
        if tool == "TaskList":
            return task_list_recorder.record(hook_input)

    if event == "SubagentStop":
        agent_type = hook_input.get("agent_type", "")
        if agent_type == "task-manager":
            return task_validator.validate(hook_input, state_path)
        return review_guard.handle(hook_input, state_path)

    if event == "Stop":
        return stop_guard.validate(hook_input, state_path)

    return "allow", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Workflow guardrail hook")
    parser.add_argument("--hook-input", type=str, help="JSON hook input string")
    parser.add_argument(
        "--advance", action="store_true", help="Manually advance to next phase"
    )
    parser.add_argument(
        "--reason", action="store_true", help="Include block reason in stderr output"
    )
    args = parser.parse_args()

    state_path = _state_path()

    if args.advance:
        _advance(state_path)
        sys.exit(0)

    if args.hook_input:
        try:
            hook_input = json.loads(args.hook_input)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        decision, reason = _dispatch(hook_input, state_path)

        if decision == "allow":
            print("allow")
        else:
            print(f"block, {reason}" if args.reason else "block")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
