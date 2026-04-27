"""Codex-backed plan reviewer — thin handler that delegates to lib.reviewer.

All iteration, JSONL parsing, and template-conformance logic lives in
``lib.reviewer``; this module only supplies the template path and the
plan-specific correction prompt.
"""

from pathlib import Path

from lib.reviewer import invoke_reviewer, template_tree_check  # type: ignore


TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "plan.md"

TEST_PROMPT = (
    f"Respond with a mock plan that is invalid and does not follow the plan "
    f"template in {TEMPLATE_PATH}. This is a test."
)
INITIAL_PROMPT = (
    f"Please review the plan and return the plan in the following format: "
    f"{TEMPLATE_PATH.read_text()}"
)


def build_plan_correction_prompt(diff: str, mock_plan: bool = True) -> str:
    """
    Build the correction prompt used when a plan review diverges from the template.

    Args:
        diff (str): Stitched diff string produced by ``trees_identical``.
        mock_plan (bool): When True, phrases the prompt around a "mock plan"
            (used by the test harness); real reviews pass False.

    Returns:
        str: Correction prompt to feed back to the reviewer.

    Raises:
        None: Pure string construction.

    Example:
        >>> build_plan_correction_prompt("diff")[:20]
        'The plan is not vali'
        Return: 'The plan is not vali'
    """
    kind = "mock " if mock_plan else ""
    return (
        f"The plan is not valid. Please revise the {kind}plan. "
        f"Make sure to follow the plan template in {TEMPLATE_PATH}."
        f"Here is the diff between the plan and the template:{diff}"
    )


def invoke_codex_plan_reviewer(prompt: str) -> str:
    """
    Run a plan review against the plan template using codex.

    Args:
        prompt (str): Initial reviewer prompt.

    Returns:
        str: Reviewed plan markdown, or a failure sentinel from lib.reviewer.

    Raises:
        json.JSONDecodeError: If codex emits malformed JSONL.

    Example:
        >>> invoke_codex_plan_reviewer(INITIAL_PROMPT)  # doctest: +SKIP
        Return: '# Plan\\n...'
    """
    # Delegate the review loop; handler stays free of parsing/recursion logic.
    return invoke_reviewer(
        "codex",
        prompt,
        template_tree_check(TEMPLATE_PATH),
        build_plan_correction_prompt,
    )


if __name__ == "__main__":
    print(invoke_codex_plan_reviewer(TEST_PROMPT))
