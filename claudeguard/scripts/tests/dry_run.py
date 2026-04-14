#!/usr/bin/env python3
"""dry_run.py — E2E simulation of the hook system using JSONL state.

Pipes JSON payloads to pre_tool_use.py, post_tool_use.py, subagent_stop.py,
and stop.py, verifying allow/block decisions at each step.

Usage:
    python3 scripts/tests/dry_run.py
    python3 scripts/tests/dry_run.py --tdd
    python3 scripts/tests/dry_run.py --implement
    python3 scripts/tests/dry_run.py --implement --tdd
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = SCRIPTS_DIR / "state.jsonl"

PRE_TOOL_USE = SCRIPTS_DIR / "pre_tool_use.py"
POST_TOOL_USE = SCRIPTS_DIR / "post_tool_use.py"
SUBAGENT_STOP = SCRIPTS_DIR / "subagent_stop.py"
STOP_HOOK = SCRIPTS_DIR / "stop.py"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

SESSION_ID = "dry-run"

results: list[dict] = []


# ═══════════════════════════════════════════════════════════════════
# State helpers
# ═══════════════════════════════════════════════════════════════════


def make_default_state(workflow_type: str = "build") -> dict:
    return {
        "session_id": SESSION_ID,
        "workflow_active": True,
        "status": "in_progress",
        "workflow_type": workflow_type,
        "phases": [],
        "tdd": False,
        "story_id": "DRY-001",
        "skip": [],
        "instructions": "",
        "agents": [],
        "plan": {
            "file_path": None,
            "written": False,
            "revised": None,
            "reviews": [],
        },
        "tasks": [],
        "project_tasks": [],
        "dependencies": {"packages": [], "installed": False},
        "contracts": {
            "file_path": None,
            "names": [],
            "code_files": [],
            "written": False,
            "validated": False,
        },
        "tests": {"file_paths": [], "executed": False, "reviews": [], "files_to_revise": [], "files_revised": []},
        "code_files_to_write": [],
        "code_files": {
            "file_paths": [],
            "reviews": [],
            "tests_to_revise": [],
            "tests_revised": [],
            "files_to_revise": [],
            "files_revised": [],
        },
        "quality_check_result": None,
        "pr": {"status": "pending", "number": None},
        "ci": {"status": "pending", "results": None},
        "report_written": False,
        "plan_files_to_modify": [],
    }


def reset_state(workflow_type: str = "build") -> None:
    state = make_default_state(workflow_type)
    line = json.dumps(state, separators=(",", ":"))
    STATE_PATH.write_text(line + "\n")


def read_state() -> dict:
    content = STATE_PATH.read_text().strip()
    for line in content.splitlines():
        entry = json.loads(line)
        if entry.get("session_id") == SESSION_ID:
            return entry
    return {}


def write_state(s: dict) -> None:
    s["session_id"] = SESSION_ID
    line = json.dumps(s, separators=(",", ":"))
    STATE_PATH.write_text(line + "\n")


# ═══════════════════════════════════════════════════════════════════
# Payload builders
# ═══════════════════════════════════════════════════════════════════


def skill_payload(skill: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill},
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def agent_payload(agent_type: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": agent_type, "description": "x", "prompt": "x"},
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def write_payload(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def edit_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "x", "new_string": "y"},
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def bash_payload(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def post_bash_payload(command: str, output: str = "") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_result": output,
        "tool_use_id": "t1",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def subagent_stop_payload(agent_type: str, message: str = "Done.") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "subagent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": message,
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
        "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def stop_payload(active: bool = False) -> dict:
    return {
        "hook_event_name": "Stop",
        "stop_hook_active": active,
        "last_assistant_message": "I'm done.",
        "session_id": SESSION_ID,
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


# ═══════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════


def run(label: str, script: Path, payload: dict, expect_block: bool, note: str = "") -> bool:
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    exit_code = result.returncode

    is_blocked = exit_code == 2 or "deny" in stdout or '"block"' in stdout
    passed = is_blocked == expect_block

    results.append({"label": label, "passed": passed})
    time.sleep(0.02)

    expected_str = "BLOCK" if expect_block else "ALLOW"
    actual_str = "BLOCK" if is_blocked else "ALLOW"

    if passed:
        color = RED if expect_block else GREEN
        print(f"  {color}{actual_str}{RESET}  {label}")
    else:
        print(f"  {RED}FAIL{RESET}  {label}")
        print(f"         expected: {expected_str}, got: {actual_str}")
        if stderr:
            print(f"         stderr: {stderr[:200]}")
        if stdout:
            print(f"         stdout: {stdout[:200]}")

    if note and passed:
        print(f"         {YELLOW}{note}{RESET}")

    return passed


def allow(label: str, script: Path, payload: dict, note: str = "") -> bool:
    return run(label, script, payload, expect_block=False, note=note)


def block(label: str, script: Path, payload: dict, note: str = "") -> bool:
    return run(label, script, payload, expect_block=True, note=note)


# ═══════════════════════════════════════════════════════════════════
# Build simulation (original)
# ═══════════════════════════════════════════════════════════════════


def simulate_build(tdd: bool) -> None:
    print("\n--- Explore phase ---")
    s = read_state()
    s["phases"] = [{"name": "explore", "status": "in_progress"}]
    write_state(s)

    allow("Read command in explore", PRE_TOOL_USE, bash_payload("ls -la"))
    block("Write blocked in explore", PRE_TOOL_USE, write_payload("notes.md"))
    allow("Explore agent allowed", PRE_TOOL_USE, agent_payload("Explore"))
    block("Wrong agent blocked", PRE_TOOL_USE, agent_payload("Plan"))

    # Research parallel
    s = read_state()
    s["agents"].append({"name": "Explore", "status": "in_progress", "tool_use_id": "e-1"})
    write_state(s)
    allow("Research parallel with explore", PRE_TOOL_USE, agent_payload("Research"))

    print("\n--- Plan phase ---")
    s = read_state()
    s["phases"] = [
        {"name": "explore", "status": "completed"},
        {"name": "research", "status": "completed"},
        {"name": "plan", "status": "in_progress"},
    ]
    s["agents"].append({"name": "Plan", "status": "completed", "tool_use_id": "p-1"})
    write_state(s)

    plan_content = "# Plan\n\n## Dependencies\n- flask\n\n## Tasks\n- Build login\n\n## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"
    allow("Write plan file", PRE_TOOL_USE, write_payload(".claude/plans/latest-plan.md", plan_content))
    block("Write wrong plan path", PRE_TOOL_USE, write_payload("wrong.md"))

    print("\n--- Plan review phase ---")
    s = read_state()
    s["phases"].append({"name": "plan-review", "status": "in_progress"})
    s["phases"][2]["status"] = "completed"
    s["plan"]["file_path"] = ".claude/plans/latest-plan.md"
    s["plan"]["written"] = True
    write_state(s)

    allow("PlanReview agent", PRE_TOOL_USE, agent_payload("PlanReview"))

    # Auto-phase skill invocation blocked
    print("\n--- Auto-phase blocking ---")
    block("write-tests skill blocked", PRE_TOOL_USE, skill_payload("write-tests"),
          note="Auto-phases cannot be invoked as skills")
    block("write-code skill blocked", PRE_TOOL_USE, skill_payload("write-code"),
          note="Auto-phases cannot be invoked as skills")

    print("\n--- PR create phase ---")
    s = read_state()
    s["phases"] = [
        {"name": "explore", "status": "completed"},
        {"name": "research", "status": "completed"},
        {"name": "plan", "status": "completed"},
        {"name": "plan-review", "status": "completed"},
        {"name": "install-deps", "status": "completed"},
        {"name": "define-contracts", "status": "completed"},
        {"name": "write-tests", "status": "completed"},
        {"name": "test-review", "status": "completed"},
        {"name": "write-code", "status": "completed"},
        {"name": "quality-check", "status": "completed"},
        {"name": "code-review", "status": "completed"},
        {"name": "pr-create", "status": "in_progress"},
    ]
    write_state(s)

    block("PR create without --json", PRE_TOOL_USE, bash_payload("gh pr create --title test"))
    allow("PR create with --json", PRE_TOOL_USE, bash_payload("gh pr create --json number"))

    pr_output = json.dumps({"number": 42, "url": "https://github.com/org/repo/pull/42"})
    allow("PR create output recorded", POST_TOOL_USE, post_bash_payload("gh pr create --json number", pr_output))

    print("\n--- CI check phase ---")
    s = read_state()
    s["phases"].append({"name": "ci-check", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "pr-create":
            p["status"] = "completed"
    s["pr"] = {"status": "created", "number": 42}
    write_state(s)

    ci_pass = json.dumps([{"name": "build", "conclusion": "SUCCESS"}, {"name": "test", "conclusion": "SUCCESS"}])
    allow("CI pass recorded", POST_TOOL_USE, post_bash_payload("gh pr checks --json name,conclusion", ci_pass))

    print("\n--- Write report phase ---")
    s = read_state()
    s["phases"].append({"name": "write-report", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "ci-check":
            p["status"] = "completed"
    write_state(s)

    allow("Write report", PRE_TOOL_USE, write_payload(".claude/reports/report.md"))


# ═══════════════════════════════════════════════════════════════════
# Implement simulation
# ═══════════════════════════════════════════════════════════════════


def simulate_implement(tdd: bool) -> None:
    print("\n--- Explore phase (implement) ---")
    s = read_state()
    s["phases"] = [{"name": "explore", "status": "in_progress"}]
    write_state(s)

    allow("Read command in explore", PRE_TOOL_USE, bash_payload("ls -la"))
    block("Write blocked in explore", PRE_TOOL_USE, write_payload("notes.md"))

    print("\n--- Plan phase (implement) ---")
    s = read_state()
    s["phases"] = [
        {"name": "explore", "status": "completed"},
        {"name": "research", "status": "completed"},
        {"name": "plan", "status": "in_progress"},
    ]
    s["agents"].append({"name": "Plan", "status": "completed", "tool_use_id": "p-1"})
    write_state(s)

    impl_plan = (
        "# Plan\n\n## Context\n\nSome context.\n\n"
        "## Approach\n\nSome approach.\n\n"
        "## Files to Create/Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n\n"
        "## Verification\n\nRun tests.\n"
    )
    allow("Write implement plan", PRE_TOOL_USE, write_payload(".claude/plans/latest-plan.md", impl_plan))

    # Build plan should be blocked in implement workflow
    build_plan = "# Plan\n\n## Dependencies\n- flask\n\n## Contracts\n- UserService\n\n## Tasks\n- Build login\n"
    block("Build plan blocked in implement", PRE_TOOL_USE, write_payload(".claude/plans/latest-plan.md", build_plan))

    print("\n--- Plan review (implement) ---")
    s = read_state()
    s["phases"].append({"name": "plan-review", "status": "in_progress"})
    s["phases"][2]["status"] = "completed"
    s["plan"]["file_path"] = ".claude/plans/latest-plan.md"
    s["plan"]["written"] = True
    write_state(s)

    allow("PlanReview agent", PRE_TOOL_USE, agent_payload("PlanReview"))

    print("\n--- Auto-phase blocking (implement) ---")
    block("create-tasks skill blocked", PRE_TOOL_USE, skill_payload("create-tasks"),
          note="Auto-phase cannot be invoked as skill")

    print("\n--- Write code file guard (implement) ---")
    s = read_state()
    s["phases"] = [
        {"name": "explore", "status": "completed"},
        {"name": "research", "status": "completed"},
        {"name": "plan", "status": "completed"},
        {"name": "plan-review", "status": "completed"},
        {"name": "create-tasks", "status": "completed"},
        {"name": "write-code", "status": "in_progress"},
    ]
    s["plan_files_to_modify"] = ["src/app.py"]
    write_state(s)

    allow("Listed file allowed", PRE_TOOL_USE, write_payload("src/app.py"))
    block("Unlisted file blocked", PRE_TOOL_USE, write_payload("src/other.py"),
          note="Implement file guard blocks unlisted files")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════


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
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hook system dry run")
    parser.add_argument("--tdd", action="store_true", help="Include write-tests phase")
    parser.add_argument("--implement", action="store_true", help="Run implement workflow simulation")
    args = parser.parse_args()

    mode = "implement" if args.implement else "build"
    print(f"\n{'='*60}")
    print(f"  Hook System Dry Run  {YELLOW}[{mode.upper()} TDD={'on' if args.tdd else 'off'}]{RESET}")
    print(f"{'='*60}")

    backup = STATE_PATH.read_text() if STATE_PATH.exists() else ""
    reset_state(mode)

    try:
        if args.implement:
            simulate_implement(args.tdd)
        else:
            simulate_build(args.tdd)
    finally:
        if backup:
            STATE_PATH.write_text(backup)
        else:
            STATE_PATH.unlink(missing_ok=True)
        print(f"\n  {YELLOW}state.jsonl restored.{RESET}")

    print_summary()
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
