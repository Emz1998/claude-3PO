"""reminder.py — Phase-aware context injection for workflow hooks.

Read-only on state (no mutations). Guards validate, recorder mutates,
reminder injects context.

Injection points:
  - PostToolUse: phase context reminders after tool completes
  - SubagentStart: agent-role instructions into the subagent
  - SubagentStop: phase transition + failure reminders after phase advances
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.state_store import StateStore


# ---------------------------------------------------------------------------
# Phase context reminders (PostToolUse)
# ---------------------------------------------------------------------------

EXPLORE_KICKOFF = (
    "Phase: EXPLORE. Launch 3 Explore agents in the background and "
    "2 Research agents in the foreground. "
    "All must complete before moving to plan phase."
)

EXPLORE_REQUIRED = {"Explore": 3, "Research": 2}

PHASE_REMINDERS: dict[str, str] = {
    "plan": (
        "Phase: PLAN. Synthesize exploration findings into a concrete "
        "implementation plan."
    ),
    "review": (
        "Phase: REVIEW. Plan review iteration {iteration}/3. "
        "Scores must be >= 80/80 to approve."
    ),
    "write-tests": (
        "Phase: WRITE-TESTS (TDD). Write failing tests, then launch "
        "TestReviewer. Only test files allowed."
    ),
    "write-code": (
        "Phase: WRITE-CODE. Files from plan: {plan_files}. "
        "When done, launch Validator agent."
    ),
    "validate": "Phase: VALIDATE. If Pass → pr-create. If Fail → back to write-code.",
}


# ---------------------------------------------------------------------------
# Agent role reminders (SubagentStart)
# ---------------------------------------------------------------------------

AGENT_REMINDERS: dict[str, str] = {
    "Explore": "Focus on codebase structure, existing patterns, and relevant files.",
    "Research": "Research external docs, best practices, and patterns for the task.",
    "Plan": (
        "Synthesize explore/research findings into a plan with steps and "
        "file changes."
    ),
    "PlanReview": (
        "Score confidence (0-100) and quality (0-100). End response with: "
        "confidence: NN, quality: NN"
    ),
    "TestReviewer": (
        "Review test coverage and quality. End response with exactly "
        "'Pass' or 'Fail'."
    ),
    "Validator": (
        "Verify implementation passes tests and matches plan. End with "
        "'Pass' or 'Fail'."
    ),
}


# ---------------------------------------------------------------------------
# Phase transition reminders (SubagentStop)
# ---------------------------------------------------------------------------

PHASE_TRANSITION_REMINDERS: dict[str, str] = {
    "plan": "All exploration complete. Launch a Plan agent to design the implementation.",
    "write-plan": (
        "Plan formulated. Write it to .claude/plans/ with required sections: "
        "Context, Approach/Steps, Files to Modify, Verification."
    ),
    "approved": (
        "Plan review passed. Use ExitPlanMode to present the plan to the "
        "user for approval."
    ),
    "write-tests": "Tasks created. TDD mode: write failing tests first.",
    "write-code": (
        "Tests reviewed. Write minimal code to pass them. " "Plan files: {plan_files}."
    ),
    "pr-create": "Validation passed. Create PR with gh pr create.",
    "ci-check": "PR created. Run gh pr checks to verify CI.",
    "report": "CI passed. Write completion report to .claude/reports/latest-report.md.",
}


# ---------------------------------------------------------------------------
# ExitPlanMode post-approval reminders (PostToolUse ExitPlanMode)
# ---------------------------------------------------------------------------

EXIT_PLAN_MODE_REMINDERS: dict[str, str] = {
    "task-create": (
        "User approved the plan. Create tasks matching the story context "
        "using TaskManager agent."
    ),
    "write-tests": "User approved the plan. TDD mode: write failing tests first.",
    "write-code": (
        "User approved the plan. Begin implementation. " "Plan files: {plan_files}."
    ),
}


# ---------------------------------------------------------------------------
# Failure / regression reminders (SubagentStop)
# ---------------------------------------------------------------------------

PLAN_REVIEW_FAIL_TEMPLATE = (
    "Plan review FAILED. Scores: confidence={confidence}, quality={quality} "
    "(threshold: 80/80). Iteration {iteration}/3. "
    "Revise the plan and launch PlanReview again."
)

PLAN_REVIEW_MAX_TEMPLATE = (
    "Plan review reached max iterations (3). Scores: confidence={confidence}, "
    "quality={quality}. Workflow failed — ask the user for guidance."
)

TEST_REVIEW_FAIL = (
    "Test review FAILED. Revise test files and launch TestReviewer again."
)

VALIDATOR_FAIL = (
    "Validation FAILED. Returning to write-code phase. "
    "Fix the implementation and re-validate."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_plan_files_list(state: dict) -> str:
    """Return comma-separated plan file list or 'N/A'."""
    cached = state.get("plan_files_cache")
    if cached:
        return ", ".join(cached)

    plan_file = state.get("plan_file")
    if not plan_file:
        return "N/A"

    try:
        content = Path(plan_file).read_text()
    except (FileNotFoundError, OSError):
        return "N/A"

    # Parse file paths from plan's Files to Modify section
    section_pattern = re.compile(
        r"^##\s+(Files to Modify|Critical Files)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = section_pattern.search(content)
    if not match:
        return "N/A"

    section_start = match.end()
    next_section = re.search(r"^##\s+", content[section_start:], re.MULTILINE)
    section_end = section_start + next_section.start() if next_section else len(content)
    section_content = content[section_start:section_end]
    backtick_paths = re.findall(r"`([^`]+\.[a-zA-Z]+)`", section_content)

    if backtick_paths:
        return ", ".join(backtick_paths)
    return "N/A"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _explore_remaining_reminder(state: dict) -> str | None:
    """Return a reminder of how many explore/research agents are still needed."""
    agents = state.get("agents", [])
    skip_explore = state.get("skip_explore", False)
    skip_research = state.get("skip_research", False)

    parts = []
    for agent_type, required in EXPLORE_REQUIRED.items():
        if agent_type == "Explore" and skip_explore:
            continue
        if agent_type == "Research" and skip_research:
            continue
        launched = sum(1 for a in agents if a.get("agent_type") == agent_type)
        remaining = required - launched
        if remaining > 0:
            parts.append(f"{remaining} more {agent_type}")

    if not parts:
        return None

    return f"Phase: EXPLORE. Still needed: {', '.join(parts)}. Launch them in parallel."


def get_post_tool_reminder(hook_input: dict, store: StateStore) -> str | None:
    """PostToolUse: return phase context reminder after tool completes.

    For ExitPlanMode PostToolUse, returns the post-approval reminder.
    For Skill PostToolUse (/implement), returns explore kickoff reminder.
    For Agent PostToolUse in explore, returns remaining agents reminder.
    For other tools, returns the current phase reminder.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return None

    phase = state.get("phase", "")
    tool = hook_input.get("tool_name", "")

    # /implement or /plan activation: explore kickoff reminder
    if tool == "Skill" and phase == "explore":
        store.set("last_reminder_phase", "explore:kickoff")
        return EXPLORE_KICKOFF

    # Agent launch during explore: remaining agents reminder (always fires)
    if tool == "Agent" and phase == "explore":
        return _explore_remaining_reminder(state)

    # ExitPlanMode PostToolUse: return post-approval reminder (once per phase)
    if tool == "ExitPlanMode":
        template = EXIT_PLAN_MODE_REMINDERS.get(phase)
        if template and state.get("last_reminder_phase") != f"exit:{phase}":
            plan_files = _load_plan_files_list(state)
            store.set("last_reminder_phase", f"exit:{phase}")
            return template.format(plan_files=plan_files)
        return None

    # General phase reminder (once per phase)
    if state.get("last_reminder_phase") == phase:
        return None

    template = PHASE_REMINDERS.get(phase)
    if not template:
        return None

    iteration = state.get("plan_review_iteration", 0) + 1
    plan_files = _load_plan_files_list(state)
    store.set("last_reminder_phase", phase)
    return template.format(iteration=iteration, plan_files=plan_files)


def get_agent_start_reminder(hook_input: dict, store: StateStore) -> str | None:
    """SubagentStart: return agent-role instructions for the subagent."""
    state = store.load()
    if not state.get("workflow_active"):
        return None

    agent_type = hook_input.get("agent_type", "")
    return AGENT_REMINDERS.get(agent_type)


def get_phase_transition_reminder(hook_input: dict, store: StateStore) -> str | None:
    """SubagentStop: return transition or failure reminder after phase advances.

    Reads state AFTER recorder has already advanced it, so it sees the
    new phase.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return None

    phase = state.get("phase", "")
    agent_type = hook_input.get("agent_type", "")

    # Check failure scenarios first
    if agent_type == "PlanReview":
        review_status = state.get("plan_review_status", "")
        scores = state.get("plan_review_scores") or {}
        confidence = scores.get("confidence", "N/A")
        quality = scores.get("quality", "N/A")
        iteration = state.get("plan_review_iteration", 0)

        if review_status == "max_iterations_reached":
            return PLAN_REVIEW_MAX_TEMPLATE.format(
                confidence=confidence,
                quality=quality,
            )
        if review_status == "revision_needed":
            return PLAN_REVIEW_FAIL_TEMPLATE.format(
                confidence=confidence,
                quality=quality,
                iteration=iteration,
            )

    if agent_type == "TestReviewer":
        if state.get("test_review_result") == "Fail":
            return TEST_REVIEW_FAIL

    if agent_type == "Validator":
        if state.get("validation_result") == "Fail":
            return VALIDATOR_FAIL

    # Phase transition reminder (once per phase)
    if state.get("last_reminder_phase") == f"transition:{phase}":
        return None

    # Dynamic write-codebase reminder with collected findings
    if phase == "write-codebase":
        findings = state.get("agent_findings", [])
        sections = []
        for i, f in enumerate(findings, 1):
            sections.append(f"### {f['agent_type']} Agent {i}\n{f['message']}")
        findings_text = "\n\n".join(sections)
        store.set("last_reminder_phase", f"transition:{phase}")
        return (
            "All exploration complete. Write CODEBASE.md using the findings below.\n\n"
            f"{findings_text}"
        )

    template = PHASE_TRANSITION_REMINDERS.get(phase)
    if not template:
        return None

    plan_files = _load_plan_files_list(state)
    store.set("last_reminder_phase", f"transition:{phase}")
    return template.format(plan_files=plan_files)
