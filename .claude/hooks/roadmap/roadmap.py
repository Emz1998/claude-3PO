#!/usr/bin/env python3
# Roadmap utilities for status loggers

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# Type aliases for schema values
StatusType = Literal["not_started", "in_progress", "completed"]
CriteriaStatusType = Literal["met", "unmet"]
TestStrategyType = Literal["TDD", "TA"]


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


def get_prd_path() -> Path:
    """Get the path to PRD.json."""
    project_dir = get_project_dir()
    return project_dir / "project" / "product" / "PRD.json"


def load_prd() -> dict | None:
    """Load PRD.json file."""
    prd_path = get_prd_path()
    if not prd_path.exists():
        return None

    try:
        with open(prd_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_current_version() -> str:
    """Retrieve current_version from PRD.json."""
    prd = load_prd()
    if prd is None:
        return ""
    return prd.get("current_version", "")


def get_roadmap_path(version: str) -> Path:
    """Get roadmap.json path for the given version."""
    project_dir = get_project_dir()
    return project_dir / "project" / version / "release-plan" / "roadmap.json"


def load_roadmap(roadmap_path: Path) -> dict | None:
    """Load roadmap.json file."""
    if not roadmap_path.exists():
        return None

    try:
        with open(roadmap_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_roadmap(roadmap_path: Path, roadmap: dict) -> bool:
    """Save roadmap.json file with updated timestamp."""
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(roadmap_path, "w") as f:
            json.dump(roadmap, f, indent=2)
        return True
    except IOError:
        return False


def find_task_in_roadmap(
    roadmap: dict, task_id: str
) -> tuple[dict | None, dict | None, dict | None]:
    """Find task in roadmap. Returns (phase, milestone, task) or (None, None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    return phase, milestone, task
    return None, None, None


def find_ac_in_roadmap(roadmap: dict, ac_id: str) -> tuple[dict | None, dict | None]:
    """Find acceptance criteria in roadmap. Returns (task, ac_entry) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                acceptance_criteria = task.get("acceptance_criteria", [])
                for ac in acceptance_criteria:
                    id = ac.get("id", "")
                    if ac_id == id:
                        return task, ac
    return None, None


def find_sc_in_roadmap(roadmap: dict, sc_id: str) -> tuple[dict | None, dict | None]:
    """Find success criteria in roadmap. Returns (milestone, sc_entry) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            success_criteria = milestone.get("success_criteria", [])
            for sc in success_criteria:
                id = sc.get("id", "")
                if sc_id == id:
                    return milestone, sc
    return None, None


def find_milestone_in_roadmap(
    roadmap: dict, milestone_id: str
) -> tuple[dict | None, dict | None]:
    """Find milestone in roadmap. Returns (phase, milestone) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            if milestone.get("id") == milestone_id:
                return phase, milestone
    return None, None


def find_phase_in_roadmap(roadmap: dict, phase_id: str) -> dict | None:
    """Find phase in roadmap by ID. Returns phase or None."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        if phase.get("id") == phase_id:
            return phase
    return None


# Phase utilities
def is_checkpoint_phase(phase: dict) -> bool:
    """Check if a phase is a checkpoint phase."""
    return phase.get("checkpoint", False) is True


def get_checkpoint_phases(roadmap: dict) -> list[dict]:
    """Get all checkpoint phases from roadmap."""
    phases = roadmap.get("phases", [])
    return [p for p in phases if is_checkpoint_phase(p)]


# Milestone utilities
def get_milestone_mcp_servers(milestone: dict) -> list[str]:
    """Get list of MCP servers for a milestone."""
    return milestone.get("mcp_servers", [])


def has_mcp_servers(milestone: dict) -> bool:
    """Check if milestone has MCP servers configured."""
    return len(get_milestone_mcp_servers(milestone)) > 0


# Task utilities
def get_task_test_strategy(task: dict) -> str:
    """Get test strategy for a task (TDD or TA)."""
    return task.get("test_strategy", "TA")


def is_tdd_task(task: dict) -> bool:
    """Check if task uses TDD (Test-Driven Development)."""
    return get_task_test_strategy(task) == "TDD"


def is_ta_task(task: dict) -> bool:
    """Check if task uses TA (Test-After Development)."""
    return get_task_test_strategy(task) == "TA"


def get_task_owner(task: dict) -> str:
    """Get the owner/agent responsible for a task."""
    return task.get("owner", "main-agent")


def is_parallel_task(task: dict) -> bool:
    """Check if task can run in parallel with other tasks."""
    return task.get("parallel", False) is True


# Criteria description utilities
def get_ac_description(ac: dict) -> str:
    """Get acceptance criteria description."""
    return ac.get("description", "")


def get_sc_description(sc: dict) -> str:
    """Get success criteria description."""
    return sc.get("description", "")


def get_ac_with_description(task: dict, ac_id: str) -> tuple[dict | None, str]:
    """Find AC in task and return (ac, description) or (None, '')."""
    for ac in task.get("acceptance_criteria", []):
        if ac.get("id") == ac_id:
            return ac, get_ac_description(ac)
    return None, ""


def get_sc_with_description(milestone: dict, sc_id: str) -> tuple[dict | None, str]:
    """Find SC in milestone and return (sc, description) or (None, '')."""
    for sc in milestone.get("success_criteria", []):
        if sc.get("id") == sc_id:
            return sc, get_sc_description(sc)
    return None, ""


def get_incomplete_task_deps(roadmap: dict, task: dict) -> list[str]:
    """Get list of incomplete dependency IDs for a task."""
    incomplete = []
    for dep_id in task.get("dependencies", []):
        _, _, dep_task = find_task_in_roadmap(roadmap, dep_id)
        if dep_task and dep_task.get("status") != "completed":
            incomplete.append(dep_id)
    return incomplete


def get_incomplete_milestone_deps(roadmap: dict, milestone: dict) -> list[str]:
    """Get list of incomplete dependency IDs for a milestone."""
    incomplete = []
    for dep_id in milestone.get("dependencies", []):
        _, dep_milestone = find_milestone_in_roadmap(roadmap, dep_id)
        if dep_milestone and dep_milestone.get("status") != "completed":
            incomplete.append(dep_id)
    return incomplete


def get_unmet_acs(task: dict) -> list[str]:
    """Get list of unmet acceptance criteria IDs for a task."""
    unmet = []
    for ac in task.get("acceptance_criteria", []):
        if ac.get("status") != "met":
            unmet.append(ac.get("id", "unknown"))
    return unmet


def get_unmet_scs(milestone: dict) -> list[str]:
    """Get list of unmet success criteria IDs for a milestone."""
    unmet = []
    for sc in milestone.get("success_criteria", []):
        if sc.get("status") != "met":
            unmet.append(sc.get("id", "unknown"))
    return unmet


def all_acs_met(task: dict) -> bool:
    """Check if all acceptance criteria for a task are met."""
    acs = task.get("acceptance_criteria", [])
    if not acs:
        return True
    return all(ac.get("status") == "met" for ac in acs)


def all_scs_met(milestone: dict) -> bool:
    """Check if all success criteria for a milestone are met."""
    scs = milestone.get("success_criteria", [])
    if not scs:
        return True
    return all(sc.get("status") == "met" for sc in scs)


def all_tasks_completed(milestone: dict) -> bool:
    """Check if all tasks in a milestone are completed."""
    tasks = milestone.get("tasks", [])
    if not tasks:
        return False
    return all(task.get("status") == "completed" for task in tasks)


def any_task_in_progress(milestone: dict) -> bool:
    """Check if any task in a milestone is in_progress."""
    tasks = milestone.get("tasks", [])
    return any(task.get("status") == "in_progress" for task in tasks)


def all_milestones_completed(phase: dict) -> bool:
    """Check if all milestones in a phase are completed."""
    milestones = phase.get("milestones", [])
    if not milestones:
        return False
    return all(ms.get("status") == "completed" for ms in milestones)


def any_milestone_in_progress(phase: dict) -> bool:
    """Check if any milestone in a phase is in_progress."""
    milestones = phase.get("milestones", [])
    return any(ms.get("status") == "in_progress" for ms in milestones)


# Query utilities for tasks by test strategy
def get_tdd_tasks(roadmap: dict) -> list[dict]:
    """Get all tasks using TDD test strategy."""
    tasks = []
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                if is_tdd_task(task):
                    tasks.append(task)
    return tasks


def get_ta_tasks(roadmap: dict) -> list[dict]:
    """Get all tasks using TA test strategy."""
    tasks = []
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                if is_ta_task(task):
                    tasks.append(task)
    return tasks


def get_parallel_tasks(milestone: dict) -> list[dict]:
    """Get all parallel tasks in a milestone."""
    return [t for t in milestone.get("tasks", []) if is_parallel_task(t)]


def get_sequential_tasks(milestone: dict) -> list[dict]:
    """Get all sequential (non-parallel) tasks in a milestone."""
    return [t for t in milestone.get("tasks", []) if not is_parallel_task(t)]


def get_milestone_tasks(roadmap: dict, milestone_id: str) -> list[dict]:
    """Get all tasks from a milestone by ID. Returns empty list if not found."""
    _, milestone = find_milestone_in_roadmap(roadmap, milestone_id)
    return milestone.get("tasks", []) if milestone else []


# Context summary utilities
def get_task_context(task: dict) -> dict:
    """Get a summary context for a task."""
    return {
        "id": task.get("id", ""),
        "description": task.get("description", ""),
        "status": task.get("status", "not_started"),
        "owner": get_task_owner(task),
        "test_strategy": get_task_test_strategy(task),
        "parallel": is_parallel_task(task),
        "dependencies": task.get("dependencies", []),
        "ac_count": len(task.get("acceptance_criteria", [])),
        "ac_met": sum(
            1 for ac in task.get("acceptance_criteria", []) if ac.get("status") == "met"
        ),
    }


def get_milestone_context(milestone: dict) -> dict:
    """Get a summary context for a milestone."""
    return {
        "id": milestone.get("id", ""),
        "feature": milestone.get("feature", ""),
        "name": milestone.get("name", ""),
        "goal": milestone.get("goal", ""),
        "status": milestone.get("status", "not_started"),
        "mcp_servers": get_milestone_mcp_servers(milestone),
        "dependencies": milestone.get("dependencies", []),
        "task_count": len(milestone.get("tasks", [])),
        "tasks_completed": sum(
            1 for t in milestone.get("tasks", []) if t.get("status") == "completed"
        ),
        "sc_count": len(milestone.get("success_criteria", [])),
        "sc_met": sum(
            1
            for sc in milestone.get("success_criteria", [])
            if sc.get("status") == "met"
        ),
    }


def get_phase_context(phase: dict) -> dict:
    """Get a summary context for a phase."""
    return {
        "id": phase.get("id", ""),
        "name": phase.get("name", ""),
        "status": phase.get("status", "not_started"),
        "checkpoint": is_checkpoint_phase(phase),
        "milestone_count": len(phase.get("milestones", [])),
        "milestones_completed": sum(
            1 for m in phase.get("milestones", []) if m.get("status") == "completed"
        ),
    }


# Current pointer utilities
def get_current_task() -> dict | None:
    """Get the current task from roadmap. Returns task dict or None."""
    version = get_current_version()
    if not version:
        return None

    roadmap = load_roadmap(get_roadmap_path(version))
    if not roadmap:
        return None

    current = roadmap.get("current", {})
    task_id = current.get("task")
    if not task_id:
        return None

    _, _, task = find_task_in_roadmap(roadmap, task_id)
    return task


def get_current_milestone() -> dict | None:
    """Get the current milestone from roadmap. Returns milestone dict or None."""
    version = get_current_version()
    if not version:
        return None

    roadmap = load_roadmap(get_roadmap_path(version))
    if not roadmap:
        return None

    current = roadmap.get("current", {})
    milestone_id = current.get("milestone")
    if not milestone_id:
        return None

    _, milestone = find_milestone_in_roadmap(roadmap, milestone_id)
    return milestone


def get_current_phase() -> dict | None:
    """Get the current phase from roadmap. Returns phase dict or None."""
    version = get_current_version()
    if not version:
        return None

    roadmap = load_roadmap(get_roadmap_path(version))
    if not roadmap:
        return None

    current = roadmap.get("current", {})
    phase_id = current.get("phase")
    if not phase_id:
        return None

    return find_phase_in_roadmap(roadmap, phase_id)


def get_current_phase_full_name() -> str | None:
    """Get the current phase full name from roadmap. Returns phase full name or None."""
    phase = get_current_phase()
    full_name = f"{phase.get('id')}_[{phase.get('name')}]" if phase else None
    return full_name


def get_current_task_id() -> str | None:
    """Get the current task ID from roadmap. Returns task ID or None."""
    task = get_current_task()
    return task.get("id") if task else None


def get_current_milestone_id() -> str | None:
    """Get the current milestone ID from roadmap. Returns milestone ID or None."""
    milestone = get_current_milestone()
    return milestone.get("id") if milestone else None


def get_current_milestone_full_name() -> str | None:
    """Get the current milestone full name from roadmap. Returns milestone full name or None."""
    milestone = get_current_milestone()
    full_name = (
        f"{milestone.get('id')}_[{milestone.get('name')}]" if milestone else None
    )
    return full_name


def get_current_phase_id() -> str | None:
    """Get the current phase ID from roadmap. Returns phase ID or None."""
    phase = get_current_phase()
    return phase.get("id") if phase else None


def get_current_task_test_strategy() -> str | None:
    """Get the test strategy of the current task. Returns 'TDD', 'TA', or None."""
    task = get_current_task()
    return get_task_test_strategy(task) if task else None
