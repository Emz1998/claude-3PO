"""Code-review reviewer — thin handler that delegates to lib.reviewer.

Parameterized by llm so either codex or claude can drive the review
against the report template. All parsing/recursion logic lives in
``lib.reviewer``.
"""

from pathlib import Path
from typing import Any
from typing_extensions import Literal


from lib.reviewer import invoke_agent, template_tree_check  # type: ignore
from lib.reviewer import ConformanceCheck
from lib.state_store import StateStore
from guardrails import phase_guard

DEFAULT_REPORT_TEMPLATE = (
    Path(__file__).parent.parent.parent / "templates" / "report.md"
)
DEFAULT_RESEARCH_PROMPT = (
    Path(__file__).parent.parent.parent.parent / "claude" / "research.md"
)


def build_correction_prompt(response: str) -> str:
    return f"The response does not match the template: {response}"


def invoke_researcher(llm: Literal["codex", "claude"]) -> str:
    prompt = DEFAULT_RESEARCH_PROMPT.read_text()
    model = "haiku" if llm == "claude" else "codex"
    report = invoke_agent(
        llm,
        "researcher",
        prompt,
        template_tree_check(DEFAULT_REPORT_TEMPLATE),
        build_correction_prompt,
        model="haiku",
    )
    return report


def handle_research(
    llm: Literal["codex", "claude"], hook_input: dict[str, Any], state: StateStore
) -> str:
    skill = state.get("skill")

    if skill != "research":
        return ""

    invoke_researcher(llm)


if __name__ == "__main__":
    print(DEFAULT_RESEARCH_PROMPT)
