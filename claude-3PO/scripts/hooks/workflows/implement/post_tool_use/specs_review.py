"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.state_store import StateStore  # type: ignore
from utils.order_validation import validate_order  # type: ignore
from lib.resolver import Resolver  # type: ignore
from typing import Any
import subprocess
import argparse
from utils.review_scores import (
    extract_scores,
    scores_valid,
    scores_passing,
    extract_verdict,
)

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


CLAUDE_ARGV = ["claude", "-p", "Please review the PRD"]

DEFAULT_SETTINGS_PATH = Path.cwd() / "settings.json"


def build_prd_review_prompt(prd: str) -> str:
    return f"""
    Please review the PRD and provide a score between 0 and 100.
    The PRD is:
    {prd}

    The score should be based on the following criteria:
    - Completeness
    - Clarity
    - Correctness
    - Conciseness
    - Consistency
    - Follows best practices
    """


def build_architecture_review_prompt(architecture: str) -> str:
    return f"""
    Please review the architecture and provide a score between 0 and 100.
    The architecture is:
    {architecture}

    The score should be based on the following criteria:
    - Completeness
    - Clarity
    - Correctness
    - Conciseness
    - Consistency
    - Follows best practices
    """


def build_backlog_review_prompt(backlog: str) -> str:
    return f"""
    Please review the backlog and provide a score between 0 and 100.
    The backlog is:

    ```
    {backlog}
    ```

    The score should be based on the following criteria:
    - Completeness
    - Clarity
    - Correctness
    - Conciseness
    - Consistency
    - Follows best practices
    """


def build_claude_argv(prompt: str, bare: bool = True) -> list[str]:
    return [
        "claude",
        "--bare" if bare else "",
        "-p",
        prompt,
        "--model",
        "opus",
        "--settings",
        str(DEFAULT_SETTINGS_PATH),
        "--output-format",
        "json",
        "--allowedTools",
        "Read, Grep, Glob",
    ]


def build_codex_argv(prompt: str) -> list[str]:
    return ["codex", "exec", "--json", prompt]


def run_claude(prompt: str, bare: bool = True) -> str:
    argv = build_claude_argv(prompt, bare)
    result = subprocess.run(argv, capture_output=True, text=True)
    default_ran = False
    if result.returncode != 0:
        if default_ran:
            raise Exception(f"Failed to run Claude: {result.stderr}")

        default_ran = True
        run_claude(prompt, bare=False)

    return result.stdout


def run_codex(prompt: str) -> str:
    argv = build_codex_argv(prompt)
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to run Codex: {result.stderr}")
    return result.stdout


PROMPT_MAP = {
    "prd": build_prd_review_prompt,
    "architecture": build_architecture_review_prompt,
    "backlog": build_backlog_review_prompt,
}


def main() -> None:
    hook_input = Hook.read_stdin()
    content = hook_input.get("tool_input", {}).get("content", "")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "specs_type",
        type=str,
        choices=["prd", "architecture", "backlog"],
        required=True,
    )
    args = parser.parse_args()
    specs_type = args.specs_type
    prompt_builder = PROMPT_MAP.get(specs_type)
    if not prompt_builder:
        raise Exception(f"Invalid specs type: {specs_type}")
    prompt = prompt_builder(content)

    response = run_claude(prompt)
    scores = extract_scores(response)

    passing, reason = scores_passing(scores)
    if not passing:
        raise Exception(f"Invalid scores: {reason}")
    verdict = extract_verdict(response)
    print(verdict)


if __name__ == "__main__":
    main()
