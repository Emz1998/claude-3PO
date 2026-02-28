"""UserPromptSubmit handler — intercepts /build and prepares parallel implement prompts."""

from typing import Any

from scripts.claude_hooks.models import UserPromptSubmit
from scripts.claude_hooks.state_store import StateStore
from scripts.claude_hooks.paths import ProjectPaths
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import activate_workflow


def handle(hook_input: dict[str, Any]) -> None:
    """Build entry handler."""
    hook = UserPromptSubmit(**hook_input)

    if hook.prompt is None:
        return
    if not hook.prompt.startswith("/build"):
        return

    sprint = Sprint.create()
    activate_workflow()
    project_paths = ProjectPaths(
        sprint_id=sprint.state.sprint_id,
        session_id=hook.session_id,
    )
    session_path = project_paths.current_session_path / "state.json"
    state = StateStore(state_path=session_path)

    args = sprint.story.ready_stories
    prompts = [
        f"/implement {story_id} --worktree {sprint.state.sprint_id}/{story_id}"
        for story_id in args
    ]

    state.set("build_active", True)
    state.save()

    print("Build Entry Point successful")
    # parallel_sessions(prompts)
