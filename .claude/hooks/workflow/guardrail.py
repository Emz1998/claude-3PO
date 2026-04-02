"""guardrail.py — Unified workflow guardrail CLI hook.

Dispatches all hook events to modular guard modules.
Supports both /plan and /implement workflows.

Phase flow:
  /implement: explore → plan → write-plan → review → approved →
              task-create → write-tests → write-code → validate →
              pr-create → ci-check → report → completed
  /plan:      explore → plan → write-plan → review → approved

Usage:
    python3 guardrail.py --hook-input '{"hook_event_name":"PreToolUse",...}'
    python3 guardrail.py --hook-input '...' --reason

Environment:
    GUARDRAIL_STATE_PATH — override the default state.json path
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.guards import (
    agent_guard,
    bash_guard,
    read_guard,
    skill_guard,
    stop_guard,
    task_guard,
    webfetch_guard,
    write_guard,
)
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "state.json"

REQUIRED_SECTIONS = [
    r"^##\s+Context",
    r"^##\s+(Approach|Steps)",
    r"^##\s+(Files to Modify|Critical Files)",
    r"^##\s+Verification",
]


def _state_path() -> Path:
    env = os.environ.get("GUARDRAIL_STATE_PATH")
    return Path(env) if env else DEFAULT_STATE_PATH


def _validate_plan_template(content: str) -> tuple[bool, list[str]]:
    """Check plan content has all required sections. Returns (passed, missing)."""
    missing = []
    for pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, content, re.MULTILINE):
            label = re.sub(r"\^##\\s\+", "", pattern)
            label = (
                label.replace("(", "")
                .replace(")", "")
                .replace("|", " or ")
                .replace("\\", "")
            )
            missing.append(label.strip())
    return len(missing) == 0, missing


def _handle_exit_plan_mode_pre(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """PreToolUse ExitPlanMode: validate plan is written and review is approved."""
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    if not state.get("plan_written"):
        return (
            "block",
            "Blocked: ExitPlanMode requires a written plan. Write your plan to .claude/plans/ before exiting plan mode.",
        )

    if state.get("plan_review_status") != "approved":
        return (
            "block",
            "Blocked: plan review is not approved yet. Run the PlanReview agent after writing the plan.",
        )

    plan_file = state.get("plan_file")
    if not plan_file:
        return "block", "Blocked: no plan file recorded. Write the plan to .claude/plans/ before exiting plan mode."

    try:
        content = Path(plan_file).read_text()
    except (FileNotFoundError, OSError) as e:
        return "block", f"Blocked: cannot read plan file '{plan_file}': {e}. Verify the file exists and is readable."

    passed, missing = _validate_plan_template(content)
    if not passed:
        return "block", f"Blocked: plan missing required sections: {', '.join(missing)}. Add them before exiting plan mode."

    return json.dumps({"additionalContext": f"Plan content:\n\n{content}"}), ""


AGENT_ONLY_PHASES = {"explore", "plan", "task-create"}
AGENT_PLUS_WRITE_PHASES = {"review"}


def _phase_gate(hook_input: dict, store: StateStore) -> tuple[str, str] | None:
    """Block non-Agent tools from the main agent during agent-only phases.

    Returns a (decision, reason) tuple to block, or None to pass through.
    Subagent calls (agent_id present) always pass through.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return None

    # Subagent calls bypass the gate
    if hook_input.get("agent_id"):
        return None

    phase = state.get("phase", "")
    tool = hook_input.get("tool_name", "")

    if phase in AGENT_ONLY_PHASES:
        if tool != "Agent":
            return "block", f"Blocked: only the Agent tool is allowed during '{phase}' phase. Launch the required agent to proceed."
        return None

    if phase in AGENT_PLUS_WRITE_PHASES:
        if tool not in ("Agent", "Write", "Edit"):
            return "block", f"Blocked: only Agent and Write/Edit tools are allowed during '{phase}' phase."
        return None

    return None


def _dispatch(hook_input: dict, state_path: Path) -> tuple[str, str]:
    store = StateStore(state_path)
    event = hook_input.get("hook_event_name", "")
    tool = hook_input.get("tool_name", "")

    if event == "PreToolUse":
        # Phase gate: block main agent from using non-Agent tools in agent-only phases
        gate_result = _phase_gate(hook_input, store)
        if gate_result is not None:
            return gate_result

        if tool == "Agent":
            return agent_guard.validate(hook_input, store)
        if tool == "Read":
            return read_guard.validate(hook_input, store)
        if tool in ("Write", "Edit"):
            return write_guard.validate_pre(hook_input, store)
        if tool == "Bash":
            return bash_guard.validate_pre(hook_input, store)
        if tool == "WebFetch":
            return webfetch_guard.validate(hook_input, store)
        if tool == "ExitPlanMode":
            return _handle_exit_plan_mode_pre(hook_input, store)

    if event == "PostToolUse":
        if tool == "Skill":
            return skill_guard.handle(hook_input, store)

    if event == "TaskCreated":
        return task_guard.validate(hook_input, store)

    if event == "Stop":
        return stop_guard.validate(hook_input, store)

    if event == "UserPromptSubmit":
        return skill_guard.handle(hook_input, store)

    return "allow", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified workflow guardrail hook")
    parser.add_argument("--hook-input", type=str, help="JSON hook input string")
    parser.add_argument(
        "--reason", action="store_true", help="Include block reason in output"
    )
    args = parser.parse_args()

    if not args.hook_input:
        parser.print_help()
        sys.exit(1)

    try:
        hook_input = json.loads(args.hook_input)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    state_path = _state_path()
    decision, reason = _dispatch(hook_input, state_path)

    if decision == "allow":
        print("allow")
    elif decision == "block":
        print(f"block, {reason}" if args.reason else "block")
    else:
        # JSON passthrough (ExitPlanMode additionalContext)
        print(decision)

    sys.exit(0)


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    content: str = """
## Summary
Some text here
"""
    passed, missing = _validate_plan_template(content)
    print(f"passed: {passed}, missing: {missing}")
