"""Code-review reviewer — thin handler that delegates to lib.reviewer.

Parameterized by llm so either codex or claude can drive the review
against the report template. All parsing/recursion logic lives in
``lib.reviewer``.
"""

from pathlib import Path
from typing_extensions import Literal

from lib.reviewer import invoke_reviewer, template_tree_check  # type: ignore


DEFAULT_REPORT_TEMPLATE = (
    Path(__file__).parent.parent.parent / "templates" / "report.md"
)


def build_test_correction_prompt(diff: str, mock_report: bool = True) -> str:
    """
    Build the correction prompt used when a code review diverges from the template.

    Args:
        diff (str): Stitched diff string produced by ``trees_identical``.
        mock_report (bool): When True, phrases the prompt around a "mock
            report" (used by the test harness); real reviews pass False.

    Returns:
        str: Correction prompt to feed back to the reviewer.

    Raises:
        None: Pure string construction.

    Example:
        >>> build_code_correction_prompt("diff")[:22]
        'The report is not vali'
        Return: 'The report is not vali'
    """
    kind = "mock " if mock_report else ""
    return (
        f"The report is not valid. Please revise the {kind}report. "
        f"Make sure to follow the report template in {DEFAULT_REPORT_TEMPLATE}."
        f"Here is the diff between the report and the template:{diff}"
    )


def invoke_code_reviewer(
    llm: Literal["codex", "claude"],
    prompt: str,
    report_template: Path | None = None,
) -> str:
    """
    Run a code review against the report template using *llm*.

    Args:
        llm (Literal["codex", "claude"]): Which headless agent drives the review.
        prompt (str): Initial reviewer prompt.
        report_template (Path | None): Override the default report template
            when the caller needs a bespoke structure.

    Returns:
        str: Reviewed report markdown, or a failure sentinel from lib.reviewer.

    Raises:
        json.JSONDecodeError: If the agent emits malformed JSONL.
        FileNotFoundError: If the template file is missing.

    Example:
        >>> invoke_code_reviewer("codex", "review this", None)  # doctest: +SKIP
        Return: '# Report\\n...'
    """
    # Fall back to the default report template when the caller passes None.
    template = report_template or DEFAULT_REPORT_TEMPLATE
    return invoke_reviewer(
        llm, prompt, template_tree_check(template), build_test_correction_prompt
    )
