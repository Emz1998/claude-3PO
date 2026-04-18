"""claude_plan_review.py — Trigger a headless Claude review of a build-phase plan.

Loads the review prompt template from ``prompts/claude/plan_review.md``,
substitutes the plan body, and delegates the subprocess call to
:func:`lib.shell.invoke_claude`. Fail-open: a missing plan, missing binary,
or any subprocess failure returns ``None`` so the caller can treat the claude
review as an optional second opinion rather than a control-flow gate.
"""


from pathlib import Path
from typing import Literal

from lib.shell import invoke_headless_agent





def invoke_reviewer(self, agent_name: Literal["claude", "codex"], review_type: Literal["plan", "code", "test"]) -> None:
    """
    Trigger a headless review of the specified type.

    Args:
        agent_name (Literal["claude", "codex"]): The headless agent to use for the review.
        review_type (str): One of "plan", "code", or "test" to specify the
            review prompt template to use.

    Returns:
        None: Side-effects only; the reviewer's feedback is not captured.

    Example:
        >>> headless.call_reviewer("plan")  # doctest: +SKIP
    """
    from config import Config
    config = Config

    if review_type == "plan":
        plan_path = Path(str(config.plan_file_path))
        invoke_headless_agent(agent_name, f"/plan-review {plan_path}", timeout=120, cwd=None)
        return

    if review_type == "code":
        # For simplicity, reusing the plan review prompt; ideally this would be a separate template.
        invoke_headless_agent(agent_name, "/code-review", timeout=120, cwd=None)
        return

    if review_type == "test":
        # For simplicity, reusing the plan review prompt; ideally this would be a separate template.
        invoke_headless_agent(agent_name, "/test-review", timeout=120, cwd=None)
        return
    