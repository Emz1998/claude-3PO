"""dry_run.py — Simulate a full workflow end-to-end using real guardrail.py subprocess calls.

Replays the exact hook payloads the real system sends, verifying all guards work correctly
in sequence using real shared state.

Usage:
    python3 .claude/hooks/workflow/dry_run.py           # non-TDD
    python3 .claude/hooks/workflow/dry_run.py --tdd     # with TDD write-tests phase
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

GUARDRAIL = Path(__file__).resolve().parent / "guardrail.py"
PHASE_ORDER = [
    "explore", "decision", "plan",
    "write-tests", "write-code", "validate", "pr-create",
]

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

results: list[dict] = []


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------

def make_initial_state(tdd: bool) -> dict:
    phases = [
        {"name": name, "status": "pending", "agents": [], "files_created": []}
        for name in PHASE_ORDER
    ]
    return {
        "workflow_active": True,
        "workflow_type": None,
        "session_id": None,
        "story_id": None,
        "TDD": tdd,
        "phases": phases,
        "ci": {"status": "inactive"},
        "review": {
            "plan": {
                "status": None, "iteration": 0, "max_iterations": 3,
                "scores": {"confidence": None, "quality": None},
                "threshold": {"confidence": 80, "quality": 80},
            },
            "tests": {
                "status": None, "iteration": 0, "max_iterations": 3,
                "scores": {"confidence": None, "quality": None},
                "threshold": {"confidence": 80, "quality": 80},
            },
        },
    }


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def skill_payload(skill: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill, "args": ""},
        "tool_use_id": "t0",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def agent_payload(subagent_type: str, tool_use_id: str, run_in_background: bool = False) -> dict:
    tool_input: dict = {"subagent_type": subagent_type, "description": "x", "prompt": "x"}
    if run_in_background:
        tool_input["run_in_background"] = True
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": tool_input,
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def stop_payload(agent_type: str, msg: str = "Done.") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": msg,
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def write_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t0",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def bash_payload(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "x"},
        "tool_use_id": "t0",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def task_create_post_payload(claude_id: str, subject: str, description: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "TaskCreate",
        "tool_input": {"subject": subject, "description": description},
        "tool_response": {"task": {"id": claude_id, "subject": subject}},
        "tool_use_id": f"tc{claude_id}",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def task_list_post_payload(tasks: list) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "TaskList",
        "tool_input": {},
        "tool_response": {"tasks": tasks},
        "tool_use_id": "tl1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def stop_event() -> dict:
    return {
        "hook_event_name": "Stop",
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
    }


# ---------------------------------------------------------------------------
# run() — call guardrail.py and check result
# ---------------------------------------------------------------------------

def run(pre: str, payload: dict, expected: str, state_path: Path, post: str = "") -> bool:
    """Print activity, call guardrail, sleep, then print result."""
    print(f"\n  {pre}")

    env = {**os.environ, "GUARDRAIL_STATE_PATH": str(state_path)}
    result = subprocess.run(
        [sys.executable, str(GUARDRAIL), "--hook-input", json.dumps(payload), "--reason"],
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
# force_complete_phase — directly advance state, bypassing guardrail
# ---------------------------------------------------------------------------

def force_complete_phase(phase_name: str, state_path: Path) -> None:
    """Mark phase completed and advance next pending phase to in_progress.

    Mirrors review_guard._advance_next_phase logic exactly. Used for phases
    with no SubagentStop path (write-tests in non-TDD, write-code).
    """
    state = json.loads(state_path.read_text())
    phases = state["phases"]

    for p in phases:
        if p["name"] == phase_name:
            p["status"] = "completed"
            break

    current_idx = PHASE_ORDER.index(phase_name)
    if current_idx + 1 < len(PHASE_ORDER):
        next_name = PHASE_ORDER[current_idx + 1]
        for p in phases:
            if p["name"] == next_name and p["status"] == "pending":
                p["status"] = "in_progress"
                break

    state_path.write_text(json.dumps(state, indent=2))
    print(f"\n  {YELLOW}[ADVANCE: {phase_name} → completed]{RESET}")


# ---------------------------------------------------------------------------
# simulate_workflow
# ---------------------------------------------------------------------------

def simulate_workflow(state_path: Path, tdd: bool) -> None:
    # ------------------------------------------------------------------
    # Up-front BLOCK checks
    # ------------------------------------------------------------------
    print("\n--- Guardrail checks (pre-workflow) ---")
    run("Writing /project/main.py...",
        write_payload("/project/main.py"), "block", state_path,
        "Blocked — plan not yet complete")
    run("Running: git push origin main",
        bash_payload("git push origin main"), "block", state_path,
        "Blocked — workflow phases not complete")
    run("Launching qa-expert...",
        agent_payload("qa-expert", "t0"), "block", state_path,
        "Blocked — no active phase")
    run("Session stop requested",
        stop_event(), "block", state_path,
        "Blocked — workflow still pending")

    # ------------------------------------------------------------------
    # task-manager (prerequisite for explore)
    # ------------------------------------------------------------------
    print("\n--- task-manager (prerequisite) ---")
    run("Invoking skill: explore (before task-manager — should block)",
        skill_payload("explore"), "block", state_path,
        "Blocked — task-manager must run first")

    # Simulate task-manager agent launching
    run("Launching task-manager agent...",
        agent_payload("task-manager", "tm1"), "allow", state_path,
        "task-manager registered")

    # Simulate 3 TaskCreate PostToolUse calls (matching SK-001 real tasks)
    project_tasks = [
        ("T-017", "Feature importance analysis documented in decisions.md with top 10 features ranked",
         "Perform feature importance analysis and document findings"),
        ("T-018", "Recommendation includes feature set with pros/cons and expected accuracy impact",
         "Develop feature set recommendations with trade-offs"),
        ("T-019", "Prototype training script tests at least 3 different feature combinations",
         "Create prototype training script with multiple feature combinations"),
    ]
    for i, (tid, title, desc) in enumerate(project_tasks):
        subject = f"{tid}: {title}"
        run(f"TaskCreate PostToolUse: {tid}",
            task_create_post_payload(str(i + 1), subject, desc), "allow", state_path,
            f"Task '{tid}' recorded")

    # Simulate SubagentStop for task-manager WITHOUT TaskList — should block
    run("task-manager SubagentStop (no TaskList — should block)",
        stop_payload("task-manager", "Tasks created for story SK-001."), "block", state_path,
        "Blocked — no TaskList snapshot found")

    # Now simulate TaskList PostToolUse (T-018 blocked by T-017="1", T-019 blocked by T-018="2")
    snapshot_tasks = [
        {"id": "1", "subject": "T-017: Feature importance analysis documented in decisions.md with top 10 features ranked", "status": "pending", "blockedBy": []},
        {"id": "2", "subject": "T-018: Recommendation includes feature set with pros/cons and expected accuracy impact", "status": "pending", "blockedBy": ["1"]},
        {"id": "3", "subject": "T-019: Prototype training script tests at least 3 different feature combinations", "status": "pending", "blockedBy": ["2"]},
    ]
    run("TaskList PostToolUse: recording snapshot",
        task_list_post_payload(snapshot_tasks), "allow", state_path,
        "Task list snapshot recorded")

    # Simulate SubagentStop for task-manager (should pass now)
    run("task-manager SubagentStop (validation should pass)",
        stop_payload("task-manager", "Tasks created for story SK-001."), "allow", state_path,
        "task-manager complete — task_manager_completed=True")

    # ------------------------------------------------------------------
    # explore
    # ------------------------------------------------------------------
    print("\n--- Phase: explore ---")
    run("Invoking skill: explore (after task-manager — should allow)",
        skill_payload("explore"), "allow", state_path,
        "explore phase activated")
    run("Launching codebase-explorer [t1] (background)...",
        agent_payload("codebase-explorer", "t1", run_in_background=True), "allow", state_path,
        "codebase-explorer [t1] registered")
    run("Launching codebase-explorer [t2] (background)...",
        agent_payload("codebase-explorer", "t2", run_in_background=True), "allow", state_path,
        "codebase-explorer [t2] registered")
    run("Launching codebase-explorer [t3] (background)...",
        agent_payload("codebase-explorer", "t3", run_in_background=True), "allow", state_path,
        "codebase-explorer [t3] registered")
    run("Launching research-specialist [t4] (background)...",
        agent_payload("research-specialist", "t4", run_in_background=True), "allow", state_path,
        "research-specialist [t4] registered")
    run("Launching research-specialist [t5]...",
        agent_payload("research-specialist", "t5"), "allow", state_path,
        "research-specialist [t5] registered")
    run("codebase-explorer [t1]: scanning repository structure...",
        stop_payload("codebase-explorer"), "allow", state_path,
        "Explorer done (1/3)")
    run("codebase-explorer [t2]: analyzing dependencies and architecture...",
        stop_payload("codebase-explorer"), "allow", state_path,
        "Explorer done (2/3)")
    run("codebase-explorer [t3]: reviewing test coverage and patterns...",
        stop_payload("codebase-explorer"), "allow", state_path,
        "Explorer done (3/3)")
    run("research-specialist [t4]: investigating best practices and patterns...",
        stop_payload("research-specialist"), "allow", state_path,
        "Researcher done (1/2)")
    run("research-specialist [t5]: reviewing documentation and prior art...",
        stop_payload("research-specialist"), "allow", state_path,
        "Researcher done (2/2) — explore complete, decision phase started")

    # ------------------------------------------------------------------
    # decision
    # ------------------------------------------------------------------
    print("\n--- Phase: decision ---")
    run("Invoking skill: decision",
        skill_payload("decision"), "allow", state_path,
        "decision phase already active")
    run("Launching tech-lead [t6]...",
        agent_payload("tech-lead", "t6"), "allow", state_path,
        "tech-lead [t6] registered")
    run("tech-lead [t6]: synthesizing findings into a technical decision...",
        stop_payload("tech-lead"), "allow", state_path,
        "Decision recorded — plan phase started")

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------
    print("\n--- Phase: plan ---")
    run("Invoking skill: plan",
        skill_payload("plan"), "allow", state_path,
        "Plan phase already active")
    run("Launching plan-reviewer (before plan-specialist)...",
        agent_payload("plan-reviewer", "t0"), "block", state_path,
        "Blocked — plan-specialist must complete first")
    run("Launching plan-specialist [t7]...",
        agent_payload("plan-specialist", "t7"), "allow", state_path,
        "plan-specialist [t7] registered")
    run("plan-specialist [t7]: drafting implementation plan...",
        stop_payload("plan-specialist"), "allow", state_path,
        "Plan draft complete")
    run("Launching plan-reviewer [t8]...",
        agent_payload("plan-reviewer", "t8"), "allow", state_path,
        "plan-reviewer [t8] registered")
    run("plan-reviewer [t8]: reviewing plan quality and confidence...",
        stop_payload("plan-reviewer", "Confidence Score: 85\nQuality Score: 90"), "allow", state_path,
        "Plan approved (confidence: 85, quality: 90) — write-tests phase started")

    # ------------------------------------------------------------------
    # write-tests — TDD only; non-TDD: force_complete + skip
    # ------------------------------------------------------------------
    if tdd:
        print("\n--- Phase: write-tests (TDD) ---")
        run("Invoking skill: write-tests",
            skill_payload("write-tests"), "allow", state_path,
            "Write-tests phase already active")
        run("Launching test-engineer [t9]...",
            agent_payload("test-engineer", "t9"), "allow", state_path,
            "test-engineer [t9] registered")
        run("test-engineer [t9]: writing failing tests (red phase)...",
            stop_payload("test-engineer"), "allow", state_path,
            "Failing tests written")
        run("Launching test-reviewer [t10]...",
            agent_payload("test-reviewer", "t10"), "allow", state_path,
            "test-reviewer [t10] registered")
        run("test-reviewer [t10]: reviewing test coverage and quality...",
            stop_payload("test-reviewer", "Confidence: 85\nQuality: 88"), "allow", state_path,
            "Tests approved (confidence: 85, quality: 88) — write-code phase started")
    else:
        print("\n--- Phase: write-tests (skipped — TDD=false) ---")
        force_complete_phase("write-tests", state_path)

    # ------------------------------------------------------------------
    # write-code
    # ------------------------------------------------------------------
    print("\n--- Phase: write-code ---")
    run("Invoking skill: write-code",
        skill_payload("write-code"), "allow", state_path,
        "Write-code phase already active")
    run("Launching codebase-explorer in write-code phase...",
        agent_payload("codebase-explorer", "t0"), "block", state_path,
        "Blocked — no subagents allowed in write-code, main agent writes directly")
    run("Writing /project/main.py...",
        write_payload("/project/main.py"), "allow", state_path,
        "File write allowed — plan complete, tests done")
    force_complete_phase("write-code", state_path)

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    print("\n--- Phase: validate ---")
    run("Invoking skill: validate",
        skill_payload("validate"), "allow", state_path,
        "Validate phase already active")
    run("Launching qa-expert [t11]...",
        agent_payload("qa-expert", "t11"), "allow", state_path,
        "qa-expert [t11] registered")
    run("qa-expert [t11]: validating all acceptance criteria...",
        stop_payload("qa-expert"), "allow", state_path,
        "Validation complete — pr-create phase started")

    # ------------------------------------------------------------------
    # pr-create
    # ------------------------------------------------------------------
    print("\n--- Phase: pr-create ---")
    run("Invoking skill: pr-create",
        skill_payload("pr-create"), "allow", state_path,
        "PR-create phase already active")
    run("Launching version-manager [t12]...",
        agent_payload("version-manager", "t12"), "allow", state_path,
        "version-manager [t12] registered")
    run("version-manager [t12]: creating pull request with conventional commits...",
        stop_payload("version-manager"), "allow", state_path,
        "Pull request created — workflow complete")

    # ------------------------------------------------------------------
    # Post-workflow checks
    # ------------------------------------------------------------------
    print("\n--- Post-workflow checks ---")
    run("Running: git push origin main",
        bash_payload("git push origin main"), "allow", state_path,
        "Push allowed — all phases complete")
    run("Session stop requested",
        stop_event(), "allow", state_path,
        "Stop allowed — workflow complete")


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
        for r in results:
            if not r["passed"]:
                print(f"    - {r['label']}")
                print(f"      expected: {r['expected']!r}, got: {r['actual']!r}")
    color = GREEN if failed == 0 else RED
    print(f"\n  {color}{'ALL PASS' if failed == 0 else f'{failed} FAILED'}{RESET}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run the workflow guardrail end-to-end")
    parser.add_argument("--tdd", action="store_true", help="Include write-tests phase (TDD mode)")
    args = parser.parse_args()

    state_path = GUARDRAIL.parent / "state.json"
    state_path.write_text(json.dumps(make_initial_state(args.tdd), indent=2))

    mode = "TDD" if args.tdd else "non-TDD"
    print(f"\nDry-run workflow guardrail ({mode})")
    print(f"State file: {state_path}")

    simulate_workflow(state_path, args.tdd)
    print_summary()

    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
