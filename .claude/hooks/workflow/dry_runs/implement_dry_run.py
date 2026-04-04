"""implement_dry_run.py — Simulate the /implement workflow end-to-end.

Usage:
    python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py
    python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd
    python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd --story-id SK-123
    python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --skip-all
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.session_store import SessionStore

GUARDRAIL = Path(__file__).resolve().parent.parent / "guardrail.py"
RECORDER = Path(__file__).resolve().parent.parent / "recorder.py"
STATE_JSONL_PATH = GUARDRAIL.parent / "state.jsonl"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

results: list[dict] = []


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def skill_payload(skill: str, args: str = "") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill, "args": args},
        "tool_response": {"success": True},
        "tool_use_id": "t0",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def agent_payload(subagent_type: str, tool_use_id: str = "t1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {
            "subagent_type": subagent_type,
            "description": "x",
            "prompt": "x",
            "run_in_background": False,
        },
        "tool_use_id": tool_use_id,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def write_payload(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def post_write_payload(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_response": {"type": "update", "filePath": file_path},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def bash_payload(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def post_bash_payload(command: str, output: str = "") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"output": output},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def subagent_stop_payload(agent_type: str, msg: str = "Done.") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": msg,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def validator_report(verdict: str) -> str:
    """Build a valid Validator report with the given verdict."""
    return (
        f"## QA Report: Test Task\n\n"
        f"### Criteria Checklist\n"
        f"| # | Criterion | Verdict | Evidence |\n"
        f"|---|-----------|---------|----------|\n"
        f"| 1 | Tests pass | Met | `tests/:1` |\n\n"
        f"### Test Results\n"
        f"- **Command**: `pytest`\n"
        f"- **Result**: 1 passed\n\n"
        f"### Final Verdict: {verdict.upper()}\n\n"
        f"{verdict}"
    )


def task_create_pre_payload(
    subject: str,
    description: str = "Do the thing.",
    parent_task_id: str | None = None,
    parent_task_title: str | None = None,
    include_metadata: bool = True,
) -> dict:
    tool_input: dict = {"subject": subject, "description": description}
    if include_metadata:
        metadata: dict = {}
        if parent_task_id is not None:
            metadata["parent_task_id"] = parent_task_id
        if parent_task_title is not None:
            metadata["parent_task_title"] = parent_task_title
        tool_input["metadata"] = metadata
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "TaskCreate",
        "tool_input": tool_input,
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def task_completed_payload(subject: str, task_id: str = "task-001") -> dict:
    return {
        "hook_event_name": "TaskCompleted",
        "task_id": task_id,
        "task_subject": subject,
        "task_description": "Do the thing.",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def exit_plan_mode_post_payload() -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_response": {},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def stop_payload() -> dict:
    return {
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# run() helper
# ---------------------------------------------------------------------------


def run(label: str, payload: dict, expected: str, note: str = "") -> bool:
    hook_json = json.dumps(payload)
    result = subprocess.run(
        [sys.executable, str(GUARDRAIL), "--hook-input", hook_json, "--reason"],
        capture_output=True,
        text=True,
    )
    actual = result.stdout.strip()
    passed = actual.startswith(expected)
    results.append(
        {"label": label, "expected": expected, "actual": actual, "passed": passed}
    )

    # If guardrail allowed, also run the recorder for state tracking
    if actual.startswith("allow") or actual.startswith("{"):
        subprocess.run(
            [sys.executable, str(RECORDER), "--hook-input", hook_json],
            capture_output=True,
            text=True,
        )

    time.sleep(0.05)

    if not passed:
        status = f"{RED}FAIL{RESET}"
    elif expected == "block":
        status = f"{RED}BLOCK{RESET}"
    else:
        status = f"{GREEN}PASS{RESET}"

    print(f"  {status}  {label[:65]}")
    if not passed:
        print(f"         expected: {expected!r}")
        print(f"         got:      {actual!r}")
        if result.stderr:
            print(f"         stderr:   {result.stderr.strip()[:200]}")
    elif note:
        print(f"         {YELLOW}{note}{RESET}")
    return passed


def print_summary() -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"\n{'='*60}")
    print(
        f"  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  ({total} total)"
    )
    if failed:
        print(f"\n  {RED}Failed:{RESET}")
        for r in results:
            if not r["passed"]:
                print(f"    - {r['label']}")
                print(f"      expected={r['expected']!r} got={r['actual']!r}")
    print(f"{'='*60}\n")


VALID_PLAN = """# My Test Plan

## Context
This plan tests the guardrail validation logic.

## Steps
### Step 1: Implement the feature
Write the code.

## Files to Modify
| File | Action |
|------|--------|
| `src/feature.py` | Create |

## Verification
Run pytest.
"""


def read_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": file_path},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def exit_plan_mode_pre_payload() -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def simulate(tdd: bool, story_id: str | None, skip_args: str, tmp_dir: Path) -> None:
    skip_explore = "--skip-explore" in skip_args or "--skip-all" in skip_args
    skip_research = "--skip-research" in skip_args or "--skip-all" in skip_args

    # Activate /implement skill
    print(f"\n--- /implement {skip_args} ---")
    impl_args = skip_args
    if tdd:
        impl_args = (impl_args + " --tdd").strip()
    if story_id:
        impl_args = (story_id + " " + impl_args).strip()

    run(
        f"/implement {impl_args} → activates workflow",
        skill_payload("implement", impl_args),
        "allow",
        "Workflow activated",
    )

    # Explore phase
    if not skip_explore:
        print("\n--- Explore phase ---")
        run("Main agent Write → block (phase gate)", write_payload("notes.md"), "block", "Only Agent tool allowed")
        run("Explore [t1] → allow", agent_payload("Explore", "t1"), "allow")
        run("Explore [t2] → allow", agent_payload("Explore", "t2"), "allow")
        run("Explore [t3] → allow", agent_payload("Explore", "t3"), "allow")

    if not skip_research:
        run("Research [t5] → allow", agent_payload("Research", "t5"), "allow")
        run("Research [t6] → allow", agent_payload("Research", "t6"), "allow")

    if not skip_explore:
        print("\n--- Complete Explore agents ---")
        run("Explore [t1] done", subagent_stop_payload("Explore", "Found src/ with main modules and utils/"), "allow")
        run("Explore [t2] done", subagent_stop_payload("Explore", "Config lives in config.yaml, tests in tests/"), "allow")
        run("Explore [t3] done", subagent_stop_payload("Explore", "Auth module at src/auth.py uses JWT tokens"), "allow")

    if not skip_research:
        run("Research [t5] done", subagent_stop_payload("Research", "Best practice: use dependency injection for services"), "allow")
        run(
            "Research [t6] done → phase=write-codebase",
            subagent_stop_payload("Research", "Latest docs recommend pydantic v2 for validation"),
            "allow",
            "Phase → write-codebase",
        )

    # Write-codebase phase
    print("\n--- Write-codebase phase ---")
    run("Write code in write-codebase → block", write_payload("src/feature.py"), "block")
    run("Write CODEBASE.md (pre) → allow", write_payload("CODEBASE.md", "# Codebase overview"), "allow")
    run(
        "Write CODEBASE.md (post) → phase=plan",
        post_write_payload("CODEBASE.md", "# Codebase overview"),
        "allow",
        "Phase → plan",
    )

    # Plan phase
    print("\n--- Plan phase ---")
    run("Main agent Write → block (phase gate)", write_payload("notes.md"), "block", "Only Agent tool allowed")
    run("Plan agent → allow", agent_payload("Plan", "tp1"), "allow")
    run(
        "Plan SubagentStop → phase=write-plan",
        subagent_stop_payload("Plan", "Plan created."),
        "allow",
        "Phase → write-plan",
    )

    # Write-plan phase
    print("\n--- Write-plan phase ---")
    plan_path = str(tmp_dir / ".claude/plans/my-plan.md")
    Path(plan_path).parent.mkdir(parents=True, exist_ok=True)
    run("Write to .claude/plans/ (pre) → allow", write_payload(plan_path, VALID_PLAN), "allow")
    Path(plan_path).write_text(VALID_PLAN)
    run(
        "Write to .claude/plans/ (post) → phase=review",
        post_write_payload(plan_path, VALID_PLAN),
        "allow",
        "Phase → review, plan_written=True",
    )

    # Review phase
    print("\n--- Review phase ---")
    run("PlanReview [tr1] → allow", agent_payload("PlanReview", "tr1"), "allow")
    run(
        "PlanReview low scores → revision_needed",
        subagent_stop_payload("PlanReview", "Confidence: 60, Quality: 55"),
        "allow",
        "iteration=1",
    )
    run("PlanReview [tr2] → allow", agent_payload("PlanReview", "tr2"), "allow")
    run(
        "PlanReview high scores → approved",
        subagent_stop_payload("PlanReview", "Confidence: 92, Quality: 88"),
        "allow",
        "Phase → approved",
    )

    # ExitPlanMode pre — valid plan
    print("\n--- ExitPlanMode (pre) ---")
    result_raw = subprocess.run(
        [
            sys.executable,
            str(GUARDRAIL),
            "--hook-input",
            json.dumps(exit_plan_mode_pre_payload()),
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if result_raw.startswith("{") and "additionalContext" in result_raw:
        print(f"  {GREEN}PASS{RESET}  ExitPlanMode valid → surfaces additionalContext")
        results.append(
            {
                "label": "ExitPlanMode pre valid",
                "expected": "{",
                "actual": result_raw,
                "passed": True,
            }
        )
    else:
        print(
            f"  {RED}FAIL{RESET}  ExitPlanMode pre → expected additionalContext, got: {result_raw[:80]}"
        )
        results.append(
            {
                "label": "ExitPlanMode pre valid",
                "expected": "additionalContext",
                "actual": result_raw,
                "passed": False,
            }
        )

    # ExitPlanMode post → advance to task-create / write-tests / write-code
    print("\n--- ExitPlanMode (post) ---")
    run(
        "ExitPlanMode post → advance phase",
        exit_plan_mode_post_payload(),
        "allow",
        f"Phase → {'task-create' if story_id else ('write-tests' if tdd else 'write-code')}",
    )

    # Task-create phase (if story_id provided)
    if story_id:
        print("\n--- Task-create phase ---")
        run("Stop before tasks done → block", stop_payload(), "block")

        # Fetch real project tasks for this story to use in payloads
        import subprocess as _sp
        _pm = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "github_project" / "project_manager.py")
        _pm_result = _sp.run(
            [sys.executable, _pm, "view", story_id, "--tasks", "--json"],
            capture_output=True, text=True,
        )
        _project_tasks = json.loads(_pm_result.stdout) if _pm_result.returncode == 0 else []

        # Validation tests (before covering all tasks)
        if _project_tasks:
            _first = _project_tasks[0]
            run(
                f"TaskCreate valid metadata ({_first['id']}) → allow",
                task_create_pre_payload(
                    "Implement feature",
                    parent_task_id=_first["id"],
                    parent_task_title=_first["title"],
                ),
                "allow",
                "subtask recorded, phase stays task-create",
            )
        run(
            "TaskCreate missing metadata → block",
            task_create_pre_payload("Wrong task", include_metadata=False),
            "block",
        )
        run(
            "TaskCreate unknown parent_task_id → block",
            task_create_pre_payload(
                "Another task",
                parent_task_id="T-999",
                parent_task_title="Nonexistent task",
            ),
            "block",
        )

        # Cover remaining tasks to trigger auto-advance
        for task in _project_tasks[1:]:
            run(
                f"TaskCreate cover {task['id']} → allow",
                task_create_pre_payload(
                    f"Subtask for {task['id']}",
                    parent_task_id=task["id"],
                    parent_task_title=task["title"],
                ),
                "allow",
            )

        # Verify TaskCompleted updates subtask status
        run(
            "TaskCompleted → subtask status updated",
            task_completed_payload("Implement feature"),
            "allow",
            "subtask completed",
        )

    # Write-tests phase (TDD)
    if tdd:
        print("\n--- Write-tests phase ---")
        run("Read plan-listed file → allow", read_payload("src/feature.py"), "allow")
        run("Read non-plan file → block", read_payload("src/other.py"), "block")
        run("Read CODEBASE.md → allow", read_payload("CODEBASE.md"), "allow")
        run("Read .json file → block (not always-allowed)", read_payload("package.json"), "block")
        run("Read .claude/ prefix → block (not always-allowed)", read_payload(".claude/settings.json"), "block")
        run(
            "Code write in write-tests → block",
            write_payload("src/feature.py"),
            "block",
        )
        run("Test write → allow", write_payload("tests/test_feature.py"), "allow")
        run(
            "Post test write → tracked",
            post_write_payload("tests/test_feature.py"),
            "allow",
            "test tracked",
        )
        run("Validator in write-tests → block", agent_payload("Validator"), "block")
        run(
            "TestReviewer without files... → allow",
            agent_payload("TestReviewer"),
            "allow",
            "test_files_created non-empty",
        )
        run(
            "TestReviewer Fail → stays in write-tests",
            subagent_stop_payload("TestReviewer", "Fail"),
            "allow",
            "Phase stays write-tests",
        )
        run(
            "TestReviewer again after Fail → allow",
            agent_payload("TestReviewer"),
            "allow",
        )
        run(
            "TestReviewer Pass → phase=write-code",
            subagent_stop_payload("TestReviewer", "Pass"),
            "allow",
            "Phase → write-code",
        )

    # Write-code phase
    print("\n--- Write-code phase ---")
    if tdd:
        run("Read previously written file → allow", read_payload("tests/test_feature.py"), "allow")
    run("Read random non-plan file → block", read_payload("src/utils.py"), "block")
    run("Code write → allow", write_payload("src/feature.py"), "allow")
    run("PR command in write-code → block", bash_payload("gh pr create"), "block")
    run(
        "Test run → allow + tracked",
        post_bash_payload("pytest tests/", output="1 passed"),
        "allow",
    )
    run(
        "Validator agent → allow + advance to validate",
        agent_payload("Validator"),
        "allow",
        "Phase → validate",
    )

    # Validate phase
    print("\n--- Validate phase ---")
    run("Code write in validate → block", write_payload("src/feature.py"), "block")
    run(
        "Validator Fail → phase=write-code",
        subagent_stop_payload("Validator", validator_report("Fail")),
        "allow",
        "Phase → write-code",
    )

    # Return to write-code and re-validate
    run("Code write again → allow", write_payload("src/feature.py"), "allow")
    run(
        "Validator again → allow + advance to validate",
        agent_payload("Validator"),
        "allow",
        "Phase → validate",
    )
    run(
        "Validator Pass → phase=pr-create",
        subagent_stop_payload("Validator", validator_report("Pass")),
        "allow",
        "Phase → pr-create",
    )

    # PR-create phase
    print("\n--- PR-create phase ---")
    run(
        "PR without validation → block (validation already pass)",
        bash_payload("gh pr create"),
        "allow",
    )
    run(
        "PR create post → phase=ci-check",
        post_bash_payload("gh pr create --title 'x'", output="https://github.com/pr/1"),
        "allow",
        "Phase → ci-check",
    )

    # CI-check phase
    print("\n--- CI-check phase ---")
    run("Stop before CI done → block", stop_payload(), "block")
    run(
        "CI pending (table format) → stays ci-check",
        post_bash_payload("gh pr checks 1", output="check-1\tpass\t1s\turl\ncheck-2\tpending\t0\turl"),
        "allow",
        "ci_status stays pending",
    )
    run(
        "CI fail (table format) → ci_status=failed",
        post_bash_payload("gh pr checks 1", output="check-1\tpass\t1s\turl\ncheck-2\tfail\t5s\turl"),
        "allow",
        "ci_status=failed",
    )

    # Code write triggers regression
    run(
        "Code write in ci-check → allow + regression",
        post_write_payload("src/feature.py"),
        "allow",
        "Phase → write-code",
    )

    # Re-run validate + PR
    run("Validator → advance to validate", agent_payload("Validator"), "allow")
    run(
        "Validator Pass → pr-create",
        subagent_stop_payload("Validator", validator_report("Pass")),
        "allow",
    )
    run(
        "PR create post → ci-check",
        post_bash_payload("gh pr create --title 'x2'", "https://github.com/pr/2"),
        "allow",
    )

    # CI pass (table format)
    run(
        "CI pass (table format) → phase=report",
        post_bash_payload("gh pr checks 2", output="check-1\tpass\t1s\turl\ncheck-2\tpass\t5s\turl"),
        "allow",
        "Phase → report",
    )

    # Report phase
    print("\n--- Report phase ---")
    run("Code write in report → block", write_payload("src/feature.py"), "block")
    report_path = ".claude/reports/latest-report.md"
    run("Report write (pre) → allow", write_payload(report_path), "allow")
    run(
        "Report write (post) → completed",
        post_write_payload(report_path),
        "allow",
        "Phase → completed",
    )

    # Completed — stop allowed
    print("\n--- Completed ---")
    run("Stop after completed → allow", stop_payload(), "allow")

    # Final state
    print("\n--- Final state ---")
    final = SessionStore("s", STATE_JSONL_PATH).load()
    print(f"  Phase:            {YELLOW}{final.get('phase')}{RESET}")
    print(f"  Validation:       {YELLOW}{final.get('validation_result')}{RESET}")
    print(f"  PR status:        {YELLOW}{final.get('pr_status')}{RESET}")
    print(f"  CI status:        {YELLOW}{final.get('ci_status')}{RESET}")
    print(f"  Report written:   {YELLOW}{final.get('report_written')}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Implement workflow dry run")
    parser.add_argument("--tdd", action="store_true", help="Enable TDD mode")
    parser.add_argument(
        "--story-id", type=str, default=None, help="Story ID (e.g. SK-123)"
    )
    parser.add_argument("--skip-all", action="store_true")
    parser.add_argument("--skip-explore", action="store_true")
    parser.add_argument("--skip-research", action="store_true")
    args = parser.parse_args()

    skip_args = ""
    if args.skip_all:
        skip_args = "--skip-all"
    elif args.skip_explore and args.skip_research:
        skip_args = "--skip-all"
    elif args.skip_explore:
        skip_args = "--skip-explore"
    elif args.skip_research:
        skip_args = "--skip-research"
    else:
        skip_args = ""

    label = (
        f"TDD={'on' if args.tdd else 'off'}, story={'yes' if args.story_id else 'no'}"
    )
    print(f"\n{'='*60}")
    print(f"  Implement Dry Run  {YELLOW}[{label}]{RESET}")
    print(f"{'='*60}")

    # Back up current state
    original_state = STATE_JSONL_PATH.read_text() if STATE_JSONL_PATH.exists() else ""
    STATE_JSONL_PATH.write_text("")
    print(f"  {YELLOW}Using state.jsonl: {STATE_JSONL_PATH}{RESET}")
    print(f"  {YELLOW}(original state backed up, will be restored after){RESET}")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            simulate(args.tdd, args.story_id, skip_args, Path(tmp))
    finally:
        STATE_JSONL_PATH.write_text(original_state)
        print(f"  {YELLOW}state.jsonl restored.{RESET}")

    print_summary()
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
