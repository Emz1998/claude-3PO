"""Headless Claude — runs a headless Claude session in a Hook.

Placement: Headless Claude Agent in a Hook.
Runs a headless Claude session.
"""

import sys
from pathlib import Path
import json
import subprocess
from typing import Literal, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_template(template_name: str) -> str:
    path = TEMPLATE_DIR / f"{template_name}.md"
    return path.read_text()


def run_claude(
    prompt: str,
    session_id: str | None = None,
    output_format: Literal["json", "stream-json"] | None = None,
    tools: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    bare: bool = False,
    _continue: bool = False,
    agent: str | None = None,
) -> str | dict:

    command = [
        "claude",
        *(["--bare"] if bare else []),
        prompt,
        "--tools",
        ",".join(tools) if tools else "Read, Grep, Glob",
        "--agent",
        *([agent] if agent else []),
        *(["--continue"] if _continue else []),
    ]
    if output_format is not None:
        command.extend(["--output-format", output_format, "--verbose"])
    if allowed_tools is not None:
        command.extend(["--allowedTools", ",".join(allowed_tools)])
    if session_id is not None:
        command.extend(["--resume", session_id])
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout


def run_claude_stream(
    prompt: str,
    session_id: str | None = None,
    tools: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    bare: bool = False,
    _continue: bool = True,
) -> str:
    if tools is None:
        tools = ["Read", "Grep", "Glob"]

    command = [
        "claude",
        *(["--bare"] if bare else []),
        prompt,
        "--output-format",
        "stream-json",
        "--tools",
        ",".join(tools) if tools else "Read, Grep, Glob",
        *(["--continue"] if _continue else []),
        *(["--allowedTools", ",".join(allowed_tools)] if allowed_tools else []),
        *(["--session-id", session_id] if session_id else []),
        "--verbose",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # merge stderr
        text=True,
    )
    if not process.stdout:
        return ""

    output = []

    for line in process.stdout:
        pretty_print_json_line(line)
        output.append(line)

    process.wait()

    return "".join(output)


def pretty_print_json_line(line: str) -> None:
    import json

    try:
        obj = json.loads(line)
        log_json_schema(obj)
        print(json.dumps(obj, indent=2), flush=True)
    except json.JSONDecodeError:
        print(line, end="", flush=True)


def log_json_schema(json_result: dict) -> None:
    path = Path(".claude/skills/claude-headless/output-schema/edit.log")
    if not path.exists():
        path.touch()
    data = path.read_text()
    data += f"{json.dumps(json_result, indent=2)}\n"
    path.write_text(data)


if __name__ == "__main__":
    result = run_claude_stream(
        "Can you edit prompt.md and write Hello World! using edit tool",
        tools=["Read, Edit"],
        allowed_tools=["Read, Edit"],
    )
