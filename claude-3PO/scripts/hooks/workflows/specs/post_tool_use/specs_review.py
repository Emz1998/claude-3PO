#!/usr/bin/env python3
import sys

from pathlib import Path

import json

sys.path.insert(
    0,
    str(Path.cwd() / "claude-3PO" / "scripts"),
)
from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from typing import Any
import subprocess
from lib.state_store import StateStore

DEFAULT_SETTINGS_PATH = Path.cwd() / "settings.json"

PROMPTS_DIR = Path.cwd() / "claude-3PO" / "prompts" / "claude"
PROMPTS_MAP = {
    "architecture": PROMPTS_DIR / "architecture_review.md",
    "prd": PROMPTS_DIR / "prd_review.md",
    "backlog": PROMPTS_DIR / "backlog_review.md",
}


ARCHITECTURE_TEST_CONTENT = (
    Path.cwd() / "claude-3PO" / "templates" / "tests" / "architecture.md"
)


SCHEMA_PATHS_MAP = {
    "architecture": Path.cwd() / "claude-3PO" / "schemas" / "architecture_review.json",
    "prd": Path.cwd() / "claude-3PO" / "schemas" / "prd_review.json",
    "backlog": Path.cwd() / "claude-3PO" / "schemas" / "backlog_review.json",
}

PROJECT_DIR = Path.cwd() / "projects"

SPEC_PATHS_MAP = {
    "architecture": PROJECT_DIR / "specs" / "architecture.md",
    "prd": PROJECT_DIR / "specs" / "prd.md",
    "backlog": PROJECT_DIR / "specs" / "backlog.md",
}


def build_prd_review_prompt(prd: str) -> str:
    prd = PROMPTS_MAP["prd"].read_text()
    return prd.format(prd=prd)


def build_backlog_review_prompt(backlog: str) -> str:
    template = PROMPTS_MAP["backlog"].read_text()
    return template.format(backlog=backlog)


def build_architecture_review_prompt(architecture: str) -> str:
    template = PROMPTS_MAP["architecture"].read_text()
    return template.format(architecture=architecture)


PROMPT_BUILDER_MAP = {
    "architecture": build_architecture_review_prompt,
    "prd": build_prd_review_prompt,
    "backlog": build_backlog_review_prompt,
}


def build_claude_argv(
    prompt: str,
    schema: dict[str, Any] | None = None,
    bare: bool = True,
    session_id: str | None = None,
) -> list[str]:
    argv = ["claude"]
    if bare:
        # `--bare` is the fast path; if the CLI rejects it we retry without.
        argv.append("--bare")

    argv.extend(
        [
            "-p",
            prompt,
            "--model",
            "haiku",
            "--settings",
            str(DEFAULT_SETTINGS_PATH),
            "--allowedTools",
            "Read,Grep,Glob",
            "--output-format",
            "json",
        ]
    )
    if schema:
        argv.extend(
            [
                "--json-schema",
                json.dumps(schema),
            ]
        )

    # Skip --resume on empty string too: `claude --resume ""` errors silently.
    if session_id:
        argv.extend(
            [
                "--resume",
                session_id,
            ]
        )

    return argv


def build_codex_argv(prompt: str, schema_path: str) -> list[str]:
    argv = [
        "codex",
        "exec",
        prompt,
    ]

    if schema_path:
        argv.extend(
            [
                "--output-schema",
                schema_path,
            ]
        )
    return argv


def run_claude(
    prompt: str,
    schema: dict[str, Any] | None = None,
    bare: bool = True,
    session_id: str | None = None,
) -> str:
    argv = build_claude_argv(prompt, schema, bare, session_id)

    result = subprocess.run(argv, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        # CLI sometimes writes errors to stdout, not stderr; surface both.
        err = (
            f"rc={result.returncode} stderr={result.stderr!r} stdout={result.stdout!r}"
        )
        print(f"Failed to run Claude: {err}")
        if not bare:
            # Already on the fallback path; don't retry again.
            raise Exception(f"Failed to run Claude: {err}")
        # First attempt (bare=True) failed — retry once with bare=False.
        return run_claude(prompt, schema=schema, bare=False, session_id=session_id)

    return result.stdout


def run_codex(prompt: str, schema_path: str) -> str:
    argv = build_codex_argv(prompt, schema_path)
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to run Codex: {result.stderr}")
    return result.stdout


PROMPT_MAP = {
    "prd": build_prd_review_prompt,
    "architecture": build_architecture_review_prompt,
    "backlog": build_backlog_review_prompt,
}


def get_confidence_score(structured_output: dict[str, Any]) -> int:
    confidence_score = structured_output.get("confidence_score", 0)
    return confidence_score


def parse_response(llm: Literal["claude", "codex"], response: str) -> dict[str, Any]:
    if llm == "claude":
        json_result = json.loads(response)
        return json_result.get("structured_output", {})
    elif llm == "codex":
        return json.loads(response)
    else:
        raise Exception(f"Invalid LLM: {llm}")


def is_workflow_type_specs(state: StateStore) -> bool:
    return state.workflow_type == "specs"


def get_session_id(response: str) -> str:
    json_result = json.loads(response)
    return json_result.get("session_id", "")


MAX_REVIEW_ATTEMPTS = 3


def get_hook_content(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("content", "")


def get_content(response: str) -> str:
    json_result = json.loads(response)
    return json_result.get("result", "")


def get_structured_output(response: str) -> dict[str, Any]:
    json_result = json.loads(response)
    return json_result.get("structured_output", {})


def review_specs(
    llm: Literal["claude", "codex"] = "claude",
    prompt: str = "",
    schema_path: str | None = None,
    test_mode: bool = False,
    session_id: str | None = None,
) -> str:
    # if not is_workflow_type_specs(state):
    #     sys.exit(0)
    if not schema_path:
        raise Exception("No schema provided")

    schema = Path(schema_path).read_text()
    schema_dict = json.loads(schema)

    if not schema:
        raise Exception("Invalid schema")

    if test_mode and not prompt:
        architecture_test = ARCHITECTURE_TEST_CONTENT.read_text()
        prompt = build_architecture_review_prompt(architecture=architecture_test)

    response = (
        run_claude(prompt, schema=schema_dict, session_id=session_id)
        if llm == "claude"
        else run_codex(prompt, schema_path)
    )
    if not response:
        raise Exception("No response from the LLM")

    return response


def get_file_path(hook_input: dict[str, Any]) -> str:
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    return file_path


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()

    skill_name = "architecture"
    file_path = get_file_path(hook_input)
    expected_path = str(SPEC_PATHS_MAP[skill_name])

    if file_path != expected_path:
        Hook.system_message(
            f"Expected file path: {expected_path}, but got: {file_path}"
        )

    content = get_hook_content(hook_input)

    prompt = PROMPT_BUILDER_MAP[skill_name](content)

    schema_path = SCHEMA_PATHS_MAP[skill_name]

    raw = review_specs(prompt=prompt, schema_path=str(schema_path))

    structured_output = get_structured_output(raw)

    if not structured_output:
        Hook.discontinue(f"No structured output returned for {skill_name}")

    confidence_score = get_confidence_score(structured_output)

    if confidence_score < 80:
        Hook.block(f"Score is too low: {confidence_score}")
        return


if __name__ == "__main__":
    main()
