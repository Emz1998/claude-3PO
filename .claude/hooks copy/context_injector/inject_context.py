#!/usr/bin/env python3
"""Inject context into hook output for /build command."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from workflow.sprint_config import SprintConfig
from workflow.sprint_manager import SprintManager
from utils import read_file, read_stdin_json

sys.path.insert(0, str(Path(__file__).parent))
from start_parallel_session import parallel_sessions  # type: ignore


TEMPLATE_DIR = ".claude/hooks/workflow/context"
STORY_TYPE_MAP: dict[str, str] = {
    "Spike": "spike.md",
    "Tech": "tech_story.md",
    "User": "user_story.md",
    "Bug": "bug.md",
}

TASK_TEMPLATE = """- **{task_id}:** {task_title}
  - **Status:** {status}
  - **Complexity:** {complexity}
  - **Depends on:** {dependencies}
  - **QA loops:** {qa_loops}
  - **Code Review loops:** {code_review_loops}
"""


def format_loops(loops: list[int] | int) -> str:
    if isinstance(loops, list) and len(loops) == 2:
        return f"{loops[0]}/{loops[1]}"
    return str(loops)


def build_tasks_context(tasks: list[dict]) -> str:
    """Build formatted task list from tasks."""
    if not tasks:
        return "No tasks for this story."
    result: list[str] = []
    for task in tasks:
        dependencies = ", ".join(task.get("dependsOn", [])) or "None"
        result.append(
            TASK_TEMPLATE.format(
                task_id=task.get("id", ""),
                task_title=task.get("title", ""),
                status=task.get("status", "Todo"),
                complexity=task.get("complexity", ""),
                dependencies=dependencies,
                qa_loops=format_loops(task.get("qaLoops", [0, 0])),
                code_review_loops=format_loops(task.get("codeReviewLoops", [0, 0])),
            )
        )
    return "\n".join(result)


def build_deliverables_context(deliverables: list[str]) -> str:
    """Build formatted deliverables list from spike."""
    if not deliverables:
        return "No deliverables defined."
    return "\n".join(f"- [ ] {d}" for d in deliverables)


def build_context(story: dict, current_story: str) -> str:
    """Build context string based on story type."""
    story_type = story.get("type", "")
    template_file = STORY_TYPE_MAP.get(story_type)
    if not template_file:
        return f"Unknown story type: {story_type}"

    template = read_file(f"{TEMPLATE_DIR}/{template_file}")
    depends_on = ", ".join(story.get("dependsOn", [])) or "None"
    blocked_by = ", ".join(story.get("blockedBy", [])) or "None"
    sprint_manager = SprintManager()
    ready_tasks = sprint_manager.get_ready_tasks(current_story)
    important_note = (
        f"Ready tasks: {', '.join(ready_tasks)}" if ready_tasks else "No ready tasks"
    )

    if story_type == "Spike":
        return template.format(
            story_title=story.get("title", ""),
            depends_on=depends_on,
            blocked_by=blocked_by,
            timebox=story.get("timebox", ""),
            points=story.get("points", 0),
            deliverables=build_deliverables_context(story.get("deliverables", [])),
        )

    if story_type == "Bug":
        return template.format(
            story_title=story.get("title", ""),
            severity=story.get("severity", ""),
            found_in=story.get("foundIn", ""),
            depends_on=depends_on,
            blocked_by=blocked_by,
            points=story.get("points", 0),
            whats_broken=story.get("whatsBroken", ""),
            expected=story.get("expected", ""),
            actual=story.get("actual", ""),
            reproduce=story.get("reproduce", ""),
            tasks_context=build_tasks_context(story.get("tasks", [])),
            important_note=important_note,
        )

    # Tech, User share the same template shape
    return template.format(
        story_title=story.get("title", ""),
        depends_on=depends_on,
        blocked_by=blocked_by,
        priority=story.get("priority", ""),
        points=story.get("points", 0),
        tasks_context=build_tasks_context(story.get("tasks", [])),
        important_note=important_note,
    )


def validate_input(prompt: str) -> bool:
    if not prompt:
        return False
    if not prompt.startswith("/implement"):
        return False

    pattern = r"^\s*(?:US|TS|SK|BG)-\d{3}\s*$"
    args = extract_args(prompt)
    if not args:
        return False
    if not re.match(pattern, args):
        return False

    return True


def extract_args(prompt: str) -> str:
    parts = prompt.split(" ", 1)
    if len(parts) < 2:
        return ""
    return parts[1]


def main() -> None:
    """Inject workflow context into session."""
    # hook_input = read_stdin_json()
    # if not hook_input:
    #     return
    # if hook_input.get("hook_event_name") != "UserPromptSubmit":
    #     return

    prompt = "/implement TS-016"
    if not validate_input(prompt):
        return

    args = extract_args(prompt)
    sprint_config = SprintConfig()
    sprint_manager = SprintManager()
    sprint_manager.resolve_tasks(args)
    story = sprint_config.find_story(args)
    if not story:
        return

    context = build_context(story, args)
    print(context)


if __name__ == "__main__":
    main()
