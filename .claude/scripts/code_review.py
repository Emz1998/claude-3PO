"""Code review script.

Runs the code review phase of the workflow.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).parent))

from agent_headless import (
    build_claude_argv,
    build_codex_argv,
    run_headless_parallel,
    ClaudeConfig,
    CodexConfig,
)

PROMPTS_DIR = Path.cwd() / "claude-3PO" / "prompts" / "claude"

CONFIG_MAP: dict[str, dict[str, Any]] = {
    "code_review": {
        "owner": "claude",
        "prompt": PROMPTS_DIR / "code_review.md",
        "schema": Path.cwd() / "claude-3PO" / "schemas" / "code_review.json",
    },
    "security": {
        "owner": "claude",
        "prompt": PROMPTS_DIR / "security_review.md",
        "schema": Path.cwd() / "claude-3PO" / "schemas" / "security_review.json",
    },
    "requirements": {
        "owner": "claude",
        "prompt": PROMPTS_DIR / "requirements_review.md",
        "schema": Path.cwd() / "claude-3PO" / "schemas" / "requirements_review.json",
    },
}

PR_CONTENT = os.environ.get("PR_CONTENT", "")

PR_NUMBER = os.environ.get("PR_NUMBER", "")

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"


class CodeReview:

    def __init__(self, pr: str, test_mode: bool = False):
        self.pr = pr
        self.test_mode = test_mode

    @property
    def test_mode_prompt(self) -> str:
        prompt = f"""
        We are in test mode. Create a mock review. Please inform if 'THIS IS A TEST. NO PR BODY' is present as a PR BODY and if PR NUMBER is 1.
        Please follow the structured_output schema when creating a mock review.
        """
        return prompt

    def build_argv(self) -> list[list[str]]:
        argv: list[list[str]] = []
        for cfg in CONFIG_MAP.values():
            owner = cfg.get("owner", "").lower()
            prompt = (
                cfg.get("prompt", "").read_text().format(pr=self.pr)
                if not self.test_mode
                else self.test_mode_prompt
            )
            schema_path = cfg.get("schema", "")
            schema = json.loads(schema_path.read_text()) if schema_path else {}

            if owner == "claude":
                claude_config = ClaudeConfig(
                    model="opus", json_schema=schema, output_format="json"
                )
                argv.append(build_claude_argv(prompt, claude_config))

            elif owner == "codex":
                codex_config = CodexConfig(model="gpt-5.4", output_schema=schema_path)
                argv.append(build_codex_argv(prompt, codex_config))

        return argv

    def fallback_claude(self, cmd: list[str], rc: int) -> list[str] | None:
        if cmd[0] != "claude":
            return None
        if "--bare" not in cmd:
            return None

        cmd.remove("--bare")
        return cmd

    def run(self) -> dict[str, Any]:
        results = run_headless_parallel(self.build_argv(), self.fallback_claude)
        if not results:
            raise Exception("Headless Cli failed")

        output: dict[str, Any] = {}

        for i, (key, cfg) in enumerate(CONFIG_MAP.items()):
            owner = cfg.get("owner", "").lower()
            output[key] = {
                "owner": owner,
                "result": results[i],
            }
        return output


def get_confidence_score(structured_output: dict[str, Any]) -> int:
    confidence_score = structured_output.get("confidence_score", 0)
    return confidence_score


def get_structured_output(response: str) -> dict[str, Any]:
    json_result = json.loads(response)
    return json_result.get("structured_output", {})


def get_report(structured_output: dict[str, Any]) -> str:
    return structured_output.get("report", "")


def run_pr_review(
    decision: Literal["approve", "request-changes"], body: str, test_mode: bool = False
) -> None:
    flag = "--approve" if decision == "approve" else "--request-changes"
    command = ["gh", "pr", "review", PR_NUMBER, flag, "-b", body]

    if test_mode:
        print(f"Simulating {decision} review")
        return

    subprocess.run(command, check=True, text=True)


def main() -> None:
    code_review = CodeReview(pr=PR_CONTENT, test_mode=TEST_MODE)
    output = code_review.run()

    for key, value in output.items():
        result = value.get("result", "")
        structured_output = get_structured_output(result)
        confidence_score = get_confidence_score(structured_output)
        report = get_report(structured_output)
        decision: Literal["approve", "request-changes"] = (
            "request-changes" if confidence_score < 80 else "approve"
        )
        run_pr_review(decision=decision, body=report, test_mode=TEST_MODE)


if __name__ == "__main__":
    main()
