"""Headless Claude — runs a headless Claude session in a Hook.

Placement: Headless Claude Agent in a Hook.
Runs a headless Claude session.
"""

import sys
from pathlib import Path
import json
import subprocess
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_template(template_name: str) -> str:
    path = TEMPLATE_DIR / f"{template_name}.md"
    return path.read_text()


def run_claude(
    prompt: str,
    session_id: str | None = None,
    output_format: Literal["json", "stream-json"] | None = None,
    tools: list[str] = ["Read", "Grep", "Glob"],
    allowed_tools: list[str] | None = None,
    bare: bool = False,
) -> str | dict:
    tools_string = ",".join(tools)
    command = [
        "claude",
        *(["--bare"] if bare else []),
        prompt,
        "--tools",
        tools_string,
    ]
    if output_format:
        command.extend(["--output-format", output_format])
    if allowed_tools:
        command.extend(["--allowedTools", ",".join(allowed_tools)])
    if session_id:
        command.extend(["--resume", session_id])
    result = subprocess.run(command, capture_output=True, text=True)
    if output_format == "json":
        return json.loads(result.stdout)
    return result.stdout
