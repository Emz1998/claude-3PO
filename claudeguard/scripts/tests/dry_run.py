#!/usr/bin/env python3
"""dry_run.py — E2E simulation of the hook system using real state.json.

Pipes JSON payloads to pre_tool_use.py, post_tool_use.py, subagent_stop.py,
and stop.py, verifying allow/block decisions at each step.

Usage:
    python3 scripts/tests/dry_run.py
    python3 scripts/tests/dry_run.py --tdd
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = SCRIPTS_DIR / "state.json"

PRE_TOOL_USE = SCRIPTS_DIR / "pre_tool_use.py"
POST_TOOL_USE = SCRIPTS_DIR / "post_tool_use.py"
SUBAGENT_STOP = SCRIPTS_DIR / "subagent_stop.py"
STOP_HOOK = SCRIPTS_DIR / "stop.py"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

results: list[dict] = []


# ═══════════════════════════════════════════════════════════════════
# State helpers
# ═══════════════════════════════════════════════════════════════════


DEFAULT_STATE = {
    "session_id": "dry-run",
    "workflow_active": True,
    "workflow_type": "implement",
    "phases": [],
    "tdd": False,
    "story_id": "DRY-001",
    "skip": [],
    "instructions": "",
    "agents": [],
    "plan": {
        "file_path": None,
        "written": False,
        "revised": False,
        "reviews": [],
    },
    "tasks": [],
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
    "ci-check": {"status": "pending", "results": []},
    "report_written": False,
}


def reset_state() -> None:
    STATE_PATH.write_text(json.dumps(DEFAULT_STATE, indent=2))


def read_state() -> dict:
    return json.loads(STATE_PATH.read_text())


# ═══════════════════════════════════════════════════════════════════
# Payload builders
# ═══════════════════════════════════════════════════════════════════


def skill_payload(skill: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill},
        "tool_use_id": "t1",
        "session_id": "dry-run",
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
        "session_id": "dry-run",
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def write_payload(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "dry-run",
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
        "session_id": "dry-run",
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
        "session_id": "dry-run",
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
        "session_id": "dry-run",
        "transcript_path": "t",
        "cwd": str(SCRIPTS_DIR),
        "permission_mode": "default",
    }


def webfetch_payload(url: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebFetch",
        "tool_input": {"url": url, "prompt": "fetch"},
        "tool_use_id": "t1",
        "session_id": "dry-run",
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
        "session_id": "dry-run",
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
        "session_id": "dry-run",
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

    # Block = exit code 2 or stdout contains "deny" or "block"
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
# Simulation
# ═══════════════════════════════════════════════════════════════════


def simulate(tdd: bool) -> None:
    # -- Explore phase --
    print("\n--- Explore phase ---")

    # Seed state with explore phase
    s = read_state()
    s["phases"] = [{"name": "explore", "status": "in_progress"}]
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Read command in explore", PRE_TOOL_USE, bash_payload("ls -la"))
    block("Write blocked in explore", PRE_TOOL_USE, write_payload("notes.md"))
    block("rm blocked in explore", PRE_TOOL_USE, bash_payload("rm -rf /"))
    allow("Explore agent allowed", PRE_TOOL_USE, agent_payload("Explore"))
    block("Wrong agent blocked", PRE_TOOL_USE, agent_payload("Plan"))
    allow("WebFetch safe domain", PRE_TOOL_USE, webfetch_payload("https://docs.python.org/3/"))
    block("WebFetch unsafe domain", PRE_TOOL_USE, webfetch_payload("https://evil.com"))

    # Research parallel with explore
    allow("Research parallel with explore", PRE_TOOL_USE, agent_payload("Research"),
          note="Research runs alongside in-progress Explore")

    # -- Research phase --
    print("\n--- Research phase ---")
    s = read_state()
    s["phases"] = [
        {"name": "explore", "status": "completed"},
        {"name": "research", "status": "in_progress"},
    ]
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Read in research", PRE_TOOL_USE, bash_payload("git status"))
    block("Write blocked in research", PRE_TOOL_USE, write_payload("notes.md"))

    # -- Plan phase --
    print("\n--- Plan phase ---")
    s = read_state()
    s["phases"].append({"name": "plan", "status": "in_progress"})
    s["phases"][1]["status"] = "completed"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Write plan file", PRE_TOOL_USE, write_payload(".claude/plans/latest-plan.md"))
    block("Write wrong plan path", PRE_TOOL_USE, write_payload("wrong.md"))

    # -- Plan review phase --
    print("\n--- Plan review phase ---")
    s = read_state()
    s["phases"].append({"name": "plan-review", "status": "in_progress"})
    s["phases"][2]["status"] = "completed"
    s["plan"]["file_path"] = ".claude/plans/latest-plan.md"
    s["plan"]["written"] = True
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Edit plan in review", PRE_TOOL_USE, edit_payload(".claude/plans/latest-plan.md"))
    block("Edit wrong file in review", PRE_TOOL_USE, edit_payload("wrong.md"))
    allow("PlanReview agent", PRE_TOOL_USE, agent_payload("PlanReview"))

    # SubagentStop with low scores -> revision
    allow("Low scores -> revision needed", SUBAGENT_STOP,
          subagent_stop_payload("PlanReview", "Confidence: 60\nQuality: 55"),
          note="Should trigger plan-revision sub-phase")

    # SubagentStop with high scores -> pass
    s = read_state()
    s["plan"]["reviews"] = []
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("High scores -> pass", SUBAGENT_STOP,
          subagent_stop_payload("PlanReview", "Confidence: 95\nQuality: 92"),
          note="Should complete plan-review phase")

    # -- Write tests phase (TDD) --
    if tdd:
        print("\n--- Write tests phase ---")
        s = read_state()
        s["phases"].append({"name": "write-tests", "status": "in_progress"})
        s["phases"][3]["status"] = "completed"
        STATE_PATH.write_text(json.dumps(s, indent=2))

        allow("Write test file", PRE_TOOL_USE, write_payload("app.test.ts"))
        block("Write non-test file", PRE_TOOL_USE, write_payload("app.txt"))

        # PostToolUse: test execution
        allow("pytest records execution", POST_TOOL_USE, post_bash_payload("pytest tests/", "1 passed"))

    # -- Write code phase --
    print("\n--- Write code phase ---")
    s = read_state()
    phase_idx = len(s["phases"])
    s["phases"].append({"name": "write-code", "status": "in_progress"})
    if tdd:
        s["phases"][-2]["status"] = "completed"
        s["tests"]["file_paths"] = ["app.test.ts"]
        s["tests"]["executed"] = True
        s["tests"]["review_result"] = "Pass"
    else:
        s["phases"][3]["status"] = "completed"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Write code file", PRE_TOOL_USE, write_payload("feature.py"))
    block("Write markdown in code phase", PRE_TOOL_USE, write_payload("readme.md"))
    allow("pytest in write-code", PRE_TOOL_USE, bash_payload("pytest tests/"))
    block("gh pr create in write-code", PRE_TOOL_USE, bash_payload("gh pr create"))

    # -- Test review phase --
    print("\n--- Test review phase ---")
    s = read_state()
    s["phases"].append({"name": "test-review", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "write-code":
            p["status"] = "completed"
    s["tests"]["file_paths"] = ["app.test.ts"]
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Edit test file in review", PRE_TOOL_USE, edit_payload("app.test.ts"))
    block("Edit non-test file", PRE_TOOL_USE, edit_payload("other.py"))

    # SubagentStop with Fail verdict
    allow("Test review Fail", SUBAGENT_STOP,
          subagent_stop_payload("TestReviewer", "Fail"),
          note="Should trigger refactor sub-phase")

    # SubagentStop with Pass verdict
    s = read_state()
    s["tests"]["review_result"] = None
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Test review Pass", SUBAGENT_STOP,
          subagent_stop_payload("TestReviewer", "Pass"),
          note="Should complete test-review phase")

    # -- Code review phase --
    print("\n--- Code review phase ---")
    s = read_state()
    s["phases"].append({"name": "code-review", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "test-review":
            p["status"] = "completed"
    s["code_files"]["file_paths"] = ["feature.py"]
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Edit code file in review", PRE_TOOL_USE, edit_payload("feature.py"))
    block("Edit non-code file", PRE_TOOL_USE, edit_payload("unknown.py"))
    allow("CodeReviewer agent", PRE_TOOL_USE, agent_payload("CodeReviewer"))

    allow("Code review low scores -> revision", SUBAGENT_STOP,
          subagent_stop_payload("CodeReviewer", "Confidence: 40\nQuality: 30"),
          note="Should trigger refactor sub-phase")

    s = read_state()
    s["code_files"]["reviews"] = []
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Code review high scores -> pass", SUBAGENT_STOP,
          subagent_stop_payload("CodeReviewer", "Confidence: 95\nQuality: 93"),
          note="Should complete code-review phase")

    # -- Quality check phase --
    print("\n--- Quality check phase ---")
    s = read_state()
    s["phases"].append({"name": "quality-check", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "code-review":
            p["status"] = "completed"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("QASpecialist agent", PRE_TOOL_USE, agent_payload("QASpecialist"))

    # -- PR create phase --
    print("\n--- PR create phase ---")
    s = read_state()
    s["phases"].append({"name": "pr-create", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "quality-check":
            p["status"] = "completed"
    s["quality_check_result"] = "Pass"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    block("PR create without --json", PRE_TOOL_USE, bash_payload("gh pr create --title test"))
    allow("PR create with --json", PRE_TOOL_USE, bash_payload("gh pr create --json number"))

    # PostToolUse: PR created
    pr_output = json.dumps({"number": 42, "url": "https://github.com/org/repo/pull/42"})
    allow("PR create output recorded", POST_TOOL_USE,
          post_bash_payload("gh pr create --json number", pr_output),
          note="pr.status=created, pr.number=42")

    # -- CI check phase --
    print("\n--- CI check phase ---")
    s = read_state()
    s["phases"].append({"name": "ci-check", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "pr-create":
            p["status"] = "completed"
    s["pr"]["status"] = "created"
    s["pr"]["number"] = 42
    STATE_PATH.write_text(json.dumps(s, indent=2))

    block("CI check without --json", PRE_TOOL_USE, bash_payload("gh pr checks"))
    allow("CI check with --json", PRE_TOOL_USE, bash_payload("gh pr checks --json name,conclusion"))

    # PostToolUse: CI failed
    ci_fail = json.dumps([{"name": "build", "conclusion": "SUCCESS"}, {"name": "test", "conclusion": "FAILURE"}])
    allow("CI failure recorded", POST_TOOL_USE,
          post_bash_payload("gh pr checks --json name,conclusion", ci_fail),
          note="ci.status=failed")

    # PostToolUse: CI passed
    s = read_state()
    s["ci-check"]["status"] = "pending"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    ci_pass = json.dumps([{"name": "build", "conclusion": "SUCCESS"}, {"name": "test", "conclusion": "SUCCESS"}])
    allow("CI pass recorded", POST_TOOL_USE,
          post_bash_payload("gh pr checks --json name,conclusion", ci_pass),
          note="ci.status=passed")

    # -- Write report phase --
    print("\n--- Write report phase ---")
    s = read_state()
    s["phases"].append({"name": "write-report", "status": "in_progress"})
    for p in s["phases"]:
        if p["name"] == "ci-check":
            p["status"] = "completed"
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Write report", PRE_TOOL_USE, write_payload(".claude/reports/report.md"))
    block("Write code in report phase", PRE_TOOL_USE, write_payload("feature.py"))

    # -- Stop hook --
    print("\n--- Stop hook ---")

    # Incomplete workflow -> block
    block("Stop before all phases done", STOP_HOOK, stop_payload())

    # Complete all phases
    s = read_state()
    for p in s["phases"]:
        p["status"] = "completed"
    # Skip test phases in non-TDD mode
    if not tdd:
        s["skip"] = ["write-tests", "test-review"]
    s["tests"]["file_paths"] = ["app.test.ts"]
    s["tests"]["executed"] = True
    s["tests"]["review_result"] = "Pass"
    s["ci-check"]["status"] = "passed"
    s["report_written"] = True
    STATE_PATH.write_text(json.dumps(s, indent=2))

    allow("Stop after all phases done", STOP_HOOK, stop_payload())

    # stop_hook_active prevents infinite loop
    allow("Stop with stop_hook_active", STOP_HOOK, stop_payload(active=True),
          note="Always allows to prevent infinite loop")


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
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Hook System Dry Run  {YELLOW}[TDD={'on' if args.tdd else 'off'}]{RESET}")
    print(f"{'='*60}")

    # Backup and reset state
    backup = STATE_PATH.read_text() if STATE_PATH.exists() else ""
    reset_state()

    try:
        simulate(args.tdd)
    finally:
        STATE_PATH.write_text(backup)
        print(f"\n  {YELLOW}state.json restored.{RESET}")

    print_summary()
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
