#!/usr/bin/env python3
"""Inject context into hook output for implement workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import add_context, get_status, read_stdin_json, set_status, read_file  # type: ignore
from roadmap.utils import (  # type: ignore
    get_current_task_id,
    get_current_milestone_id,
    get_current_phase_id,
    get_current_version,
    get_milestone_tasks,
    load_roadmap,
    get_roadmap_path,
    get_task_owner,
    get_task_test_strategy,
)


STDIN_TEST = {
    "session_id": "1234567890",
}

VERSION = get_current_version()

TODO_TEMPLATE_PATH = ".claude/hooks/context-injector/templates/todo.md"
ROADMAP_PATH = Path(f"project/{VERSION}/release-plan/roadmap.json")

TASKS_TEMPLATE = """
# {task_id}: {task_description}

**Parallel**: {parallel}
**Test Strategy**: {test_strategy}
**Owner**: {owner}
**Dependencies**: {dependencies}

**Acceptance Criteria:**

{acceptance_criteria}
"""

ORCHESTRATION_SEQUENCE_TEMPLATE = """
# Orchetration Sequence

{orchetration_sequence}


"""


def build_tasks_template(tasks: list[dict]) -> str:
    ## Build tasks template from tasks.

    ac = [ac for task in tasks for ac in task["acceptance_criteria"]]
    deps = [dep for task in tasks for dep in task["dependencies"]]

    ac_formatted = "\n".join(f"- [ ] {ac['id']}: {ac['description']}" for ac in ac)
    dependencies_formatted = ", ".join(deps)

    return "\n".join(
        [
            TASKS_TEMPLATE.format(
                task_id=task["id"],
                task_description=task["description"],
                parallel=task["parallel"],
                test_strategy=(
                    get_task_test_strategy(task)
                    if get_task_test_strategy(task)
                    else "N/A"
                ),
                owner=get_task_owner(task),
                dependencies=dependencies_formatted,
                acceptance_criteria=ac_formatted,
            )
            for task in tasks
        ]
    )


def build_context(roadmap: dict, tasks: list[dict]) -> str:
    """Build context string from project status."""

    _tasks = build_tasks_template(tasks)

    keys = {
        "tasks": _tasks,
        "current_phase": get_current_phase_id(),
        "current_milestone": get_current_milestone_id(),
        "current_task": get_current_task_id(),
        "current_version": VERSION,
    }

    todo_template = read_file(TODO_TEMPLATE_PATH)
    return todo_template.format(**keys)


def inject_context() -> None:
    """Inject workflow context into session."""
    try:
        hook_input = read_stdin_json()

        roadmap = load_roadmap(ROADMAP_PATH) or {}
        tasks = get_milestone_tasks(roadmap, get_current_milestone_id() or "")

        context = build_context(roadmap, tasks)
        add_context(context)

    except Exception as e:
        print(f"Context injection error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    roadmap = load_roadmap(ROADMAP_PATH) or {}
    tasks = get_milestone_tasks(roadmap, get_current_milestone_id() or "")
    print(build_context(roadmap, tasks))
