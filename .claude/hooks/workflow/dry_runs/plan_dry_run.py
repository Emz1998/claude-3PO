"""plan_dry_run.py — Simulate the plan guardrail workflow end-to-end.

Uses real plan_guardrail.py subprocess calls to verify all guards work correctly.

Usage:
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-explore
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-research
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-all
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PLAN_GUARDRAIL = Path(__file__).resolve().parent.parent / "plan_guardrail.py"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

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


def webfetch_payload(url: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebFetch",
        "tool_input": {"url": url},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def websearch_payload(query: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebSearch",
        "tool_input": {"query": query},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def write_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "# Plan"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def post_write_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "# Plan"},
        "tool_response": {"type": "update", "filePath": file_path, "content": "# Plan"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def exit_plan_mode_payload() -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_use_id": "t1",
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


# ---------------------------------------------------------------------------
# run() — call plan_guardrail.py and check result
# ---------------------------------------------------------------------------

def run(pre: str, payload: dict, expected: str, state_path: Path, post: str = "") -> bool:
    env = {**os.environ, "PLAN_GUARDRAIL_STATE_PATH": str(state_path)}
    result = subprocess.run(
        [sys.executable, str(PLAN_GUARDRAIL), "--hook-input", json.dumps(payload), "--reason"],
        capture_output=True, text=True, env=env,
    )
    actual = result.stdout.strip()
    passed = actual.startswith(expected)
    results.append({"label": pre, "expected": expected, "actual": actual, "passed": passed})

    time.sleep(0.1)

    if not passed:
        status = f"{RED}FAIL{RESET}"
    elif expected == "block":
        status = f"{RED}BLOCK{RESET}"
    else:
        status = f"{GREEN}PASS{RESET}"

    label_short = pre[:60]
    print(f"  {status}  {label_short}")
    if not passed:
        print(f"         expected: {expected!r}")
        print(f"         got:      {actual!r}")
        if result.stderr:
            print(f"         stderr:   {result.stderr.strip()}")
    elif post:
        print(f"         {YELLOW}{post}{RESET}")
    return passed


def print_summary() -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  ({total} total)")
    if failed:
        print(f"\n  {RED}Failed scenarios:{RESET}")
        for r in results:
            if not r["passed"]:
                print(f"    - {r['label']}")
                print(f"      expected={r['expected']!r} got={r['actual']!r}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Plan file helpers
# ---------------------------------------------------------------------------

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

INVALID_PLAN = """# Bad Plan

## Steps
Do stuff without context or verification.
"""


def simulate_workflow(state_path: Path, skip_args: str, tmp_dir: Path) -> None:

    # ------------------------------------------------------------------
    # Pre-workflow blocks
    # ------------------------------------------------------------------
    print("\n--- Pre-workflow: no restrictions ---")
    run("Agent before workflow active → allow",
        agent_payload("Explore"), "allow", state_path,
        "Workflow not active — pass through")
    run("Write outside plans dir before workflow → allow",
        write_payload("src/app.py"), "allow", state_path,
        "Workflow not active — pass through")

    # ------------------------------------------------------------------
    # Skill interception: /plan
    # ------------------------------------------------------------------
    print(f"\n--- Skill interception: /plan {skip_args} ---")
    run(f"/plan {skip_args} → activates workflow",
        skill_payload("plan", skip_args), "allow", state_path,
        "Workflow activated")
    run("Non-plan skill → allow, no state change",
        skill_payload("explore"), "allow", state_path)

    # ------------------------------------------------------------------
    # Explore phase (or skipped)
    # ------------------------------------------------------------------
    skip_explore = "--skip-explore" in skip_args or "--skip-all" in skip_args
    skip_research = "--skip-research" in skip_args or "--skip-all" in skip_args

    if not skip_explore:
        print("\n--- Explore phase: Explore agents ---")
        run("Explore [t1] → allow",
            agent_payload("Explore", "t1"), "allow", state_path)
        run("Explore [t2] → allow",
            agent_payload("Explore", "t2"), "allow", state_path)
        run("Explore [t3] → allow",
            agent_payload("Explore", "t3"), "allow", state_path)
        run("Explore [t4] over max 3 → block",
            agent_payload("Explore", "t4"), "block", state_path,
            "Max 3 reached")

    if not skip_research:
        print("\n--- Explore phase: Research agents ---")
        run("Research [t5] → allow",
            agent_payload("Research", "t5"), "allow", state_path)
        run("Research [t6] → allow",
            agent_payload("Research", "t6"), "allow", state_path)
        run("Research [t7] over max 2 → block",
            agent_payload("Research", "t7"), "block", state_path,
            "Max 2 reached")

    # ------------------------------------------------------------------
    # WebFetch / WebSearch guard (Research agents use these)
    # ------------------------------------------------------------------
    print("\n--- WebFetch/WebSearch guard ---")
    run("WebFetch safe domain (github.com) → allow",
        webfetch_payload("https://github.com/anthropics/claude"), "allow", state_path)
    run("WebFetch unsafe domain → block",
        webfetch_payload("https://evil.example.com/page"), "block", state_path,
        "Domain not allowed")
    run("WebSearch → allow",
        websearch_payload("python async patterns"), "allow", state_path)

    # ------------------------------------------------------------------
    # Plan agent blocked before explorers done
    # ------------------------------------------------------------------
    if not skip_explore or not skip_research:
        print("\n--- Plan agent: requires explore complete ---")
        run("Plan before explore done → block",
            agent_payload("Plan", "tp1"), "block", state_path,
            "Requires explore/research first")

    # ------------------------------------------------------------------
    # Complete explore via SubagentStop
    # ------------------------------------------------------------------
    if not skip_explore:
        print("\n--- SubagentStop: completing Explore agents ---")
        run("Explore [t1] done", stop_payload("Explore"), "allow", state_path)
        run("Explore [t2] done", stop_payload("Explore"), "allow", state_path)
        run("Explore [t3] done", stop_payload("Explore"), "allow", state_path)

    if not skip_research:
        run("Research [t5] done", stop_payload("Research"), "allow", state_path)
        last_research_msg = "Research [t6] done"
        if not skip_explore:
            last_research_msg += " — phase should advance to plan"
        run(last_research_msg, stop_payload("Research"), "allow", state_path,
            "Phase → plan")

    # ------------------------------------------------------------------
    # Plan phase
    # ------------------------------------------------------------------
    print("\n--- Plan phase ---")
    run("Plan agent → allow",
        agent_payload("Plan", "tp1"), "allow", state_path)
    run("Plan agent [tp2] over max 1 → block",
        agent_payload("Plan", "tp2"), "block", state_path,
        "Max 1 reached")
    run("Plan-Review before plan done → block",
        agent_payload("Plan-Review", "tr1"), "block", state_path,
        "Not in review phase")
    run("Plan agent SubagentStop → phase=write",
        stop_payload("Plan", "I have created the plan."), "allow", state_path,
        "Phase → write")

    # ------------------------------------------------------------------
    # Write phase
    # ------------------------------------------------------------------
    print("\n--- Write phase ---")
    run("Write outside .claude/plans/ → block",
        write_payload("src/app.py"), "block", state_path,
        "Must write to .claude/plans/")

    run("Plan-Review before plan write → block",
        agent_payload("Plan-Review", "tr1"), "block", state_path,
        "Write must succeed first")

    plan_path = str(tmp_dir / ".claude/plans/my-plan.md")

    run("Write to .claude/plans/my-plan.md (pre) → allow",
        write_payload(plan_path), "allow", state_path)

    Path(plan_path).parent.mkdir(parents=True, exist_ok=True)
    Path(plan_path).write_text(VALID_PLAN)

    run("Write to .claude/plans/my-plan.md (post) → allow",
        post_write_payload(plan_path), "allow", state_path,
        "Phase → review, plan_file recorded")

    # ------------------------------------------------------------------
    # Review phase
    # ------------------------------------------------------------------
    print("\n--- Review phase ---")
    run("Plan-Review [tr1] → allow",
        agent_payload("Plan-Review", "tr1"), "allow", state_path)

    # Failing review → revision
    run("Plan-Review done (low scores) → revision_needed",
        stop_payload("Plan-Review", "Confidence score: 60, Quality score: 55"),
        "allow", state_path, "iteration=1, revision_needed")

    # Re-run review
    run("Plan-Review [tr2] → allow (iteration 2)",
        agent_payload("Plan-Review", "tr2"), "allow", state_path)

    # Passing review → approved phase
    run("Plan-Review done (high scores) → approved, phase=approved",
        stop_payload("Plan-Review", "Confidence score: 92, Quality score: 88"),
        "allow", state_path, "Phase → approved")

    # ------------------------------------------------------------------
    # ExitPlanMode — valid plan
    # ------------------------------------------------------------------
    print("\n--- ExitPlanMode: valid plan ---")
    result_raw = subprocess.run(
        [sys.executable, str(PLAN_GUARDRAIL), "--hook-input", json.dumps(exit_plan_mode_payload())],
        capture_output=True, text=True,
        env={**os.environ, "PLAN_GUARDRAIL_STATE_PATH": str(state_path)},
    ).stdout.strip()

    if result_raw.startswith("{"):
        data = json.loads(result_raw)
        if "additionalContext" in data:
            print(f"  {GREEN}PASS{RESET}  ExitPlanMode valid → surfaces additionalContext")
            results.append({"label": "ExitPlanMode valid", "expected": "{", "actual": result_raw, "passed": True})
        else:
            print(f"  {RED}FAIL{RESET}  ExitPlanMode: unexpected JSON: {result_raw[:80]}")
            results.append({"label": "ExitPlanMode valid", "expected": "additionalContext", "actual": result_raw, "passed": False})
    else:
        print(f"  {RED}FAIL{RESET}  ExitPlanMode valid → expected JSON, got: {result_raw[:80]}")
        results.append({"label": "ExitPlanMode valid", "expected": "additionalContext", "actual": result_raw, "passed": False})

    # ------------------------------------------------------------------
    # ExitPlanMode — invalid plan
    # ------------------------------------------------------------------
    print("\n--- ExitPlanMode: invalid plan ---")
    bad_path = str(tmp_dir / ".claude/plans/bad-plan.md")

    # Temporarily update state to point to bad plan
    state_data = json.loads(state_path.read_text())
    original_plan_file = state_data.get("plan_workflow", {}).get("plan_file")
    state_data.setdefault("plan_workflow", {})["plan_file"] = bad_path
    state_path.write_text(json.dumps(state_data))

    Path(bad_path).write_text(INVALID_PLAN)
    run("ExitPlanMode invalid plan → block",
        exit_plan_mode_payload(), "block", state_path,
        "Missing sections listed")

    # Restore original plan_file
    state_data["plan_workflow"]["plan_file"] = original_plan_file
    state_path.write_text(json.dumps(state_data))

    # ------------------------------------------------------------------
    # Post-workflow state check
    # ------------------------------------------------------------------
    print("\n--- Final state ---")
    final_state = json.loads(state_path.read_text())
    pw = final_state.get("plan_workflow", {})
    print(f"  Phase: {YELLOW}{pw.get('phase')}{RESET}")
    print(f"  Plan file: {YELLOW}{pw.get('plan_file')}{RESET}")
    review = pw.get("review", {})
    print(f"  Review status: {YELLOW}{review.get('status')}{RESET}")
    print(f"  Review scores: {YELLOW}{review.get('scores')}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan guardrail dry run")
    parser.add_argument("--skip-explore", action="store_true")
    parser.add_argument("--skip-research", action="store_true")
    parser.add_argument("--skip-all", action="store_true")
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

    print(f"\n{'='*60}")
    print(f"  Plan Guardrail Dry Run  {YELLOW}{skip_args or '(default)'}{RESET}")
    print(f"{'='*60}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        state_path = tmp_dir / "state.json"
        state_path.write_text("{}")

        simulate_workflow(state_path, skip_args, tmp_dir)

    print_summary()
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
