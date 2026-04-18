"""codex_plan_review.py — Trigger a headless Codex review of a build-phase plan.

Loads the review prompt template from ``prompts/codex/plan_review.md``,
substitutes the plan body, and delegates the subprocess call to
:func:`lib.shell.invoke_codex`. Fail-open: a missing plan, missing binary,
or any subprocess failure returns ``None`` so the caller can treat the codex
review as an optional second opinion rather than a control-flow gate.
"""

from pathlib import Path

from lib.shell import invoke_headless_agent


PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "headless" / "prompts" / "codex" / "plan_review.md"
)


def _load_template() -> str:
    """Read the review prompt template from :data:`PROMPT_PATH`.

    Returns:
        str: Raw template text containing a ``{plan}`` placeholder.

    Raises:
        FileNotFoundError: If the template file has been moved or deleted.

    Example:
        >>> "{plan}" in _load_template()  # doctest: +SKIP
        True
    """
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_prompt(plan_text: str) -> str:
    """Substitute *plan_text* into the review prompt template.

    Args:
        plan_text (str): Full plan markdown body.

    Returns:
        str: Review prompt ready to send to codex.

    Example:
        >>> "HELLO" in _build_prompt("HELLO")  # doctest: +SKIP
        True
    """
    return _load_template().replace("{plan}", plan_text)


def invoke_codex_plan_review(
    plan_path: Path,
    timeout: int = 120,
    cwd: Path | None = None,
) -> str | None:
    """
    Ask headless Codex to review the plan at *plan_path*.

    Reads the plan, builds the review prompt, and delegates to
    :func:`lib.shell.invoke_codex`. Returns ``None`` if the plan file does
    not exist, so callers can use this as an optional enrichment after a
    plan is written in the build phase.

    Args:
        plan_path (Path): Path to the plan markdown file.
        timeout (int): Max seconds for the codex subprocess. Defaults to 120.
        cwd (Path | None): Working directory for codex; ``None`` uses current.

    Returns:
        str | None: Reviewer message on success, ``None`` on any failure.

    Example:
        >>> invoke_codex_plan_review(Path("plan.md"))  # doctest: +SKIP
    """
    if not plan_path.is_file():
        return None
    prompt = _build_prompt(plan_path.read_text(encoding="utf-8"))
    return invoke_headless_agent("codex", prompt, timeout=timeout, cwd=cwd)
