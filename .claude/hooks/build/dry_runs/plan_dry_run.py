"""plan_dry_run.py — Simulate the /plan workflow end-to-end against unified guardrail.py.

Uses the real state.json (backed up and restored after the run).

Usage:
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-all
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-explore
    python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-research
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from build.session_store import SessionStore
from build.utils.initializer import initialize

GUARDRAIL = Path(__file__).resolve().parent.parent / "guardrail.py"
RECORDER = Path(__file__).resolve().parent.parent / "recorder.py"
STATE_JSONL_PATH = GUARDRAIL.parent / "state.jsonl"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

results: list[dict] = []


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def agent_payload(subagent_type: str, tool_use_id: str = "t1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": subagent_type, "description": "x", "prompt": "x", "run_in_background": False},
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def webfetch_payload(url: str, agent_id: str | None = None) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebFetch",
        "tool_input": {"url": url},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }
    if agent_id:
        payload["agent_id"] = agent_id
        payload["agent_type"] = "Research"
    return payload


def write_payload(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def post_write_payload(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_response": {"type": "update", "filePath": file_path, "content": content},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def exit_plan_mode_pre_payload() -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def subagent_stop_payload(agent_type: str, msg: str = "Done.") -> dict:
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
# run() helper
# ---------------------------------------------------------------------------

def run(label: str, payload: dict, expected: str, note: str = "") -> bool:
    hook_json = json.dumps(payload)
    result = subprocess.run(
        [sys.executable, str(GUARDRAIL), "--hook-input", hook_json, "--reason"],
        capture_output=True, text=True,
    )
    actual = result.stdout.strip()
    passed = actual.startswith(expected)
    results.append({"label": label, "expected": expected, "actual": actual, "passed": passed})

    # If guardrail allowed, also run the recorder for state tracking
    if actual.startswith("allow") or actual.startswith("{"):
        subprocess.run(
            [sys.executable, str(RECORDER), "--hook-input", hook_json],
            capture_output=True, text=True,
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
    print(f"  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  ({total} total)")
    if failed:
        print(f"\n  {RED}Failed:{RESET}")
        for r in results:
            if not r["passed"]:
                print(f"    - {r['label']}")
                print(f"      expected={r['expected']!r} got={r['actual']!r}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Plan content
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


# ---------------------------------------------------------------------------
# Simulate workflow
# ---------------------------------------------------------------------------

def simulate(skip_args: str, plan_dir: Path) -> None:
    skip_explore = "--skip-explore" in skip_args or "--skip-all" in skip_args
    skip_research = "--skip-research" in skip_args or "--skip-all" in skip_args

    # Pre-workflow: no restrictions
    print("\n--- Pre-workflow ---")
    run("Agent before workflow → allow", agent_payload("Explore"), "allow")
    run("Write before workflow → allow", write_payload("src/app.py"), "allow")

    # Activate /plan
    print(f"\n--- /plan {skip_args} ---")
    initialize("plan", "s", skip_args, STATE_JSONL_PATH)
    print(f"  {GREEN}PASS{RESET}  /plan {skip_args} → workflow initialized")
    results.append({"label": f"/plan {skip_args} → initialized", "expected": "allow", "actual": "allow", "passed": True})

    # Explore phase
    if not skip_explore:
        print("\n--- Explore phase ---")
        run("Explore [t1] → allow", agent_payload("Explore", "t1"), "allow")
        run("Explore [t2] → allow", agent_payload("Explore", "t2"), "allow")
        run("Explore [t3] → allow", agent_payload("Explore", "t3"), "allow")
        run("Explore [t4] over max → block", agent_payload("Explore", "t4"), "block", "Max 3 reached")

    if not skip_research:
        run("Research [t5] → allow", agent_payload("Research", "t5"), "allow")
        run("Research [t6] → allow", agent_payload("Research", "t6"), "allow")
        run("Research [t7] over max → block", agent_payload("Research", "t7"), "block", "Max 2 reached")

    # Phase gate: main agent blocked during explore
    print("\n--- Phase gate (explore) ---")
    run("Main agent Write → block (phase gate)", write_payload("src/app.py"), "block", "Only Agent tool allowed")
    run("Main agent WebFetch → block (phase gate)", webfetch_payload("https://github.com/foo"), "block", "Only Agent tool allowed")

    # WebFetch guard (subagent calls bypass phase gate)
    print("\n--- WebFetch guard (subagent) ---")
    run("Subagent WebFetch github.com → allow", webfetch_payload("https://github.com/foo", agent_id="sub1"), "allow")
    run("Subagent WebFetch evil.com → block", webfetch_payload("https://evil.example.com", agent_id="sub1"), "block", "Domain not allowed")

    # Plan agent blocked before explore done
    if not skip_explore or not skip_research:
        print("\n--- Plan agent requires explore first ---")
        run("Plan before explore done → block", agent_payload("Plan", "tp1"), "block")

    # Complete explore via SubagentStop
    if not skip_explore:
        print("\n--- Complete Explore agents ---")
        run("Explore [t1] done", subagent_stop_payload("Explore", "Found src/ with main modules and utils/"), "allow")
        run("Explore [t2] done", subagent_stop_payload("Explore", "Config lives in config.yaml, tests in tests/"), "allow")
        run("Explore [t3] done", subagent_stop_payload("Explore", "Auth module at src/auth.py uses JWT tokens"), "allow")

    if not skip_research:
        run("Research [t5] done", subagent_stop_payload("Research", "Best practice: use dependency injection for services"), "allow")
        run(
            "Research [t6] done → phase=plan",
            subagent_stop_payload("Research", "Latest docs recommend pydantic v2 for validation"),
            "allow",
            "Phase → plan",
        )

    # Plan phase
    print("\n--- Plan phase ---")
    run("Main agent Write → block (phase gate)", write_payload("notes.md"), "block", "Only Agent tool allowed")
    run("Plan agent → allow", agent_payload("Plan", "tp1"), "allow")
    run("Plan agent [tp2] over max → block", agent_payload("Plan", "tp2"), "block", "Max 1")
    run("PlanReview before plan done → block", agent_payload("PlanReview", "tr1"), "block")
    run("Plan SubagentStop → phase=write-plan", subagent_stop_payload("Plan", "Plan created."), "allow", "Phase → write-plan")

    # Write-plan phase
    print("\n--- Write-plan phase ---")
    run("Write code → block", write_payload("src/app.py"), "block")
    run("PlanReview before write → block", agent_payload("PlanReview", "tr1"), "block")

    plan_path = str(plan_dir / ".claude/plans/dry-run-plan.md")
    Path(plan_path).parent.mkdir(parents=True, exist_ok=True)
    run("Write to .claude/plans/ (pre) → allow", write_payload(plan_path, VALID_PLAN), "allow")

    Path(plan_path).write_text(VALID_PLAN)

    run("Write to .claude/plans/ (post) → allow", post_write_payload(plan_path, VALID_PLAN), "allow", "Phase → review, plan_written=True")

    # Review phase
    print("\n--- Review phase ---")
    run("PlanReview [tr1] → allow", agent_payload("PlanReview", "tr1"), "allow")
    run("PlanReview low scores → revision_needed", subagent_stop_payload("PlanReview", "Confidence: 60, Quality: 55"), "allow", "iteration=1")
    run("PlanReview [tr2] → allow", agent_payload("PlanReview", "tr2"), "allow")
    run("PlanReview high scores → approved", subagent_stop_payload("PlanReview", "Confidence: 92, Quality: 88"), "allow", "Phase → approved")

    # ExitPlanMode — valid plan
    print("\n--- ExitPlanMode (valid plan) ---")
    result_raw = subprocess.run(
        [sys.executable, str(GUARDRAIL), "--hook-input", json.dumps(exit_plan_mode_pre_payload())],
        capture_output=True, text=True,
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

    # ExitPlanMode — invalid plan
    print("\n--- ExitPlanMode (invalid plan) ---")
    bad_path = str(plan_dir / "bad-plan.md")
    store = SessionStore("s", STATE_JSONL_PATH)
    state_data = store.load()
    orig_plan = state_data.get("plan", {}).get("file_path")
    def _set_bad_plan(s: dict) -> None:
        s.setdefault("plan", {})["file_path"] = bad_path
    store.update(_set_bad_plan)
    Path(bad_path).write_text(INVALID_PLAN)
    run("ExitPlanMode invalid plan → block", exit_plan_mode_pre_payload(), "block", "Missing sections")
    def _restore_plan(s: dict) -> None:
        s.setdefault("plan", {})["file_path"] = orig_plan
    store.update(_restore_plan)

    # Final state
    print("\n--- Final state ---")
    final = SessionStore("s", STATE_JSONL_PATH).load()
    plan = final.get("plan", {})
    review = plan.get("review", {})
    print(f"  Phase: {YELLOW}{final.get('phase')}{RESET}")
    print(f"  Plan file: {YELLOW}{plan.get('file_path')}{RESET}")
    print(f"  Plan review status: {YELLOW}{review.get('status')}{RESET}")
    print(f"  Plan review scores: {YELLOW}{review.get('scores')}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan workflow dry run")
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
    print(f"  Plan Dry Run  {YELLOW}{skip_args or '(default)'}{RESET}")
    print(f"{'='*60}")

    # Back up current state
    original_state = STATE_JSONL_PATH.read_text() if STATE_JSONL_PATH.exists() else ""
    STATE_JSONL_PATH.write_text("")
    print(f"  {YELLOW}Using state.jsonl: {STATE_JSONL_PATH}{RESET}")
    print(f"  {YELLOW}(original state backed up, will be restored after){RESET}")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            simulate(skip_args, Path(tmp))
    finally:
        STATE_JSONL_PATH.write_text(original_state)
        print(f"  {YELLOW}state.jsonl restored.{RESET}")

    print_summary()
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
