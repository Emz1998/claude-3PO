"""coding_dry_run.py — Simulate the coding guardrail workflow end-to-end.

Uses real coding_guardrail.py subprocess calls to verify the implementation
workflow behaves correctly for both TDD and non-TDD paths.

Usage:
    python3 .claude/hooks/workflow/dry_runs/coding_dry_run.py
    python3 .claude/hooks/workflow/dry_runs/coding_dry_run.py --tdd
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CODING_GUARDRAIL = Path(__file__).resolve().parent.parent / "coding_guardrail.py"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

results: list[dict] = []


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------

def make_initial_state(tdd: bool) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": "plan",
        "TDD": tdd,
        "plan_workflow": {
            "plan_workflow_active": True,
            "phase": "write",
            "instructions": "Implement feature",
            "agents": [],
            "plan_file": ".claude/plans/test-plan.md",
            "review": {"status": "approved"},
        },
    }


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def exit_plan_mode_payload() -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_response": {
            "plan": None,
            "isAgent": False,
            "filePath": "/home/emhar/.claude/plans/test-plan.md",
        },
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def write_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def agent_payload(subagent_type: str, tool_use_id: str = "t1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": subagent_type, "description": "x", "prompt": "x"},
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def stop_payload(agent_type: str, verdict: str) -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": verdict,
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def bash_payload(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def post_bash_payload(command: str) -> dict:
    payload = bash_payload(command)
    payload["hook_event_name"] = "PostToolUse"
    payload["tool_response"] = {"stdout": "ok"}
    return payload


def stop_event() -> dict:
    return {
        "hook_event_name": "Stop",
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
    }


# ---------------------------------------------------------------------------
# run() — call coding_guardrail.py and check result
# ---------------------------------------------------------------------------

def run(pre: str, payload: dict, expected: str, state_path: Path, post: str = "") -> bool:
    print(f"\n  {pre}")

    env = {**os.environ, "CODING_GUARDRAIL_STATE_PATH": str(state_path)}
    result = subprocess.run(
        [sys.executable, str(CODING_GUARDRAIL), "--hook-input", json.dumps(payload), "--reason"],
        capture_output=True,
        text=True,
        env=env,
    )
    actual = result.stdout.strip()
    passed = actual.startswith(expected)
    results.append({"label": pre, "expected": expected, "actual": actual, "passed": passed})

    time.sleep(5)

    if not passed:
        status = f"{RED}FAIL{RESET}"
    elif expected == "block":
        status = f"{RED}BLOCK{RESET}"
    else:
        status = f"{GREEN}PASS{RESET}"

    print(f"  {status}  {post or actual}")
    if not passed:
        print(f"         expected: {expected!r}, got: {actual!r}")
        if result.stderr:
            print(f"         stderr: {result.stderr.strip()}")
    return passed


# ---------------------------------------------------------------------------
# simulate_workflow
# ---------------------------------------------------------------------------

def simulate_workflow(state_path: Path, tdd: bool) -> None:
    print("\n--- Activation ---")
    run(
        "PostToolUse: ExitPlanMode accepted",
        exit_plan_mode_payload(),
        "allow",
        state_path,
        "coding_workflow initialized",
    )

    if tdd:
        print("\n--- TDD Gate ---")
        run(
            "Writing /project/src/app.py before test review",
            write_payload("/project/src/app.py"),
            "block",
            state_path,
            "Blocked — implementation code not allowed before TestReviewer passes",
        )
        run(
            "Writing /project/tests/test_app.py",
            write_payload("/project/tests/test_app.py"),
            "allow",
            state_path,
            "Test file write allowed",
        )
        run(
            "Launching TestReviewer [t1]",
            agent_payload("TestReviewer", "t1"),
            "allow",
            state_path,
            "TestReviewer registered",
        )
        run(
            "TestReviewer [t1]: review returns Fail",
            stop_payload("TestReviewer", "Fail"),
            "allow",
            state_path,
            "Tests marked failing",
        )
        run(
            "Session stop requested while tests failing",
            stop_event(),
            "block",
            state_path,
            "Blocked — failing tests still gate the workflow",
        )
        run(
            "Writing /project/src/app.py while test review is failing",
            write_payload("/project/src/app.py"),
            "block",
            state_path,
            "Blocked — implementation code still forbidden after failed test review",
        )
        run(
            "Rewriting /project/tests/test_app.py after failed review",
            write_payload("/project/tests/test_app.py"),
            "allow",
            state_path,
            "Test file rewrite allowed",
        )
        run(
            "Launching TestReviewer [t2]",
            agent_payload("TestReviewer", "t2"),
            "allow",
            state_path,
            "TestReviewer retry registered",
        )
        run(
            "TestReviewer [t2]: review returns Pass",
            stop_payload("TestReviewer", "Pass"),
            "allow",
            state_path,
            "Tests approved — write-code unlocked",
        )

    print("\n--- Implementation ---")
    run(
        "Writing /project/src/app.py",
        write_payload("/project/src/app.py"),
        "allow",
        state_path,
        "Implementation write allowed",
    )
    run(
        "Running: gh pr create --fill before validation",
        bash_payload("gh pr create --fill"),
        "block",
        state_path,
        "Blocked — validation must pass first",
    )

    print("\n--- Validation ---")
    run(
        "Launching Validator [t3]",
        agent_payload("Validator", "t3"),
        "allow",
        state_path,
        "Validator registered",
    )
    run(
        "Validator [t3]: validation returns Fail",
        stop_payload("Validator", "Fail"),
        "allow",
        state_path,
        "Validation marked failing",
    )
    run(
        "Session stop requested while validation failing",
        stop_event(),
        "block",
        state_path,
        "Blocked — validation still failing",
    )
    run(
        "Rewriting /project/src/app.py after failed validation",
        write_payload("/project/src/app.py"),
        "allow",
        state_path,
        "Implementation rewrite allowed",
    )
    run(
        "Launching Validator [t4]",
        agent_payload("Validator", "t4"),
        "allow",
        state_path,
        "Validator retry registered",
    )
    run(
        "Validator [t4]: validation returns Pass",
        stop_payload("Validator", "Pass"),
        "allow",
        state_path,
        "Validation approved — pr-create unlocked",
    )

    print("\n--- PR Creation ---")
    run(
        "Running: gh pr create --fill",
        bash_payload("gh pr create --fill"),
        "allow",
        state_path,
        "PR creation command allowed",
    )
    run(
        "PostToolUse: gh pr create --fill",
        post_bash_payload("gh pr create --fill"),
        "allow",
        state_path,
        "PR marked created — workflow complete",
    )

    print("\n--- Completion ---")
    run(
        "Session stop requested after completion",
        stop_event(),
        "allow",
        state_path,
        "Stop allowed — workflow complete",
    )


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed")
    if failed:
        print(f"\n  {RED}FAILURES:{RESET}")
        for result in results:
            if not result["passed"]:
                print(f"    - {result['label']}")
                print(f"      expected: {result['expected']!r}, got: {result['actual']!r}")
    color = GREEN if failed == 0 else RED
    print(f"\n  {color}{'ALL PASS' if failed == 0 else f'{failed} FAILED'}{RESET}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run the coding guardrail end-to-end")
    parser.add_argument("--tdd", action="store_true", help="Include TDD test-review gate")
    args = parser.parse_args()

    state_path = CODING_GUARDRAIL.parent / "state.json"
    state_path.write_text(json.dumps(make_initial_state(args.tdd), indent=2))

    mode = "TDD" if args.tdd else "non-TDD"
    print(f"\nDry-run coding guardrail ({mode})")
    print(f"State file: {state_path}")

    simulate_workflow(state_path, args.tdd)
    print_summary()

    failed = sum(1 for result in results if not result["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
